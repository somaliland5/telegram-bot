import telebot
import json
import random
import os
import yt_dlp

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 7983838654

bot = telebot.TeleBot(TOKEN)

USERS_FILE = "users.json"
WITHDRAWALS_FILE = "withdrawals.json"

# ---------------- DATABASE ----------------

def load_users():
    try:
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_users(data):
    with open(USERS_FILE, "w") as f:
        json.dump(data, f, indent=4)

def load_withdrawals():
    try:
        with open(WITHDRAWALS_FILE, "r") as f:
            return json.load(f)
    except:
        return []

def save_withdrawals(data):
    with open(WITHDRAWALS_FILE, "w") as f:
        json.dump(data, f, indent=4)

users = load_users()
withdrawals = load_withdrawals()

def random_bot_id():
    return str(random.randint(1000000000, 9999999999))

# ---------------- CREATE USER ----------------

def create_user(uid, ref=None):
    uid = str(uid)
    if uid not in users:
        users[uid] = {
            "bot_id": random_bot_id(),
            "balance": 0,
            "banned": False
        }
        if ref:
            for u in users:
                if users[u]["bot_id"] == ref:
                    users[u]["balance"] += 0.25
        save_users(users)

# ---------------- START ----------------

@bot.message_handler(commands=["start"])
def start(message):
    args = message.text.split()
    ref = args[1] if len(args) > 1 else None

    create_user(message.from_user.id, ref)

    if users[str(message.from_user.id)]["banned"]:
        return

    kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("💰 Balance", "👥 Referral")
    kb.add("🆔 BOT ID", "💸 Withdraw")
    if message.from_user.id == ADMIN_ID:
        kb.add("⚙️ Admin Panel")

    bot.send_message(message.chat.id, "Welcome! Updated buttons available now.", reply_markup=kb)

# ---------------- BALANCE ----------------

@bot.message_handler(func=lambda m: m.text == "💰 Balance")
def balance(message):
    uid = str(message.from_user.id)
    bot.send_message(message.chat.id, f"💰 Balance: ${users[uid]['balance']}")

# ---------------- REFERRAL ----------------

@bot.message_handler(func=lambda m: m.text == "👥 Referral")
def ref(message):
    uid = str(message.from_user.id)
    link = f"https://t.me/{bot.get_me().username}?start={users[uid]['bot_id']}"
    bot.send_message(message.chat.id, f"🔗 Referral Link:\n{link}")

# ---------------- BOT ID ----------------

@bot.message_handler(func=lambda m: m.text == "🆔 BOT ID")
def bot_id(message):
    uid = str(message.from_user.id)
    bot.send_message(message.chat.id, f"🆔 BOT ID: {users[uid]['bot_id']}")

# ---------------- WITHDRAW ----------------

withdraw_cache = {}

@bot.message_handler(func=lambda m: m.text == "💸 Withdraw")
def withdraw(message):
    bot.send_message(message.chat.id, "Send amount:")
    bot.register_next_step_handler(message, withdraw_amount)

def withdraw_amount(message):
    try:
        amount = float(message.text)
        uid = str(message.from_user.id)
        if amount > users[uid]["balance"]:
            bot.send_message(message.chat.id, "❌ Not enough balance")
            return
        withdraw_cache[uid] = amount
        bot.send_message(message.chat.id, "Send USDT BEP20 address:")
        bot.register_next_step_handler(message, withdraw_address)
    except:
        bot.send_message(message.chat.id, "Invalid amount")

def withdraw_address(message):
    uid = str(message.from_user.id)
    address = message.text
    if not address.startswith("0"):
        bot.send_message(message.chat.id, "❌ Address must start with 0")
        return
    amount = withdraw_cache[uid]
    req_id = random.randint(10000, 99999)

    bot.send_message(message.chat.id, f"""
✅ Request #{req_id} Sent!
💵 Amount: ${amount}
🧾 Net Due: ${amount}
⏳ Pending 6-12 hours
""")

    withdrawal_data = {
        "user_id": uid,
        "bot_id": users[uid]["bot_id"],
        "amount": amount,
        "address": address,
        "status": "pending"
    }
    withdrawals.append(withdrawal_data)
    save_withdrawals(withdrawals)

    bot.send_message(ADMIN_ID, f"""
📤 Withdrawal Request
User: {uid}
BOT ID: {users[uid]['bot_id']}
Amount: {amount}
Address: {address}
Commands:
CONFIRM {uid}
REJECT {uid}
BAN {uid}
""")

# ---------------- VIDEO / PHOTO / LINK DOWNLOAD ----------------
def download_media(chat_id, url):
    try:

        # -------- TIKTOK PHOTO --------
        if "tiktok.com" in url and "/photo/" in url:

            r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
            soup = BeautifulSoup(r.text, "html.parser")

            meta = soup.find("meta", property="og:image")

            if not meta:
                bot.send_message(chat_id, "❌ Photo lama helin")
                return

            image_url = meta["content"]

            img = requests.get(image_url).content

            filename = "tiktok_photo.jpg"
            with open(filename, "wb") as f:
                f.write(img)

            bot.send_photo(chat_id, open(filename, "rb"))
            os.remove(filename)
            return

        # -------- VIDEO (YouTube / TikTok / Facebook) --------
        if "youtube.com" in url or "youtu.be" in url or "tiktok.com" in url or "facebook.com" in url:

            ydl_opts = {
                'format': 'mp4',
                'outtmpl': 'video.%(ext)s'
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)

            bot.send_video(chat_id, open(filename, "rb"))
            os.remove(filename)

        else:
            bot.send_message(chat_id, "❌ Link lama taageero")

    except Exception as e:
        bot.send_message(chat_id, f"Download failed: {e}")
@bot.message_handler(func=lambda m: m.text == "📥 Download Video")
def download(message):
    bot.send_message(message.chat.id, "Send TikTok / YouTube / Facebook link:")
    bot.register_next_step_handler(message, process_download)

def process_download(message):
    url = message.text
    bot.send_message(message.chat.id, "Downloading...")
    try:
        ydl_opts = {'outtmpl': 'video.%(ext)s', 'format': 'mp4'}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
        with open(filename, "rb") as f:
            bot.send_video(message.chat.id, f)
        os.remove(filename)
    except:
        bot.send_message(message.chat.id, "Download failed. Make sure the link is valid.")

# ---------------- ADMIN PANEL ----------------

@bot.message_handler(func=lambda m: m.text == "⚙️ Admin Panel")
def admin_panel(message):
    if message.from_user.id != ADMIN_ID:
        return
    kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("➕ Add Balance", "🚫 Ban User")
    kb.add("✅ Unban User", "🎁 Random Gift")
    kb.add("📢 Broadcast", "📊 Stats", "📝 Users List")
    bot.send_message(message.chat.id, "Admin Panel", reply_markup=kb)

# ---------------- ADMIN COMMANDS ----------------

@bot.message_handler(func=lambda m: m.text == "➕ Add Balance")
def add_balance(message):
    if message.from_user.id != ADMIN_ID:
        return
    bot.send_message(message.chat.id, "Send: user_id amount")
    bot.register_next_step_handler(message, process_add_balance)

def process_add_balance(message):
    uid, amount = message.text.split()
    users[uid]["balance"] += float(amount)
    save_users(users)
    bot.send_message(message.chat.id, "✅ Balance Added")

@bot.message_handler(func=lambda m: m.text == "🚫 Ban User")
def ban_user(message):
    if message.from_user.id != ADMIN_ID:
        return
    bot.send_message(message.chat.id, "Send user_id")
    bot.register_next_step_handler(message, process_ban)

def process_ban(message):
    users[message.text]["banned"] = True
    save_users(users)
    bot.send_message(message.chat.id, "🚫 User Banned")

@bot.message_handler(func=lambda m: m.text == "✅ Unban User")
def unban_user(message):
    if message.from_user.id != ADMIN_ID:
        return
    bot.send_message(message.chat.id, "Send user_id")
    bot.register_next_step_handler(message, process_unban)

def process_unban(message):
    users[message.text]["banned"] = False
    save_users(users)
    bot.send_message(message.chat.id, "✅ User Unbanned")

@bot.message_handler(func=lambda m: m.text == "🎁 Random Gift")
def gift(message):
    if message.from_user.id != ADMIN_ID:
        return
    u = random.choice(list(users.keys()))
    users[u]["balance"] += 1
    save_users(users)
    bot.send_message(message.chat.id, f"🎁 Gift sent to {u}")

@bot.message_handler(func=lambda m: m.text == "📢 Broadcast")
def broadcast(message):
    if message.from_user.id != ADMIN_ID:
        return
    bot.send_message(message.chat.id, "Send message/photo/video")
    bot.register_next_step_handler(message, process_broadcast)

def process_broadcast(message):
    for uid in users:
        try:
            if message.text:
                bot.send_message(uid, message.text)
            elif message.photo:
                bot.send_photo(uid, message.photo[-1].file_id)
            elif message.video:
                bot.send_video(uid, message.video.file_id)
        except:
            pass
    bot.send_message(ADMIN_ID, "✅ Broadcast Sent")

@bot.message_handler(func=lambda m: m.text == "📊 Stats")
def stats(message):
    if message.from_user.id != ADMIN_ID:
        return
    total_users = len(users)
    total_balance = sum(users[u]["balance"] for u in users)
    bot.send_message(message.chat.id, f"👥 Total Users: {total_users}\n💰 Total Balance: ${total_balance:.2f}")

@bot.message_handler(func=lambda m: m.text == "📝 Users List")
def users_list(message):
    if message.from_user.id != ADMIN_ID:
        return
    msg = "📋 Users Info:\n"
    for uid in users:
        u = users[uid]
        msg += f"ID: {uid}\nBOT ID: {u['bot_id']}\nBalance: ${u['balance']}\nBanned: {u['banned']}\n\n"
    bot.send_message(message.chat.id, msg)

# ---------------- WITHDRAWAL COMMANDS ----------------

@bot.message_handler(func=lambda m: m.text.startswith("CONFIRM"))
def confirm(message):
    if message.from_user.id != ADMIN_ID:
        return
    uid = message.text.split()[1]
    for w in withdrawals:
        if w["user_id"] == uid and w["status"] == "pending":
            w["status"] = "confirmed"
            users[uid]["balance"] -= w["amount"]
            save_users(users)
            save_withdrawals(withdrawals)
            bot.send_message(uid, "✅ Withdrawal Confirmed")

@bot.message_handler(func=lambda m: m.text.startswith("REJECT"))
def reject(message):
    if message.from_user.id != ADMIN_ID:
        return
    uid = message.text.split()[1]
    for w in withdrawals:
        if w["user_id"] == uid and w["status"] == "pending":
            w["status"] = "rejected"
            save_withdrawals(withdrawals)
            bot.send_message(uid, "❌ Withdrawal Rejected")

@bot.message_handler(func=lambda m: m.text.startswith("BAN"))
def ban_cmd(message):
    if message.from_user.id != ADMIN_ID:
        return
    uid = message.text.split()[1]
    users[uid]["banned"] = True
    save_users(users)
    bot.send_message(message.chat.id, "User banned")

# ---------------- RUN BOT ----------------

print("Bot Running...")
bot.infinity_polling()
