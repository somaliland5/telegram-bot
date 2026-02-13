import os
import json
import random
from telebot import TeleBot, types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import yt_dlp

# ------------------------
# Telegram Token
# ------------------------
TOKEN = "7991131193:AAEfHWU_FmkrwNLVpuW3axsEKbsqWf8WzOQ"
bot = TeleBot(TOKEN)

# ------------------------
# Data file
# ------------------------
DATA_FILE = "users.json"
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({}, f)

# ------------------------
# Admin ID
# ------------------------
ADMIN_ID = 7983838654  # Badal adiga

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
    return str(random.randint(1000000, 10000000))

def main_menu(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("💰 Balance", "🔗 Referral Link", "💸 Withdraw")
    bot.send_message(chat_id, "👋 Main Menu:", reply_markup=markup)

# ------------------------
# START COMMAND
# ------------------------
@bot.message_handler(commands=['start'])
def start(message):
    users = load_users()
    user_id = str(message.from_user.id)

    if user_id not in users:
        users[user_id] = {
            "balance": 0.0,
            "referrals": 0,
            "ref_id": generate_ref_id()
        }
        save_users(users)

    main_menu(message.chat.id)

# ------------------------
# Handle Buttons and Links
# ------------------------
@bot.message_handler(func=lambda message: True)
def handle_buttons(message):
    users = load_users()
    user_id = str(message.from_user.id)

    if message.text == "💰 Balance":
        bot.send_message(message.chat.id, f"💰 Your Balance: ${users[user_id]['balance']}")

    elif message.text == "🔗 Referral Link":
        ref_id = users[user_id]["ref_id"]
        link = f"https://t.me/{bot.get_me().username}?start={ref_id}"
        bot.send_message(message.chat.id,
f"🔗 Your Referral Link:\n{link}\n👥 Total Referrals: {users[user_id]['referrals']}\n💰 Earn $0.5 per user")

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

    elif message.text.startswith("http"):
        download_video(message)

    else:
        bot.send_message(message.chat.id, "❌ Unknown command. Use buttons or send a video link.")
        main_menu(message.chat.id)

# ------------------------
# Video Downloader
# ------------------------
def download_video(message):
    url = message.text.strip()
    chat_id = message.chat.id
    bot.send_message(chat_id, "⏳ Downloading video, please wait...")

    try:
        ydl_opts = {'format': 'best', 'outtmpl': 'video.mp4'}
        # Optional: YouTube cookies
        # ydl_opts['cookies'] = 'cookies.txt'
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        with open("video.mp4", "rb") as f:
            bot.send_video(chat_id, f)
        os.remove("video.mp4")
    except Exception as e:
        bot.send_message(chat_id, f"❌ Error downloading video: {str(e)}")

# ------------------------
# Withdrawal Flow
# ------------------------
def ask_amount(message):
    if message.text == "Cancel":
        bot.send_message(message.chat.id, "❌ Withdrawal cancelled.")
        main_menu(message.chat.id)
        return

    coin = message.text
    msg = bot.send_message(message.chat.id,
        f"Enter amount to withdraw (minimum $1) for {coin}:")
    bot.register_next_step_handler(msg, ask_address, coin)

def ask_address(message, coin):
    try:
        amount = float(message.text.strip())
    except:
        bot.send_message(message.chat.id, "❌ Invalid amount. Withdrawal cancelled.")
        main_menu(message.chat.id)
        return

    user_id = str(message.from_user.id)
    users = load_users()
    if users[user_id]["balance"] < amount:
        bot.send_message(message.chat.id, "❌ You don't have enough balance.")
        main_menu(message.chat.id)
        return

    msg = bot.send_message(message.chat.id,
        f"Enter your {coin} wallet address (must start with 0):")
    bot.register_next_step_handler(msg, process_withdrawal, coin, amount)

def process_withdrawal(message, coin, amount):
    address = message.text.strip()
    if not address.startswith("0"):
        bot.send_message(message.chat.id, "❌ Invalid address. Withdrawal cancelled.")
        main_menu(message.chat.id)
        return

    users = load_users()
    user_id = str(message.from_user.id)

    # Deduct balance immediately
    users[user_id]["balance"] -= amount
    save_users(users)

    # Notify user
    bot.send_message(message.chat.id, "✅ Your Request has been Sent. It can take 2-12 hours. 🙂")

    # Admin notification
    withdrawal_id = random.randint(10000, 99999)
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(
        "CONFIRM ✅",
        callback_data=f"confirm_{user_id}_{amount}_{coin}_{withdrawal_id}"
    ))

    bot.send_message(ADMIN_ID,
f"""
💸 NEW WITHDRAWAL REQUEST
👤 User ID: {user_id}
💰 Amount: ${amount}
🪙 Coin: {coin}
📬 Address: {address}
🧾 Withdrawal ID: #{withdrawal_id}
""", reply_markup=markup)

    main_menu(message.chat.id)

# ------------------------
# CONFIRM CALLBACK
# ------------------------
@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_"))
def confirm_withdraw(call):

    if call.from_user.id != ADMIN_ID:
        return

    data = call.data.split("_")
    user_id = data[1]
    amount = data[2]
    coin = data[3]
    withdrawal_id = data[4]

    text = f"""
💸 Payment Sent Successfully!
🧾 Withdrawal ID: #{withdrawal_id}
💰 Amount: ${amount}
🔄 Method: {coin}
🆓 Fee (0.00%): $0.00
📤 Amount Sent: ${amount}
"""
    bot.send_message(user_id, text)
    bot.answer_callback_query(call.id, "Payment Confirmed ✅")

# ------------------------
# ADMIN GIFT
# ------------------------
@bot.message_handler(commands=['gift'])
def gift_user(message):
    if message.from_user.id != ADMIN_ID:
        return

    args = message.text.split()
    if len(args) != 3:
        bot.send_message(message.chat.id, "Usage: /gift user_id amount")
        return

    target_id = args[1]
    amount = float(args[2])
    users = load_users()

    if target_id not in users:
        users[target_id] = {"balance": 0.0, "referrals": 0, "ref_id": generate_ref_id()}

    users[target_id]["balance"] += amount
    save_users(users)

    bot.send_message(target_id, f"🎁 You received a gift of ${amount}!")
    bot.send_message(message.chat.id, f"✅ Gift of ${amount} sent to {target_id}")

# ------------------------
# ADMIN RANDOM BONUS $1
# ------------------------
@bot.message_handler(commands=['randomgift'])
def random_gift(message):
    if message.from_user.id != ADMIN_ID:
        return

    users = load_users()
    if not users:
        bot.send_message(message.chat.id, "No users found.")
        return

    target_id = random.choice(list(users.keys()))
    users[target_id]["balance"] += 1.0
    save_users(users)

    bot.send_message(target_id, "🎉 Congratulations! You received a $1 bonus!")
    bot.send_message(message.chat.id, f"✅ Random gift of $1 sent to {target_id}")

# ------------------------
# RUN BOT
# ------------------------
print("Bot Running...")
bot.infinity_polling()
