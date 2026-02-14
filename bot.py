import os
import json
import random
from datetime import datetime, timedelta
from functools import partial
from telebot import TeleBot, types
import yt_dlp

# -------- CONFIG --------
TOKEN = os.environ.get("TOKEN")
if not TOKEN:
    raise ValueError("Bot token not found!")
ADMIN_ID = 7983838654
DATA_FILE = "users.json"
BOT_ID_RANGE = (1000000000, 1999999999)
WITHDRAW_ID_RANGE = (10000, 99999)

bot = TeleBot(TOKEN)

# -------- INIT FILES --------
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({}, f)

def load_users():
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(DATA_FILE, "w") as f:
        json.dump(users, f, indent=4)

# -------- GENERATORS --------
def generate_ref_id():
    return str(random.randint(*BOT_ID_RANGE))

def generate_withdraw_id():
    return str(random.randint(*WITHDRAW_ID_RANGE))

# -------- MAIN MENU --------
def main_menu(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("💰 Balance", "🔗 Referral Link")
    markup.add("🆔 Get My ID", "📞 Customer")
    if str(chat_id) == str(ADMIN_ID):
        markup.add("⚙️ Admin Panel")
    bot.send_message(chat_id, "Main Menu", reply_markup=markup)

# -------- START --------
@bot.message_handler(commands=['start'])
def start(message):
    users = load_users()
    user_id = str(message.from_user.id)
    ref_id = None
    if message.text.startswith("/start "):
        ref_id = message.text.split()[1]

    if user_id not in users:
        users[user_id] = {
            "balance": 0.0,
            "points": 0,
            "referrals": 0,
            "withdrawn": 0.0,
            "ref_id": generate_ref_id(),
            "created_at": datetime.now().strftime("%Y-%m-%d"),
            "last_bonus": None,
            "banned": False,
            "withdrawals": {}  # Withdrawal history
        }
        if ref_id and ref_id in users:
            users[ref_id]["balance"] += 0.25
            users[ref_id]["points"] += 5
            users[ref_id]["referrals"] += 1
            bot.send_message(int(ref_id), f"🎉 You earned $0.25 and 5 points! Referral: {user_id}")

    save_users(users)
    bot.send_message(message.chat.id,
f"Welcome {message.from_user.first_name}!\n🎁 Enjoy bonus, referral, and downloads!")
    main_menu(message.chat.id)

# -------- BUTTON HANDLER --------
@bot.message_handler(func=lambda m: True)
def handler(message):
    users = load_users()
    user_id = str(message.from_user.id)
    if user_id not in users: return
    if users[user_id].get("banned"):
        bot.send_message(user_id, "🚫 You are banned.")
        return

    text = message.text
    is_admin = (user_id == str(ADMIN_ID))

    # -------- ADMIN PANEL --------
    if text == "⚙️ Admin Panel" and is_admin:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("📊 Stats", "💌 Broadcast", "🎁 Mass Gift")
        markup.add("🛠️ Ban User", "🛠️ Unban User", "📥 Withdrawal Check", "🔙 Back to Main Menu")
        bot.send_message(user_id, "⚙️ Admin Panel", reply_markup=markup)
        return

    if is_admin:
        if text == "📊 Stats":
            total_users = len(users)
            total_balance = sum(u.get("balance",0) for u in users.values())
            total_withdrawn = sum(u.get("withdrawn",0) for u in users.values())
            bot.send_message(user_id,
f"""📊 BOT STATS
👥 Total Users: {total_users}
💰 Total Balance: ${total_balance}
💸 Total Paid Out: ${total_withdrawn}""")
            return
        elif text == "💌 Broadcast":
            msg = bot.send_message(user_id, "Enter message to broadcast:")
            bot.register_next_step_handler(msg, admin_broadcast)
            return
        elif text == "🎁 Mass Gift":
            msg = bot.send_message(user_id, "Enter gift amount for all users:")
            bot.register_next_step_handler(msg, admin_mass_gift)
            return
        elif text == "🛠️ Ban User":
            msg = bot.send_message(user_id, "Enter user ID to ban:")
            bot.register_next_step_handler(msg, admin_ban)
            return
        elif text == "🛠️ Unban User":
            msg = bot.send_message(user_id, "Enter user ID to unban:")
            bot.register_next_step_handler(msg, admin_unban)
            return
        elif text == "📥 Withdrawal Check":
            msg = bot.send_message(user_id, "Enter Withdrawal ID (#XXXX):")
            bot.register_next_step_handler(msg, admin_withdrawal_check)
            return
        elif text == "🔙 Back to Main Menu":
            main_menu(user_id)
            return

    # -------- USER BUTTONS --------
    if text == "💰 Balance":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("💸 Withdraw", "🔙 Back")
        bot.send_message(message.chat.id,
f"💰 Balance: ${users[user_id]['balance']}\nPoints: {users[user_id]['points']}", reply_markup=markup)
    elif text == "🔙 Back":
        main_menu(message.chat.id)
    elif text == "💸 Withdraw":
        msg = bot.send_message(message.chat.id, "Enter withdrawal amount (min $1):")
        bot.register_next_step_handler(msg, process_withdrawal_request)
    elif text == "🔗 Referral Link":
        ref = users[user_id]["ref_id"]
        link = f"https://t.me/{bot.get_me().username}?start={ref}"
        bot.send_message(message.chat.id,
f"🔗 Referral Link:\n{link}\nReferrals: {users[user_id]['referrals']}\nEarn $0.25 per referral")
    elif text == "🆔 Get My ID":
        u = users[user_id]
        bot.send_message(message.chat.id, f"Your IDs:\nTelegram ID: {user_id}\nBot ID: {u['ref_id']}")
    elif text == "📞 Customer":
        bot.send_message(message.chat.id, "Contact: @scholes1")
    elif text.startswith("http"):
        download_media(message)
    else:
        bot.send_message(message.chat.id, "❌ Unknown command or button.")

# -------- DAILY BONUS --------
def daily_bonus(message):
    users = load_users()
    user_id = str(message.from_user.id)
    now = datetime.now()
    last = users[user_id].get("last_bonus")
    if last:
        last_time = datetime.fromisoformat(last)
        if now - last_time < timedelta(hours=24):
            bot.send_message(message.chat.id, "⏳ Daily bonus already claimed. Wait 24h.")
            return
    bonus = round(random.uniform(0.01, 0.05),2)
    users[user_id]["balance"] += bonus
    users[user_id]["points"] += 1
    users[user_id]["last_bonus"] = now.isoformat()
    save_users(users)
    bot.send_message(message.chat.id, f"🎁 You received ${bonus} and 1 point!")

# -------- DOWNLOAD MEDIA --------
def download_media(message):
    bot.send_message(message.chat.id, "Downloading...")
    url = message.text
    try:
        if any(x in url for x in ["tiktok.com","youtube.com","youtu.be","facebook.com","pinterest.com"]):
            ydl_opts = {'format':'best','outtmpl':'video.mp4'}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            with open("video.mp4","rb") as f:
                bot.send_video(message.chat.id,f)
            os.remove("video.mp4")
        else:
            bot.send_message(message.chat.id, "❌ Unsupported URL.")
    except Exception as e:
        bot.send_message(message.chat.id, f"Download failed: {str(e)}")

# -------- WITHDRAWAL SYSTEM --------
def process_withdrawal_request(message):
    users = load_users()
    user_id = str(message.from_user.id)
    try:
        amount = float(message.text.strip())
    except:
        bot.send_message(message.chat.id, "❌ Invalid amount")
        return
    if amount < 1:
        bot.send_message(message.chat.id, "❌ Minimum $1")
        return
    if users[user_id]['balance'] < amount:
        bot.send_message(message.chat.id, "❌ Not enough balance")
        return

    withdraw_id = generate_withdraw_id()
    users[user_id]['balance'] -= amount
    users[user_id]['withdrawn'] += amount
    users[user_id]['withdrawals'][withdraw_id] = {
        "amount": amount,
        "status": "Pending",
        "bot_id": users[user_id]['ref_id'],
        "requested_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    save_users(users)

    bot.send_message(message.chat.id,
f"✅ Your request has been approved. You can wait 2-12 hours for confirmation. Thank you.\nWithdrawal ID: #{withdraw_id}")
    bot.send_message(ADMIN_ID,
f"💸 NEW WITHDRAWAL REQUEST\nUser: {user_id}\nBot ID: {users[user_id]['ref_id']}\nAmount: ${amount}\nWithdrawal ID: #{withdraw_id}")

# -------- ADMIN WITHDRAWAL CHECK --------
def admin_withdrawal_check(message):
    wid = message.text.strip().replace("#","")
    users = load_users()
    found = False
    text = ""
    for uid, u in users.items():
        if wid in u.get("withdrawals",{}):
            w = u["withdrawals"][wid]
            text = f"""💰 Withdrawal ID: #{wid}
User: {uid}
Bot ID: {w['bot_id']}
Amount: ${w['amount']}
Status: {w['status']}
Requested at: {w['requested_at']}"""
            found = True
            break
    if not found:
        bot.send_message(ADMIN_ID, f"❌ Withdrawal ID #{wid} not found")
        return
    bot.send_message(ADMIN_ID, text)

# -------- ADMIN FUNCTIONS --------
def admin_broadcast(message):
    msg = message.text
    users = load_users()
    for uid in users:
        try: bot.send_message(uid, msg)
        except: pass
    bot.send_message(ADMIN_ID, f"✅ Broadcast sent to {len(users)} users")

def admin_mass_gift(message):
    try:
        amount = float(message.text.strip())
    except:
        bot.send_message(ADMIN_ID, "❌ Invalid amount")
        return
    users = load_users()
    for uid in users:
        users[uid]["balance"] += amount
    save_users(users)
    bot.send_message(ADMIN_ID, f"✅ Gift ${amount} sent to all users")

def admin_ban(message):
    uid = message.text.strip()
    users = load_users()
    if uid in users:
        users[uid]["banned"] = True
        save_users(users)
        bot.send_message(ADMIN_ID, f"✅ Banned {uid}")
        bot.send_message(uid, "🚫 You have been banned by admin!")

def admin_unban(message):
    uid = message.text.strip()
    users = load_users()
    if uid in users:
        users[uid]["banned"] = False
        save_users(users)
        bot.send_message(ADMIN_ID, f"✅ Unbanned {uid}")
        bot.send_message(uid, "✅ You have been unbanned by admin!")

# -------- RUN BOT --------
print("Bot Running...")
bot.infinity_polling()
