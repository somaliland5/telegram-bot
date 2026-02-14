import os
from flask import Flask, render_template, request, redirect, url_for, session
import json

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "fallback_secret")

ADMIN_IDS = ["7983838654"]  # Telegram ID-gaaga
DATA_FILE = "../users.json"

def load_users():
    with open(DATA_FILE) as f:
        return json.load(f)

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == "POST":
        telegram_id = request.form.get("telegram_id")
        if telegram_id in ADMIN_IDS:
            session['admin'] = telegram_id
            return redirect(url_for('index'))
        return "Access Denied"
    return render_template('login.html')

@app.route('/')
def index():
    if 'admin' not in session:
        return redirect(url_for('login'))
    users = load_users()
    return render_template('index.html',
                           total_users=len(users),
                           total_balance=sum(u.get('balance',0) for u in users.values()),
                           total_withdrawal=sum(u.get('withdrawn',0) for u in users.values()),
                           total_banned=sum(1 for u in users.values() if u.get('banned',False)))

@app.route('/users')
def users_page():
    if 'admin' not in session:
        return redirect(url_for('login'))
    users = load_users()
    return render_template('users.html', users=users)

@app.route('/broadcast', methods=['GET','POST'])
def broadcast():
    if 'admin' not in session:
        return redirect(url_for('login'))
    if request.method == "POST":
        message = request.form.get("message")
        media_url = request.form.get("media_url")
        return f"Broadcast sent: {message} | {media_url}"
    return render_template('broadcast.html')

@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect(url_for('login'))

if __name__=="__main__":
    app.run(debug=True)
