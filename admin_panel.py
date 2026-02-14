from flask import Flask, render_template_string, request, redirect
import json
import os

DATA_FILE = "users.json"
ADMIN_PASSWORD = "5060708090"  # Change this for security

app = Flask(__name__)

def load_users():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w") as f:
            json.dump({}, f)
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(DATA_FILE, "w") as f:
        json.dump(users, f, indent=4)

@app.route("/", methods=["GET", "POST"])
def dashboard():
    password = request.args.get("pass","")
    if password != ADMIN_PASSWORD:
        return "❌ Wrong password! Use ?pass=YOUR_PASSWORD"

    users = load_users()
    return render_template_string("""
    <h1>Admin Dashboard</h1>
    <h2>Users: {{users|length}}</h2>
    <table border="1">
        <tr><th>Telegram ID</th><th>Bot ID</th><th>Balance</th><th>Withdrawn</th></tr>
        {% for uid, info in users.items() %}
        <tr>
            <td>{{uid}}</td>
            <td>{{info.ref_id}}</td>
            <td>{{info.balance}}</td>
            <td>{{info.withdrawn}}</td>
        </tr>
        {% endfor %}
    </table>
    """, users=users)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
