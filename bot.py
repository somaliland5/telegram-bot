import os
import json
import random
import requests
from functools import partial
from datetime import datetime
from telebot import TeleBot, types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import yt_dlp

# ===== CONFIG =====
TOKEN = os.environ.get("TOKEN")
ADMIN_ID = 7983838654

if not TOKEN:
    raise ValueError("TOKEN not found")

bot = TeleBot(TOKEN)
DATA_FILE = "users.json"


# ===== DATABASE =====
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({}, f)


def load_users():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return {}


def save_users(users):
    with open(DATA_FILE, "w") as f:
        json.dump(users, f, indent=4)


def generate_ref():
    return str(random.randint(1000000, 9999999))


def check_ban(uid, chat_id):
    users = load_users()
    if users.get(uid, {}).get("ban"):
        bot.send_message(chat_id, "❌ You are banned from using this bot.")
        return True
    return False


# ===== MENU =====
def main_menu(chat_id):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("💰 Balance", "🔗 Referral Link")
    kb.row("💸 Withdraw", "🆔 Get My ID")
    bot.send_message(chat_id, "📋 Main Menu", reply_markup=kb)


# ===== START =====
@bot.message_handler(commands=["start"])
def start(message):
    users = load_users()
    uid = str(message.from_user.id)

    ref = None
    if message.text.startswith("/start "):
        ref = message.text.split()[1]

    if uid not in users:
        users[uid] = {
            "balance": 0,
            "referrals": 0,
            "withdrawn": 0,
            "ref_id": generate_ref(),
            "ban": False
        }

        # Referral reward
        if ref:
            for u, d in users.items():
                if d["ref_id"] == ref:
                    users[u]["balance"] += 0.5
                    users[u]["referrals"] += 1
                    bot.send_message(u, "🎉 You earned $0.5 referral bonus!")

    save_users(users)
    main_menu(message.chat.id)


# ===== ADMIN ADD BALANCE =====
@bot.message_handler(commands=["addbalance"])
def add_balance(message):
    if message.from_user.id != ADMIN_ID:
        return

    try:
        _, uid, amount = message.text.split()
        amount = float(amount)
    except:
        bot.send_message(message.chat.id, "Usage: /addbalance USERID AMOUNT")
        return

    users = load_users()

    if uid not in users:
        bot.send_message(message.chat.id, "User not found")
        return

    users[uid]["balance"] += amount
    save_users(users)

    bot.send_message(uid, f"💰 Admin added ${amount} to your balance")


# ===== BAN / UNBAN =====
@bot.message_handler(commands=["ban"])
def ban_user(message):
    if message.from_user.id != ADMIN_ID:
        return

    uid = message.text.split()[1]
    users = load_users()

    if uid in users:
        users[uid]["ban"] = True
        save_users(users)
        bot.send_message(message.chat.id, "User banned")


@bot.message_handler(commands=["unban"])
def unban_user(message):
    if message.from_user.id != ADMIN_ID:
        return

    uid = message.text.split()[1]
    users = load_users()

    if uid in users:
        users[uid]["ban"] = False
        save_users(users)
        bot.send_message(message.chat.id, "User unbanned")


# ===== MAIN HANDLER =====
@bot.message_handler(func=lambda m: True)
def handler(message):

    if message.text.startswith("/"):
        return

    uid = str(message.from_user.id)
    users = load_users()

    if check_ban(uid, message.chat.id):
        return

    # Balance
    if message.text == "💰 Balance":
        bot.send_message(message.chat.id, f"💰 Balance: ${users[uid]['balance']}")

    # Referral
    elif message.text == "🔗 Referral Link":
        link = f"https://t.me/{bot.get_me().username}?start={users[uid]['ref_id']}"
        bot.send_message(
            message.chat.id,
            f"🔗 Your Link:\n{link}\n\n👥 Referrals: {users[uid]['referrals']}"
        )

    # Withdraw
    elif message.text == "💸 Withdraw":
        msg = bot.send_message(message.chat.id, "Enter amount (Min $1)")
        bot.register_next_step_handler(msg, withdraw_amount)

    # Get ID
    elif message.text == "🆔 Get My ID":
        bot.send_message(
            message.chat.id,
            f"🆔 YOUR ID\n\nTelegram ID: {message.from_user.id}"
        )

    # Downloader
    elif message.text.startswith("http"):
        download_media(message)


# ===== WITHDRAW =====
def withdraw_amount(message):
    uid = str(message.from_user.id)
    users = load_users()

    try:
        amount = float(message.text)
    except:
        return

    if users[uid]["balance"] < amount or amount < 1:
        bot.send_message(message.chat.id, "❌ Invalid amount")
        return

    msg = bot.send_message(message.chat.id, "Send wallet address")
    bot.register_next_step_handler(msg, process_withdraw, amount)


def process_withdraw(message, amount):
    uid = str(message.from_user.id)
    users = load_users()

    address = message.text
    wid = random.randint(10000, 99999)

    users[uid]["balance"] -= amount
    users[uid]["withdrawn"] += amount
    save_users(users)

    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_{uid}_{amount}_{wid}"),
        InlineKeyboardButton("❌ Reject", callback_data=f"reject_{uid}_{amount}_{wid}")
    )
    kb.row(
        InlineKeyboardButton("🚫 Ban User", callback_data=f"ban_{uid}")
    )

    bot.send_message(
        ADMIN_ID,
        f"""💸 Withdrawal Request

User: {uid}
Amount: ${amount}
Address: {address}
ID: {wid}""",
        reply_markup=kb
    )

    bot.send_message(message.chat.id, "⌛ It may take 2-12 hours to confirm.")


# ===== CALLBACK =====
@bot.callback_query_handler(func=lambda call: True)
def callbacks(call):

    data = call.data.split("_")
    users = load_users()

    if data[0] == "confirm":
        uid, amount, wid = data[1], data[2], data[3]
        bot.send_message(uid, f"✅ Payment Sent\nID: {wid}\nAmount: ${amount}")

    elif data[0] == "reject":
        uid, amount = data[1], float(data[2])
        users[uid]["balance"] += amount
        save_users(users)
        bot.send_message(uid, "❌ Withdrawal rejected. Balance refunded.")

    elif data[0] == "ban":
        uid = data[1]
        users[uid]["ban"] = True
        save_users(users)
        bot.send_message(uid, "🚫 You have been banned.")

    bot.answer_callback_query(call.id)


# ===== DOWNLOADER =====
def download_media(message):
    bot.send_message(message.chat.id, "Downloading...")

    url = message.text

    # Expand short links
    try:
        url = requests.get(url, allow_redirects=True).url
    except:
        pass

    # TikTok API
    try:
        api = f"https://www.tikwm.com/api/?url={url}"
        res = requests.get(api).json()

        if res["code"] == 0:

            data = res["data"]

            if data.get("images"):
                for img in data["images"]:
                    bot.send_photo(message.chat.id, requests.get(img).content)
                return

            if data.get("play"):
                bot.send_video(message.chat.id, requests.get(data["play"]).content)
                return
    except:
        pass

    # yt-dlp fallback
    try:
        ydl_opts = {"outtmpl": "media.%(ext)s", "format": "best"}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            ext = info["ext"]

        file = f"media.{ext}"

        if ext in ["mp4", "webm"]:
            bot.send_video(message.chat.id, open(file, "rb"))
        else:
            bot.send_photo(message.chat.id, open(file, "rb"))

        os.remove(file)

    except:
        bot.send_message(message.chat.id, "❌ Download failed")


# ===== RUN =====
print("Bot Running...")
bot.infinity_polling()
