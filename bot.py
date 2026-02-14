import os
import json
import random
from datetime import datetime, timedelta
from telebot import TeleBot, types
import yt_dlp

TOKEN = os.getenv("TOKEN")
ADMIN_ID = 7983838654
DATA_FILE = "users.json"

PREMIUM_PRICE = 15
PAY_ADDRESS = "0x98ffcb29a4fc182d461ebdba54648d8fe24597ac"

bot = TeleBot(TOKEN)

# ---------------- USERS FILE ----------------

if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({}, f)

def load_users():
    with open(DATA_FILE) as f:
        return json.load(f)

def save_users(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ---------------- MENU ----------------

def main_menu(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("💰 Balance", "🔗 Referral")
    markup.add("🎁 Random Bonus", "💸 Withdraw")
    markup.add("🎬 Video Editing")
    markup.add("👤 Profile")
    if str(chat_id) == str(ADMIN_ID):
        markup.add("⚙️ Admin Panel")
    bot.send_message(chat_id, "🏠 Main Menu", reply_markup=markup)

# ---------------- START ----------------

@bot.message_handler(commands=['start'])
def start(message):
    users = load_users()
    uid = str(message.from_user.id)

    if uid not in users:
        users[uid] = {
            "balance": 0,
            "points": 0,
            "premium": False,
            "awaiting_payment": False,
            "banned": False
        }
        save_users(users)

    main_menu(uid)

# ---------------- VIDEO EDITING ----------------

@bot.message_handler(func=lambda m: m.text == "🎬 Video Editing")
def premium_feature(message):
    users = load_users()
    uid = str(message.from_user.id)

    if users[uid]["premium"]:
        bot.send_message(uid, "✅ You are premium.\nSend video link.")
        return

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ PAID", callback_data="paid"))
    markup.add(types.InlineKeyboardButton("❌ CANCEL", callback_data="cancel"))

    users[uid]["awaiting_payment"] = True
    save_users(users)

    bot.send_message(uid,
f"""🎬 Video Editing Premium
💰 Price: ${PREMIUM_PRICE}

Send USDT to:
{PAY_ADDRESS}

After payment click PAID.""",
reply_markup=markup)

# ---------------- PAYMENT CALLBACK ----------------

@bot.callback_query_handler(func=lambda c: True)
def callback(call):
    users = load_users()
    uid = str(call.from_user.id)

    if call.data == "cancel":
        users[uid]["awaiting_payment"] = False
        save_users(users)
        bot.send_message(uid, "❌ Payment cancelled.")
        main_menu(uid)

    if call.data == "paid":
        if users[uid]["awaiting_payment"]:

            users[uid]["premium"] = True
            users[uid]["awaiting_payment"] = False
            save_users(users)

            bot.send_message(uid, "✅ Premium Activated! Send video link.")

            # ADMIN NOTIFICATION
            bot.send_message(ADMIN_ID,
f"""💎 NEW PREMIUM USER

👤 Telegram ID: {uid}
🎬 Video Editing Activated
💰 Payment: ${PREMIUM_PRICE}
""")

# ---------------- MEDIA DOWNLOADER ----------------

@bot.message_handler(func=lambda m: m.text and m.text.startswith("http"))
def download_media(message):
    users = load_users()
    uid = str(message.from_user.id)

    if not users[uid]["premium"]:
        bot.send_message(uid, "❌ Only Premium users can download.")
        return

    url = message.text
    bot.send_message(uid, "⏳ Downloading...")

    try:
        ydl_opts = {
            'format': 'best',
            'outtmpl': 'video.%(ext)s'
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

        with open(filename, "rb") as f:
            bot.send_video(uid, f)

        os.remove(filename)

    except Exception as e:
        bot.send_message(uid, f"❌ Download failed\n{e}")

# ---------------- RANDOM BONUS ----------------

@bot.message_handler(func=lambda m: m.text == "🎁 Random Bonus")
def bonus(message):
    users = load_users()
    uid = str(message.from_user.id)

    amount = round(random.uniform(0.01, 0.1), 2)
    users[uid]["balance"] += amount
    users[uid]["points"] += 1
    save_users(users)

    bot.send_message(uid, f"🎁 You got ${amount}")

# ---------------- WITHDRAW ----------------

@bot.message_handler(func=lambda m: m.text == "💸 Withdraw")
def withdraw(message):
    bot.send_message(message.chat.id, "Send amount to withdraw")

    bot.register_next_step_handler(message, withdraw_amount)

def withdraw_amount(message):
    users = load_users()
    uid = str(message.from_user.id)

    amount = float(message.text)

    if users[uid]["balance"] < amount:
        bot.send_message(uid, "❌ Not enough balance")
        return

    users[uid]["balance"] -= amount
    save_users(users)

    bot.send_message(uid, "✅ Withdrawal requested")

# ---------------- PROFILE ----------------

@bot.message_handler(func=lambda m: m.text == "👤 Profile")
def profile(message):
    users = load_users()
    uid = str(message.from_user.id)
    u = users[uid]

    bot.send_message(uid,
f"""
👤 ID: {uid}
💰 Balance: ${u['balance']}
⭐ Points: {u['points']}
💎 Premium: {u['premium']}
""")

# ---------------- ADMIN PANEL ----------------

@bot.message_handler(func=lambda m: m.text == "⚙️ Admin Panel")
def admin_panel(message):
    if str(message.from_user.id) != str(ADMIN_ID):
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📊 Stats", "📢 Broadcast")
    markup.add("🔙 Back")
    bot.send_message(message.chat.id, "Admin Panel", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "📊 Stats")
def stats(message):
    if str(message.from_user.id) != str(ADMIN_ID):
        return

    users = load_users()

    bot.send_message(message.chat.id,
f"""
👥 Users: {len(users)}
💎 Premium Users: {sum(1 for u in users.values() if u['premium'])}
""")

@bot.message_handler(func=lambda m: m.text == "📢 Broadcast")
def broadcast(message):
    if str(message.from_user.id) != str(ADMIN_ID):
        return

    bot.send_message(message.chat.id, "Send broadcast message")
    bot.register_next_step_handler(message, do_broadcast)

def do_broadcast(message):
    users = load_users()

    for uid in users:
        try:
            bot.send_message(uid, message.text)
        except:
            pass

    bot.send_message(ADMIN_ID, "✅ Broadcast sent")

# ---------------- RUN ----------------

print("Bot Running...")
bot.infinity_polling()
