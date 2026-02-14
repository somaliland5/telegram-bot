import os
from flask import Flask, render_template, request, redirect, url_for, session
import json
import threading
from bot import bot, load_users, save_users

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "fallback_secret")

ADMIN_IDS = ["7983838654"]

DATA_FILE = "../users.json"

# ----------------- ROUTES -----------------

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
                           total_banned=sum(1 for u in users.values() if u.get('banned',False))
                           )

@app.route('/users')
def users_page():
    if 'admin' not in session:
        return redirect(url_for('login'))
    users = load_users()
    return render_template('index.html', users=users)

@app.route('/broadcast', methods=['GET','POST'])
def broadcast():
    if 'admin' not in session:
        return redirect(url_for('login'))
    if request.method == "POST":
        message = request.form.get("message")
        media_url = request.form.get("media_url")
        # Broadcast via bot
        users = load_users()
        for uid in users:
            try:
                if media_url:
                    bot.send_message(uid, message + f"\n{media_url}")
                else:
                    bot.send_message(uid, message)
            except:
                pass
        return f"Broadcast sent to {len(users)} users"
    return render_template('broadcast.html')

@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect(url_for('login'))

# ----------------- RUN BOT IN THREAD -----------------
def run_bot():
    print("Bot Running...")
    bot.infinity_polling()

if __name__=="__main__":
    threading.Thread(target=run_bot).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",8080)))
