import os
import json
import random
import requests
from functools import partial
from datetime import datetime
from telebot import TeleBot, types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import yt_dlp

# ---------- CONFIG ----------
TOKEN = os.environ.get("TOKEN")
if not TOKEN:
    raise ValueError("TOKEN not found")

ADMIN_ID = 7983838654
DATA_FILE = "users.json"

bot = TeleBot(TOKEN)

# ---------- FILE INIT ----------
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({}, f)

# ---------- USER FUNCTIONS ----------
def load_users():
    try:
        with open(DATA_FILE) as f:
            return json.load(f)
    except:
        return {}

def save_users(users):
    with open(DATA_FILE, "w") as f:
        json.dump(users, f, indent=4)

def generate_bot_id():
    return str(random.randint(1000000000, 9999999999))

def generate_ref():
    return str(random.randint(100000, 999999))

# ---------- MENU ----------
def main_menu(chat_id, is_admin=False):

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)

    kb.add("💰 Balance", "🔗 Referral")
    kb.add("💸 Withdraw", "🆔 Get My ID")

    if is_admin:
        kb.add("🛠 Admin Panel")

    bot.send_message(chat_id, "🏠 Main Menu", reply_markup=kb)

# ---------- START ----------
@bot.message_handler(commands=["start"])
def start(message):

    users = load_users()
    user_id = str(message.from_user.id)

    ref_code = None
    if " " in message.text:
        ref_code = message.text.split()[1]

    if user_id not in users:

        users[user_id] = {
            "balance": 0,
            "referrals": 0,
            "withdrawn": 0,
            "bot_id": generate_bot_id(),
            "ref_code": generate_ref(),
            "banned": False
        }

        # Referral reward
        if ref_code:
            for uid in users:
                if users[uid]["ref_code"] == ref_code:
                    users[uid]["balance"] += 0.5
                    users[uid]["referrals"] += 1

                    bot.send_message(
                        int(uid),
                        f"🎉 New referral joined\n💰 You earned $0.5"
                    )

    save_users(users)

    bot.send_message(
        message.chat.id,
        "👋 Welcome to Downloader & Earn Bot"
    )

    main_menu(message.chat.id, message.from_user.id == ADMIN_ID)

# ---------- ADMIN PANEL ----------
@bot.message_handler(func=lambda m: m.text == "🛠 Admin Panel")
def admin_panel(message):

    if message.from_user.id != ADMIN_ID:
        return

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("➕ Add Balance", "🎁 Random Gift")
    kb.add("🔓 Unban User", "🔙 Back")

    bot.send_message(message.chat.id, "⚙️ Admin Panel", reply_markup=kb)

# ---------- ADD BALANCE ----------
@bot.message_handler(func=lambda m: m.text == "➕ Add Balance")
def add_balance_start(message):

    if message.from_user.id != ADMIN_ID:
        return

    msg = bot.send_message(message.chat.id, "Enter Bot ID:")
    bot.register_next_step_handler(msg, add_balance_user)

def add_balance_user(message):
    users = load_users()

    for uid in users:
        if users[uid]["bot_id"] == message.text:
            msg = bot.send_message(message.chat.id, "Enter amount:")
            bot.register_next_step_handler(msg, add_balance_amount, uid)
            return

    bot.send_message(message.chat.id, "❌ User not found")

def add_balance_amount(message, uid):
    users = load_users()

    try:
        amount = float(message.text)
    except:
        return

    users[uid]["balance"] += amount
    save_users(users)

    bot.send_message(int(uid), f"💰 Admin added ${amount} to your balance")
    bot.send_message(message.chat.id, "✅ Balance added")

# ---------- RANDOM GIFT ----------
@bot.message_handler(func=lambda m: m.text == "🎁 Random Gift")
def random_gift(message):

    if message.from_user.id != ADMIN_ID:
        return

    msg = bot.send_message(message.chat.id, "Enter gift amount:")
    bot.register_next_step_handler(msg, process_random_gift)

def process_random_gift(message):

    users = load_users()

    try:
        amount = float(message.text)
    except:
        return

    uid = random.choice(list(users.keys()))

    users[uid]["balance"] += amount
    save_users(users)

    bot.send_message(int(uid), f"🎁 Random Gift Received\n💰 ${amount}")
    bot.send_message(message.chat.id, "✅ Gift Sent")

# ---------- BALANCE ----------
@bot.message_handler(func=lambda m: m.text == "💰 Balance")
def balance(message):

    users = load_users()
    uid = str(message.from_user.id)

    bot.send_message(
        message.chat.id,
        f"💰 Balance: ${users[uid]['balance']}"
    )

# ---------- GET ID ----------
@bot.message_handler(func=lambda m: m.text == "🆔 Get My ID")
def get_id(message):

    users = load_users()
    uid = str(message.from_user.id)

    bot.send_message(
        message.chat.id,
        f"🆔 Your Bot ID: {users[uid]['bot_id']}"
    )

# ---------- REFERRAL ----------
@bot.message_handler(func=lambda m: m.text == "🔗 Referral")
def referral(message):

    users = load_users()
    uid = str(message.from_user.id)

    code = users[uid]["ref_code"]

    link = f"https://t.me/{bot.get_me().username}?start={code}"

    bot.send_message(
        message.chat.id,
        f"🔗 Your Link:\n{link}\n\n👥 Referrals: {users[uid]['referrals']}"
    )

# ---------- WITHDRAW ----------
@bot.message_handler(func=lambda m: m.text == "💸 Withdraw")
def withdraw_start(message):

    users = load_users()
    uid = str(message.from_user.id)

    if users[uid]["banned"]:
        bot.send_message(message.chat.id, "🚫 You are banned")
        return

    msg = bot.send_message(message.chat.id, "Enter amount ($1 minimum):")
    bot.register_next_step_handler(msg, withdraw_amount)

def withdraw_amount(message):

    users = load_users()
    uid = str(message.from_user.id)

    try:
        amount = float(message.text)
    except:
        return

    if amount > users[uid]["balance"]:
        bot.send_message(message.chat.id, "❌ Insufficient balance")
        return

    msg = bot.send_message(message.chat.id, "Enter USDT‑BEP20 address:")
    bot.register_next_step_handler(msg, withdraw_address, amount)

def withdraw_address(message, amount):

    users = load_users()
    uid = str(message.from_user.id)
    address = message.text

    wid = random.randint(10000, 99999)

    users[uid]["balance"] -= amount
    users[uid]["withdrawn"] += amount
    save_users(users)

    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_{uid}_{amount}_{wid}"),
        InlineKeyboardButton("❌ Reject", callback_data=f"reject_{uid}_{amount}_{wid}"),
        InlineKeyboardButton("🚫 Ban", callback_data=f"ban_{uid}")
    )

    bot.send_message(
        ADMIN_ID,
        f"💸 Withdrawal Request\nUser:{uid}\nAmount:${amount}\nAddress:{address}\nID:{wid}",
        reply_markup=kb
    )

    bot.send_message(
        message.chat.id,
        "✅ Request Sent\n⏳ It may take 2‑12 hours"
    )

# ---------- CALLBACK ----------
@bot.callback_query_handler(func=lambda c: True)
def callbacks(call):

    data = call.data.split("_")
    users = load_users()

    if data[0] == "confirm":

        uid = data[1]
        amount = data[2]

        bot.send_message(uid, f"✅ Withdrawal Confirmed\n💰 ${amount}")

    if data[0] == "reject":

        uid = data[1]
        amount = float(data[2])

        users[uid]["balance"] += amount
        save_users(users)

        bot.send_message(uid, "❌ Withdrawal Rejected")

    if data[0] == "ban":

        uid = data[1]
        users[uid]["banned"] = True
        save_users(users)

        bot.send_message(uid, "🚫 You are banned")

    bot.answer_callback_query(call.id)

# ---------- BACK ----------
@bot.message_handler(func=lambda m: m.text == "🔙 Back")
def back(message):
    main_menu(message.chat.id, message.from_user.id == ADMIN_ID)

# ---------- DOWNLOADER ----------
@bot.message_handler(func=lambda m: m.text.startswith("http"))
def downloader(message):

    url = message.text
    chat = message.chat.id

    bot.send_message(chat, "⏳ Downloading...")

    try:

        # TikTok photo
        if "tiktok.com" in url and "/photo/" in url:
            r = requests.get(url)
            with open("photo.jpg", "wb") as f:
                f.write(r.content)

            bot.send_photo(chat, open("photo.jpg", "rb"))
            os.remove("photo.jpg")
            return

        # Video download
        ydl_opts = {
            "format": "best",
            "outtmpl": "video.mp4"
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        bot.send_video(chat, open("video.mp4", "rb"))
        os.remove("video.mp4")

    except Exception as e:
        bot.send_message(chat, f"❌ Download Failed\n{e}")

# ---------- RUN ----------
print("BOT RUNNING")
bot.infinity_polling()
