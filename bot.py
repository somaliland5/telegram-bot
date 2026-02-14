import os
import json
import random
from datetime import datetime, timedelta
from functools import partial
from telebot import TeleBot, types
import yt_dlp

# ---------- CONFIG ----------
TOKEN = os.getenv("TOKEN")
ADMIN_ID = "7983838654"
CUSTOMER = "@scholes1"
DATA_FILE = "users.json"

bot = TeleBot(TOKEN)

# ---------- INIT FILES ----------
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({}, f)

def load_users():
    with open(DATA_FILE) as f:
        return json.load(f)

def save_users(users):
    with open(DATA_FILE, "w") as f:
        json.dump(users, f, indent=4)

def generate_bot_id():
    return str(random.randint(1000000000, 9999999999))

def generate_referral():
    return str(random.randint(100000000000000, 999999999999999))

def generate_withdraw_id():
    return str(random.randint(1000000, 9999999))

# ---------- MAIN MENU ----------
def main_menu(chat_id):
    users = load_users()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("💰 Balance")
    markup.add("🔗 Referral")
    markup.add("🆔 Get ID")
    if str(chat_id) == ADMIN_ID:
        markup.add("⚙️ Admin Panel")
    markup.add("📞 Customer")
    bot.send_message(chat_id, "🏠 Main Menu", reply_markup=markup)

# ---------- START ----------
@bot.message_handler(commands=['start'])
def start(message):
    users = load_users()
    uid = str(message.from_user.id)
    ref = None
    if len(message.text.split()) > 1:
        ref = message.text.split()[1]

    if uid not in users:
        users[uid] = {
            "balance": 0.0,
            "bot_id": generate_bot_id(),
            "referral_id": generate_referral(),
            "referrals": 0,
            "withdrawn": 0.0,
            "banned": False
        }

        if ref:
            for u in users:
                if users[u]["referral_id"] == ref:
                    users[u]["balance"] += 0.25
                    users[u]["referrals"] += 1
                    bot.send_message(int(u), f"🎉 You earned $0.25! Referral: {uid}")

    save_users(users)
    bot.send_message(uid, f"Welcome {message.from_user.first_name}!\n🎁 Enjoy bonuses, referral rewards, and weekly leaderboard!")
    main_menu(uid)

# ---------- BUTTON HANDLER ----------
@bot.message_handler(func=lambda m: True)
def handler(message):
    users = load_users()
    uid = str(message.from_user.id)
    if uid not in users: return
    if users[uid].get("banned"): 
        bot.send_message(uid, "🚫 You are banned.")
        return

    text = message.text
    is_admin = (uid == str(ADMIN_ID))

    # ----- ADMIN PANEL -----
    if text == "⚙️ Admin Panel" and is_admin:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("📊 Stats", "➕ Add Balance", "🛠️ Unban User", "🔙 Back to Main Menu")
        bot.send_message(uid, "⚙️ Admin Panel", reply_markup=markup)
        return

    if is_admin:
        if text == "📊 Stats":
            total_users = len(users)
            total_balance = sum(u.get("balance",0) for u in users.values())
            total_withdrawn = sum(u.get("withdrawn",0) for u in users.values())
            bot.send_message(uid,
f"""📊 BOT STATS
👥 Users: {total_users}
💰 Total Balance: ${total_balance}
💸 Total Paid: ${total_withdrawn}""")
            return
        elif text == "➕ Add Balance":
            msg = bot.send_message(uid, "Enter Telegram ID to add balance:")
            bot.register_next_step_handler(msg, admin_add_balance_step1)
            return
        elif text == "🛠️ Unban User":
            msg = bot.send_message(uid, "Enter Telegram ID to unban:")
            bot.register_next_step_handler(msg, admin_unban_user)
            return
        elif text == "🔙 Back to Main Menu":
            main_menu(uid)
            return

    # ----- USER BUTTONS -----
    if text == "💰 Balance":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("💸 Withdraw", "🔙 Back")
        bot.send_message(uid, f"💰 Balance: ${users[uid]['balance']}", reply_markup=markup)
    elif text == "🔙 Back":
        main_menu(uid)
    elif text == "💸 Withdraw":
        msg = bot.send_message(uid, "Enter amount to withdraw (Min $1):")
        bot.register_next_step_handler(msg, withdraw_step1)
    elif text == "🔗 Referral":
        link = f"https://t.me/{bot.get_me().username}?start={users[uid]['referral_id']}"
        bot.send_message(uid, f"🔗 Referral Link:\n{link}\nReferrals: {users[uid]['referrals']}")
    elif text == "🆔 Get ID":
        bot.send_message(uid, f"Telegram ID: {uid}\nBot ID: {users[uid]['bot_id']}")
    elif text == "📞 Customer":
        bot.send_message(uid, f"Contact: {CUSTOMER}")
    elif text.startswith("http"):
        download_media(message)
    else:
        bot.send_message(uid, "❌ Unknown command or button.")

# ---------- DOWNLOAD MEDIA ----------
def download_media(message):
    url = message.text
    bot.send_message(message.chat.id, "⏳ Downloading...")
    try:
        ydl_opts = {'format': 'best', 'outtmpl': 'video.mp4'}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        with open("video.mp4", "rb") as f:
            bot.send_video(message.chat.id, f)
        os.remove("video.mp4")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Failed: {str(e)}")

# ---------- WITHDRAWAL ----------
def withdraw_step1(message):
    users = load_users()
    uid = str(message.from_user.id)
    try:
        amount = float(message.text)
    except:
        bot.send_message(uid, "❌ Invalid amount")
        return
    if amount < 1 or users[uid]["balance"] < amount:
        bot.send_message(uid, "❌ Insufficient balance")
        return
    withdraw_id = generate_withdraw_id()
    users[uid]["balance"] -= amount
    users[uid]["withdrawn"] += amount
    save_users(users)

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("CONFIRM ✅", callback_data=f"confirm_{uid}_{amount}_{withdraw_id}"))
    markup.add(types.InlineKeyboardButton("CANCEL ❌", callback_data=f"cancel_{uid}_{amount}_{withdraw_id}"))

    bot.send_message(ADMIN_ID,
f"💸 Withdrawal Request\nUser: {uid}\nAmount: ${amount}\nID: {withdraw_id}", reply_markup=markup)
    bot.send_message(uid, f"💸 Withdrawal request sent!\nWaiting admin confirmation.")

# ---------- CALLBACK HANDLER ----------
@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    users = load_users()
    data = call.data.split("_")
    action, uid, amount, wid = data[0], data[1], float(data[2]), data[3]

    if action == "confirm":
        bot.send_message(uid, f"✅ Withdrawal confirmed!\nAmount: ${amount}")
    elif action == "cancel":
        users[uid]["balance"] += amount
        save_users(users)
        bot.send_message(uid, f"❌ Withdrawal canceled. Amount refunded.")

# ---------- ADMIN FUNCTIONS ----------
def admin_add_balance_step1(message):
    uid_target = message.text.strip()
    msg = bot.send_message(ADMIN_ID, f"Enter amount to add to {uid_target}:")
    bot.register_next_step_handler(msg, partial(admin_add_balance_step2, uid_target))

def admin_add_balance_step2(message, uid_target):
    amount = float(message.text.strip())
    users = load_users()
    if uid_target in users:
        users[uid_target]["balance"] += amount
        save_users(users)
        bot.send_message(ADMIN_ID, f"✅ Added ${amount} to {uid_target}")
        bot.send_message(uid_target, f"💰 Admin added ${amount} to your balance!")

def admin_unban_user(message):
    uid_target = message.text.strip()
    users = load_users()
    if uid_target in users:
        users[uid_target]["banned"] = False
        save_users(users)
        bot.send_message(ADMIN_ID, f"✅ Unbanned {uid_target}")
        bot.send_message(uid_target, "✅ You have been unbanned by admin!")

# ---------- RUN BOT ----------
print("Bot running...")
bot.infinity_polling()
