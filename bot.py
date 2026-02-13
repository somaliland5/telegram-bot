import os
import json
import random
from datetime import datetime
from telebot import TeleBot, types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import yt_dlp

TOKEN = os.environ.get("TOKEN")
ADMIN_ID = 7983838654

if not TOKEN:
    raise ValueError("TOKEN missing")

bot = TeleBot(TOKEN)
DATA_FILE = "users.json"


# ---------------- FILE ----------------
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({}, f)


def load_users():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f) or {}
    except:
        return {}


def save_users(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)


# ---------------- GENERATORS ----------------
def generate_ref():
    return str(random.randint(1000000, 9999999))


def generate_bot_id(users):
    base = 1000000000
    existing = [u.get("bot_id", base) for u in users.values()]
    return max(existing) + 1 if existing else base


def get_uid_from_bot_id(bot_id):
    users = load_users()
    for uid, data in users.items():
        if str(data.get("bot_id")) == str(bot_id):
            return uid
    return None


# ---------------- MENU ----------------
def menu(chat_id):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("💰 Balance", "🔗 Referral Link")
    kb.add("💸 Withdraw", "🆔 Get My ID")
    bot.send_message(chat_id, "Main Menu", reply_markup=kb)


# ---------------- START ----------------
@bot.message_handler(commands=['start'])
def start(msg):
    users = load_users()
    uid = str(msg.from_user.id)

    ref = None
    if len(msg.text.split()) > 1:
        ref = msg.text.split()[1]

    if uid not in users:
        bot_id = generate_bot_id(users)

        users[uid] = {
            "bot_id": bot_id,
            "balance": 0,
            "withdrawn": 0,
            "referrals": 0,
            "ref_id": generate_ref(),
            "ban": False,
            "created_at": str(datetime.now().date())
        }

        # referral credit
        if ref:
            for u, d in users.items():
                if d["ref_id"] == ref:
                    users[u]["balance"] += 0.5
                    users[u]["referrals"] += 1
                    bot.send_message(u, "🎉 You earned $0.5 referral bonus!")

    save_users(users)
    menu(msg.chat.id)


# ---------------- BUTTON HANDLER ----------------
@bot.message_handler(func=lambda m: True)
def handler(msg):
    text = msg.text
    users = load_users()
    uid = str(msg.from_user.id)

    if uid not in users:
        return

    if users[uid]["ban"]:
        return bot.send_message(msg.chat.id, "🚫 You are banned")

    # BALANCE
    if text == "💰 Balance":
        bot.send_message(msg.chat.id,
                         f"💰 Balance: ${users[uid]['balance']}")

    # REFERRAL
    elif text == "🔗 Referral Link":
        ref = users[uid]["ref_id"]
        link = f"https://t.me/{bot.get_me().username}?start={ref}"

        bot.send_message(msg.chat.id,
                         f"🔗 Your Link:\n{link}\n\n👥 Referrals: {users[uid]['referrals']}")

    # GET ID
    elif text == "🆔 Get My ID":
        bot.send_message(msg.chat.id,
                         f"🆔 Your Bot ID: {users[uid]['bot_id']}")

    # WITHDRAW
    elif text == "💸 Withdraw":
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add("USDT-BEP20", "🔙 Back")
        bot.send_message(msg.chat.id, "Select Method", reply_markup=kb)

    elif text == "🔙 Back":
        menu(msg.chat.id)

    elif text == "USDT-BEP20":
        m = bot.send_message(msg.chat.id, "Enter amount:")
        bot.register_next_step_handler(m, withdraw_amount)

    elif text.startswith("http"):
        download_media(msg)


# ---------------- WITHDRAW ----------------
def withdraw_amount(msg):
    users = load_users()
    uid = str(msg.from_user.id)

    try:
        amount = float(msg.text)
    except:
        return bot.send_message(msg.chat.id, "Invalid amount")

    if amount < 1:
        return bot.send_message(msg.chat.id, "Minimum $1")

    if users[uid]["balance"] < amount:
        return bot.send_message(msg.chat.id, "Not enough balance")

    m = bot.send_message(msg.chat.id, "Enter wallet address:")
    bot.register_next_step_handler(m, process_withdraw, amount)


def process_withdraw(msg, amount):
    users = load_users()
    uid = str(msg.from_user.id)
    address = msg.text

    wid = random.randint(10000, 99999)
    bot_id = users[uid]["bot_id"]

    users[uid]["balance"] -= amount
    users[uid]["withdrawn"] += amount
    save_users(users)

    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("CONFIRM ✅",
                             callback_data=f"confirm_{uid}_{amount}_{wid}"),
        InlineKeyboardButton("REJECT ❌",
                             callback_data=f"reject_{uid}_{amount}_{wid}"),
        InlineKeyboardButton("BAN 🚫",
                             callback_data=f"ban_{uid}")
    )

    bot.send_message(
        ADMIN_ID,
        f"💸 Withdrawal Request\n"
        f"👤 Telegram ID: {uid}\n"
        f"🆔 Bot ID: {bot_id}\n"
        f"💰 Amount: ${amount}\n"
        f"📬 Address: {address}\n"
        f"🧾 ID: {wid}",
        reply_markup=kb
    )

    bot.send_message(msg.chat.id,
                     "✅ Request sent. Wait 2-12 hours.")


# ---------------- CALLBACK ----------------
@bot.callback_query_handler(func=lambda c: True)
def callbacks(call):
    data = call.data.split("_")

    users = load_users()

    # CONFIRM
    if data[0] == "confirm":
        uid, amount, wid = data[1], data[2], data[3]

        bot.send_message(uid,
                         f"✅ Payment Sent\nID:{wid}\nAmount:${amount}")

    # REJECT
    elif data[0] == "reject":
        uid, amount, wid = data[1], data[2], data[3]

        users[uid]["balance"] += float(amount)
        save_users(users)

        bot.send_message(uid,
                         f"❌ Withdrawal Rejected\nAmount refunded ${amount}")

    # BAN
    elif data[0] == "ban":
        uid = data[1]
        users[uid]["ban"] = True
        save_users(users)
        bot.send_message(uid, "🚫 You are banned")

    bot.answer_callback_query(call.id)


# ---------------- ADMIN ----------------
@bot.message_handler(commands=['addbalance'])
def addbal(msg):
    if msg.from_user.id != ADMIN_ID:
        return

    try:
        _, bot_id, amount = msg.text.split()
        amount = float(amount)
    except:
        return bot.send_message(msg.chat.id,
                                "Usage: /addbalance BOTID AMOUNT")

    uid = get_uid_from_bot_id(bot_id)
    if not uid:
        return bot.send_message(msg.chat.id, "User not found")

    users = load_users()
    users[uid]["balance"] += amount
    save_users(users)

    bot.send_message(uid, f"💰 Admin added ${amount}")


@bot.message_handler(commands=['unban'])
def unban(msg):
    if msg.from_user.id != ADMIN_ID:
        return

    try:
        _, bot_id = msg.text.split()
    except:
        return

    uid = get_uid_from_bot_id(bot_id)
    if not uid:
        return

    users = load_users()
    users[uid]["ban"] = False
    save_users(users)

    bot.send_message(uid, "✅ You are unbanned")


# ---------------- DOWNLOADER ----------------
def download_media(msg):
    try:
        bot.send_message(msg.chat.id, "Downloading...")

        ydl_opts = {
            'format': 'best',
            'outtmpl': 'media.%(ext)s'
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(msg.text, download=True)
            file = ydl.prepare_filename(info)

        if file.endswith(".mp4"):
            with open(file, "rb") as f:
                bot.send_video(msg.chat.id, f)
        else:
            with open(file, "rb") as f:
                bot.send_photo(msg.chat.id, f)

        os.remove(file)

    except Exception as e:
        bot.send_message(msg.chat.id, f"Download failed: {e}")


# ---------------- RUN ----------------
print("Bot Running...")
bot.infinity_polling()
