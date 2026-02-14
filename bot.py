import os
import json
import random
from telebot import TeleBot, types
import yt_dlp

TOKEN = os.getenv("TOKEN")
ADMIN_ID = 7983838654
BOT_USERNAME = "Downloadvedioytibot"
DATA_FILE = "users.json"

bot = TeleBot(TOKEN)

# ---------- FILE ----------
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({}, f)


def load_users():
    with open(DATA_FILE) as f:
        return json.load(f)


def save_users(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)


# ---------- RANDOM ----------
def random_bot_id():
    return str(random.randint(1000000000, 9999999999))


def random_request_code():
    return str(random.randint(1000000000, 9999999999))


# ---------- MENU ----------
def main_menu(uid):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📥 Download", "💰 Balance")
    kb.add("🔗 Referral", "🆔 My IDs")
    kb.add("📞 Customer")

    if str(uid) == str(ADMIN_ID):
        kb.add("⚙️ Admin Panel")

    bot.send_message(uid, "📌 Main Menu", reply_markup=kb)


# ---------- START ----------
@bot.message_handler(commands=["start"])
def start(msg):
    users = load_users()
    uid = str(msg.from_user.id)

    ref = None
    if " " in msg.text:
        ref = msg.text.split()[1]

    if uid not in users:
        users[uid] = {
            "balance": 0,
            "referrals": 0,
            "bot_id": random_bot_id(),
            "withdrawals": {},
            "banned": False
        }

        if ref and ref in users:
            users[ref]["balance"] += 0.25
            users[ref]["referrals"] += 1

    save_users(users)

    bot.send_message(uid,
                     "👋 Hi Welcome\nYou can Send TikTok or Facebook Link And You Get Vedio Easy 😃")

    main_menu(uid)


# ---------- HANDLER ----------
@bot.message_handler(func=lambda m: True)
def handler(msg):
    users = load_users()
    uid = str(msg.from_user.id)
    text = msg.text

    if users.get(uid, {}).get("banned"):
        bot.send_message(uid, "🚫 You are banned")
        return

    # ---- DOWNLOAD ----
    if text == "📥 Download":
        bot.send_message(uid, "Send TikTok or Facebook Link")

    elif text.startswith("http"):
        download_media(msg)

    # ---- BALANCE ----
    elif text == "💰 Balance":
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add("💸 Withdraw")
        kb.add("🔙 Back")

        bot.send_message(uid,
                         f"💰 Balance: ${users[uid]['balance']}",
                         reply_markup=kb)

    elif text == "💸 Withdraw":
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add("USDT-BEP20")
        kb.add("❌ Cancel")

        bot.send_message(uid, "Select withdrawal method", reply_markup=kb)

    elif text == "USDT-BEP20":
        m = bot.send_message(uid, "Enter withdrawal amount:")
        bot.register_next_step_handler(m, withdraw_amount)

    elif text == "❌ Cancel":
        main_menu(uid)

    elif text == "🔙 Back":
        main_menu(uid)

    # ---- REFERRAL ----
    elif text == "🔗 Referral":
        ref = users[uid]["bot_id"]

        bot.send_message(uid,
                         f"🔗 Referral Link:\n"
                         f"https://t.me/{BOT_USERNAME}?start={ref}\n\n"
                         f"👥 Referrals: {users[uid]['referrals']}\n"
                         f"Earn $0.25 per referral")

    # ---- IDS ----
    elif text == "🆔 My IDs":
        bot.send_message(uid,
                         f"🆔 TELEGRAM ID: {uid}\n"
                         f"🤖 BOT ID: {users[uid]['bot_id']}")

    elif text == "📞 Customer":
        bot.send_message(uid, "Contact: @scholes1")

    # ---- ADMIN PANEL ----
    elif text == "⚙️ Admin Panel" and uid == str(ADMIN_ID):
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add("📢 Broadcast", "➕ Add Balance")
        kb.add("🔍 Withdrawal Check")
        kb.add("🔙 Back")

        bot.send_message(uid, "Admin Panel", reply_markup=kb)

    elif text == "📢 Broadcast" and uid == str(ADMIN_ID):
        m = bot.send_message(uid, "Send broadcast message")
        bot.register_next_step_handler(m, broadcast)

    elif text == "➕ Add Balance" and uid == str(ADMIN_ID):
        m = bot.send_message(uid, "Send BOT ID or Telegram ID")
        bot.register_next_step_handler(m, admin_add_balance)

    elif text == "🔍 Withdrawal Check" and uid == str(ADMIN_ID):
        m = bot.send_message(uid, "Send Request Code")
        bot.register_next_step_handler(m, admin_check)

    else:
        bot.send_message(uid, "Send link or choose menu")


# ---------- WITHDRAW ----------
def withdraw_amount(msg):
    users = load_users()
    uid = str(msg.from_user.id)

    try:
        amount = float(msg.text)
    except:
        bot.send_message(uid, "Invalid amount")
        return

    if amount > users[uid]["balance"]:
        bot.send_message(uid, "Not enough balance")
        return

    m = bot.send_message(uid, "Enter USDT-BEP20 address (must start 0x)")
    bot.register_next_step_handler(m, lambda m2: withdraw_address(m2, amount))


def withdraw_address(msg, amount):
    users = load_users()
    uid = str(msg.from_user.id)

    addr = msg.text.strip()

    if not addr.startswith("0x"):
        bot.send_message(uid, "Address must start with 0x")
        return

    code = random_request_code()

    users[uid]["balance"] -= amount
    users[uid]["withdrawals"][code] = {
        "amount": amount,
        "address": addr,
        "status": "Pending"
    }

    save_users(users)

    # USER MESSAGE
    bot.send_message(uid,
                     f"""✅ Request #{code} Sent!

💵 Amount: ${amount}
⏳ Pending approval
🕒 Processing: 2-12 hours""")

    # ADMIN MESSAGE
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("CONFIRM", callback_data=f"c_{uid}_{code}"))
    kb.add(types.InlineKeyboardButton("REJECT", callback_data=f"r_{uid}_{code}"))
    kb.add(types.InlineKeyboardButton("BAN", callback_data=f"b_{uid}_{code}"))

    bot.send_message(ADMIN_ID,
                     f"""💸 NEW WITHDRAWAL

👤 USER TELEGRAM ID: {uid}
🤖 BOT ID: {users[uid]['bot_id']}
🔢 REQUEST CODE: {code}
👥 REFERRALS: {users[uid]['referrals']}
💵 AMOUNT: ${amount}
🏦 ADDRESS: {addr}""",
                     reply_markup=kb)


# ---------- CALLBACK ----------
@bot.callback_query_handler(func=lambda c: True)
def callback(call):
    users = load_users()
    action, uid, code = call.data.split("_")

    w = users[uid]["withdrawals"][code]

    if action == "c":
        w["status"] = "Confirmed"
        bot.send_message(uid, f"✅ Withdrawal #{code} Confirmed")

    if action == "r":
        w["status"] = "Rejected"
        users[uid]["balance"] += w["amount"]
        bot.send_message(uid, f"❌ Withdrawal #{code} Rejected")

    if action == "b":
        users[uid]["banned"] = True
        bot.send_message(uid, "🚫 You are banned")

    save_users(users)


# ---------- ADMIN ----------
def admin_add_balance(msg):
    users = load_users()
    target = msg.text.strip()

    m = bot.send_message(ADMIN_ID, "Enter amount:")
    bot.register_next_step_handler(m, lambda m2: admin_add_balance2(m2, target))


def admin_add_balance2(msg, target):
    users = load_users()
    amount = float(msg.text)

    for uid, u in users.items():
        if target == uid or target == u["bot_id"]:
            users[uid]["balance"] += amount
            bot.send_message(uid, f"Admin added ${amount}")

    save_users(users)
    bot.send_message(ADMIN_ID, "Done")


def admin_check(msg):
    users = load_users()
    code = msg.text.strip()

    for uid, u in users.items():
        if code in u["withdrawals"]:
            w = u["withdrawals"][code]

            bot.send_message(ADMIN_ID,
                             f"""REQUEST #{code}

USER ID: {uid}
BOT ID: {u['bot_id']}
REFERRALS: {u['referrals']}
AMOUNT: ${w['amount']}
ADDRESS: {w['address']}
STATUS: {w['status']}""")
            return

    bot.send_message(ADMIN_ID, "Not Found")


def broadcast(msg):
    users = load_users()

    for u in users:
        try:
            bot.send_message(u, msg.text)
        except:
            pass

    bot.send_message(ADMIN_ID, "Broadcast Sent")


# ---------- DOWNLOAD ----------
def download_media(msg):
    url = msg.text.strip()

    if not ("tiktok.com" in url or "facebook.com" in url or "fb.watch" in url):
        bot.send_message(msg.chat.id, "Only TikTok or Facebook supported")
        return

    bot.send_message(msg.chat.id, "Downloading...")

    try:
        ydl_opts = {
            "outtmpl": "file.%(ext)s",
            "format": "best"
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        for f in os.listdir():
            if f.startswith("file"):
                with open(f, "rb") as file:
                    bot.send_document(msg.chat.id, file)
                os.remove(f)

    except Exception as e:
        bot.send_message(msg.chat.id, f"Download Failed: {e}")


print("BOT RUNNING...")
bot.infinity_polling()
