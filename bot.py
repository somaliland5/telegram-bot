import os
import json
import random
import time
from datetime import datetime
from telebot import TeleBot, types
import yt_dlp

TOKEN = os.getenv("TOKEN")
ADMIN_ID = 7983838654

bot = TeleBot(TOKEN)
DATA_FILE = "users.json"

# ---------------- FILE ----------------

if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({}, f)

def load_users():
    with open(DATA_FILE) as f:
        return json.load(f)

def save_users(users):
    with open(DATA_FILE, "w") as f:
        json.dump(users, f, indent=4)

# ---------------- MENU ----------------

def main_menu(chat_id, admin=False):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)

    kb.add("💰 Balance", "🔗 Referral")
    kb.add("💸 Withdraw", "🎁 Random Bonus")
    kb.add("🆔 Get My ID", "📞 Customer")

    if admin:
        kb.add("⚙️ Admin Panel")

    bot.send_message(chat_id, "Main Menu", reply_markup=kb)

# ---------------- START ----------------

@bot.message_handler(commands=['start'])
def start(message):

    users = load_users()
    uid = str(message.from_user.id)

    ref = None
    if " " in message.text:
        ref = message.text.split()[1]

    if uid not in users:
        users[uid] = {
            "balance": 0,
            "points": 0,
            "referrals": 0,
            "bot_id": str(random.randint(1000000000, 9999999999)),
            "last_bonus": 0,
            "banned": False
        }

        # referral reward
        if ref and ref in users and ref != uid:
            users[ref]["balance"] += 0.5
            users[ref]["points"] += 5
            users[ref]["referrals"] += 1

            bot.send_message(ref,
                             f"🎉 New Referral!\nYou earned $0.5 + 5 points")

    save_users(users)

    bot.send_message(message.chat.id,
                     "👋 Welcome to Download & Reward Bot")

    main_menu(message.chat.id,
              message.from_user.id == ADMIN_ID)

# ---------------- BALANCE ----------------

@bot.message_handler(func=lambda m: m.text == "💰 Balance")
def balance(m):
    users = load_users()
    u = users[str(m.from_user.id)]

    bot.send_message(m.chat.id,
                     f"💰 Balance: ${u['balance']}\n⭐ Points: {u['points']}")

# ---------------- REFERRAL ----------------

@bot.message_handler(func=lambda m: m.text == "🔗 Referral")
def referral(m):

    bot_username = bot.get_me().username
    uid = str(m.from_user.id)

    link = f"https://t.me/{bot_username}?start={uid}"

    users = load_users()

    bot.send_message(m.chat.id,
                     f"🔗 Your Referral Link:\n{link}\n\n👥 {users[uid]['referrals']} referrals")

# ---------------- RANDOM BONUS ----------------

@bot.message_handler(func=lambda m: m.text == "🎁 Random Bonus")
def bonus(m):

    users = load_users()
    uid = str(m.from_user.id)

    now = time.time()

    if now - users[uid]["last_bonus"] < 43200:
        bot.send_message(m.chat.id,
                         "❌ You can claim bonus every 12 hours")
        return

    amount = round(random.uniform(0.01, 0.1), 2)

    users[uid]["balance"] += amount
    users[uid]["last_bonus"] = now

    save_users(users)

    bot.send_message(m.chat.id,
                     f"🎁 Bonus Received: ${amount}")

# ---------------- GET ID ----------------

@bot.message_handler(func=lambda m: m.text == "🆔 Get My ID")
def get_id(m):

    users = load_users()
    u = users[str(m.from_user.id)]

    bot.send_message(m.chat.id,
                     f"Telegram ID: {m.from_user.id}\nBOT ID: {u['bot_id']}")

# ---------------- CUSTOMER ----------------

@bot.message_handler(func=lambda m: m.text == "📞 Customer")
def customer(m):
    bot.send_message(m.chat.id, "Contact: @scholes1")

# ---------------- WITHDRAW ----------------

@bot.message_handler(func=lambda m: m.text == "💸 Withdraw")
def withdraw_menu(m):

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("USDT-BEP20")
    kb.add("Cancel")

    bot.send_message(m.chat.id, "Choose method", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == "Cancel")
def cancel(m):
    main_menu(m.chat.id, m.from_user.id == ADMIN_ID)

@bot.message_handler(func=lambda m: m.text == "USDT-BEP20")
def ask_amount(m):

    msg = bot.send_message(m.chat.id, "Enter amount")
    bot.register_next_step_handler(msg, process_amount)

def process_amount(m):

    users = load_users()
    uid = str(m.from_user.id)

    try:
        amount = float(m.text)
    except:
        return bot.send_message(m.chat.id, "Invalid number")

    if amount > users[uid]["balance"]:
        return bot.send_message(m.chat.id, "❌ Insufficient balance")

    msg = bot.send_message(m.chat.id,
                           "Enter USDT address (start with 0x)")
    bot.register_next_step_handler(msg,
                                   process_address,
                                   amount)

def process_address(m, amount):

    if not m.text.startswith("0x"):
        return bot.send_message(m.chat.id, "❌ Invalid address")

    users = load_users()
    uid = str(m.from_user.id)

    users[uid]["balance"] -= amount
    users[uid]["points"] += 10

    save_users(users)

    wid = random.randint(10000, 99999)

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("CONFIRM",
                                      callback_data=f"c_{uid}_{amount}_{wid}"))
    kb.add(types.InlineKeyboardButton("REJECT",
                                      callback_data=f"r_{uid}_{amount}_{wid}"))
    kb.add(types.InlineKeyboardButton("BAN",
                                      callback_data=f"b_{uid}"))

    bot.send_message(ADMIN_ID,
                     f"Withdrawal Request\nUser: {uid}\nAmount: {amount}\nID: {wid}\nAddress: {m.text}",
                     reply_markup=kb)

    bot.send_message(m.chat.id,
                     "✅ Request sent. 2‑12 hours processing.")

# ---------------- CALLBACK ----------------

@bot.callback_query_handler(func=lambda call: True)
def callbacks(call):

    users = load_users()
    data = call.data.split("_")

    if data[0] == "c":
        uid, amount, wid = data[1], data[2], data[3]

        bot.send_message(uid,
                         f"💸 Payment Sent\nAmount: ${amount}\nID: {wid}")

    if data[0] == "r":
        uid, amount, wid = data[1], float(data[2]), data[3]

        users[uid]["balance"] += amount
        save_users(users)

        bot.send_message(uid, "❌ Withdrawal rejected")

    if data[0] == "b":
        users[data[1]]["banned"] = True
        save_users(users)

# ---------------- ADMIN PANEL ----------------

@bot.message_handler(func=lambda m: m.text == "⚙️ Admin Panel")
def admin_panel(m):

    if m.from_user.id != ADMIN_ID:
        return

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("➕ Add Balance", "🎁 Random Gift")
    kb.add("🚫 Ban", "✅ Unban")
    kb.add("📊 Stats", "🔙 Back")

    bot.send_message(m.chat.id, "Admin Panel", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == "🔙 Back")
def back_admin(m):
    main_menu(m.chat.id, True)

# ----- ADD BALANCE -----

@bot.message_handler(func=lambda m: m.text == "➕ Add Balance")
def addbal(m):
    msg = bot.send_message(m.chat.id, "Send BOT_ID amount")
    bot.register_next_step_handler(msg, do_addbal)

def do_addbal(m):
    users = load_users()
    botid, amount = m.text.split()
    amount = float(amount)

    for uid in users:
        if users[uid]["bot_id"] == botid:
            users[uid]["balance"] += amount
            bot.send_message(uid, f"Admin added ${amount}")

    save_users(users)

# ----- RANDOM GIFT -----

@bot.message_handler(func=lambda m: m.text == "🎁 Random Gift")
def rgift(m):

    users = load_users()
    uid = random.choice(list(users.keys()))

    amount = round(random.uniform(0.1, 1), 2)
    users[uid]["balance"] += amount

    save_users(users)

    bot.send_message(uid, f"🎁 You got random gift ${amount}")

# ----- BAN -----

@bot.message_handler(func=lambda m: m.text == "🚫 Ban")
def ban(m):
    msg = bot.send_message(m.chat.id, "Send BOT_ID")
    bot.register_next_step_handler(msg, do_ban)

def do_ban(m):
    users = load_users()

    for uid in users:
        if users[uid]["bot_id"] == m.text:
            users[uid]["banned"] = True

    save_users(users)

# ----- UNBAN -----

@bot.message_handler(func=lambda m: m.text == "✅ Unban")
def unban(m):
    msg = bot.send_message(m.chat.id, "Send BOT_ID")
    bot.register_next_step_handler(msg, do_unban)

def do_unban(m):
    users = load_users()

    for uid in users:
        if users[uid]["bot_id"] == m.text:
            users[uid]["banned"] = False

    save_users(users)

# ----- STATS -----

@bot.message_handler(func=lambda m: m.text == "📊 Stats")
def stats(m):

    users = load_users()

    total = len(users)
    bal = sum(u["balance"] for u in users.values())

    bot.send_message(m.chat.id,
                     f"Users: {total}\nTotal Balance: ${bal}")

# ---------------- DOWNLOAD ----------------

@bot.message_handler(func=lambda m: m.text.startswith("http"))
def download(m):

    try:
        bot.send_message(m.chat.id, "Downloading...")

        ydl_opts = {
            "outtmpl": "media.%(ext)s",
            "format": "best"
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(m.text, download=True)

        file = None
        for f in os.listdir():
            if f.startswith("media"):
                file = f

        if file.endswith(("jpg", "png", "jpeg", "webp")):
            bot.send_photo(m.chat.id, open(file, "rb"))
        else:
            bot.send_video(m.chat.id, open(file, "rb"))

        os.remove(file)

    except Exception as e:
        bot.send_message(m.chat.id, f"❌ Download failed\n{e}")

# ---------------- RUN ----------------

print("BOT RUNNING...")
bot.infinity_polling()
