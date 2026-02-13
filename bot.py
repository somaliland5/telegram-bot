import os
import json
import random
from telebot import TeleBot, types
import yt_dlp

# ------------------------
# TOKEN (Environment Variable)
# ------------------------
TOKEN = os.getenv("TOKEN")  # Railway environment variable
bot = TeleBot(TOKEN)

# ------------------------
# Data file
# ------------------------
DATA_FILE = "users.json"

# Ensure users.json exists
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({}, f)

# ------------------------
# Admin ID
# ------------------------
ADMIN_ID = 7983838654  # Your Telegram ID

# ------------------------
# Helpers
# ------------------------
def load_users():
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(DATA_FILE, "w") as f:
        json.dump(users, f, indent=4)

def generate_ref_id():
    return str(random.randint(1000000, 9999999))

def main_menu(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("💰 Balance", "🔗 Referral Link", "💸 Withdraw")
    bot.send_message(chat_id, "👋 Main Menu:", reply_markup=markup)

# ------------------------
# /start command
# ------------------------
@bot.message_handler(commands=['start'])
def start(message):
    users = load_users()
    user_id = str(message.from_user.id)
    args = message.text.split()

    if user_id not in users:
        ref_id = generate_ref_id()
        users[user_id] = {
            "balance": 0.0,
            "referrals": 0,
            "ref_id": ref_id
        }

        # Referral check
        if len(args) > 1:
            inviter_ref = args[1]
            for uid, data in users.items():
                if data["ref_id"] == inviter_ref:
                    users[uid]["balance"] += 0.5
                    users[uid]["referrals"] += 1
                    bot.send_message(uid, "🎉 You got $0.5 from new referral!")

        save_users(users)

    main_menu(message.chat.id)
    bot.send_message(message.chat.id,
        "Welcome! You can also send a public video link to download a video.")

# ------------------------
# Handle buttons and video links
# ------------------------
@bot.message_handler(func=lambda message: True)
def handle_buttons(message):
    users = load_users()
    user_id = str(message.from_user.id)

    # Balance button
    if message.text == "💰 Balance":
        bal = users[user_id]["balance"]
        bot.send_message(message.chat.id, f"💰 Your Balance: ${bal:.2f}")

    # Referral button
    elif message.text == "🔗 Referral Link":
        user_data = users[user_id]
        ref_id = user_data["ref_id"]
        total_referrals = user_data["referrals"]
        balance = user_data["balance"]

        link = f"https://t.me/{bot.get_me().username}?start={ref_id}"
        msg = f"🔗 Your Referral Link:\n{link}\n\n" \
              f"👥 Total Referrals: {total_referrals}\n" \
              f"💰 Earned: ${balance:.2f} (0.5 per referral)"
        bot.send_message(message.chat.id, msg)

    # Withdraw button
    elif message.text == "💸 Withdraw":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add("USDT-BEP20", "Cancel")
        msg = bot.send_message(message.chat.id,
            "Select coin for withdrawal:",
            reply_markup=markup)
        bot.register_next_step_handler(msg, ask_amount)

    elif message.text == "Cancel":
        bot.send_message(message.chat.id, "❌ Action cancelled.")
        main_menu(message.chat.id)

    # Video links
    elif message.text.startswith("http"):
        download_video(message)

    else:
        bot.send_message(message.chat.id, "❌ Unknown command. Use buttons or send a public video link.")
        main_menu(message.chat.id)

# ------------------------
# Video downloader using yt-dlp
# ------------------------
def download_video(message):
    url = message.text.strip()
    chat_id = message.chat.id
    bot.send_message(chat_id, "⏳ Downloading video, please wait...")

    try:
        ydl_opts = {
            'format': 'best[height<=720]/best',
            'outtmpl': 'video.mp4',
            'retries': 3,
            'socket_timeout': 30
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        with open("video.mp4", "rb") as f:
            bot.send_video(chat_id, f)

        os.remove("video.mp4")

    except Exception as e:
        bot.send_message(chat_id, f"❌ Download failed: {e}")

# ------------------------
# Withdraw flow
# ------------------------
def ask_amount(message):
    if message.text == "Cancel":
        bot.send_message(message.chat.id, "❌ Withdrawal cancelled.")
        main_menu(message.chat.id)
        return

    coin = message.text
    msg = bot.send_message(message.chat.id, f"Enter amount to withdraw (minimum $1) for {coin}:")
    bot.register_next_step_handler(msg, ask_address, coin)

def ask_address(message, coin):
    try:
        amount = float(message.text.strip())
    except:
        bot.send_message(message.chat.id, "❌ Invalid amount. Withdrawal cancelled.")
        main_menu(message.chat.id)
        return

    if amount < 1:
        bot.send_message(message.chat.id, "❌ Minimum withdrawal is $1")
        main_menu(message.chat.id)
        return

    users = load_users()
    user_id = str(message.from_user.id)
    if users[user_id]["balance"] < amount:
        bot.send_message(message.chat.id, "❌ You don't have enough balance.")
        main_menu(message.chat.id)
        return

    msg = bot.send_message(message.chat.id, f"Enter your {coin} wallet address (must start with 0):")
    bot.register_next_step_handler(msg, process_withdrawal, coin, amount)

def process_withdrawal(message, coin, amount):
    address = message.text.strip()
    if not address.startswith("0"):
        bot.send_message(message.chat.id, "❌ Invalid address. Withdrawal cancelled.")
        main_menu(message.chat.id)
        return

    users = load_users()
    user_id = str(message.from_user.id)

    users[user_id]["balance"] -= amount
    save_users(users)

    bot.send_message(message.chat.id,
f"✅ Withdrawal request sent!\nCoin: {coin}\nAmount: ${amount}\nAddress: {address}")
    bot.send_message(message.chat.id,
"Please wait, it may take 2-5 hours to complete.")

    bot.send_message(ADMIN_ID,
f"""
💸 NEW WITHDRAWAL REQUEST

👤 User ID: {user_id}
💰 Amount: ${amount}
🪙 Coin: {coin}
📬 Address: {address}
""")
    main_menu(message.chat.id)

# ------------------------
# Run bot
# ------------------------
print("Bot Running...")
bot.infinity_polling(timeout=60, long_polling_timeout=60)
