import os
import json
import random
from datetime import datetime, timedelta
from functools import partial
from telebot import TeleBot, types
import yt_dlp
import threading
import requests

# ---------------- CONFIG ----------------
TOKEN = os.environ.get("TOKEN")
if not TOKEN:
    raise ValueError("Bot token not found!")
ADMIN_ID = 7983838654
DATA_FILE = "users.json"
BOT_ID_RANGE = (1000000000, 1999999999)

# Binance Payment Details
BINANCE_API_KEY = os.environ.get("BINANCE_API_KEY")  # Private API key
PAYMENT_ADDRESS = "0x98ffcb29a4fc182d461ebdba54648d8fe24597ac"
PREMIUM_PRICE = 15  # $15 USDT per month

bot = TeleBot(TOKEN)

# ---------------- INIT FILES ----------------
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({}, f)

def load_users():
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(DATA_FILE, "w") as f:
        json.dump(users, f, indent=4)

def generate_ref_id():
    return str(random.randint(*BOT_ID_RANGE))

# ---------------- MAIN MENU ----------------
def main_menu(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("💰 Balance", "🔗 Referral Link", "💸 Withdraw")
    markup.add("🎁 Random Bonus", "🏆 Weekly Rank")
    markup.add("👤 Profile", "🆔 Get My ID")
    markup.add("📞 Customer")
    markup.add("🎬 Premium Video Editing")
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
            "premium_until": None,
            "ref_id": generate_ref_id(),
            "created_at": datetime.now().strftime("%Y-%m-%d"),
            "last_random": None,
            "banned": False
        }
        if ref_id and ref_id in users:
            users[ref_id]["balance"] += 0.5
            users[ref_id]["points"] += 5
            users[ref_id]["referrals"] += 1
            bot.send_message(int(ref_id), f"🎉 You earned $0.5 and 5 points! Referral: {user_id}")

    save_users(users)
    bot.send_message(message.chat.id,
f"Welcome {message.from_user.first_name}!\n\n🎁 Enjoy earning points, random bonus, and weekly leaderboard!")
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

    # ---------- ADMIN PANEL ----------
    if text == "⚙️ Admin Panel" and is_admin:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("📊 Stats", "➕ Add Balance", "🎁 Random Gift")
        markup.add("📢 Broadcast", "🛠️ Unban User", "🔙 Back to Main Menu")
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
        elif text == "🎁 Random Gift":
            msg = bot.send_message(user_id, "Enter amount to send as random gift:")
            bot.register_next_step_handler(msg, admin_random_gift)
            return
        elif text == "🛠️ Unban User":
            msg = bot.send_message(user_id, "Enter User Telegram ID to unban:")
            bot.register_next_step_handler(msg, admin_unban_user)
            return
        elif text == "📢 Broadcast":
            msg = bot.send_message(user_id, "Enter your message to broadcast:")
            bot.register_next_step_handler(msg, admin_broadcast)
            return
        elif text == "🔙 Back to Main Menu":
            main_menu(user_id)
            return

    # ---------- USER BUTTONS ----------
    if text == "💰 Balance":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("💰 Show Balance", "🔙 Back")
        bot.send_message(user_id, "Select:", reply_markup=markup)
    elif text == "💰 Show Balance":
        bot.send_message(user_id, f"💰 Balance: ${users[user_id]['balance']}\nPoints: {users[user_id]['points']}")
    elif text == "💸 Withdraw":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("USDT-BEP20", "🔙 Back")
        bot.send_message(user_id, "Select Withdrawal Method:", reply_markup=markup)
    elif text == "🎁 Random Bonus":
        give_random_bonus(message)
    elif text == "🏆 Weekly Rank":
        show_leaderboard(message)
    elif text == "👤 Profile":
        u = users[user_id]
        bot.send_message(user_id,
f"👤 Profile\nTelegram ID: {user_id}\nBot ID: {u['ref_id']}\nBalance: {u['balance']}\nPoints: {u['points']}\nReferrals: {u['referrals']}\nPremium Until: {u.get('premium_until')}")
    elif text == "🆔 Get My ID":
        u = users[user_id]
        bot.send_message(user_id, f"Your IDs:\nTelegram ID: {user_id}\nBot ID: {u['ref_id']}")
    elif text == "📞 Customer":
        bot.send_message(user_id, "Contact: @scholes1")
    elif text == "🎬 Premium Video Editing":
        # Check if premium active
        premium_until = users[user_id].get("premium_until")
        now = datetime.now()
        if premium_until and datetime.fromisoformat(premium_until) > now:
            bot.send_message(user_id, "✅ Premium Access Active! Send your video now.")
        else:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("PAID 💵", callback_data=f"premium_paid_{user_id}"))
            markup.add(types.InlineKeyboardButton("CANCEL ❌", callback_data=f"premium_cancel_{user_id}"))
            bot.send_message(user_id, f"💵 Premium Video Editing Subscription: ${PREMIUM_PRICE}/month\nSend payment to {PAYMENT_ADDRESS}", reply_markup=markup)
    elif text.startswith("http"):
        download_media(message)
    elif text == "🔙 Back":
        main_menu(user_id)
    else:
        bot.send_message(user_id, "❌ Unknown command or button.")

# ---------------- RANDOM BONUS ----------------
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
    bonus = round(random.uniform(0.01, 0.1),2)
    users[user_id]["balance"] += bonus
    users[user_id]["points"] += 1
    users[user_id]["last_random"] = now.isoformat()
    save_users(users)
    bot.send_message(message.chat.id, f"🎁 You received ${bonus} and 1 point!")

# ---------------- DOWNLOAD MEDIA ----------------
def download_media(message):
    url = message.text
    bot.send_message(message.chat.id, "⏳ Downloading...")
    try:
        ydl_opts = {'format':'best', 'outtmpl':'video.mp4'}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        with open("video.mp4","rb") as f:
            bot.send_video(message.chat.id, f)
        os.remove("video.mp4")
    except Exception as e:
        bot.send_message(message.chat.id, f"Download failed: {str(e)}")

# ---------------- CALLBACK HANDLER ----------------
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    users = load_users()
    data = call.data.split("_")
    action = data[0]
    user_id = data[2] if len(data) > 2 else None

    if action == "premium":
        sub_action = data[1]
        if sub_action == "paid":
            # Verify Payment via Binance API
            success = verify_binance_payment(user_id)
            if success:
                users[user_id]["premium_until"] = (datetime.now() + timedelta(days=30)).isoformat()
                save_users(users)
                bot.send_message(user_id, "✅ Premium Activated! You can now send your video.")
                bot.send_message(ADMIN_ID, f"💎 User {user_id} activated Premium successfully!")
            else:
                bot.send_message(user_id, "❌ PAYMENT FAILED !!")
        elif sub_action == "cancel":
            bot.send_message(user_id, "❌ Subscription Cancelled.")
            main_menu(user_id)

# ---------------- BINANCE PAYMENT MOCK ----------------
def verify_binance_payment(user_id):
    """
    Implement Binance API check here. Return True if transaction of $15 to PAYMENT_ADDRESS exists.
    """
    # Placeholder: Always fail for testing
    # Replace this with real Binance API call
    return False

# ---------------- ADMIN FUNCTIONS ----------------
def admin_add_balance_step1(message):
    user_id_target = message.text.strip()
    msg = bot.send_message(ADMIN_ID, f"Enter amount to add to {user_id_target}:")
    bot.register_next_step_handler(msg, partial(admin_add_balance_step2, user_id_target))

def admin_add_balance_step2(message, user_id_target):
    amount = float(message.text.strip())
    users = load_users()
    if user_id_target in users:
        users[user_id_target]["balance"] += amount
        save_users(users)
        bot.send_message(ADMIN_ID, f"✅ Added ${amount} to {user_id_target}")
        bot.send_message(user_id_target, f"💰 Admin added ${amount} to your balance!")

def admin_random_gift(message):
    amount = float(message.text.strip())
    users = load_users()
    if not users:
        bot.send_message(ADMIN_ID, "No users found")
        return
    user = random.choice(list(users.keys()))
    users[user]["balance"] += amount
    save_users(users)
    bot.send_message(user, f"🎁 RANDOM GIFT\nYou received ${amount}!")
    bot.send_message(ADMIN_ID, f"✅ Gift Sent\nUser: {user}\nAmount: ${amount}")

def admin_unban_user(message):
    user_id_target = message.text.strip()
    users = load_users()
    if user_id_target in users:
        users[user_id_target]["banned"] = False
        save_users(users)
        bot.send_message(ADMIN_ID, f"✅ Unbanned {user_id_target}")
        bot.send_message(user_id_target, "✅ You have been unbanned by admin!")

def admin_broadcast(message):
    users = load_users()
    for uid in users:
        try:
            bot.send_message(uid, message.text)
        except:
            pass
    bot.send_message(ADMIN_ID, f"✅ Broadcast sent to {len(users)} users.")

# ---------------- LEADERBOARD ----------------
def show_leaderboard(message):
    users = load_users()
    leaderboard = sorted(users.items(), key=lambda x: x[1]["points"], reverse=True)
    text = "🏆 Weekly Leaderboard\n\n"
    for i, (uid, info) in enumerate(leaderboard[:100], 1):
        text += f"{i}. {uid} | Points: {info['points']} 💎\n"
    bot.send_message(message.chat.id, text)

# ---------------- RUN BOT ----------------
def run_bot():
    print("Bot Running...")
    bot.infinity_polling()

threading.Thread(target=run_bot).start()
