import os
import json
import random
import yt_dlp
import requests
from telebot import TeleBot, types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime

TOKEN = os.environ.get("TOKEN")
ADMIN_ID = 7983838654

bot = TeleBot(TOKEN)
DATA_FILE = "users.json"


# ---------- FILE ----------
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({}, f)


def load_users():
    with open(DATA_FILE, "r") as f:
        return json.load(f)


def save_users(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)


def gen_bot_id():
    return str(random.randint(1000000000, 9999999999))


# ---------- MENU ----------
def main_menu(chat_id):

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("💰 Balance", "🔗 Referral")
    kb.add("💸 Withdraw", "🆔 Get My ID")
    kb.add("Rate🌟")

    if chat_id == ADMIN_ID:
        kb.add("⚙ Admin Panel")

    bot.send_message(chat_id, "🏠 Main Menu", reply_markup=kb)


# ---------- START ----------
@bot.message_handler(commands=['start'])
def start(message):

    users = load_users()
    uid = str(message.from_user.id)

    ref = None
    if len(message.text.split()) > 1:
        ref = message.text.split()[1]

    if uid not in users:

        users[uid] = {
            "balance": 0,
            "withdrawn": 0,
            "referrals": 0,
            "bot_id": gen_bot_id(),
            "ref_code": str(uid),
            "banned": False
        }

        if ref and ref in users and ref != uid:
            users[ref]["balance"] += 0.5
            users[ref]["referrals"] += 1
            bot.send_message(ref, "🎉 You received $0.5 referral bonus")

    save_users(users)

    bot.send_message(
        message.chat.id,
        "👋 Welcome!\nSend video or TikTok photo link to download."
    )

    main_menu(message.chat.id)


# ---------- BALANCE ----------
@bot.message_handler(func=lambda m: m.text == "💰 Balance")
def balance(message):

    users = load_users()
    uid = str(message.from_user.id)

    bot.send_message(
        message.chat.id,
        f"💰 Balance: ${users[uid]['balance']}"
    )


# ---------- REFERRAL ----------
@bot.message_handler(func=lambda m: m.text == "🔗 Referral")
def referral(message):

    users = load_users()
    uid = str(message.from_user.id)

    link = f"https://t.me/{bot.get_me().username}?start={uid}"

    bot.send_message(
        message.chat.id,
        f"🔗 Your Link:\n{link}\n\n👥 Referrals: {users[uid]['referrals']}"
    )


# ---------- GET ID ----------
@bot.message_handler(func=lambda m: m.text == "🆔 Get My ID")
def get_id(message):

    users = load_users()
    uid = str(message.from_user.id)

    bot.send_message(
        message.chat.id,
        f"Your BOT ID: {users[uid]['bot_id']}"
    )


# ---------- WITHDRAW ----------
@bot.message_handler(func=lambda m: m.text == "💸 Withdraw")
def withdraw_menu(message):

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("USDT-BEP20")
    kb.add("❌ Cancel")

    bot.send_message(message.chat.id, "Select method", reply_markup=kb)


@bot.message_handler(func=lambda m: m.text == "USDT-BEP20")
def withdraw_amount(message):

    msg = bot.send_message(message.chat.id, "Enter amount (min $1)")
    bot.register_next_step_handler(msg, withdraw_amount_process)


def withdraw_amount_process(message):

    users = load_users()
    uid = str(message.from_user.id)

    try:
        amount = float(message.text)
    except:
        bot.send_message(message.chat.id, "Invalid amount")
        return

    if amount > users[uid]["balance"]:
        bot.send_message(message.chat.id, "Insufficient balance")
        return

    msg = bot.send_message(message.chat.id, "Enter wallet address")
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
        f"Withdrawal Request\nUser:{uid}\nAmount:${amount}\nAddress:{address}\nID:{wid}",
        reply_markup=kb
    )

    bot.send_message(message.chat.id, "Request sent (2‑12 hours)")
    main_menu(message.chat.id)


@bot.message_handler(func=lambda m: m.text == "❌ Cancel")
def cancel(message):
    main_menu(message.chat.id)


# ---------- CALLBACK ----------
@bot.callback_query_handler(func=lambda call: True)
def callbacks(call):

    users = load_users()
    data = call.data.split("_")

    if data[0] == "confirm":
        uid = data[1]
        amt = data[2]

        bot.send_message(uid, f"✅ Withdrawal ${amt} sent")

    if data[0] == "reject":
        uid = data[1]
        amt = float(data[2])

        users[uid]["balance"] += amt
        save_users(users)

        bot.send_message(uid, "❌ Withdrawal rejected")

    if data[0] == "ban":
        uid = data[1]
        users[uid]["banned"] = True
        save_users(users)
        bot.send_message(uid, "🚫 You are banned")


# ---------- ADMIN PANEL ----------
@bot.message_handler(func=lambda m: m.text == "⚙ Admin Panel")
def admin_panel(message):

    if message.from_user.id != ADMIN_ID:
        return

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("➕ Add Balance", "🎁 Random Gift")
    kb.add("🔓 Unban User", "⬅ Back")

    bot.send_message(message.chat.id, "Admin Panel", reply_markup=kb)


@bot.message_handler(func=lambda m: m.text == "➕ Add Balance")
def add_balance_start(message):

    msg = bot.send_message(message.chat.id, "Enter BOT ID")
    bot.register_next_step_handler(msg, add_balance_user)


def add_balance_user(message):

    users = load_users()
    bot_id = message.text

    for uid in users:
        if users[uid]["bot_id"] == bot_id:
            msg = bot.send_message(message.chat.id, "Enter amount")
            bot.register_next_step_handler(msg, add_balance_amount, uid)
            return

    bot.send_message(message.chat.id, "User not found")


def add_balance_amount(message, uid):

    users = load_users()

    amount = float(message.text)
    users[uid]["balance"] += amount
    save_users(users)

    bot.send_message(uid, f"🎁 Admin added ${amount}")
    bot.send_message(message.chat.id, "Done")


@bot.message_handler(func=lambda m: m.text == "🎁 Random Gift")
def random_gift(message):

    users = load_users()

    uid = random.choice(list(users.keys()))
    users[uid]["balance"] += 1
    save_users(users)

    bot.send_message(uid, "🎁 You received random $1 gift")
    bot.send_message(message.chat.id, "Gift sent")


@bot.message_handler(func=lambda m: m.text == "🔓 Unban User")
def unban_start(message):

    msg = bot.send_message(message.chat.id, "Enter BOT ID")
    bot.register_next_step_handler(msg, unban_user)


def unban_user(message):

    users = load_users()
    bot_id = message.text

    for uid in users:
        if users[uid]["bot_id"] == bot_id:
            users[uid]["banned"] = False
            save_users(users)
            bot.send_message(uid, "✅ You are unbanned")
            bot.send_message(message.chat.id, "Done")
            return

    bot.send_message(message.chat.id, "User not found")


# ---------- DOWNLOAD ----------
@bot.message_handler(func=lambda m: m.text.startswith("http"))
def download(message):

    url = message.text
    bot.send_message(message.chat.id, "Downloading...")

    try:

        if "tiktok.com" in url and "/photo/" in url:
            r = requests.get(url)
            with open("photo.jpg", "wb") as f:
                f.write(r.content)
            bot.send_photo(message.chat.id, open("photo.jpg", "rb"))
            os.remove("photo.jpg")
            return

        ydl_opts = {'format': 'best', 'outtmpl': 'video.mp4'}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        bot.send_video(message.chat.id, open("video.mp4", "rb"))
        os.remove("video.mp4")

    except Exception as e:
        bot.send_message(message.chat.id, str(e))


print("Bot Running")
bot.infinity_polling()
