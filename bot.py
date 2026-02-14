import os
import json
import random
from datetime import datetime, timedelta
from functools import partial
from telebot import TeleBot, types
import yt_dlp

# ---------------- CONFIG ----------------
TOKEN = os.environ.get("TOKEN")
ADMIN_ID = 7983838654
DATA_FILE = "users.json"

BOT_ID_RANGE = (1000000000, 1999999999)
WITHDRAW_ID_RANGE = (10000, 99999)

bot = TeleBot(TOKEN)

# ---------------- FILE ----------------
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({}, f)

def load_users():
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_users(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

def generate_bot_id():
    return str(random.randint(*BOT_ID_RANGE))

def generate_withdraw_id():
    return str(random.randint(*WITHDRAW_ID_RANGE))

# ---------------- MAIN MENU ----------------
def main_menu(cid):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("💰 Balance", "🔗 Referral Link")
    markup.add("🆔 Get My ID")
    markup.add("📞 Customer")

    if str(cid) == str(ADMIN_ID):
        markup.add("⚙️ Admin Panel")

    bot.send_message(cid, "Main Menu", reply_markup=markup)

# ---------------- START ----------------
@bot.message_handler(commands=['start'])
def start(message):

    users = load_users()
    uid = str(message.from_user.id)

    ref = None
    if len(message.text.split()) > 1:
        ref = message.text.split()[1]

    if uid not in users:

        users[uid] = {
            "balance":0,
            "points":0,
            "referrals":0,
            "withdrawn":0,
            "bot_id":generate_bot_id(),
            "withdrawals":{},
            "banned":False
        }

        # referral reward
        if ref:
            for u in users:
                if users[u]["bot_id"] == ref:
                    users[u]["balance"] += 0.25
                    users[u]["referrals"] += 1
                    bot.send_message(int(u),"🎉 New referral earned $0.25")
                    break

    save_users(users)

    bot.send_message(uid,
"Hi Welcome You can Send Link And You Get Vedio Easy. 😃")

    main_menu(uid)

# ---------------- USER BUTTONS ----------------
@bot.message_handler(func=lambda m: True)
def handler(message):

    users = load_users()
    uid = str(message.from_user.id)

    if uid not in users:
        return

    if users[uid]["banned"]:
        bot.send_message(uid,"🚫 You are banned")
        return

    text = message.text

    # ---------- BALANCE ----------
    if text == "💰 Balance":

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("💸 Withdraw")
        markup.add("🔙 Back")

        bot.send_message(uid,
f"💰 Balance: ${users[uid]['balance']}",
reply_markup=markup)

    # ---------- WITHDRAW ----------
    elif text == "💸 Withdraw":
        msg = bot.send_message(uid,"Enter Amount (min $1)")
        bot.register_next_step_handler(msg, withdraw_amount)

    # ---------- REF LINK ----------
    elif text == "🔗 Referral Link":

        username = bot.get_me().username
        bot.send_message(uid,
f"""🔗 Referral Link:
https://t.me/{username}?start={users[uid]['bot_id']}

Referrals: {users[uid]['referrals']}
Earn $0.25 per referral""")

    # ---------- ID ----------
    elif text == "🆔 Get My ID":
        bot.send_message(uid,
f"Telegram ID: {uid}\nBOT ID: {users[uid]['bot_id']}")

    # ---------- CUSTOMER ----------
    elif text == "📞 Customer":
        bot.send_message(uid,"Contact: @scholes1")

    # ---------- BACK ----------
    elif text == "🔙 Back":
        main_menu(uid)

    # ---------- ADMIN PANEL ----------
    elif text == "⚙️ Admin Panel" and uid == str(ADMIN_ID):

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("📊 Stats","➕ Add Balance")
        markup.add("🛠 Ban/Unban","🔍 Withdrawal Check")
        markup.add("📢 Broadcast")
        markup.add("🔙 Back")

        bot.send_message(uid,"Admin Panel",reply_markup=markup)

    # ---------- ADMIN STATS ----------
    elif text == "📊 Stats" and uid == str(ADMIN_ID):

        total_users = len(users)
        total_balance = sum(u["balance"] for u in users.values())

        bot.send_message(uid,
f"Users: {total_users}\nTotal Balance: ${total_balance}")

    # ---------- ADMIN ADD BAL ----------
    elif text == "➕ Add Balance" and uid == str(ADMIN_ID):
        msg = bot.send_message(uid,"Send BOT ID or Telegram ID")
        bot.register_next_step_handler(msg, admin_add_balance_step1)

    # ---------- BAN UNBAN ----------
    elif text == "🛠 Ban/Unban" and uid == str(ADMIN_ID):
        msg = bot.send_message(uid,"Send Telegram ID")
        bot.register_next_step_handler(msg, admin_ban)

    # ---------- WITHDRAW CHECK ----------
    elif text == "🔍 Withdrawal Check" and uid == str(ADMIN_ID):
        msg = bot.send_message(uid,"Enter Withdraw ID")
        bot.register_next_step_handler(msg, admin_withdraw_check)

    # ---------- BROADCAST ----------
    elif text == "📢 Broadcast" and uid == str(ADMIN_ID):
        msg = bot.send_message(uid,"Send Broadcast Message")
        bot.register_next_step_handler(msg, admin_broadcast)

    # ---------- LINK DOWNLOAD ----------
    elif text.startswith("http"):
        download_media(message)

# ---------------- WITHDRAW ----------------
def withdraw_amount(message):

    users = load_users()
    uid = str(message.from_user.id)

    try:
        amount = float(message.text)
    except:
        bot.send_message(uid,"Invalid amount")
        return

    if amount < 1:
        bot.send_message(uid,"Minimum $1")
        return

    if users[uid]["balance"] < amount:
        bot.send_message(uid,"Not enough balance")
        return

    wid = generate_withdraw_id()

    users[uid]["balance"] -= amount
    users[uid]["withdrawals"][wid] = {
        "amount":amount,
        "status":"Pending",
        "time":str(datetime.now())
    }

    save_users(users)

    bot.send_message(uid,
f"""✅ Request #{wid} Sent!

💵 Amount: ${amount}
💸 Fee (0.00%): -$0.00
🧾 Net Due: ${amount}

⏳ Your request is pending approval
🕒 Pending time: 6–12 hours
🙏 Please be patient 🙂""")

    # admin notification
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("CONFIRM",callback_data=f"confirm_{uid}_{wid}"))
    markup.add(types.InlineKeyboardButton("REJECT",callback_data=f"reject_{uid}_{wid}"))
    markup.add(types.InlineKeyboardButton("BAN",callback_data=f"ban_{uid}_{wid}"))

    bot.send_message(ADMIN_ID,
f"""💸 NEW WITHDRAW

User: {uid}
BOT ID: {users[uid]['bot_id']}
Referrals: {users[uid]['referrals']}
Amount: ${amount}
Withdraw ID: #{wid}""",
reply_markup=markup)

# ---------------- CALLBACK ----------------
@bot.callback_query_handler(func=lambda c:True)
def callback(call):

    users = load_users()
    data = call.data.split("_")

    action = data[0]
    uid = data[1]
    wid = data[2]

    if action == "confirm":
        users[uid]["withdrawals"][wid]["status"]="Confirmed"
        users[uid]["withdrawn"] += users[uid]["withdrawals"][wid]["amount"]

        bot.send_message(uid,f"✅ Withdrawal #{wid} Confirmed")

    elif action == "reject":
        amt = users[uid]["withdrawals"][wid]["amount"]
        users[uid]["balance"] += amt
        users[uid]["withdrawals"][wid]["status"]="Rejected"

        bot.send_message(uid,f"❌ Withdrawal #{wid} Rejected")

    elif action == "ban":
        users[uid]["banned"]=True
        bot.send_message(uid,"🚫 You are banned")

    save_users(users)

# ---------------- ADMIN FUNCTIONS ----------------
def admin_add_balance_step1(message):

    users = load_users()
    target = message.text.strip()

    # allow BOT ID
    for uid in users:
        if target == uid or target == users[uid]["bot_id"]:

            msg = bot.send_message(ADMIN_ID,"Enter amount")
            bot.register_next_step_handler(msg, admin_add_balance_step2, uid)
            return

    bot.send_message(ADMIN_ID,"User not found")

def admin_add_balance_step2(message,uid):

    users = load_users()
    amount = float(message.text)

    users[uid]["balance"] += amount
    save_users(users)

    bot.send_message(ADMIN_ID,"Balance added")
    bot.send_message(uid,f"💰 Admin added ${amount}")

def admin_ban(message):
    users = load_users()
    uid = message.text.strip()

    if uid in users:
        users[uid]["banned"] = not users[uid]["banned"]
        save_users(users)
        bot.send_message(uid,"Ban status changed")

def admin_withdraw_check(message):

    users = load_users()
    wid = message.text.strip()

    for uid in users:
        if wid in users[uid]["withdrawals"]:
            bot.send_message(ADMIN_ID,
f"""Withdraw #{wid}
User {uid}
BOT ID {users[uid]['bot_id']}
Status {users[uid]['withdrawals'][wid]['status']}""")
            return

def admin_broadcast(message):

    users = load_users()
    text = message.text

    for u in users:
        try:
            bot.send_message(u,text)
        except:
            pass

# ---------------- DOWNLOAD ----------------
    import requests

def download_media(message):
    url = message.text.strip()
    bot.send_message(message.chat.id, "Downloading...")

    try:
        # TikTok sawir
        if "tiktok.com" in url and "/photo/" in url:
            resp = requests.get(url, stream=True)
            if resp.status_code == 200:
                with open("photo.jpg","wb") as f:
                    for chunk in resp.iter_content(1024):
                        f.write(chunk)
                with open("photo.jpg","rb") as f:
                    bot.send_photo(message.chat.id, f)
                os.remove("photo.jpg")
                return
            else:
                bot.send_message(message.chat.id,"❌ Failed to download photo")
                return

        # Video (TikTok / YouTube / Facebook / Pinterest)
        ydl_opts = {"format":"best","outtmpl":"media.mp4"}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        with open("media.mp4","rb") as f:
            bot.send_video(message.chat.id,f)
        os.remove("media.mp4")

    except Exception as e:
        bot.send_message(message.chat.id,f"❌ Download failed: {str(e)}")

# ---------------- RUN ----------------
print("Bot Running...")
bot.infinity_polling
