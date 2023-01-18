from __future__ import annotations

import datetime as dt
import json
import logging
import os
import typing as t

from flask import Flask, redirect, render_template, request, url_for
from flask_dance.contrib.meetup import make_meetup_blueprint, meetup
from flask_sqlalchemy import SQLAlchemy
from pyairtable import Table
from sqlalchemy import text
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
app.secret_key = os.environ["FLASK_SECRET_KEY"]
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ["DATABASE_URL"]
app.config["MEETUP_EVENT_ID"] = os.environ["MEETUP_EVENT_ID"]

db = SQLAlchemy(app)

meetup_bp = make_meetup_blueprint(
    key=os.environ["MEETUP_OAUTH_CLIENT_ID"],
    secret=os.environ["MEETUP_OAUTH_CLIENT_SECRET"],
    redirect_to="checkin",
)
app.register_blueprint(meetup_bp, url_prefix="/login")

AIRTABLE_API_KEY = os.environ["AIRTABLE_API_KEY"]
AIRTABLE_BASE = os.environ["AIRTABLE_BASE"]
AIRTABLE_RSVPS_TABLE = os.environ["AIRTABLE_RSVPS_TABLE"]
AIRTABLE_CHECKINS_TABLE = os.environ["AIRTABLE_CHECKINS_TABLE"]

MEETUP_ADMIN_IDS = {
    int(meetup_id) for meetup_id in os.environ["MEETUP_ADMIN_IDS"].split(",")
}

logging.basicConfig(level=logging.DEBUG)


def fetch_all_tickets(event_id: int) -> list[dict[str, t.Any]]:
    event_rsvps_query = """
query($eventId: ID!, $rsvpsQuery: TicketsConnectionInput) {
  event(id: $eventId) {
    id
    title
    dateTime
    waitlistMode
    status
    maxTickets
    going
    waiting
    tickets(input: $rsvpsQuery) {
      count
      yesCount
      noCount
      waitlistCount
      pageInfo {
        endCursor
        hasNextPage
      }
      edges {
        node {
          id
          user {
            name
          }
          createdAt
          updatedAt
          status
          isFirstEvent
          answer {
            text
          }
        }
      }
    }
  }
}
"""
    all_tickets = []
    end_cursor = None
    while True:
        resp = meetup.post(
            "/gql",
            data=json.dumps(
                {
                    "variables": {
                        "eventId": event_id,
                        "rsvpsQuery": {
                            "after": end_cursor,
                        }
                        if end_cursor
                        else {},
                    },
                    "query": event_rsvps_query,
                }
            ),
        )
        logging.debug(resp.json())
        resp.raise_for_status()

        tickets_info = resp.json()["data"]["event"]["tickets"]
        all_tickets.extend([t["node"] for t in tickets_info["edges"]])

        if tickets_info["pageInfo"]["hasNextPage"]:
            end_cursor = tickets_info["pageInfo"]["endCursor"]
        else:
            break

    return all_tickets


def do_save_rsvps(event_id: int, base_id: str, table_name: str) -> None:
    all_tickets = fetch_all_tickets(event_id)

    records = [
        {
            "meetup_id": int(ticket["id"]),
            "name": ticket["user"]["name"],
            "event_id": event_id,
            "waiting_list": False,  # No waiting list members are returned!
            "rsvped_on": dt.datetime.strptime(
                ticket["updatedAt"], "%Y-%m-%dT%H:%M:%S%z"
            )
            .astimezone(dt.timezone.utc)
            .strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        }
        for ticket in all_tickets
    ]
    logging.info("RECORDS: %s", records)

    table = Table(AIRTABLE_API_KEY, base_id, table_name)
    table.batch_create(records)


@app.route("/save_rsvps")
@meetup_bp.session.authorization_required
def save_rsvps():
    try:
        resp = meetup.post(
            "/gql", data='{"query": "query { self { id email isLeader } }"}'
        )
        resp.raise_for_status()
        user_data = resp.json()["data"]["self"]

        logging.info(user_data)
        logging.info(MEETUP_ADMIN_IDS)

        event_id = int(request.args["event_id"])
        if user_data["isLeader"] and int(user_data["id"]) in MEETUP_ADMIN_IDS:
            do_save_rsvps(event_id, AIRTABLE_BASE, AIRTABLE_RSVPS_TABLE)
            return "Saved", 201
        else:
            return "Unauthorized", 401
    except Exception:
        logging.exception("Error while registering checkin")
        return "There was an error, please try again", 500


@app.route("/")
def home():
    return "<h1>PyData Madrid Check-in</h1>"


@app.route("/health")
def health():
    return {"status": "ok"}


@app.route("/checkin", methods=["GET", "POST"])
@meetup_bp.session.authorization_required
def checkin():
    if request.method == "POST":
        try:
            resp = meetup.post(
                "/gql", data='{"query": "query { self { id name email } }"}'
            )
            resp.raise_for_status()
            user_data = resp.json()["data"]["self"]
            assert user_data is not None

            do_register_checkin(
                int(app.config["MEETUP_EVENT_ID"]),
                user_data,
                request.form,
                AIRTABLE_BASE,
                AIRTABLE_CHECKINS_TABLE,
            )
            return redirect(url_for("thankyou"))
        except Exception:
            logging.exception("Error while registering checkin")
            return "There was an error, please try again", 500
    else:
        return render_template("checkin.html")


@app.route("/thankyou")
def thankyou():
    return "Thank you!"


def do_register_checkin(event_id, user_data, form_data, base_id: str, table_name: str):
    logging.debug(user_data)
    logging.debug(form_data)

    record = {
        "meetup_id": int(user_data["id"]),
        "event_id": event_id,
        "name": user_data["name"],
        "email": user_data["email"],
        "photographs_consent": bool(form_data.get("photographs_consent", False)),
        "email_consent": bool(form_data.get("email_consent", False)),
        "date_checkin": dt.datetime.now(dt.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%S.%fZ"
        ),
    }

    with db.engine.connect() as connection:
        with connection.begin():
            connection.execute(
                text(
                    """INSERT INTO
checkins (meetup_id, event_id, name, email, photographs_consent, email_consent)
VALUES
(:meetup_id, :event_id, :name, :email, :photographs_consent, :email_consent);
"""
                ),
                **record,
            )

    table = Table(AIRTABLE_API_KEY, base_id, table_name)
    table.create(record)
