import os
import json
import random
from datetime import datetime, timedelta
from functools import partial
from telebot import TeleBot, types
import yt_dlp

# ---------------- CONFIG ----------------
TOKEN = os.environ.get("TOKEN")
if not TOKEN:
    raise ValueError("Bot token not found!")

ADMIN_ID = 7983838654
DATA_FILE = "users.json"
BOT_ID_RANGE = (1000000000, 1999999999)
WITHDRAW_ID_RANGE = (100000, 999999)

bot = TeleBot(TOKEN)

# ---------------- INIT FILE ----------------
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({}, f, indent=4)

def load_users():
    with open(DATA_FILE, "r") as f:
        data = json.load(f)
        return data if data else {}

def save_users(users):
    with open(DATA_FILE, "w") as f:
        json.dump(users, f, indent=4)

def generate_bot_id():
    return str(random.randint(*BOT_ID_RANGE))

def generate_withdraw_id():
    return str(random.randint(*WITHDRAW_ID_RANGE))

# ---------------- MAIN MENU ----------------
def main_menu(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("💰 Balance")
    markup.add("🔗 Referral Link", "🆔 Get My ID")
    markup.add("📞 Customer")
    if str(chat_id) == str(ADMIN_ID):
        markup.add("⚙️ Admin Panel")
    bot.send_message(chat_id, "Main Menu", reply_markup=markup)

# ---------------- START ----------------
@bot.message_handler(commands=['start'])
def start(message):
    users = load_users()
    user_id = str(message.from_user.id)
    ref_id = None
    if message.text.startswith("/start "):
        ref_id = message.text.split()[1]

    if user_id not in users:
        users[user_id] = {
            "balance": 0.0,
            "points": 0,
            "referrals": 0,
            "withdrawn": 0.0,
            "bot_id": generate_bot_id(),
            "created_at": datetime.now().strftime("%Y-%m-%d"),
            "last_random": None,
            "banned": False,
            "withdrawals": {}
        }
        if ref_id and ref_id in users:
            users[ref_id]["balance"] += 0.25
            users[ref_id]["points"] += 1
            users[ref_id]["referrals"] += 1
            bot.send_message(int(ref_id), f"🎉 Referral bonus! $0.25 and 1 point from {user_id}")

    save_users(users)
    bot.send_message(message.chat.id,
f"Hi Welcome Send a Link And You Get vedio Easy 😃 {message.from_user.first_name}!\n🎁 Enjoy earning points, referral bonus, random gift!")
    main_menu(message.chat.id)

# ---------------- BUTTON HANDLER ----------------
@bot.message_handler(func=lambda m: True)
def handler(message):
    users = load_users()
    user_id = str(message.from_user.id)
    if user_id not in users: return
    if users[user_id].get("banned"):
        bot.send_message(user_id, "🚫 You are banned.")
        return

    text = message.text
    is_admin = (user_id == str(ADMIN_ID))

    # ------------- ADMIN PANEL ----------------
    if text == "⚙️ Admin Panel" and is_admin:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("📊 Stats", "➕ Add Balance", "🎁 Random Gift")
        markup.add("🛠️ Ban/Unban Users", "🔍 Withdrawal Check")
        markup.add("📢 Broadcast", "🔙 Back to Main Menu")
        bot.send_message(user_id, "Admin Panel", reply_markup=markup)
        return

    if is_admin:
        if text == "📊 Stats":
            total_users = len(users)
            total_balance = sum(u.get("balance",0) for u in users.values())
            total_withdrawn = sum(u.get("withdrawn",0) for u in users.values())
            total_banned = sum(1 for u in users.values() if u.get("banned",False))
            bot.send_message(user_id,
f"""📊 BOT STATS
👥 Total Users: {total_users}
💰 Total Balance: ${total_balance}
💸 Total Paid Out: ${total_withdrawn}
🚫 Total Banned: {total_banned}""")
            return
        elif text == "➕ Add Balance":
            msg = bot.send_message(user_id, "Enter User Telegram ID to add balance:")
            bot.register_next_step_handler(msg, admin_add_balance_step1)
            return
        elif text == "🎁 Random Gift":
            msg = bot.send_message(user_id, "Enter gift amount:")
            bot.register_next_step_handler(msg, admin_random_gift)
            return
        elif text == "🛠️ Ban/Unban Users":
            msg = bot.send_message(user_id, "Enter User Telegram ID to Ban/Unban:")
            bot.register_next_step_handler(msg, admin_ban_unban)
            return
        elif text == "🔍 Withdrawal Check":
            msg = bot.send_message(user_id, "Enter Withdrawal ID to check:")
            bot.register_next_step_handler(msg, admin_withdraw_check)
            return
        elif text == "📢 Broadcast":
            msg = bot.send_message(user_id, "Enter message to broadcast:")
            bot.register_next_step_handler(msg, admin_broadcast)
            return
        elif text == "🔙 Back to Main Menu":
            main_menu(user_id)
            return

    # ------------- USER BUTTONS ----------------
    if text == "💰 Balance":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("💸 Withdraw", "🔙 Back")
        bot.send_message(user_id,
f"💰 Balance: ${users[user_id]['balance']}\nPoints: {users[user_id]['points']}", reply_markup=markup)
    elif text == "💸 Withdraw":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("USDT-BEP20")
        markup.add("🔙 Cancel")
        msg = bot.send_message(user_id, "Select withdrawal method:", reply_markup=markup)
    elif text == "USDT-BEP20":
        msg = bot.send_message(user_id, "Enter withdrawal amount (min $1):")
        bot.register_next_step_handler(msg, withdraw_request)
    elif text == "🔙 Cancel":
        main_menu(user_id)
    elif text == "🔗 Referral Link":
        bot.send_message(user_id, f"🔗 Referral Link: /start {users[user_id]['bot_id']}")
    elif text == "🆔 Get My ID":
        bot.send_message(user_id, f"Telegram ID: {user_id}\nBot ID: {users[user_id]['bot_id']}")
    elif text == "📞 Customer":
        bot.send_message(user_id, "Contact: @scholes1")
    elif text.startswith("http"):
        download_media(message)
    else:
        bot.send_message(user_id, "❌ Unknown command")

# ---------------- RANDOM GIFT ----------------
def give_random_bonus(message):
    users = load_users()
    user_id = str(message.from_user.id)
    now = datetime.now()
    last = users[user_id].get("last_random")
    if last:
        last_time = datetime.fromisoformat(last)
        if now - last_time < timedelta(hours=24):
            bot.send_message(user_id, "⏳ You can get random bonus once every 24 hours.")
            return
    bonus = round(random.uniform(0.01,0.05),2)
    users[user_id]["balance"] += bonus
    users[user_id]["points"] += 1
    users[user_id]["last_random"] = now.isoformat()
    save_users(users)
    bot.send_message(user_id, f"🎁 You received ${bonus} and 1 point!")

# ---------------- DOWNLOAD MEDIA ----------------
def download_media(message):
    url = message.text.strip()
    bot.send_message(message.chat.id, "Downloading...")
    try:
        ydl_opts = {'format':'best','outtmpl':'video_or_photo'}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        with open("video_or_photo", "rb") as f:
            bot.send_video(message.chat.id, f)
        os.remove("video_or_photo")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Download failed: {str(e)}")

# ---------------- RUN BOT ----------------
print("Bot Running...")
bot.infinity_polling()
