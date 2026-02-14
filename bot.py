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

# -------- FILE --------
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({}, f)

def load_users():
    with open(DATA_FILE) as f:
        return json.load(f)

def save_users(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

def rand_bot_id():
    return str(random.randint(1000000000, 9999999999))

def rand_withdraw_id():
    return str(random.randint(10000, 99999))


# -------- MENU --------
def main_menu(uid):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("💰 Balance", "🔗 Referral Link")
    kb.add("🆔 Get My ID")
    kb.add("📞 Customer")

    if str(uid) == str(ADMIN_ID):
        kb.add("⚙️ Admin Panel")

    bot.send_message(uid, "Main Menu", reply_markup=kb)


# -------- START --------
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
            "bot_id": rand_bot_id(),
            "withdrawals": {},
            "banned": False
        }

        if ref and ref in users:
            users[ref]["balance"] += 0.25
            users[ref]["referrals"] += 1

    save_users(users)

    bot.send_message(uid,
                     "Hi Welcome You can Send TikTok or Facebook Link And You Get Vedio Easy. 😃")

    main_menu(uid)


# -------- BUTTON HANDLER --------
@bot.message_handler(func=lambda m: True)
def handler(msg):
    users = load_users()
    uid = str(msg.from_user.id)
    txt = msg.text

    if users.get(uid, {}).get("banned"):
        bot.send_message(uid, "🚫 You are banned")
        return

    if txt == "💰 Balance":
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add("💸 Withdraw")
        kb.add("🔙 Back")

        bot.send_message(uid,
                         f"💰 Balance: ${users[uid]['balance']}",
                         reply_markup=kb)

    elif txt == "🔙 Back":
        main_menu(uid)

    elif txt == "💸 Withdraw":
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add("USDT-BEP20")
        kb.add("❌ Cancel")

        bot.send_message(uid, "Select Withdrawal Method", reply_markup=kb)

    elif txt == "❌ Cancel":
        main_menu(uid)

    elif txt == "USDT-BEP20":
        m = bot.send_message(uid, "Enter withdrawal amount:")
        bot.register_next_step_handler(m, withdraw_step1)

    elif txt == "🔗 Referral Link":
        ref = users[uid]["bot_id"]

        bot.send_message(uid,
                         f"🔗 Referral Link:\nhttps://t.me/{BOT_USERNAME}?start={ref}\n\n"
                         f"Referrals: {users[uid]['referrals']}\n"
                         f"Earn $0.25 per referral")

    elif txt == "🆔 Get My ID":
        bot.send_message(uid,
                         f"Telegram ID: {uid}\nBOT ID: {users[uid]['bot_id']}")

    elif txt == "📞 Customer":
        bot.send_message(uid, "Contact: @scholes1")

    elif txt == "⚙️ Admin Panel" and uid == str(ADMIN_ID):
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add("📢 Broadcast", "➕ Add Balance")
        kb.add("🔍 Withdrawal Check")
        kb.add("🔙 Back")

        bot.send_message(uid, "Admin Panel", reply_markup=kb)

    elif txt == "📢 Broadcast" and uid == str(ADMIN_ID):
        m = bot.send_message(uid, "Send broadcast message")
        bot.register_next_step_handler(m, broadcast)

    elif txt == "➕ Add Balance" and uid == str(ADMIN_ID):
        m = bot.send_message(uid, "Send BOT ID or Telegram ID")
        bot.register_next_step_handler(m, admin_add_balance_step1)

    elif txt == "🔍 Withdrawal Check" and uid == str(ADMIN_ID):
        m = bot.send_message(uid, "Send Withdrawal ID")
        bot.register_next_step_handler(m, admin_withdraw_check)

    elif txt.startswith("http"):
        download_media(msg)

    else:
        bot.send_message(uid, "Send TikTok or Facebook link")


# -------- WITHDRAW --------
def withdraw_step1(msg):
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

    m = bot.send_message(uid, "Enter USDT‑BEP20 address starting with 0x")
    bot.register_next_step_handler(m, lambda m2: withdraw_step2(m2, amount))


def withdraw_step2(msg, amount):
    users = load_users()
    uid = str(msg.from_user.id)

    addr = msg.text.strip()

    if not addr.startswith("0x"):
        bot.send_message(uid, "Address must start with 0x")
        return

    rid = rand_withdraw_id()

    users[uid]["balance"] -= amount

    users[uid]["withdrawals"][rid] = {
        "amount": amount,
        "address": addr,
        "status": "Pending"
    }

    save_users(users)

    bot.send_message(uid,
                     f"✅ Request #{rid} Sent!\nAmount: ${amount}\nPending 6‑12 hours")

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("CONFIRM", callback_data=f"c_{uid}_{rid}"))
    kb.add(types.InlineKeyboardButton("REJECT", callback_data=f"r_{uid}_{rid}"))
    kb.add(types.InlineKeyboardButton("BAN", callback_data=f"b_{uid}_{rid}"))

    bot.send_message(ADMIN_ID,
                     f"Withdrawal #{rid}\nUser: {uid}\nBOT ID: {users[uid]['bot_id']}\nAmount: ${amount}\nAddress: {addr}",
                     reply_markup=kb)


# -------- CALLBACK --------
@bot.callback_query_handler(func=lambda c: True)
def cb(call):
    users = load_users()
    action, uid, rid = call.data.split("_")

    w = users[uid]["withdrawals"][rid]

    if action == "c":
        w["status"] = "Confirmed"
        bot.send_message(uid, f"Withdrawal #{rid} confirmed")

    if action == "r":
        w["status"] = "Rejected"
        users[uid]["balance"] += w["amount"]
        bot.send_message(uid, f"Withdrawal #{rid} rejected")

    if action == "b":
        users[uid]["banned"] = True
        bot.send_message(uid, "You are banned")

    save_users(users)


# -------- ADMIN ADD BALANCE --------
def admin_add_balance_step1(msg):
    target = msg.text.strip()
    m = bot.send_message(ADMIN_ID, "Enter amount")
    bot.register_next_step_handler(m, lambda m2: admin_add_balance_step2(m2, target))


def admin_add_balance_step2(msg, target):
    users = load_users()
    amount = float(msg.text)

    for uid, u in users.items():
        if target == uid or target == u["bot_id"]:
            users[uid]["balance"] += amount
            bot.send_message(uid, f"Admin added ${amount}")
            break

    save_users(users)
    bot.send_message(ADMIN_ID, "Done")


# -------- ADMIN WITHDRAW CHECK --------
def admin_withdraw_check(msg):
    users = load_users()
    rid = msg.text.strip()

    for uid, u in users.items():
        if rid in u["withdrawals"]:
            w = u["withdrawals"][rid]

            bot.send_message(ADMIN_ID,
                             f"Withdrawal #{rid}\nUser: {uid}\nBOT ID: {u['bot_id']}\nAmount: ${w['amount']}\nAddress: {w['address']}\nStatus: {w['status']}")
            return

    bot.send_message(ADMIN_ID, "Not found")


# -------- BROADCAST --------
def broadcast(msg):
    users = load_users()
    for u in users:
        try:
            bot.send_message(u, msg.text)
        except:
            pass

    bot.send_message(ADMIN_ID, "Broadcast Sent")


# -------- DOWNLOAD (TikTok + Facebook ONLY) --------
def download_media(msg):
    url = msg.text.strip()

    if not ("tiktok.com" in url or "facebook.com" in url or "fb.watch" in url):
        bot.send_message(msg.chat.id, "Only TikTok or Facebook supported")
        return

    try:
        bot.send_message(msg.chat.id, "Downloading...")

        ydl_opts = {
            "outtmpl": "media.%(ext)s",
            "format": "best"
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        for file in os.listdir():
            if file.startswith("media"):
                with open(file, "rb") as f:
                    bot.send_document(msg.chat.id, f)
                os.remove(file)

    except Exception as e:
        bot.send_message(msg.chat.id, f"Download Failed: {e}")


print("Bot Running...")
bot.infinity_polling()
