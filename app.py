import logging
import os

from flask import Flask, render_template, request, url_for, redirect
from flask_dance.contrib.meetup import make_meetup_blueprint, meetup
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
app.secret_key = os.environ["FLASK_SECRET_KEY"]
app.wsgi_app = ProxyFix(
    app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1
)

blueprint = make_meetup_blueprint(
    key=os.environ["MEETUP_OAUTH_CLIENT_ID"],
    secret=os.environ["MEETUP_OAUTH_CLIENT_SECRET"],
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

    resp = meetup.post("/gql", data='{"query": "query { self { id name email } }"}')
    resp.raise_for_status()
    user_data = resp.json()["data"]["self"]

    if request.method == "POST":
        register_checkin(user_data, request.form)
        return redirect(url_for("thankyou"))
    else:
        return render_template("checkin.html")


@app.route("/thankyou")
def thankyou():
    return "Thank you!"


def register_checkin(user_data, form_data):
    print(user_data)
    print(form_data)
