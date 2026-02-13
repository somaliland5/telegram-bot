import os
import json
import random
from functools import partial
from datetime import datetime
from telebot import TeleBot, types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import yt_dlp

# -------- CONFIG --------
TOKEN = os.environ.get("TOKEN")
if not TOKEN:
    raise ValueError("❌ Bot token not found! Please set TOKEN environment variable.")
ADMIN_ID = 7983838654  # Admin Telegram ID

bot = TeleBot(TOKEN)
DATA_FILE = "users.json"
BANNED_FILE = "banned.json"

# -------- INIT FILES --------
for file in [DATA_FILE, BANNED_FILE]:
    if not os.path.exists(file):
        with open(file, "w") as f:
            json.dump({} if file==DATA_FILE else [], f)

# -------- USERS FUNCTIONS --------
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

def load_banned():
    try:
        with open(BANNED_FILE, "r") as f:
            data = json.load(f)
            return data if data else []
    except:
        return []

def save_banned(banned):
    with open(BANNED_FILE, "w") as f:
        json.dump(banned, f, indent=4)

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
    ref_id = None
    parts = message.text.split()
    if len(parts) > 1:
        ref_id = parts[1]

    # Add user new
    new_user = False
    if user_id not in users:
        users[user_id] = {
            "balance": 0.0,
            "referrals": 0,
            "withdrawn": 0.0,
            "ref_id": generate_ref_id(),
            "created_at": datetime.now().strftime("%Y-%m-%d")
        }
        new_user = True

    # Credit referral AFTER new user created
    if new_user and ref_id and ref_id in users and ref_id != user_id:
        users[ref_id]["balance"] += 0.5
        users[ref_id]["referrals"] += 1
        bot.send_message(
            int(ref_id),
f"🎉 You earned $0.5! New referral: {user_id}"
        )

    save_users(users)

    # ----- WELCOME MESSAGE -----
    welcome_text = f"""
👋 Welcome {message.from_user.first_name}!

This bot allows you to:
💰 Check your balance
🔗 Get referral link and earn rewards
💸 Request withdrawals
📹 Download videos or photos from TikTok, YouTube, Pinterest, Facebook

Start exploring now!
"""
    bot.send_message(message.chat.id, welcome_text)
    main_menu(message.chat.id)

# -------- ADMIN COMMANDS --------
@bot.message_handler(commands=['randomgift'])
def random_gift(message):
    if message.from_user.id != ADMIN_ID:
        return
    users = load_users()
    if not users:
        bot.send_message(message.chat.id, "No users found")
        return
    user_id = random.choice(list(users.keys()))
    users[user_id]["balance"] += 1
    save_users(users)
    bot.send_message(user_id,
f"""🎁 RANDOM GIFT
You received $1!"""
    )
    bot.send_message(message.chat.id,
f"""✅ Gift Sent
User: {user_id}
Amount: $1"""
    )

@bot.message_handler(commands=['addbalance'])
def add_balance(message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        parts = message.text.split()
        target_id = parts[1]
        amount = float(parts[2])
    except:
        bot.send_message(message.chat.id, "Usage: /addbalance <user_id> <amount>")
        return
    users = load_users()
    if target_id not in users:
        users[target_id] = {
            "balance": 0.0,
            "referrals": 0,
            "withdrawn": 0.0,
            "ref_id": generate_ref_id(),
            "created_at": datetime.now().strftime("%Y-%m-%d")
        }
    users[target_id]["balance"] += amount
    save_users(users)
    bot.send_message(message.chat.id,
f"✅ Successfully added ${amount} to user {target_id}")
    bot.send_message(target_id,
f"🎁 You received a gift! Your balance has been changed by ${amount}")

@bot.message_handler(commands=['stats'])
def stats(message):
    if message.from_user.id != ADMIN_ID:
        return
    users = load_users()
    total_users = len(users)
    total_balance = sum(u.get("balance",0) for u in users.values())
    total_withdrawn = sum(u.get("withdrawn",0) for u in users.values())
    bot.send_message(message.chat.id,
f"""📊 BOT STATS

👥 Total Users: {total_users}
💰 Total Balance: ${total_balance}
💸 Total Paid Out: ${total_withdrawn}"""
    )

@bot.message_handler(commands=['unban'])
def unban_user(message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        target_id = message.text.split()[1]
    except:
        bot.send_message(message.chat.id, "Usage: /unban <user_id>")
        return
    banned = load_banned()
    if target_id in banned:
        banned.remove(target_id)
        save_banned(banned)
        bot.send_message(message.chat.id, f"✅ User {target_id} has been unbanned.")
        bot.send_message(target_id, "✅ You have been unbanned. You can now use the bot.")
    else:
        bot.send_message(message.chat.id, "❌ User is not banned.")

# -------- MAIN HANDLER --------
@bot.message_handler(func=lambda m: True)
def handler(message):
    banned = load_banned()
    user_id = str(message.from_user.id)
    if user_id in banned:
        bot.send_message(message.chat.id, "❌ You are banned from using this bot.")
        return
    users = load_users()
    if user_id not in users:
        users[user_id] = {
            "balance": 0.0,
            "referrals": 0,
            "withdrawn": 0.0,
            "ref_id": generate_ref_id(),
            "created_at": datetime.now().strftime("%Y-%m-%d")
        }
        save_users(users)

    if message.text == "💰 Balance":
        bot.send_message(message.chat.id,
                         f"💰 Balance: ${users[user_id].get('balance',0)}")
    elif message.text == "🔗 Referral Link":
        ref = users[user_id]["ref_id"]
        link = f"https://t.me/{bot.get_me().username}?start={ref}"
        bot.send_message(message.chat.id,
f"""🔗 Your Referral Link:
{link}

👥 Referrals: {users[user_id].get('referrals',0)}
💰 Earn $0.5 per referral"""
        )
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
        bot.register_next_step_handler(msg, partial(withdraw_amount, method="USDT-BEP20"))
    elif message.text == "🔙 Back":
        main_menu(message.chat.id)
    elif message.text.startswith("http"):
        download_video(message)
    else:
        bot.send_message(message.chat.id,
                         "❌ Unknown command. Use buttons or send video/photo link.")

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
        bot.send_message(chat_id, "❌ Minimum withdrawal is $1")
        return
    if users[user_id].get("balance",0) < amount:
        bot.send_message(chat_id, "❌ Not enough balance")
        return
    msg = bot.send_message(chat_id,
                           "Enter your USDT-BEP20 wallet address (must start with 0):")
    bot.register_next_step_handler(msg, partial(process_withdraw, amount=amount, method=method))

def process_withdraw(message, amount, method):
    users = load_users()
    user_id = str(message.from_user.id)
    chat_id = message.chat.id
    address = message.text
    withdrawal_id = random.randint(10000, 99999)
    users[user_id]["balance"] -= amount
    users[user_id]["withdrawn"] += amount
    save_users(users)
    referral_count = users[user_id].get("referrals",0)

    markup = types.InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("CONFIRM ✅", callback_data=f"withdraw_confirm_{user_id}_{amount}_{withdrawal_id}"),
        InlineKeyboardButton("REJECT ❌", callback_data=f"withdraw_reject_{user_id}_{amount}_{withdrawal_id}"),
        InlineKeyboardButton("BAN 🚫", callback_data=f"withdraw_ban_{user_id}_{amount}_{withdrawal_id}")
    )

    bot.send_message(
        ADMIN_ID,
f"""💸 NEW WITHDRAWAL REQUEST

👤 User ID: {user_id}
💰 Amount: ${amount}
🪙 Coin: {method}
📬 Address: {address}
🧾 Withdrawal ID: #{withdrawal_id}
👥 Referrals: {referral_count}
""",
        reply_markup=markup
    )

    bot.send_message(chat_id,
                     "✅ Your Request has been Sent. It may take 2-12 hours to confirm. Please wait 🙂")

# -------- CONFIRM / REJECT / BAN --------
@bot.callback_query_handler(func=lambda call: call.data.startswith("withdraw"))
def withdraw_actions(call):
    parts = call.data.split("_")
    action = parts[1]
    user_id = parts[2]
    amount = float(parts[3])
    wid = parts[4]

    users = load_users()
    banned = load_banned()

    if action == "confirm":
        bot.send_message(user_id,
f"""💸 Payment Sent Successfully!
🧾 Withdrawal ID: #{wid}
💰 Amount: ${amount}
🔄 Method: USDT-BEP20
🆓 Fee (0.00%): $0.00
📤 Amount Sent: ${amount}"""
        )
        bot.answer_callback_query(call.id, "Payment Confirmed ✅")
    elif action == "reject":
        users[user_id]["balance"] += amount
        save_users(users)
        bot.send_message(user_id,
f"""❌ Withdrawal Rejected
🧾 Withdrawal ID: #{wid}
💰 Amount Refunded: ${amount}"""
        )
        bot.answer_callback_query(call.id, "Withdrawal Rejected ❌")
    elif action == "ban":
        if user_id not in banned:
            banned.append(user_id)
            save_banned(banned)
        bot.send_message(user_id, "❌ You have been banned from using this bot.")
        bot.answer_callback_query(call.id, "User has been banned 🚫")

# -------- VIDEO & PHOTO DOWNLOADER --------
def download_video(message):
    bot.send_message(message.chat.id, "Downloading...")
    try:
        url = message.text
        ydl_opts = {
            'format': 'best',
            'outtmpl': 'downloaded_media.%(ext)s',
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            ext = info.get('ext', 'mp4')

        file_name = f"downloaded_media.{ext}"

        if ext in ['mp4', 'webm']:
            with open(file_name, "rb") as f:
                bot.send_video(message.chat.id, f)
        elif ext in ['jpg', 'png', 'webp']:
            with open(file_name, "rb") as f:
                bot.send_photo(message.chat.id, f)
        else:
            bot.send_message(message.chat.id, "❌ Unknown media type.")

        os.remove(file_name)

    except Exception as e:
        bot.send_message(message.chat.id, f"Download failed: {str(e)}")

# -------- RUN BOT --------
print("Bot Running")
bot.infinity_polling()
