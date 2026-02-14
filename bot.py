import os
import json
import random
from datetime import datetime, timedelta
from functools import partial
from telebot import TeleBot, types
import yt_dlp
import requests

# -------- CONFIG --------
TOKEN = os.environ.get("TOKEN")
if not TOKEN:
    raise ValueError("Bot token not found!")

ADMIN_ID = 7983838654
DATA_FILE = "users.json"
BOT_ID_RANGE = (1000000000, 1999999999)

# Binance API key for subscription verification
BINANCE_API_KEY = os.environ.get("BINANCE_API_KEY")

bot = TeleBot(TOKEN)

# -------- INIT FILES --------
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({}, f)

def load_users():
    with open(DATA_FILE, "r") as f:
        data = json.load(f)
        return data if data else {}

def save_users(users):
    with open(DATA_FILE, "w") as f:
        json.dump(users, f, indent=4)

def generate_ref_id():
    return str(random.randint(*BOT_ID_RANGE))

# -------- MAIN MENU --------
def main_menu(chat_id):
    users = load_users()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("💰 Balance", "🔗 Referral Link", "💸 Withdraw")
    markup.add("🎁 Random Bonus", "🏆 Weekly Rank")
    markup.add("🎬 Video Edit")
    markup.add("👤 Profile", "🆔 Get My ID")
    markup.add("📞 Customer")
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
            "premium": False,
            "premium_expiry": None,
            "ref_id": generate_ref_id(),
            "created_at": datetime.now().strftime("%Y-%m-%d"),
            "last_random": None,
            "banned": False
        }
        if ref_id and ref_id in users:
            users[ref_id]["balance"] += 0.5
            users[ref_id]["points"] += 5
            users[ref_id]["referrals"] += 1
            bot.send_message(int(ref_id), f"🎉 You earned $0.5 and 5 points! Referral: {user_id}")

    save_users(users)
    bot.send_message(message.chat.id,
f"Welcome {message.from_user.first_name}!\n\n🎁 Enjoy earning points, random bonus, and weekly leaderboard!")
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
        markup.add("📊 Stats", "➕ Add Balance", "🎁 Random Gift")
        markup.add("🛠️ Unban User", "📝 Broadcast")
        markup.add("🔙 Back to Main Menu")
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
        elif text == "➕ Add Balance":
            msg = bot.send_message(user_id, "Enter User Telegram ID to add balance:")
            bot.register_next_step_handler(msg, admin_add_balance_step1)
            return
        elif text == "🎁 Random Gift":
            msg = bot.send_message(user_id, "Enter amount to send as random gift:")
            bot.register_next_step_handler(msg, admin_random_gift)
            return
        elif text == "🛠️ Unban User":
            msg = bot.send_message(user_id, "Enter User Telegram ID to unban:")
            bot.register_next_step_handler(msg, admin_unban_user)
            return
        elif text == "📝 Broadcast":
            msg = bot.send_message(user_id, "Enter your message (or video/photo URL):")
            bot.register_next_step_handler(msg, admin_broadcast)
            return
        elif text == "🔙 Back to Main Menu":
            main_menu(user_id)
            return

    # -------- USER BUTTONS --------
    if text == "💰 Balance":
        bot.send_message(message.chat.id, f"💰 Balance: ${users[user_id]['balance']}\nPoints: {users[user_id]['points']}")
    elif text == "🔗 Referral Link":
        ref = users[user_id]["ref_id"]
        link = f"https://t.me/{bot.get_me().username}?start={ref}"
        bot.send_message(message.chat.id,
f"🔗 Referral Link:\n{link}\nReferrals: {users[user_id]['referrals']}\nEarn $0.5 and 5 points per referral")
    elif text == "💸 Withdraw":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("USDT-BEP20")
        markup.add("🔙 Back")
        bot.send_message(message.chat.id, "Select Withdrawal Method:", reply_markup=markup)
    elif text == "🔙 Back":
        main_menu(message.chat.id)
    elif text == "USDT-BEP20":
        msg = bot.send_message(message.chat.id, "Enter withdrawal amount (Min $1):")
        bot.register_next_step_handler(msg, partial(withdraw_amount, method="USDT-BEP20"))
    elif text == "🎁 Random Bonus":
        give_random_bonus(message)
    elif text == "🏆 Weekly Rank":
        show_leaderboard(message)
    elif text == "👤 Profile":
        u = users[user_id]
        premium_text = "✅ Premium Active" if u.get("premium") else "❌ Not Premium"
        bot.send_message(message.chat.id,
f"""👤 Profile
Telegram ID: {user_id}
Bot ID: {u['ref_id']}
Balance: {u['balance']}
Points: {u['points']}
Referrals: {u['referrals']}
{premium_text}""")
    elif text == "🆔 Get My ID":
        u = users[user_id]
        bot.send_message(message.chat.id, f"Your IDs:\nTelegram ID: {user_id}\nBot ID: {u['ref_id']}")
    elif text == "📞 Customer":
        bot.send_message(message.chat.id, "Contact: @scholes1")
    elif text == "🎬 Video Edit":
        handle_premium_access(message)
    elif text.startswith("http"):
        download_media(message)
    else:
        bot.send_message(message.chat.id, "❌ Unknown command or button.")

# -------- PREMIUM VIDEO EDIT FEATURE --------
def handle_premium_access(message):
    users = load_users()
    user_id = str(message.from_user.id)
    user = users[user_id]
    now = datetime.now()
    # Check if user is premium and subscription valid
    if user.get("premium") and user.get("premium_expiry"):
        expiry = datetime.fromisoformat(user["premium_expiry"])
        if expiry > now:
            bot.send_message(message.chat.id, "🎬 You have access to video editing. Send your video URL:")
            bot.register_next_step_handler(message, download_media)
            return
        else:
            # Expired
            user["premium"] = False
            user["premium_expiry"] = None
            save_users(users)
    # Not premium, ask to pay
    bot.send_message(message.chat.id, "💳 Video editing is premium ($15/month). Send 'PAY' to pay via Binance.")
    bot.register_next_step_handler(message, handle_binance_payment)

def handle_binance_payment(message):
    users = load_users()
    user_id = str(message.from_user.id)
    if message.text.upper() != "PAY":
        bot.send_message(message.chat.id, "❌ Payment cancelled.")
        return
    # Simulate payment verification
    success = simulate_binance_payment(user_id, 15)
    if success:
        users[user_id]["premium"] = True
        users[user_id]["premium_expiry"] = (datetime.now() + timedelta(days=30)).isoformat()
        save_users(users)
        bot.send_message(message.chat.id, "✅ Payment confirmed. You can now access Video Editing.")
    else:
        bot.send_message(message.chat.id, "❌ Payment failed. Try again later.")

def simulate_binance_payment(user_id, amount):
    """
    Placeholder: Implement Binance API verification here
    """
    # For now, we simulate always successful
    return True

# -------- RANDOM BONUS --------
def give_random_bonus(message):
    users = load_users()
    user_id = str(message.from_user.id)
    now = datetime.now()
    last = users[user_id].get("last_random")
    if last:
        last_time = datetime.fromisoformat(last)
        if now - last_time < timedelta(hours=12):
            bot.send_message(message.chat.id, "⏳ You can get random bonus once every 12 hours.")
            return
    bonus = round(random.uniform(0.01, 0.1),2)
    users[user_id]["balance"] += bonus
    users[user_id]["points"] += 1
    users[user_id]["last_random"] = now.isoformat()
    save_users(users)
    bot.send_message(message.chat.id, f"🎁 You received ${bonus} and 1 point!")

# -------- LEADERBOARD --------
def show_leaderboard(message):
    users = load_users()
    leaderboard = sorted(users.items(), key=lambda x: x[1]["points"], reverse=True)
    text = "🏆 Weekly Leaderboard\n\n"
    for i, (uid, info) in enumerate(leaderboard[:100], 1):
        text += f"{i}. {uid} | Points: {info['points']} 💎\n"
    bot.send_message(message.chat.id, text)

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
        bot.send_message(chat_id, "❌ Minimum withdrawal $1")
        return
    if users[user_id]["balance"] < amount:
        bot.send_message(chat_id, "❌ Not enough balance")
        return
    msg = bot.send_message(chat_id, "Enter your USDT-BEP20 wallet address (must start with 0):")
    bot.register_next_step_handler(msg, partial(process_withdraw, amount=amount, method=method))

def process_withdraw(message, amount, method):
    users = load_users()
    user_id = str(message.from_user.id)
    chat_id = message.chat.id
    address = message.text
    withdrawal_id = random.randint(10000, 99999)
    users[user_id]["balance"] -= amount
    users[user_id]["withdrawn"] += amount
    users[user_id]["points"] += 10
    save_users(users)
    bot.send_message(chat_id,
f"""✅ Withdrawal Request Sent
🧾 ID: #{withdrawal_id}
💰 Amount: ${amount}
⏳ It may take 2-12 hours to confirm.""")

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("CONFIRM ✅", callback_data=f"confirm_{user_id}_{amount}_{withdrawal_id}"))
    markup.add(types.InlineKeyboardButton("REJECT ❌", callback_data=f"reject_{user_id}_{amount}_{withdrawal_id}"))
    markup.add(types.InlineKeyboardButton("BAN 🚫", callback_data=f"ban_{user_id}_{amount}_{withdrawal_id}"))

    bot.send_message(ADMIN_ID,
f"""💸 NEW WITHDRAWAL REQUEST
👤 Telegram ID: {user_id}
💰 Amount: ${amount}
📬 Address: {address}
🧾 Withdrawal ID: #{withdrawal_id}
👥 Referrals: {users[user_id]['referrals']}
🆔 Bot ID: {users[user_id]['ref_id']}""",
        reply_markup=markup)

# -------- CALLBACK HANDLER --------
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    users = load_users()
    data = call.data.split("_")
    action = data[0]
    user_id = data[1]
    amount = data[2]
    wid = data[3]
    if action == "confirm":
        bot.send_message(user_id,
f"""💸 Payment Sent Successfully!
🧾 Withdrawal ID: #{wid}
💰 Amount: ${amount}
🔄 Method: USDT-BEP20""")
    elif action == "reject":
        users[user_id]["balance"] += float(amount)
        save_users(users)
        bot.send_message(user_id, f"❌ Your withdrawal #{wid} has been rejected. Amount refunded: ${amount}")
    elif action == "ban":
        users[user_id]["banned"] = True
        save_users(users)
        bot.send_message(user_id, "🚫 You have been banned by admin.")

# -------- DOWNLOAD MEDIA --------
def download_media(message):
    bot.send_message(message.chat.id, "Downloading...")
    url = message.text
    try:
        if any(x in url for x in ["tiktok.com","youtube.com","youtu.be","facebook.com","pinterest.com"]):
            ydl_opts = {'format': 'best', 'outtmpl': 'video.mp4'}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            with open("video.mp4","rb") as f:
                bot.send_video(message.chat.id,f)
            os.remove("video.mp4")
        else:
            bot.send_message(message.chat.id,"❌ Unsupported URL.")
    except Exception as e:
        bot.send_message(message.chat.id, f"Download failed: {str(e)}")

# -------- ADMIN FUNCTIONS --------
def admin_add_balance_step1(message):
    user_id_target = message.text.strip()
    msg = bot.send_message(ADMIN_ID, f"Enter amount to add to {user_id_target}:")
    bot.register_next_step_handler(msg, partial(admin_add_balance_step2, user_id_target))

def admin_add_balance_step2(message, user_id_target):
    amount = float(message.text.strip())
    users = load_users()
    if user_id_target in users:
        users[user_id_target]["balance"] += amount
        save_users(users)
        bot.send_message(ADMIN_ID, f"✅ Added ${amount} to {user_id_target}")
        bot.send_message(user_id_target, f"💰 Admin added ${amount} to your balance!")

def admin_random_gift(message):
    amount = float(message.text.strip())
    users = load_users()
    if not users:
        bot.send_message(ADMIN_ID, "No users found")
        return
    user = random.choice(list(users.keys()))
    users[user]["balance"] += amount
    save_users(users)
    bot.send_message(user, f"🎁 RANDOM GIFT\nYou received ${amount}!")
    bot.send_message(ADMIN_ID, f"✅ Gift Sent\nUser: {user}\nAmount: ${amount}")

def admin_unban_user(message):
    user_id_target = message.text.strip()
    users = load_users()
    if user_id_target in users:
        users[user_id_target]["banned"] = False
        save_users(users)
        bot.send_message(ADMIN_ID, f"✅ Unbanned {user_id_target}")
        bot.send_message(user_id_target, "✅ You have been unbanned by admin!")

def admin_broadcast(message):
    users = load_users()
    text = message.text
    count = 0
    for uid in users:
        try:
            bot.send_message(uid,text)
            count += 1
        except:
            pass
    bot.send_message(ADMIN_ID, f"✅ Broadcast sent to {count} users")

# -------- RUN BOT --------
print("Bot Running...")
bot.infinity_polling()
