import os
import json
from flask import Flask, render_template, request, redirect, session
from telebot import TeleBot

TOKEN = os.getenv("TOKEN")
bot = TeleBot(TOKEN)

app = Flask(__name__)
app.secret_key = "adminsecret"

ADMIN_ID = "7983838654"
DATA_FILE = "users.json"


def load_users():
    with open(DATA_FILE) as f:
        return json.load(f)


@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form["admin"] == ADMIN_ID:
            session["admin"] = ADMIN_ID
            return redirect("/dashboard")
    return render_template("login.html")


@app.route("/dashboard")
def dashboard():
    if "admin" not in session:
        return redirect("/")

    users = load_users()

    return render_template(
        "dashboard.html",
        total_users=len(users),
        total_balance=sum(u["balance"] for u in users.values()),
        total_withdraw=sum(u["withdrawn"] for u in users.values())
    )


@app.route("/broadcast", methods=["GET","POST"])
def broadcast():
    if "admin" not in session:
        return redirect("/")

    if request.method == "POST":
        msg = request.form["msg"]

        users = load_users()
        for uid in users:
            try:
                bot.send_message(uid, msg)
            except:
                pass

        return "Message Sent"

    return render_template("broadcast.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
