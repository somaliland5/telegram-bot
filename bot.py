import os
import json
import random
from datetime import datetime, timedelta
from functools import partial
from telebot import TeleBot, types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import yt_dlp
import requests

# -------- CONFIG --------
TOKEN = os.environ.get("TOKEN")
if not TOKEN:
    raise ValueError("❌ Bot token not found! Set TOKEN env var.")
ADMIN_ID = 7983838654  # Your Telegram ID for admin
DATA_FILE = "users.json"
BOT_ID_RANGE = (1000000000, 1999999999)

bot = TeleBot(TOKEN)

# -------- INIT FILE --------
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({}, f)

# -------- USERS FUNCTIONS --------
def load_users():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w") as f:
            json.dump({}, f)
    with open(DATA_FILE, "r") as f:
        data = json.load(f)
        if data is None:
            data = {}
        return data

def save_users(users):
    with open(DATA_FILE, "w") as f:
        json.dump(users, f, indent=4)

def generate_ref_id():
    return str(random.randint(*BOT_ID_RANGE))

# -------- MAIN MENU --------
def main_menu(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("💰 Balance", "🔗 Referral Link", "💸 Withdraw")
    markup.add("🎁 Random Bonus", "🏆 Weekly Rank")
    markup.add("👤 Profile", "🆔 Get My ID")
    markup.add("📞 Customer")
    if str(chat_id) == str(ADMIN_ID):
        markup.add("⚙️ Admin Panel")
    bot.send_message(chat_id, "Main Menu", reply_markup=markup)

# -------- START --------
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
            "ref_id": generate_ref_id(),
            "created_at": datetime.now().strftime("%Y-%m-%d"),
            "last_random": None
        }
        # Referral credit
        if ref_id and ref_id in users:
            users[ref_id]["balance"] += 0.5
            users[ref_id]["points"] += 5
            users[ref_id]["referrals"] += 1
            bot.send_message(int(ref_id), f"🎉 You earned $0.5 and 5 points! Referral: {user_id}")
    save_users(users)
    bot.send_message(message.chat.id, f"Welcome {message.from_user.first_name}!")
    main_menu(message.chat.id)

# -------- BUTTON HANDLER --------
@bot.message_handler(func=lambda m: True)
def handler(message):
    if message.text.startswith("/"):
        return
    users = load_users()
    user_id = str(message.from_user.id)
    if user_id not in users:
        return

    if message.text == "💰 Balance":
        bot.send_message(message.chat.id, f"💰 Balance: ${users[user_id]['balance']}\nPoints: {users[user_id]['points']}")
    elif message.text == "🔗 Referral Link":
        ref = users[user_id]["ref_id"]
        link = f"https://t.me/{bot.get_me().username}?start={ref}"
        bot.send_message(message.chat.id, f"🔗 Referral Link:\n{link}\nReferrals: {users[user_id]['referrals']}\nEarn $0.5 and 5 points per referral")
    elif message.text == "💸 Withdraw":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("USDT-BEP20")
        markup.add("🔙 Back")
        bot.send_message(message.chat.id, "Select Withdrawal Method:", reply_markup=markup)
    elif message.text == "USDT-BEP20":
        msg = bot.send_message(message.chat.id, "Enter withdrawal amount (Min $1):")
        bot.register_next_step_handler(msg, partial(withdraw_amount, method="USDT-BEP20"))
    elif message.text == "🔙 Back":
        main_menu(message.chat.id)
    elif message.text == "🎁 Random Bonus":
        give_random_bonus(message)
    elif message.text == "🏆 Weekly Rank":
        show_leaderboard(message)
    elif message.text == "👤 Profile":
        u = users[user_id]
        bot.send_message(message.chat.id, f"👤 Profile\nTelegram ID: {user_id}\nBot ID: {u['ref_id']}\nBalance: {u['balance']}\nPoints: {u['points']}\nReferrals: {u['referrals']}")
    elif message.text == "🆔 Get My ID":
        u = users[user_id]
        bot.send_message(message.chat.id, f"Your IDs:\nTelegram ID: {user_id}\nBot ID: {u['ref_id']}")
    elif message.text == "📞 Customer":
        bot.send_message(message.chat.id, "Contact: @scholes1")
    elif message.text == "⚙️ Admin Panel" and user_id == str(ADMIN_ID):
        bot.send_message(message.chat.id, "Admin Panel activated! Use /stats, /addbalance, /randomgift")
    elif message.text.startswith("http"):
        download_media(message)
    else:
        bot.send_message(message.chat.id, "❌ Unknown command or button.")

# -------- RANDOM BONUS --------
def give_random_bonus(message):
    users = load_users()
    user_id = str(message.from_user.id)
    now = datetime.now()
    last = users[user_id].get("last_random")
    if last:
        last_time = datetime.fromisoformat(last)
        if now - last_time < timedelta(hours=12):
            bot.send_message(message.chat.id, "⏳ You can get random bonus once every 12 hours.")
            return
    bonus = round(random.uniform(0.01, 0.1), 2)
    users[user_id]["balance"] += bonus
    users[user_id]["points"] += 1
    users[user_id]["last_random"] = now.isoformat()
    save_users(users)
    bot.send_message(message.chat.id, f"🎁 You received ${bonus} and 1 point!")
    
# -------- LEADERBOARD --------
def show_leaderboard(message):
    users = load_users()
    leaderboard = sorted(users.items(), key=lambda x: x[1]["points"], reverse=True)
    text = "🏆 Weekly Leaderboard\n\n"
    for i, (uid, info) in enumerate(leaderboard[:10], 1):
        text += f"{i}. {uid} | Points: {info['points']}\n"
    bot.send_message(message.chat.id, text)

# -------- WITHDRAWAL --------
def withdraw_amount(message, method):
    users = load_users()
    user_id = str(message.from_user.id)
    chat_id = message.chat.id
    try:
        amount = float(message.text)
    except:
        bot.send_message(chat_id, "❌ Invalid amount")
        return
    if amount < 1:
        bot.send_message(chat_id, "❌ Minimum withdrawal $1")
        return
    if users[user_id]["balance"] < amount:
        bot.send_message(chat_id, "❌ Not enough balance")
        return
    msg = bot.send_message(chat_id, "Enter USDT-BEP20 wallet address (must start with 0):")
    bot.register_next_step_handler(msg, partial(process_withdraw, amount=amount, method=method))

def process_withdraw(message, amount, method):
    users = load_users()
    user_id = str(message.from_user.id)
    chat_id = message.chat.id
    address = message.text
    withdrawal_id = random.randint(10000, 99999)
    users[user_id]["balance"] -= amount
    users[user_id]["withdrawn"] += amount
    users[user_id]["points"] += 10
    save_users(users)
    # Admin notification
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("CONFIRM ✅", callback_data=f"confirm_{user_id}_{amount}_{withdrawal_id}"))
    markup.add(InlineKeyboardButton("REJECT ❌", callback_data=f"reject_{user_id}_{amount}_{withdrawal_id}"))
    markup.add(InlineKeyboardButton("BAN 🚫", callback_data=f"ban_{user_id}_{amount}_{withdrawal_id}"))
    bot.send_message(ADMIN_ID,
        f"💸 NEW WITHDRAWAL REQUEST\n\nUser ID: {user_id}\nAmount: ${amount}\nCoin: {method}\nAddress: {address}\nWithdrawal ID: #{withdrawal_id}\nReferrals: {users[user_id]['referrals']}\nPoints: {users[user_id]['points']}",
        reply_markup=markup
    )
    bot.send_message(chat_id, f"✅ Your request has been sent. It may take 2-12 hours to confirm.")

# -------- CALLBACK HANDLER --------
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    data = call.data.split("_")
    action = data[0]
    user_id = data[1]
    amount = data[2]
    wid = data[3]
    users = load_users()
    if action == "confirm":
        bot.send_message(user_id, f"💸 Payment Sent Successfully!\nWithdrawal ID: #{wid}\nAmount: ${amount}\nMethod: USDT-BEP20")
    elif action == "reject":
        users[user_id]["balance"] += float(amount)
        save_users(users)
        bot.send_message(user_id, f"❌ Your withdrawal request #{wid} has been rejected. Amount refunded: ${amount}")
    elif action == "ban":
        users[user_id]["banned"] = True
        save_users(users)
        bot.send_message(user_id, f"🚫 You have been banned by admin.")

# -------- DOWNLOAD MEDIA --------
def download_media(message):
    bot.send_message(message.chat.id, "Downloading...")
    url = message.text
    try:
        if "tiktok.com" in url or "youtube.com" in url or "youtu.be" in url or "facebook.com" in url or "pinterest.com" in url:
            ydl_opts = {'format': 'best', 'outtmpl': 'video.mp4'}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            with open("video.mp4", "rb") as f:
                bot.send_video(message.chat.id, f)
            os.remove("video.mp4")
        else:
            bot.send_message(message.chat.id, "❌ Unsupported URL.")
    except Exception as e:
        bot.send_message(message.chat.id, f"Download failed: {str(e)}")

# -------- RUN BOT --------
print("BOT RUNNING")
bot.infinity_polling()
