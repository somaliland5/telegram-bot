import os
import json
import random
from datetime import datetime, timedelta
from telebot import TeleBot, types
import yt_dlp
import threading

# ---------------- CONFIG ----------------
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("Bot token not found!")
ADMIN_ID = "7983838654"
DATA_FILE = "users.json"
PREMIUM_PRICE = 15
PAY_ADDRESS = "0x98ffcb29a4fc182d461ebdba54648d8fe24597ac"

bot = TeleBot(TOKEN)

# ---------------- INIT FILE ----------------
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({}, f)

def load_users():
    with open(DATA_FILE) as f:
        return json.load(f)

def save_users(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ---------------- MAIN MENU ----------------
def main_menu(uid):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("💰 Balance", "🔗 Referral", "🎁 Random Bonus")
    markup.add("💸 Withdraw", "🎬 Video Editing", "👤 Profile")
    if str(uid) == ADMIN_ID:
        markup.add("⚙️ Admin Panel")
    bot.send_message(uid, "🏠 Main Menu", reply_markup=markup)

# ---------------- START ----------------
@bot.message_handler(commands=["start"])
def start(message):
    uid = str(message.from_user.id)
    users = load_users()
    if uid not in users:
        users[uid] = {
            "balance": 0,
            "points": 0,
            "premium": False,
            "premium_expiry": None,
            "awaiting_payment": False,
            "banned": False,
            "ref_id": str(random.randint(1000,9999)),
            "referrals": 0
        }
        save_users(users)
    main_menu(uid)

# ---------------- REFERRAL ----------------
@bot.message_handler(func=lambda m: m.text=="🔗 Referral")
def referral(message):
    uid = str(message.from_user.id)
    users = load_users()
    link = f"https://t.me/{bot.get_me().username}?start={users[uid]['ref_id']}"
    bot.send_message(uid, f"🔗 Your referral link:\n{link}\nReferrals: {users[uid]['referrals']}")

# ---------------- BALANCE ----------------
@bot.message_handler(func=lambda m: m.text=="💰 Balance")
def balance(message):
    uid = str(message.from_user.id)
    users = load_users()
    u = users[uid]
    bot.send_message(uid, f"💰 Balance: ${u['balance']}\n⭐ Points: {u['points']}\n💎 Premium: {u['premium']}")

# ---------------- RANDOM BONUS ----------------
@bot.message_handler(func=lambda m: m.text=="🎁 Random Bonus")
def random_bonus(message):
    uid = str(message.from_user.id)
    users = load_users()
    amount = round(random.uniform(0.01,0.1),2)
    users[uid]["balance"] += amount
    users[uid]["points"] += 1
    save_users(users)
    bot.send_message(uid, f"🎁 You received ${amount} and 1 point!")

# ---------------- WITHDRAW ----------------
@bot.message_handler(func=lambda m: m.text=="💸 Withdraw")
def withdraw(message):
    uid = str(message.from_user.id)
    bot.send_message(uid, "Enter withdrawal amount:")
    bot.register_next_step_handler(message, process_withdraw)

def process_withdraw(message):
    uid = str(message.from_user.id)
    users = load_users()
    try:
        amount = float(message.text)
    except:
        bot.send_message(uid, "❌ Invalid amount")
        return
    if users[uid]["balance"] < amount:
        bot.send_message(uid, "❌ Not enough balance")
        return
    users[uid]["balance"] -= amount
    save_users(users)
    bot.send_message(uid, f"✅ Withdrawal of ${amount} requested")

# ---------------- VIDEO EDITING PREMIUM ----------------
@bot.message_handler(func=lambda m: m.text=="🎬 Video Editing")
def video_editing(message):
    uid = str(message.from_user.id)
    users = load_users()
    u = users[uid]

    # check premium expiry
    if u["premium"] and u["premium_expiry"]:
        expiry = datetime.fromisoformat(u["premium_expiry"])
        if expiry < datetime.now():
            u["premium"] = False
            u["premium_expiry"] = None
            save_users(users)
            bot.send_message(uid,"⚠️ Your premium expired")
            main_menu(uid)
            return

    if u["premium"]:
        bot.send_message(uid, "✅ Premium active. Send video link to download.")
        return

    # not premium → payment buttons
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ PAID", callback_data="paid"))
    markup.add(types.InlineKeyboardButton("❌ CANCEL", callback_data="cancel"))
    u["awaiting_payment"] = True
    save_users(users)
    bot.send_message(uid,
f"""🎬 Video Editing Premium
💰 Price: ${PREMIUM_PRICE}
Send USDT-BEP20 to:
{PAY_ADDRESS}
Click PAID when done.""",
reply_markup=markup)

# ---------------- PAYMENT CALLBACK ----------------
@bot.callback_query_handler(func=lambda c: True)
def payment_callback(call):
    uid = str(call.from_user.id)
    users = load_users()
    u = users[uid]

    if call.data=="cancel":
        u["awaiting_payment"] = False
        save_users(users)
        bot.send_message(uid,"❌ Payment cancelled")
        main_menu(uid)

    elif call.data=="paid":
        if u.get("awaiting_payment",False):
            u["premium"] = True
            u["premium_expiry"] = (datetime.now() + timedelta(days=30)).isoformat()
            u["awaiting_payment"] = False
            save_users(users)
            bot.send_message(uid,"✅ Premium activated! Send video link.")

            # notify admin
            bot.send_message(ADMIN_ID,
f"""💎 NEW PREMIUM USER
👤 ID: {uid}
💰 Payment: ${PREMIUM_PRICE}""")

# ---------------- MEDIA DOWNLOADER ----------------
@bot.message_handler(func=lambda m: m.text and m.text.startswith("http"))
def media_downloader(message):
    uid = str(message.from_user.id)
    users = load_users()
    u = users[uid]

    if not u["premium"]:
        bot.send_message(uid,"❌ Only premium users can download.")
        return

    url = message.text
    bot.send_message(uid,"⏳ Downloading...")

    try:
        ydl_opts = {'format':'best','outtmpl':'media.%(ext)s'}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

        with open(filename,"rb") as f:
            if info.get("ext","") in ["mp4","mkv","mov"]:
                bot.send_video(uid,f)
            else:
                bot.send_document(uid,f)
        os.remove(filename)
    except Exception as e:
        bot.send_message(uid,f"❌ Download failed: {e}")

# ---------------- PROFILE ----------------
@bot.message_handler(func=lambda m: m.text=="👤 Profile")
def profile(message):
    uid = str(message.from_user.id)
    users = load_users()
    u = users[uid]
    bot.send_message(uid,f"""👤 ID: {uid}
💰 Balance: ${u['balance']}
⭐ Points: {u['points']}
💎 Premium: {u['premium']}
Expires: {u.get('premium_expiry','-')}""")

# ---------------- ADMIN PANEL ----------------
@bot.message_handler(func=lambda m: m.text=="⚙️ Admin Panel")
def admin_panel(message):
    uid = str(message.from_user.id)
    if uid != ADMIN_ID:
        return
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📊 Stats","📢 Broadcast","💎 Premium Users","🔙 Back")
    bot.send_message(uid,"Admin Panel",reply_markup=markup)

@bot.message_handler(func=lambda m: m.text=="📊 Stats")
def admin_stats(message):
    uid = str(message.from_user.id)
    if uid != ADMIN_ID: return
    users = load_users()
    bot.send_message(uid,f"👥 Total Users: {len(users)}\n💎 Premium: {sum(1 for u in users.values() if u['premium'])}")

@bot.message_handler(func=lambda m: m.text=="📢 Broadcast")
def admin_broadcast(message):
    uid = str(message.from_user.id)
    if uid != ADMIN_ID: return
    bot.send_message(uid,"Send broadcast message:")
    bot.register_next_step_handler(message, do_broadcast)

def do_broadcast(message):
    users = load_users()
    for uid in users:
        try: bot.send_message(uid,message.text)
        except: pass
    bot.send_message(ADMIN_ID,"✅ Broadcast sent")

@bot.message_handler(func=lambda m: m.text=="💎 Premium Users")
def admin_premium_list(message):
    uid = str(message.from_user.id)
    if uid != ADMIN_ID: return
    users = load_users()
    premium_users = [k for k,v in users.items() if v["premium"]]
    bot.send_message(uid,"Premium Users:\n" + "\n".join(premium_users))

# ---------------- RUN BOT ----------------
print("Bot Running...")
bot.infinity_polling()
