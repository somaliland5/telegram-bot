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
    raise ValueError("TOKEN not found!")

bot = TeleBot(TOKEN)
DATA_FILE = "users.json"

# -------- USERS DATA --------
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({}, f)

def load_users():
    try:
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
            return data if data else {}
    except:
        return {}

def save_users(users):
    with open(DATA_FILE, "w") as f:
        json.dump(users, f, indent=4)

def generate_ref():
    return str(random.randint(1000000, 9999999))

# -------- BAN CHECK --------
def check_ban(uid, chat_id):
    users = load_users()
    if uid in users and users[uid].get("ban", False):
        bot.send_message(chat_id, "❌ You are banned from using this bot.")
        return True
    return False

# -------- MENU --------
def menu(chat_id):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("💰 Balance", "🔗 Referral Link")
    kb.add("💸 Withdraw")
    bot.send_message(chat_id, "Main Menu", reply_markup=kb)

# -------- START --------
@bot.message_handler(commands=['start'])
def start(msg):
    uid = str(msg.from_user.id)
    if check_ban(uid, msg.chat.id):
        return

    users = load_users()
    ref = None
    if msg.text.startswith("/start "):
        ref = msg.text.split()[1]

    if uid not in users:
        users[uid] = {
            "balance":0,
            "withdrawn":0,
            "referrals":0,
            "ref_id":generate_ref(),
            "ban":False,
            "created_at": datetime.now().strftime("%Y-%m-%d")
        }
        # Referral reward
        if ref:
            for u in users:
                if users[u]["ref_id"] == ref and u != uid:
                    users[u]["balance"] += 0.5
                    users[u]["referrals"] += 1
                    bot.send_message(int(u), f"🎉 New referral! You earned $0.5")

    save_users(users)
    bot.send_message(msg.chat.id, "👋 Welcome! Send a TikTok / YouTube / Facebook / Pinterest link.")
    menu(msg.chat.id)

# -------- BUTTON HANDLER --------
@bot.message_handler(func=lambda m: True)
def handle_buttons(msg):
    uid = str(msg.from_user.id)
    if check_ban(uid, msg.chat.id):
        return

    users = load_users()
    if uid not in users:
        bot.send_message(msg.chat.id, "❌ Please send /start first.")
        return

    text = msg.text

    if text == "💰 Balance":
        bot.send_message(msg.chat.id, f"💰 Balance: ${users[uid]['balance']}")
    elif text == "🔗 Referral Link":
        ref = users[uid]["ref_id"]
        link = f"https://t.me/{bot.get_me().username}?start={ref}"
        bot.send_message(msg.chat.id,
f"""🔗 Your referral link:
{link}

👥 Referrals: {users[uid]['referrals']}
💰 Earn $0.5 per referral""")
    elif text == "💸 Withdraw":
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add("USDT-BEP20", "🔙 Back")
        bot.send_message(msg.chat.id, "Select withdrawal method", reply_markup=kb)
    elif text == "USDT-BEP20":
        msg2 = bot.send_message(msg.chat.id, "Enter withdrawal amount (Min $1)")
        bot.register_next_step_handler(msg2, partial(withdraw_amount, method="USDT-BEP20"))
    elif text == "🔙 Back":
        menu(msg.chat.id)
    elif text.startswith("http"):
        downloader(msg)
    else:
        bot.send_message(msg.chat.id, "❌ Unknown command. Use buttons or send a video/photo link.")

# -------- WITHDRAWAL --------
def withdraw_amount(msg, method):
    uid = str(msg.from_user.id)
    users = load_users()
    try:
        amount = float(msg.text)
    except:
        return bot.send_message(msg.chat.id, "❌ Invalid amount")

    if amount < 1:
        return bot.send_message(msg.chat.id, "❌ Minimum withdrawal is $1")
    if users[uid]["balance"] < amount:
        return bot.send_message(msg.chat.id, "❌ Not enough balance")

    msg2 = bot.send_message(msg.chat.id, "Enter your wallet address (USDT-BEP20):")
    bot.register_next_step_handler(msg2, partial(process_withdraw, amount=amount, method=method))

def process_withdraw(msg, amount, method):
    uid = str(msg.from_user.id)
    users = load_users()
    address = msg.text
    wid = random.randint(10000,99999)

    users[uid]["balance"] -= amount
    users[uid]["withdrawn"] += amount
    save_users(users)

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("CONFIRM ✅", callback_data=f"confirm_{uid}_{amount}_{wid}"))
    kb.add(InlineKeyboardButton("REJECT ❌", callback_data=f"reject_{uid}_{amount}_{wid}"))
    kb.add(InlineKeyboardButton("🚫 BAN USER", callback_data=f"banuser_{uid}"))

    bot.send_message(ADMIN_ID,
f"""💸 NEW WITHDRAWAL REQUEST
👤 User ID: {uid}
💰 Amount: ${amount}
📬 Address: {address}
🧾 ID: {wid}""", reply_markup=kb)

    bot.send_message(msg.chat.id,"✅ Your request has been sent. It may take 2-12 hours 🙂")

# -------- CALLBACKS --------
@bot.callback_query_handler(func=lambda c:c.data.startswith("confirm"))
def confirm(call):
    _, uid, amount, wid = call.data.split("_")
    bot.send_message(uid,
f"""💸 Payment Sent Successfully!
🧾 Withdrawal ID: #{wid}
💰 Amount: ${amount}
🔄 Method: USDT-BEP20""")
    bot.answer_callback_query(call.id, "Payment Confirmed")

@bot.callback_query_handler(func=lambda c:c.data.startswith("reject"))
def reject(call):
    _, uid, amount, wid = call.data.split("_")
    users = load_users()
    users[uid]["balance"] += float(amount)
    save_users(users)
    bot.send_message(uid, f"❌ Withdrawal rejected. ${amount} returned to balance.")
    bot.answer_callback_query(call.id, "Withdrawal Rejected")

@bot.callback_query_handler(func=lambda c:c.data.startswith("banuser"))
def ban(call):
    uid = call.data.split("_")[1]
    users = load_users()
    if uid in users:
        users[uid]["ban"] = True
        save_users(users)
        bot.send_message(uid,"🚫 You have been banned from using this bot.")
        bot.answer_callback_query(call.id, "User banned")

# -------- RANDOM GIFT & ADMIN --------
@bot.message_handler(commands=['randomgift'])
def gift(msg):
    if msg.from_user.id != ADMIN_ID:
        return
    try:
        amount = float(msg.text.split()[1])
    except:
        return bot.send_message(msg.chat.id,"Usage: /randomgift <amount>")
    users = load_users()
    uid = random.choice(list(users.keys()))
    users[uid]["balance"] += amount
    save_users(users)
    bot.send_message(uid,f"🎁 Random gift received: ${amount}")

@bot.message_handler(commands=['addbalance'])
def addbal(msg):
    if msg.from_user.id != ADMIN_ID:
        return
    try:
        _, uid, amount = msg.text.split()
        amount = float(amount)
    except:
        return bot.send_message(msg.chat.id,"Usage: /addbalance <user_id> <amount>")
    users = load_users()
    users[uid]["balance"] += amount
    save_users(users)
    bot.send_message(uid,f"💰 Admin added ${amount} to your balance.")

# -------- MEDIA DOWNLOADER --------
def downloader(msg):
    uid = str(msg.from_user.id)
    if check_ban(uid, msg.chat.id):
        return
    bot.send_message(msg.chat.id,"Downloading...")
    url = msg.text
    # Expand short links
    try:
        r = requests.get(url, allow_redirects=True, timeout=10)
        url = r.url
    except:
        pass
    # TikWM API
    try:
        api = f"https://www.tikwm.com/api/?url={url}"
        res = requests.get(api).json()
        if res.get("code")==0:
            data = res["data"]
            if data.get("images"):
                for img in data["images"]:
                    bot.send_photo(msg.chat.id, requests.get(img).content)
                return
            video = data.get("play")
            if video:
                bot.send_video(msg.chat.id, requests.get(video).content)
                return
    except:
        pass
    # yt-dlp fallback
    try:
        ydl_opts = {"outtmpl":"media.%(ext)s","format":"best"}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            ext = info["ext"]
        file = f"media.{ext}"
        if ext in ["mp4","webm"]:
            bot.send_video(msg.chat.id, open(file,"rb"))
        else:
            bot.send_photo(msg.chat.id, open(file,"rb"))
        os.remove(file)
    except:
        bot.send_message(msg.chat.id,"❌ Download failed")

# -------- RUN BOT --------
print("Bot Running...")
bot.infinity_polling()
