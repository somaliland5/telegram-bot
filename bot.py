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
ADMIN_ID = 7983838654

if not TOKEN:
    raise ValueError("TOKEN missing")

bot = TeleBot(TOKEN)
DATA_FILE = "users.json"

# -------- INIT --------
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({}, f)

# -------- USERS --------
def load_users():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_users(users):
    with open(DATA_FILE, "w") as f:
        json.dump(users, f, indent=4)

def generate_ref():
    return str(random.randint(1000000, 9999999))

# -------- MENU --------
def main_menu(chat_id):

    bot.send_message(chat_id, "Loading menu...")

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)

    kb.row("💰 Balance", "🔗 Referral Link")
    kb.row("💸 Withdraw", "🆔 Get My ID")

    bot.send_message(chat_id, "Main Menu", reply_markup=kb)
# -------- START --------
@bot.message_handler(commands=['start'])
def start(message):

    users = load_users()
    uid = str(message.from_user.id)

    ref_code = None
    if message.text.startswith("/start "):
        ref_code = message.text.split()[1]

    if uid not in users:
        users[uid] = {
            "balance": 0.0,
            "withdrawn": 0.0,
            "referrals": 0,
            "ref_code": generate_ref(),
            "ban": False
        }

        # ---- referral reward ----
        if ref_code:
            for u in users:
                if users[u]["ref_code"] == ref_code:
                    users[u]["balance"] += 0.5
                    users[u]["referrals"] += 1
                    bot.send_message(int(u), "🎉 You earned $0.5 referral bonus!")
                    break

    save_users(users)
    main_menu(message.chat.id)

# -------- ADMIN COMMANDS --------
@bot.message_handler(commands=['addbalance'])
def add_balance(message):

    if message.from_user.id != ADMIN_ID:
        return

    try:
        uid, amount = message.text.split()[1:]
        amount = float(amount)
    except:
        bot.send_message(message.chat.id, "Usage: /addbalance ID amount")
        return

    users = load_users()

    if uid in users:
        users[uid]["balance"] += amount
        save_users(users)

        bot.send_message(uid, f"💰 Admin added ${amount}")
        bot.send_message(message.chat.id, "Balance added")

# ---- BAN ----
@bot.message_handler(commands=['ban'])
def ban_user(message):

    if message.from_user.id != ADMIN_ID:
        return

    uid = message.text.split()[1]
    users = load_users()

    if uid in users:
        users[uid]["ban"] = True
        save_users(users)

        bot.send_message(uid, "🚫 You are banned")

# ---- UNBAN ----
@bot.message_handler(commands=['unban'])
def unban_user(message):

    if message.from_user.id != ADMIN_ID:
        return

    uid = message.text.split()[1]
    users = load_users()

    if uid in users:
        users[uid]["ban"] = False
        save_users(users)

        bot.send_message(uid, "✅ You are unbanned")

# ---- STATS ----
@bot.message_handler(commands=['stats'])
def stats(message):

    if message.from_user.id != ADMIN_ID:
        return

    users = load_users()

    total = len(users)
    paid = sum(u["withdrawn"] for u in users.values())

    bot.send_message(message.chat.id,
f"""📊 Stats
Users: {total}
Paid: ${paid}
""")

# ---- RANDOM GIFT ----
@bot.message_handler(commands=['randomgift'])
def randomgift(message):

    if message.from_user.id != ADMIN_ID:
        return

    amount = float(message.text.split()[1])

    users = load_users()
    uid = random.choice(list(users.keys()))

    users[uid]["balance"] += amount
    save_users(users)

    bot.send_message(uid, f"🎁 Random gift ${amount}")

# -------- BUTTON HANDLER --------
@bot.message_handler(func=lambda m: True)
def handler(message):

    users = load_users()
    uid = str(message.from_user.id)

    if uid not in users:
        return

    if users[uid].get("ban"):
        bot.send_message(message.chat.id, "🚫 You are banned")
        return

    # BALANCE
    if message.text == "💰 Balance":
        bot.send_message(message.chat.id,
                         f"💰 Balance: ${users[uid]['balance']}")

    # REFERRAL
    elif message.text == "🔗 Referral Link":

        ref = users[uid]["ref_code"]
        link = f"https://t.me/{bot.get_me().username}?start={ref}"

        bot.send_message(message.chat.id,
f"""🔗 Your Referral Link
{link}

👥 Referrals: {users[uid]['referrals']}
Earn $0.5 per referral
""")

    # GET ID
    elif message.text == "🆔 Get My ID":

        bot.send_message(message.chat.id,
f"""🆔 Your ID
Telegram ID: {message.from_user.id}
Chat ID: {message.chat.id}
""")

    # WITHDRAW
    elif message.text == "💸 Withdraw":

        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add("USDT-BEP20")
        kb.add("🔙 Back")

        bot.send_message(message.chat.id, "Select method", reply_markup=kb)

    elif message.text == "USDT-BEP20":

        msg = bot.send_message(message.chat.id, "Enter amount (min $1)")
        bot.register_next_step_handler(msg, withdraw_amount)

    elif message.text == "🔙 Back":
        main_menu(message.chat.id)

    # VIDEO / PHOTO DOWNLOAD
    elif message.text.startswith("http"):
        download_media(message)

# -------- WITHDRAW --------
def withdraw_amount(message):

    users = load_users()
    uid = str(message.from_user.id)

    try:
        amount = float(message.text)
    except:
        return

    if amount < 1 or users[uid]["balance"] < amount:
        bot.send_message(message.chat.id, "Invalid amount")
        return

    msg = bot.send_message(message.chat.id, "Send USDT-BEP20 address")
    bot.register_next_step_handler(msg,
                                   partial(process_withdraw, amount=amount))

def process_withdraw(message, amount):

    users = load_users()
    uid = str(message.from_user.id)
    address = message.text

    wid = random.randint(10000, 99999)

    users[uid]["balance"] -= amount
    users[uid]["withdrawn"] += amount
    save_users(users)

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("CONFIRM ✅",
        callback_data=f"confirm_{uid}_{amount}_{wid}"))
    kb.add(InlineKeyboardButton("REJECT ❌",
        callback_data=f"reject_{uid}_{amount}_{wid}"))
    kb.add(InlineKeyboardButton("🚫 BAN USER",
        callback_data=f"ban_{uid}"))

    bot.send_message(ADMIN_ID,
f"""💸 NEW WITHDRAWAL

User: {uid}
Amount: ${amount}
Address: {address}
ID: {wid}
""", reply_markup=kb)

    bot.send_message(message.chat.id,
                     "Your request sent. It may take 2-12 hours 🙂")

# -------- CALLBACK --------
@bot.callback_query_handler(func=lambda c: True)
def callbacks(call):

    data = call.data.split("_")
    action = data[0]

    users = load_users()

    if action == "confirm":
        uid, amount, wid = data[1], data[2], data[3]

        bot.send_message(uid,
f"""💸 Payment Sent

Withdrawal ID: {wid}
Amount: ${amount}
""")

    elif action == "reject":
        uid, amount, wid = data[1], float(data[2]), data[3]

        users[uid]["balance"] += amount
        save_users(users)

        bot.send_message(uid, "❌ Withdrawal rejected. Balance returned")

    elif action == "ban":
        uid = data[1]

        users[uid]["ban"] = True
        save_users(users)

        bot.send_message(uid, "🚫 You are banned")

# -------- DOWNLOAD --------
def download_media(message):

    bot.send_message(message.chat.id, "Downloading...")

    try:
        ydl_opts = {
            'outtmpl': 'media.%(ext)s',
            'format': 'best'
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(message.text, download=True)
            file = ydl.prepare_filename(info)

        if file.endswith(".mp4"):
            with open(file, "rb") as f:
                bot.send_video(message.chat.id, f)
        else:
            with open(file, "rb") as f:
                bot.send_photo(message.chat.id, f)

        os.remove(file)

    except Exception as e:
        bot.send_message(message.chat.id, f"Download failed: {e}")

# -------- RUN --------
print("Bot running...")
bot.infinity_polling()
