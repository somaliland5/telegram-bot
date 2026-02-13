import os
import json
import random
from datetime import datetime
from telebot import TeleBot, types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import yt_dlp

# -------- CONFIG --------
TOKEN = "PUT_YOUR_TOKEN_HERE"  # Bedel token-kaaga
ADMIN_ID = 7983838654          # Bedel admin ID (int)

bot = TeleBot(TOKEN)
DATA_FILE = "users.json"

# -------- INIT FILE --------
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({}, f)

# -------- USERS --------
def load_users():
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(DATA_FILE, "w") as f:
        json.dump(users, f, indent=4)

def generate_ref_id():
    return str(random.randint(1000000, 9999999))

# -------- MAIN MENU --------
def main_menu(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("💰 Balance", "🔗 Referral Link", "💸 Withdraw")
    bot.send_message(chat_id, "Main Menu", reply_markup=markup)

# -------- START COMMAND --------
@bot.message_handler(commands=['start'])
def start(message):
    users = load_users()
    user_id = str(message.from_user.id)

    if user_id not in users:
        users[user_id] = {
            "balance": 0.0,
            "referrals": 0,
            "withdrawn": 0.0,
            "ref_id": generate_ref_id(),
            "created_at": datetime.now().strftime("%Y-%m-%d")
        }
        save_users(users)

    main_menu(message.chat.id)

# -------- ADMIN RANDOM GIFT --------
@bot.message_handler(commands=['randomgift'])
def random_gift(message):
    if message.from_user.id != ADMIN_ID:
        return

    try:
        amount = float(message.text.split()[1])
    except:
        bot.send_message(message.chat.id, "Usage: /randomgift 1")
        return

    users = load_users()
    if not users:
        bot.send_message(message.chat.id, "No users found")
        return

    user = random.choice(list(users.keys()))
    users[user]["balance"] += amount
    save_users(users)

    bot.send_message(user,
f"""🎁 RANDOM GIFT
You received ${amount}!
""")

    bot.send_message(message.chat.id,
f"""✅ Gift Sent
User: {user}
Amount: ${amount}
""")

# -------- ADMIN STATS --------
@bot.message_handler(commands=['stats'])
def stats(message):
    if message.from_user.id != ADMIN_ID:
        return

    users = load_users()
    total_users = len(users)
    total_balance = sum(u["balance"] for u in users.values())
    total_withdrawn = sum(u["withdrawn"] for u in users.values())

    bot.send_message(message.chat.id,
f"""📊 BOT STATS

👥 Total Users: {total_users}
💰 Total Balance: ${total_balance}
💸 Total Paid Out: ${total_withdrawn}
""")

# -------- MAIN HANDLER --------
@bot.message_handler(func=lambda m: True)
def handler(message):

    if message.text.startswith("/"):
        return

    users = load_users()
    user_id = str(message.from_user.id)

    if user_id not in users:
        return

    # ----- BUTTONS -----
    if message.text == "💰 Balance":
        bot.send_message(message.chat.id,
                         f"💰 Balance: ${users[user_id]['balance']}")

    elif message.text == "🔗 Referral Link":
        ref = users[user_id]["ref_id"]
        link = f"https://t.me/{bot.get_me().username}?start={ref}"
        bot.send_message(message.chat.id,
f"""🔗 Your Referral Link:
{link}

👥 Referrals: {users[user_id]['referrals']}
💰 Earn $0.5 per referral
""")

    elif message.text == "💸 Withdraw":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("USDT-BEP20")
        markup.add("🔙 Back")
        bot.send_message(message.chat.id,
                         "Select Withdrawal Method",
                         reply_markup=markup)

    elif message.text == "USDT-BEP20":
        msg = bot.send_message(message.chat.id,
                               "Enter withdrawal amount (Min $1):")
        bot.register_next_step_handler(msg, withdraw_amount, "USDT-BEP20")

    elif message.text == "🔙 Back":
        main_menu(message.chat.id)

    elif message.text.startswith("http"):
        download_video(message)

    else:
        bot.send_message(message.chat.id,
                         "❌ Unknown command. Use buttons or send video link.")

# -------- WITHDRAWAL FUNCTIONS --------
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
        bot.send_message(chat_id, "❌ Minimum withdrawal is $1")
        return

    if users[user_id]["balance"] < amount:
        bot.send_message(chat_id, "❌ Not enough balance")
        return

    msg = bot.send_message(chat_id,
                           "Enter your USDT-BEP20 wallet address (must start with 0):")
    bot.register_next_step_handler(msg, process_withdraw, amount, method)

def process_withdraw(message, amount, method):
    users = load_users()
    user_id = str(message.from_user.id)
    chat_id = message.chat.id
    address = message.text
    withdrawal_id = random.randint(10000, 99999)

    # Deduct balance and save
    users[user_id]["balance"] -= amount
    users[user_id]["withdrawn"] += amount
    save_users(users)

    # Admin notification
    markup = types.InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(
        "CONFIRM ✅",
        callback_data=f"confirm_{user_id}_{amount}_{withdrawal_id}"
    ))

    bot.send_message(
        ADMIN_ID,
f"""💸 NEW WITHDRAWAL REQUEST

👤 User ID: {user_id}
💰 Amount: ${amount}
🪙 Coin: {method}
📬 Address: {address}
🧾 Withdrawal ID: #{withdrawal_id}
""",
        reply_markup=markup
    )

    # User confirmation
    bot.send_message(
        chat_id,
        "✅ Your Request has been Sent. It may take 2-12 hours to confirm. Please wait 🙂"
    )

# -------- CONFIRM PAYMENT --------
@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm"))
def confirm_payment(call):
    data = call.data.split("_")
    user_id = data[1]
    amount = data[2]
    wid = data[3]

    bot.send_message(user_id,
f"""💸 Payment Sent Successfully!

🧾 Withdrawal ID: #{wid}
💰 Amount: ${amount}
🔄 Method: USDT-BEP20
🆓 Fee (0.00%): $0.00
📤 Amount Sent: ${amount}
""")

    bot.answer_callback_query(call.id, "Payment Confirmed")

# -------- VIDEO DOWNLOADER --------
def download_video(message):
    bot.send_message(message.chat.id, "Downloading...")

    try:
        ydl_opts = {
            'format': 'best',
            'outtmpl': 'video.mp4',
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([message.text])

        with open("video.mp4", "rb") as f:
            bot.send_video(message.chat.id, f)

        os.remove("video.mp4")

    except Exception as e:
        bot.send_message(message.chat.id, f"Download failed: {str(e)}")

# -------- RUN BOT --------
print("Bot Running")
bot.infinity_polling()
