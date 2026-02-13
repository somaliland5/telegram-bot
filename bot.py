import os
import json
import random
from datetime import datetime
from telebot import TeleBot, types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import yt_dlp

TOKEN = "PUT_YOUR_TOKEN_HERE"
ADMIN_ID = 7983838654

bot = TeleBot(TOKEN)

DATA_FILE = "users.json"

# Create users file
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({}, f)

# ---------- USERS ----------
def load_users():
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(DATA_FILE, "w") as f:
        json.dump(users, f, indent=4)

def generate_ref_id():
    return str(random.randint(1000000, 9999999))

# ---------- MAIN MENU ----------
def main_menu(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("💰 Balance", "🔗 Referral Link", "💸 Withdraw")
    bot.send_message(chat_id, "Main Menu", reply_markup=markup)

# ---------- START ----------
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

# ---------- BUTTON HANDLER ----------
@bot.message_handler(func=lambda m: True)
def handler(message):
    users = load_users()
    user_id = str(message.from_user.id)

    if user_id not in users:
        return

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
💰 Earn $0.5 per user
""")

    elif message.text == "💸 Withdraw":
        msg = bot.send_message(message.chat.id, "Enter amount (Min $1):")
        bot.register_next_step_handler(msg, withdraw_amount)

    elif message.text.startswith("http"):
        download_video(message)

# ---------- WITHDRAW ----------
def withdraw_amount(message):
    users = load_users()
    user_id = str(message.from_user.id)

    try:
        amount = float(message.text)
    except:
        bot.send_message(message.chat.id, "Invalid amount")
        return

    if amount < 1:
        bot.send_message(message.chat.id, "Minimum withdrawal is $1")
        return

    if users[user_id]["balance"] < amount:
        bot.send_message(message.chat.id, "Not enough balance")
        return

    msg = bot.send_message(message.chat.id, "Enter wallet address:")
    bot.register_next_step_handler(msg, process_withdraw, amount)

def process_withdraw(message, amount):
    users = load_users()
    user_id = str(message.from_user.id)
    address = message.text

    users[user_id]["balance"] -= amount
    users[user_id]["withdrawn"] += amount
    save_users(users)

    withdrawal_id = random.randint(10000, 99999)

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(
        "CONFIRM ✅",
        callback_data=f"confirm_{user_id}_{amount}_{withdrawal_id}"
    ))

    bot.send_message(ADMIN_ID,
f"""💸 NEW WITHDRAWAL REQUEST
👤 User: {user_id}
💰 Amount: ${amount}
📬 Address: {address}
🧾 ID: #{withdrawal_id}
""", reply_markup=markup)

    bot.send_message(message.chat.id,
                     "Your Request has been Sent. It can take 2-12 hours 🙂")

# ---------- CONFIRM PAYMENT ----------
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
""")

    bot.answer_callback_query(call.id, "Payment Confirmed")

# ---------- RANDOM GIFT ----------
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
You received ${amount}
""")

    bot.send_message(message.chat.id,
f"""✅ Gift Sent
User: {user}
Amount: ${amount}
""")

# ---------- STATS ----------
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

# ---------- VIDEO DOWNLOAD ----------
def download_video(message):

    bot.send_message(message.chat.id, "Downloading...")

    try:
        ydl_opts = {'format': 'best', 'outtmpl': 'video.mp4'}

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([message.text])

        with open("video.mp4", "rb") as f:
            bot.send_video(message.chat.id, f)

        os.remove("video.mp4")

    except:
        bot.send_message(message.chat.id, "Download failed")

print("Bot Running")
bot.infinity_polling()
