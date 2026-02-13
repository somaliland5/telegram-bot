import os
import json
import random
import requests
from functools import partial
from datetime import datetime
from telebot import TeleBot, types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import yt_dlp

# -------- CONFIG --------
TOKEN = os.environ.get("TOKEN")
ADMIN_ID = 7983838654

if not TOKEN:
    raise ValueError("TOKEN not found")

bot = TeleBot(TOKEN)
DATA_FILE = "users.json"

# -------- INIT FILE --------
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({}, f)

# -------- USER DATABASE --------
def load_users():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_users(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

def generate_ref():
    return str(random.randint(1000000, 9999999))

# -------- MENU --------
def menu(chat_id):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("💰 Balance", "🔗 Referral Link")
    kb.add("💸 Withdraw")
    bot.send_message(chat_id, "Main Menu", reply_markup=kb)

# -------- START + REFERRAL --------
@bot.message_handler(commands=['start'])
def start(msg):

    users = load_users()
    uid = str(msg.from_user.id)

    ref = None
    if msg.text.startswith("/start "):
        ref = msg.text.split()[1]

    if uid not in users:
        users[uid] = {
            "balance": 0,
            "withdrawn": 0,
            "referrals": 0,
            "ref_id": generate_ref()
        }

        # referral reward
        if ref:
            for u in users:
                if users[u]["ref_id"] == ref:
                    users[u]["balance"] += 0.5
                    users[u]["referrals"] += 1
                    bot.send_message(int(u),
                        f"🎉 New referral joined!\nYou earned $0.5")

    save_users(users)

    bot.send_message(msg.chat.id,
        "👋 Welcome!\nSend any TikTok / YouTube / Facebook / Pinterest link to download.")
    menu(msg.chat.id)

# -------- BALANCE --------
@bot.message_handler(func=lambda m: m.text=="💰 Balance")
def balance(msg):
    users = load_users()
    uid = str(msg.from_user.id)

    bot.send_message(msg.chat.id,
        f"💰 Balance: ${users[uid]['balance']}")

# -------- REFERRAL --------
@bot.message_handler(func=lambda m: m.text=="🔗 Referral Link")
def ref(msg):

    users = load_users()
    uid = str(msg.from_user.id)

    ref = users[uid]["ref_id"]
    link = f"https://t.me/{bot.get_me().username}?start={ref}"

    bot.send_message(msg.chat.id,
f"""🔗 Your referral link:
{link}

👥 Referrals: {users[uid]['referrals']}
💰 Earn $0.5 each
""")

# -------- WITHDRAW --------
@bot.message_handler(func=lambda m: m.text=="💸 Withdraw")
def withdraw_menu(msg):

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("USDT-BEP20", "🔙 Back")

    bot.send_message(msg.chat.id,
        "Select method",
        reply_markup=kb)

@bot.message_handler(func=lambda m: m.text=="USDT-BEP20")
def withdraw_amount(msg):

    ask = bot.send_message(msg.chat.id,
        "Enter withdrawal amount (Min $1)")
    bot.register_next_step_handler(ask, withdraw_address)

def withdraw_address(msg):

    users = load_users()
    uid = str(msg.from_user.id)

    try:
        amount = float(msg.text)
    except:
        bot.send_message(msg.chat.id,"Invalid amount")
        return

    if users[uid]["balance"] < amount:
        bot.send_message(msg.chat.id,"Not enough balance")
        return

    ask = bot.send_message(msg.chat.id,"Enter wallet address")
    bot.register_next_step_handler(ask, process_withdraw, amount)

def process_withdraw(msg, amount):

    users = load_users()
    uid = str(msg.from_user.id)

    address = msg.text
    wid = random.randint(10000,99999)

    users[uid]["balance"] -= amount
    users[uid]["withdrawn"] += amount
    save_users(users)

    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("CONFIRM ✅",
            callback_data=f"confirm_{uid}_{amount}_{wid}"),
        InlineKeyboardButton("REJECT ❌",
            callback_data=f"reject_{uid}_{amount}_{wid}")
    )

    bot.send_message(ADMIN_ID,
f"""💸 NEW WITHDRAWAL REQUEST

User: {uid}
Amount: ${amount}
Address: {address}
ID: {wid}
""", reply_markup=kb)

    bot.send_message(msg.chat.id,
        "✅ Request sent. It may take 2-12 hours 🙂")

# -------- CONFIRM --------
@bot.callback_query_handler(func=lambda c:c.data.startswith("confirm"))
def confirm(call):

    _,uid,amount,wid = call.data.split("_")

    bot.send_message(uid,
f"""💸 Payment Sent Successfully!

ID: {wid}
Amount: ${amount}
Method: USDT-BEP20
""")

# -------- REJECT --------
@bot.callback_query_handler(func=lambda c:c.data.startswith("reject"))
def reject(call):

    _,uid,amount,wid = call.data.split("_")

    users = load_users()
    users[uid]["balance"] += float(amount)
    save_users(users)

    bot.send_message(uid,
        f"❌ Withdrawal rejected. ${amount} returned to balance.")

# -------- ADMIN ADD BALANCE --------
@bot.message_handler(commands=['addbalance'])
def add_balance(msg):

    if msg.from_user.id != ADMIN_ID:
        return

    try:
        _,uid,amount = msg.text.split()
        amount=float(amount)
    except:
        return bot.send_message(msg.chat.id,"Usage /addbalance user amount")

    users = load_users()
    users[uid]["balance"] += amount
    save_users(users)

    bot.send_message(uid,f"💰 Admin updated your balance by ${amount}")

# -------- RANDOM GIFT --------
@bot.message_handler(commands=['randomgift'])
def randomgift(msg):

    if msg.from_user.id != ADMIN_ID:
        return

    amount=float(msg.text.split()[1])
    users=load_users()

    uid=random.choice(list(users.keys()))
    users[uid]["balance"]+=amount
    save_users(users)

    bot.send_message(uid,f"🎁 You received random gift ${amount}")

# -------- VIDEO + PHOTO DOWNLOADER --------
def download_media(msg):

    url = msg.text

    try:
        ydl_opts = {
            "outtmpl": "media.%(ext)s",
            "format": "best"
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            ext = info["ext"]

        file = f"media.{ext}"

        if ext in ["mp4","webm"]:
            bot.send_video(msg.chat.id, open(file,"rb"))
        else:
            bot.send_photo(msg.chat.id, open(file,"rb"))

        os.remove(file)

    except Exception:

        # TikTok photo fallback
        try:
            r=requests.get(url)
            with open("photo.jpg","wb") as f:
                f.write(r.content)
            bot.send_photo(msg.chat.id, open("photo.jpg","rb"))
            os.remove("photo.jpg")
        except:
            bot.send_message(msg.chat.id,"Download failed")

# -------- LINK DETECTOR --------
@bot.message_handler(func=lambda m:m.text.startswith("http"))
def downloader(msg):
    bot.send_message(msg.chat.id,"Downloading...")
    download_media(msg)

# -------- RUN --------
print("Bot running...")
bot.infinity_polling()
