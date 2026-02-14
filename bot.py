import os
import json
import random
import yt_dlp
from telebot import TeleBot, types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = os.environ.get("TOKEN")
ADMIN_ID = 7983838654

bot = TeleBot(TOKEN)
DATA_FILE = "users.json"

# ---------- FILE ----------
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({}, f)

def load_users():
    try:
        with open(DATA_FILE) as f:
            return json.load(f)
    except:
        return {}

def save_users(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

def gen_bot_id():
    return str(random.randint(1000000000, 9999999999))

def gen_ref_id():
    return str(random.randint(1000000, 9999999))

# ---------- MENU ----------
def main_menu(chat_id):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("💰 Balance", "🔗 Referral")
    kb.add("💸 Withdraw", "🆔 Get My ID")
    kb.add("👤 CUSTOMER")

    if chat_id == ADMIN_ID:
        kb.add("⚙ Admin Panel", "/stats")

    bot.send_message(chat_id, "🏠 Main Menu", reply_markup=kb)

# ---------- START ----------
@bot.message_handler(commands=['start'])
def start(message):

    users = load_users()
    uid = str(message.from_user.id)

    ref_code = None
    if len(message.text.split()) > 1:
        ref_code = message.text.split()[1]

    if uid not in users:

        users[uid] = {
            "balance": 0,
            "withdrawn": 0,
            "referrals": 0,
            "bot_id": gen_bot_id(),
            "ref_id": gen_ref_id(),
            "banned": False
        }

        # referral reward
        if ref_code:
            for r_uid in users:
                if users[r_uid]["ref_id"] == ref_code and r_uid != uid:
                    users[r_uid]["balance"] += 0.5
                    users[r_uid]["referrals"] += 1
                    bot.send_message(r_uid, "🎉 You received $0.5 referral bonus!")

    save_users(users)

    bot.send_message(
        message.chat.id,
        "👋 Welcome!\nSend TikTok / YouTube / Facebook / Pinterest link to download."
    )

    main_menu(message.chat.id)

# ---------- BALANCE ----------
@bot.message_handler(func=lambda m: m.text == "💰 Balance")
def balance(message):
    users = load_users()
    uid = str(message.from_user.id)

    bot.send_message(
        message.chat.id,
        f"💰 Balance: ${users[uid]['balance']}"
    )

# ---------- REFERRAL ----------
@bot.message_handler(func=lambda m: m.text == "🔗 Referral")
def referral(message):

    users = load_users()
    uid = str(message.from_user.id)

    link = f"https://t.me/{bot.get_me().username}?start={users[uid]['ref_id']}"

    bot.send_message(
        message.chat.id,
        f"🔗 Your referral link:\n{link}\n\n👥 Referrals: {users[uid]['referrals']}"
    )

# ---------- GET ID ----------
@bot.message_handler(func=lambda m: m.text == "🆔 Get My ID")
def get_id(message):

    users = load_users()
    uid = str(message.from_user.id)

    bot.send_message(
        message.chat.id,
        f"""🆔 YOUR IDS

Telegram ID: {uid}
BOT ID: {users[uid]['bot_id']}
"""
    )

# ---------- CUSTOMER ----------
@bot.message_handler(func=lambda m: m.text == "👤 CUSTOMER")
def customer(message):
    bot.send_message(message.chat.id, "📞 Contact: @scholes1")

# ---------- WITHDRAW ----------
@bot.message_handler(func=lambda m: m.text == "💸 Withdraw")
def withdraw_menu(message):

    users = load_users()
    uid = str(message.from_user.id)

    if users[uid]["banned"]:
        bot.send_message(message.chat.id, "🚫 You are banned")
        return

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("USDT-BEP20")
    kb.add("❌ Cancel")

    bot.send_message(
        message.chat.id,
        "Select withdrawal method:",
        reply_markup=kb
    )

@bot.message_handler(func=lambda m: m.text == "USDT-BEP20")
def withdraw_amount(message):

    msg = bot.send_message(
        message.chat.id,
        "Enter withdrawal amount (Min $1):"
    )

    bot.register_next_step_handler(msg, withdraw_amount_process)

def withdraw_amount_process(message):

    users = load_users()
    uid = str(message.from_user.id)

    try:
        amount = float(message.text)
    except:
        bot.send_message(message.chat.id, "❌ Invalid amount")
        return

    if amount < 1:
        bot.send_message(message.chat.id, "❌ Minimum withdrawal is $1")
        return

    if amount > users[uid]["balance"]:
        bot.send_message(message.chat.id, "❌ Insufficient balance")
        return

    msg = bot.send_message(
        message.chat.id,
        "Enter USDT-BEP20 wallet address:"
    )

    bot.register_next_step_handler(msg, withdraw_address, amount)

def withdraw_address(message, amount):

    users = load_users()
    uid = str(message.from_user.id)
    address = message.text
    wid = random.randint(10000, 99999)

    users[uid]["balance"] -= amount
    users[uid]["withdrawn"] += amount
    save_users(users)

    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_{uid}_{amount}_{wid}"),
        InlineKeyboardButton("❌ Reject", callback_data=f"reject_{uid}_{amount}_{wid}"),
        InlineKeyboardButton("🚫 Ban", callback_data=f"ban_{uid}")
    )

    bot.send_message(
        ADMIN_ID,
        f"""💸 NEW WITHDRAWAL REQUEST

👤 Telegram ID: {uid}
💰 Amount: ${amount}
📬 Address: {address}
🧾 Withdrawal ID: #{wid}
👥 Referrals: {users[uid]['referrals']}
🆔 Bot ID: {users[uid]['bot_id']}""",
        reply_markup=kb
    )

    bot.send_message(
        uid,
        f"""✅ Withdrawal Request Sent

🧾 ID: #{wid}
💰 Amount: ${amount}
⏳ It may take 2-12 hours to confirm."""
    )

    main_menu(message.chat.id)

@bot.message_handler(func=lambda m: m.text == "❌ Cancel")
def cancel(message):
    main_menu(message.chat.id)

# ---------- CALLBACK ----------
@bot.callback_query_handler(func=lambda call: True)
def callbacks(call):

    users = load_users()
    data = call.data.split("_")

    if data[0] == "confirm":
        bot.send_message(data[1], f"✅ Withdrawal ${data[2]} confirmed")

    elif data[0] == "reject":
        users[data[1]]["balance"] += float(data[2])
        save_users(users)
        bot.send_message(data[1], "❌ Withdrawal rejected")

    elif data[0] == "ban":
        users[data[1]]["banned"] = True
        save_users(users)
        bot.send_message(data[1], "🚫 You are banned")

# ---------- ADMIN PANEL ----------
@bot.message_handler(func=lambda m: m.text == "⚙ Admin Panel")
def admin_panel(message):

    if message.from_user.id != ADMIN_ID:
        return

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("➕ Add Balance", "🎁 Random Gift")
    kb.add("🔓 Unban User", "⬅ Back")

    bot.send_message(message.chat.id, "Admin Panel", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == "⬅ Back")
def admin_back(message):
    main_menu(message.chat.id)

# ---------- STATS ----------
@bot.message_handler(commands=['stats'])
def stats(message):

    if message.from_user.id != ADMIN_ID:
        return

    users = load_users()

    total_users = len(users)
    total_balance = sum(u.get("balance", 0) for u in users.values())
    total_withdrawn = sum(u.get("withdrawn", 0) for u in users.values())
    total_referrals = sum(u.get("referrals", 0) for u in users.values())

    bot.send_message(
        message.chat.id,
        f"""📊 BOT STATS

👥 Users: {total_users}
💰 Balance: ${total_balance}
💸 Withdrawn: ${total_withdrawn}
👥 Referrals: {total_referrals}
"""
    )

# ---------- ADD BALANCE ----------
@bot.message_handler(func=lambda m: m.text == "➕ Add Balance")
def add_balance_start(message):

    msg = bot.send_message(message.chat.id, "Enter BOT ID:")
    bot.register_next_step_handler(msg, add_balance_user)

def add_balance_user(message):

    users = load_users()

    for uid in users:
        if users[uid]["bot_id"] == message.text:

            msg = bot.send_message(message.chat.id, "Enter amount:")
            bot.register_next_step_handler(msg, add_balance_amount, uid)
            return

    bot.send_message(message.chat.id, "User not found")

def add_balance_amount(message, uid):

    users = load_users()
    amount = float(message.text)

    users[uid]["balance"] += amount
    save_users(users)

    bot.send_message(uid, f"🎁 Admin added ${amount}")
    bot.send_message(message.chat.id, "✅ Done")

# ---------- RANDOM GIFT ----------
@bot.message_handler(func=lambda m: m.text == "🎁 Random Gift")
def random_gift(message):

    users = load_users()
    uid = random.choice(list(users.keys()))

    users[uid]["balance"] += 1
    save_users(users)

    bot.send_message(uid, "🎁 You received $1 gift")
    bot.send_message(message.chat.id, "✅ Gift sent")

# ---------- UNBAN ----------
@bot.message_handler(func=lambda m: m.text == "🔓 Unban User")
def unban_start(message):

    msg = bot.send_message(message.chat.id, "Enter BOT ID:")
    bot.register_next_step_handler(msg, unban_user)

def unban_user(message):

    users = load_users()

    for uid in users:
        if users[uid]["bot_id"] == message.text:
            users[uid]["banned"] = False
            save_users(users)
            bot.send_message(uid, "✅ You are unbanned")
            bot.send_message(message.chat.id, "Done")
            return

    bot.send_message(message.chat.id, "User not found")

# ---------- DOWNLOAD (TikTok Photo + Video FIXED) ----------
@bot.message_handler(func=lambda m: m.text.startswith("http"))
def download(message):

    url = message.text
    chat = message.chat.id

    bot.send_message(chat, "⏳ Downloading...")

    try:
        ydl_opts = {
            'format': 'best',
            'outtmpl': 'media.%(ext)s',
            'noplaylist': True
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

            if 'entries' in info:
                info = info['entries'][0]

            file = ydl.prepare_filename(info)

        if file.endswith(".mp4"):
            bot.send_video(chat, open(file, "rb"))
        else:
            bot.send_photo(chat, open(file, "rb"))

        os.remove(file)

    except Exception as e:
        bot.send_message(chat, f"❌ Download failed\n{e}")

print("BOT RUNNING")
bot.infinity_polling()
