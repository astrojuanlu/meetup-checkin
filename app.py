import os

from flask import Flask, render_template, request, url_for, redirect
from flask_dance.contrib.meetup import make_meetup_blueprint, meetup

app = Flask(__name__)
app.secret_key = os.environ["FLASK_SECRET_KEY"]

blueprint = make_meetup_blueprint()
app.register_blueprint(blueprint, url_prefix="/login")


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
    resp = meetup.get("/members/self")
    assert resp.ok
    print(resp.json())

    if request.method == "POST":
        print(request.form)
        return redirect(url_for("thankyou"))
    else:
        return render_template("checkin.html")


@app.route("/thankyou")
def thankyou():
    return "Thank you!"
