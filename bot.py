import os
import json
import random
from datetime import datetime, timedelta
from functools import partial
from telebot import TeleBot, types
import yt_dlp
import requests

# -------- CONFIG --------
TOKEN = os.environ.get("TOKEN")
if not TOKEN:
    raise ValueError("Bot token not found!")

ADMIN_ID = 7983838654
DATA_FILE = "users.json"
BOT_ID_RANGE = (1000000000, 1999999999)
PREMIUM_PRICE_USDT = 15
PREMIUM_ADDRESS = "0x98ffcb29a4fc182d461ebdba54648d8fe24597ac"

bot = TeleBot(TOKEN)

# -------- INIT FILES --------
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({}, f)

def load_users():
    with open(DATA_FILE, "r") as f:
        data = json.load(f)
        return data if data else {}

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
    markup.add("🎬 Video Editing")
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
            "last_random": None,
            "premium": False,
            "banned": False
        }
        if ref_id and ref_id in users:
            users[ref_id]["balance"] += 0.5
            users[ref_id]["points"] += 5
            users[ref_id]["referrals"] += 1
            bot.send_message(int(ref_id), f"🎉 You earned $0.5 and 5 points! Referral: {user_id}")

    save_users(users)
    bot.send_message(message.chat.id,
f"Welcome {message.from_user.first_name}!\n🎁 Enjoy earning points, random bonus, and weekly leaderboard!")
    main_menu(message.chat.id)

# -------- BUTTON HANDLER --------
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

    # -------- ADMIN PANEL --------
    if text == "⚙️ Admin Panel" and is_admin:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("📊 Stats", "➕ Add Balance", "🎁 Broadcast")
        markup.add("🛠️ Unban User", "🔙 Back to Main Menu")
        bot.send_message(user_id, "⚙️ Admin Panel", reply_markup=markup)
        return

    if is_admin:
        if text == "📊 Stats":
            total_users = len(users)
            total_balance = sum(u.get("balance",0) for u in users.values())
            total_withdrawn = sum(u.get("withdrawn",0) for u in users.values())
            bot.send_message(user_id,
f"📊 BOT STATS\n👥 Total Users: {total_users}\n💰 Total Balance: ${total_balance}\n💸 Total Paid Out: ${total_withdrawn}")
            return
        elif text == "➕ Add Balance":
            msg = bot.send_message(user_id, "Enter User Telegram ID to add balance:")
            bot.register_next_step_handler(msg, admin_add_balance_step1)
            return
        elif text == "🎁 Broadcast":
            msg = bot.send_message(user_id, "Enter message to broadcast (media URL optional, format: message|url):")
            bot.register_next_step_handler(msg, admin_broadcast)
            return
        elif text == "🛠️ Unban User":
            msg = bot.send_message(user_id, "Enter User Telegram ID to unban:")
            bot.register_next_step_handler(msg, admin_unban_user)
            return
        elif text == "🔙 Back to Main Menu":
            main_menu(user_id)
            return

    # -------- USER BUTTONS --------
    if text == "💰 Balance":
        bot.send_message(user_id, f"💰 Balance: ${users[user_id]['balance']}\nPoints: {users[user_id]['points']}\nPremium: {users[user_id]['premium']}")
    elif text == "🔗 Referral Link":
        ref = users[user_id]["ref_id"]
        link = f"https://t.me/{bot.get_me().username}?start={ref}"
        bot.send_message(user_id, f"🔗 Referral Link:\n{link}\nReferrals: {users[user_id]['referrals']}\nEarn $0.5 and 5 points per referral")
    elif text == "💸 Withdraw":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("USDT-BEP20")
        markup.add("🔙 Back")
        bot.send_message(user_id, "Select Withdrawal Method:", reply_markup=markup)
    elif text == "🎁 Random Bonus":
        give_random_bonus(message)
    elif text == "🏆 Weekly Rank":
        show_leaderboard(message)
    elif text == "👤 Profile":
        u = users[user_id]
        bot.send_message(user_id, f"👤 Profile\nTelegram ID: {user_id}\nBot ID: {u['ref_id']}\nBalance: {u['balance']}\nPoints: {u['points']}\nReferrals: {u['referrals']}\nPremium: {u['premium']}")
    elif text == "🆔 Get My ID":
        u = users[user_id]
        bot.send_message(user_id, f"Your IDs:\nTelegram ID: {user_id}\nBot ID: {u['ref_id']}")
    elif text == "📞 Customer":
        bot.send_message(user_id, "Contact: @scholes1")
    elif text == "🎬 Video Editing":
        handle_video_editing(user_id)
    elif text.startswith("http"):
        download_media(message)
    elif text == "🔙 Back":
        main_menu(user_id)
    else:
        bot.send_message(user_id, "❌ Unknown command or button.")

# -------- RANDOM BONUS --------
def give_random_bonus(message):
    users = load_users()
    user_id = str(message.from_user.id)
    now = datetime.now()
    last = users[user_id].get("last_random")
    if last:
        last_time = datetime.fromisoformat(last)
        if now - last_time < timedelta(hours=12):
            bot.send_message(user_id, "⏳ You can get random bonus once every 12 hours.")
            return
    bonus = round(random.uniform(0.01, 0.1),2)
    users[user_id]["balance"] += bonus
    users[user_id]["points"] += 1
    users[user_id]["last_random"] = now.isoformat()
    save_users(users)
    bot.send_message(user_id, f"🎁 You received ${bonus} and 1 point!")

# -------- LEADERBOARD --------
def show_leaderboard(message):
    users = load_users()
    leaderboard = sorted(users.items(), key=lambda x: x[1]["points"], reverse=True)
    text = "🏆 Weekly Leaderboard\n\n"
    for i, (uid, info) in enumerate(leaderboard[:100], 1):
        text += f"{i}. {uid} | Points: {info['points']} 💎\n"
    bot.send_message(message.chat.id, text)

# -------- VIDEO EDITING (PREMIUM) --------
def handle_video_editing(user_id):
    users = load_users()
    if not users[user_id]["premium"]:
        bot.send_message(user_id, f"🎬 Video Editing is premium!\nPlease send ${PREMIUM_PRICE_USDT} USDT to:\n{PREMIUM_ADDRESS}")
        msg = bot.send_message(user_id, "Type 'PAID' after payment to verify:")
        bot.register_next_step_handler(msg, partial(verify_payment, user_id))
        return
    bot.send_message(user_id, "✅ You are premium! Send your video URL now.")

def verify_payment(message, user_id):
    text = message.text.strip().upper()
    users = load_users()
    if text == "PAID":
        # **Simple placeholder check** (replace with Binance API verification)
        users[user_id]["premium"] = True
        save_users(users)
        bot.send_message(user_id, "✅ Payment verified! You can now access Video Editing.")
    else:
        bot.send_message(user_id, "❌ Payment not verified. Send 'PAID' after sending USDT.")

# -------- WITHDRAWAL --------
# [Wax walba sida aad horay u haysay]

# -------- DOWNLOAD MEDIA --------
def download_media(message):
    bot.send_message(message.chat.id, "Downloading...")
    url = message.text
    try:
        if any(x in url for x in ["tiktok.com", "youtube.com", "youtu.be", "facebook.com", "pinterest.com"]):
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

# -------- ADMIN FUNCTIONS --------
# [Add Balance, Broadcast, Unban etc. sida horay u haysay]

# -------- RUN BOT --------
print("Bot Running...")
bot.infinity_polling()
