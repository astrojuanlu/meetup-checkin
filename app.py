from flask import Flask, render_template, request, url_for, redirect

app = Flask(__name__)


@app.route("/")
def home():
    return "<h1>PyData Madrid Check-in</h1>"


@app.route("/health")
def health():
    return {"status": "ok"}


@app.route("/checkin", methods=["GET", "POST"])
def checkin():
    if request.method == "POST":
        print(request.form)
        return redirect(url_for("thankyou"))
    else:
        return render_template("checkin.html")


@app.route("/thankyou")
def thankyou():
    return "Thank you!"
