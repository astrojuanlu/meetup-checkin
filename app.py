import logging
import os

from flask import Flask, redirect, render_template, request, url_for
from flask_dance.contrib.meetup import make_meetup_blueprint, meetup
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
app.secret_key = os.environ["FLASK_SECRET_KEY"]
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ["DATABASE_URL"]
app.config["MEETUP_EVENT_ID"] = os.environ["MEETUP_EVENT_ID"]

db = SQLAlchemy(app)

blueprint = make_meetup_blueprint(
    key=os.environ["MEETUP_OAUTH_CLIENT_ID"],
    secret=os.environ["MEETUP_OAUTH_CLIENT_SECRET"],
    redirect_to="checkin",
)
app.register_blueprint(blueprint, url_prefix="/login")

logging.basicConfig(level=logging.DEBUG)


@app.route("/")
def home():
    return "<h1>PyData Madrid Check-in</h1>"


@app.route("/health")
def health():
    return {"status": "ok"}


@app.route("/checkin", methods=["GET", "POST"])
def checkin():
    if not meetup.authorized:
        return redirect(url_for("meetup.login"))

    if request.method == "POST":
        try:
            resp = meetup.post(
                "/gql", data='{"query": "query { self { id name email } }"}'
            )
            resp.raise_for_status()
            user_data = resp.json()["data"]["self"]

            register_checkin(
                int(app.config["MEETUP_EVENT_ID"]), user_data, request.form
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


def register_checkin(event_id, user_data, form_data):
    logging.debug(user_data)
    logging.debug(form_data)

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
                **{
                    "meetup_id": int(user_data["id"]),
                    "event_id": event_id,
                    "name": user_data["name"],
                    "email": user_data["email"],
                    "photographs_consent": bool(
                        form_data.get("photographs_consent", False)
                    ),
                    "email_consent": bool(form_data.get("email_consent", False)),
                },
            )
