import telebot
import requests
from telebot.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
import os, json, random
from datetime import datetime
import yt_dlp
import subprocess
import os
import re

# ================= CONFIG =================
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [7983838654]  # Liiska admins, waxaad ku dari kartaa ID kale haddii loo baahdo

BASE_DIR = os.getcwd()  # Folder-ka bot-ku ka shaqeeyo
CAPTION_TEXT = "✅ Downloaded via @YourBotUsername"


bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# ================= DATABASE FILES =================
USERS_FILE = "users.json"
WITHDRAWS_FILE = "withdraws.json"

# ================= JSON FUNCTIONS =================
def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=4)

users = load_json(USERS_FILE, {})
withdraws = load_json(WITHDRAWS_FILE, [])

def save_users():
    save_json(USERS_FILE, users)

def save_withdraws():
    save_json(WITHDRAWS_FILE, withdraws)

# ================= HELPER FUNCTIONS =================
def random_ref():
    return str(random.randint(1000000000, 9999999999))

def random_botid():
    return str(random.randint(10000000000, 99999999999))

def now_month():
    return datetime.now().month

def is_admin(uid):
    return int(uid) in ADMIN_IDS

def find_user_by_botid(bid):
    for u, data in users.items():
        if data.get("bot_id") == bid:
            return u
    return None

def banned_guard(m):
    uid = str(m.from_user.id)
    if uid in users and users[uid].get("banned"):
        bot.send_message(m.chat.id, "🚫 You are banned.")
        return True
    return False

# ================= MENUS =================
def user_menu(show_admin=False):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("💰 BALANCE", "💸 WITHDRAWAL")
    kb.add("👥 REFERRAL", "🆔 GET ID")
    kb.add("☎️ CUSTOMER")
    if show_admin:
        kb.add("👑 ADMIN PANEL")
    return kb

def admin_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📊 STATS", "📢 BROADCAST")
    kb.add("➕ ADD BALANCE", "➖ REMOVE MONEY")
    kb.add("✅ UNBAN USER", "💳 WITHDRAWAL CHECK")
    kb.add("💰 UNBLOCK MONEY")
    kb.add("🔙 BACK MAIN MENU")
    return kb

# ================= BACK TO MAIN MENU =================
def back_to_main_menu(m):
    uid = str(m.from_user.id)
    bot.send_message(
        m.chat.id,
        "🔙 Returning to main menu",
        reply_markup=user_menu(is_admin(uid))
    )

@bot.message_handler(func=lambda m: m.text == "🔙 BACK MAIN MENU")
def back_button_handler(m):
    back_to_main_menu(m)

# ================= START HANDLER =================
@bot.message_handler(commands=['start'])
def start_handler(m):
    uid = str(m.from_user.id)
    args = m.text.split()

    if uid not in users:
        ref = args[1] if len(args) > 1 else None
        users[uid] = {
            "balance": 0.0,
            "blocked": 0.0,
            "ref": random_ref(),
            "bot_id": random_botid(),
            "invited": 0,
            "banned": False,
            "month": now_month()
        }
        # Referral reward
        if ref:
            ref_user = next((u for u, d in users.items() if d["ref"] == ref), None)
            if ref_user:
                users[ref_user]["balance"] += 0.2
                users[ref_user]["invited"] += 1
                bot.send_message(int(ref_user), "🎉 You earned $0.2 from referral!")

        save_users()

    bot.send_message(m.chat.id, "👋 Welcome!", reply_markup=user_menu(is_admin(uid)))

# ================= ADMIN PANEL =================
@bot.message_handler(func=lambda m: m.text == "👑 ADMIN PANEL")
def open_admin_panel(m):
    if not is_admin(m.from_user.id):
        bot.send_message(m.chat.id, "❌ You are not admin")
        return
    bot.send_message(m.chat.id, "👑 Admin Panel", reply_markup=admin_menu())

    # ================= BALANCE =================
@bot.message_handler(func=lambda m: m.text == "💰 BALANCE")
def balance_handler(m):
    if banned_guard(m):
        return
    uid = str(m.from_user.id)
    bal = users[uid].get("balance", 0.0)
    blocked = users[uid].get("blocked", 0.0)
    bot.send_message(
        m.chat.id,
        f"💰 Available Balance: ${bal:.2f}\n"
        f"⏳ Blocked Amount: ${blocked:.2f}"
    )

# ================= GET ID =================
@bot.message_handler(func=lambda m: m.text == "🆔 GET ID")
def get_id_handler(m):
    if banned_guard(m):
        return
    uid = str(m.from_user.id)
    bot.send_message(
        m.chat.id,
        f"🆔 BOT ID: <code>{users[uid]['bot_id']}</code>\n"
        f"👤 Telegram ID: <code>{uid}</code>"
    )

# ================= REFERRAL =================
@bot.message_handler(func=lambda m: m.text == "👥 REFERRAL")
def referral_handler(m):
    if banned_guard(m):
        return
    uid = str(m.from_user.id)
    bot_username = bot.get_me().username
    link = f"https://t.me/{bot_username}?start={users[uid]['ref']}"
    invited = users[uid].get("invited", 0)
    bot.send_message(
        m.chat.id,
        f"🔗 Your Referral Link:\n{link}\n\n"
        f"👥 Invited Users: {invited}\n"
        f"🎁 You earn $0.2 per referral!"
    )

# ================= CUSTOMER SUPPORT =================
@bot.message_handler(func=lambda m: m.text == "☎️ CUSTOMER")
def customer_handler(m):
    if banned_guard(m):
        return
    bot.send_message(
        m.chat.id,
        "☎️ Customer Support:\n@scholes1"
    )

# ================= WITHDRAWAL MENU =================
@bot.message_handler(func=lambda m: m.text == "💸 WITHDRAWAL")
def withdraw_menu(m):
    if banned_guard(m):
        return
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("USDT-BEP20")
    kb.add("🔙 CANCEL")
    bot.send_message(
        m.chat.id,
        "Select withdrawal method:",
        reply_markup=kb
    )

# ================= WITHDRAWAL METHOD =================
@bot.message_handler(func=lambda m: m.text in ["USDT-BEP20", "🔙 CANCEL"])
def withdraw_method(m):
    uid = str(m.from_user.id)
    if m.text == "🔙 CANCEL":
        back_to_main_menu(m)
        return
    if m.text == "USDT-BEP20":
        kb = ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add("🔙 CANCEL")
        msg = bot.send_message(
            m.chat.id,
            "Enter your USDT BEP20 address (must start with 0x)\nOr press 🔙 CANCEL",
            reply_markup=kb
        )
        bot.register_next_step_handler(msg, withdraw_address_step)

# ================= WITHDRAWAL ADDRESS =================
def withdraw_address_step(m):
    uid = str(m.from_user.id)
    text = (m.text or "").strip()
    if text == "🔙 CANCEL":
        back_to_main_menu(m)
        return
    if not text.startswith("0x"):
        kb = ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add("🔙 CANCEL")
        msg = bot.send_message(
            m.chat.id,
            "❌ Invalid address. Must start with 0x.\nTry again or press 🔙 CANCEL",
            reply_markup=kb
        )
        bot.register_next_step_handler(msg, withdraw_address_step)
        return
    users[uid]["temp_addr"] = text
    save_users()
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🔙 CANCEL")
    msg = bot.send_message(
        m.chat.id,
        f"Enter withdrawal amount\nMinimum: $1\nBalance: ${users[uid]['balance']:.2f}\n\nOr press 🔙 CANCEL",
        reply_markup=kb
    )
    bot.register_next_step_handler(msg, withdraw_amount_step)

# ================= WITHDRAWAL AMOUNT =================
def withdraw_amount_step(m):
    uid = str(m.from_user.id)
    text = (m.text or "").strip()
    if text == "🔙 CANCEL":
        back_to_main_menu(m)
        return
    try:
        amt = float(text)
    except:
        kb = ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add("🔙 CANCEL")
        msg = bot.send_message(
            m.chat.id,
            "❌ Invalid number.\nEnter again or press 🔙 CANCEL",
            reply_markup=kb
        )
        bot.register_next_step_handler(msg, withdraw_amount_step)
        return
    if amt < 1:
        bot.send_message(
            m.chat.id,
            "❌ Minimum withdrawal is $1",
            reply_markup=user_menu(is_admin(uid))
        )
        return
    if amt > users[uid]["balance"]:
        bot.send_message(
            m.chat.id,
            "❌ Insufficient balance",
            reply_markup=user_menu(is_admin(uid))
        )
        return

    # ================= CREATE WITHDRAWAL REQUEST =================
def withdraw_amount_step(m):
    uid = str(m.from_user.id)
    text = (m.text or "").strip()

    if text == "🔙 CANCEL":
        back_to_main_menu(m)
        return

    try:
        amt = float(text)
    except:
        kb = ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add("🔙 CANCEL")
        msg = bot.send_message(
            m.chat.id,
            "❌ Invalid number.\nEnter again or press 🔙 CANCEL",
            reply_markup=kb
        )
        bot.register_next_step_handler(msg, withdraw_amount_step)
        return

    if amt < 1:
        bot.send_message(
            m.chat.id,
            "❌ Minimum withdrawal is $1",
            reply_markup=user_menu(is_admin(uid))
        )
        return

    if amt > users[uid]["balance"]:
        bot.send_message(
            m.chat.id,
            "❌ Insufficient balance",
            reply_markup=user_menu(is_admin(uid))
        )
        return

    # ===== Create withdrawal request =====
    wid = random.randint(10000, 99999)

    users[uid]["balance"] -= amt
    users[uid]["blocked"] += amt

    withdrawal = {
        "id": wid,
        "user": uid,
        "amount": amt,
        "blocked": amt,
        "address": users[uid].get("temp_addr", "N/A"),
        "status": "pending",
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    withdraws.append(withdrawal)
    save_users()
    save_withdraws()

    # ===== Notify user =====
    bot.send_message(
        int(uid),
        f"✅ Withdrawal Request Sent\n"
        f"🧾 Request ID: {wid}\n"
        f"💵 Amount: ${amt:.2f}\n"
        f"🏦 Address: {withdrawal['address']}\n"
        f"💰 Balance Left: ${users[uid]['balance']:.2f}\n"
        f"⏳ Status: Pending"
    )

    # ===== Notify admins =====
    admin_text = (
        f"💳 NEW WITHDRAWAL\n\n"
        f"👤 User: {uid}\n"
        f"🤖 BOT ID: {users[uid]['bot_id']}\n"
        f"👥 Referrals: {users[uid]['invited']}\n"
        f"💵 Amount: ${amt:.2f}\n"
        f"🧾 Request ID: {wid}\n"
        f"🏦 Address: {withdrawal['address']}\n"
        f"⏳ Status: Pending"
    )

    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("✅ CONFIRM", callback_data=f"confirm_{wid}"),
        InlineKeyboardButton("❌ REJECT", callback_data=f"reject_{wid}"),
        InlineKeyboardButton("🚫 BAN USER", callback_data=f"ban_{uid}"),
        InlineKeyboardButton("💰 BAN MONEY", callback_data=f"block_{wid}")
    )

    # Loop through admin IDs
    for admin in [7983838654]:  # Halkan waxaad ku dari kartaa liiska admin IDs
        bot.send_message(admin, admin_text, reply_markup=markup)

    # ================= ADMIN INLINE CALLBACKS =================
@bot.callback_query_handler(func=lambda call: call.data.startswith(("confirm_", "reject_", "ban_", "block_")))
def admin_callbacks(call):

    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ You are not admin")
        return

    data = call.data

    # ===== CONFIRM WITHDRAWAL =====
    if data.startswith("confirm_"):
        wid = int(data.split("_")[1])
        w = next((x for x in withdraws if x["id"] == wid), None)
        if not w or w["status"] != "pending":
            return
        w["status"] = "paid"
        users[w["user"]]["blocked"] -= w["blocked"]
        save_users()
        save_withdraws()
        bot.answer_callback_query(call.id, "✅ Confirmed")
        bot.send_message(int(w["user"]), f"✅ Withdrawal #{wid} approved!")

    # ===== REJECT WITHDRAWAL =====
    elif data.startswith("reject_"):
        wid = int(data.split("_")[1])
        w = next((x for x in withdraws if x["id"] == wid), None)
        if not w or w["status"] != "pending":
            return
        w["status"] = "rejected"
        users[w["user"]]["balance"] += w["blocked"]
        users[w["user"]]["blocked"] -= w["blocked"]
        save_users()
        save_withdraws()
        bot.answer_callback_query(call.id, "❌ Rejected")
        bot.send_message(int(w["user"]), f"❌ Withdrawal #{wid} rejected")

    # ===== BAN USER =====
    elif data.startswith("ban_"):
        uid = data.split("_")[1]
        if uid in users:
            users[uid]["banned"] = True
            save_users()
            bot.answer_callback_query(call.id, "🚫 User banned")
            bot.send_message(int(uid), "🚫 You have been banned by admin.")

    # ===== BLOCK MONEY =====
    elif data.startswith("block_"):
        wid = int(data.split("_")[1])
        w = next((x for x in withdraws if x["id"] == wid), None)
        if not w or w["status"] != "pending":
            return
        uid = w["user"]
        amt = w["blocked"]
        w["status"] = "blocked"
        code = str(random.randint(1000, 9999))
        w["block_code"] = code
        users[uid]["blocked"] -= amt
        save_users()
        save_withdraws()
        bot.answer_callback_query(call.id, "💰 Money Blocked")
        bot.send_message(
            int(uid),
            f"🚫 Your withdrawal of ${amt:.2f} is BLOCKED.\n"
            f"🔢 Block Code: {code}\n"
            f"Contact admin to unlock."
        )

# ================= UNBLOCK MONEY =================
@bot.message_handler(func=lambda m: m.text == "💰 UNBLOCK MONEY")
def unblock_money_start(m):
    if not is_admin(m.from_user.id):
        bot.send_message(m.chat.id, "❌ You are not admin")
        return

    msg = bot.send_message(
        m.chat.id,
        "🔢 Send 4-digit Block Code to UNBLOCK funds:"
    )
    bot.register_next_step_handler(msg, unblock_money_process)


def unblock_money_process(m):
    if not is_admin(m.from_user.id):
        return

    code = (m.text or "").strip()
    w = next((x for x in withdraws if x.get("block_code") == code), None)

    if not w:
        bot.send_message(m.chat.id, "❌ Invalid Block Code")
        return

    uid = w["user"]
    amt = w["blocked"]

    users[uid]["balance"] += amt
    w["status"] = "unblocked"
    w.pop("block_code", None)

    save_users()
    save_withdraws()

    bot.send_message(
        int(uid),
        f"✅ Your blocked ${amt:.2f} is now available in balance!"
    )
    bot.send_message(
        m.chat.id,
        f"✅ Money unblocked for user {uid}"
    )


# ================= UNBAN USER =================
@bot.message_handler(func=lambda m: m.text == "✅ UNBAN USER")
def unban_user_start(m):
    if not is_admin(m.from_user.id):
        bot.send_message(m.chat.id, "❌ You are not admin")
        return

    msg = bot.send_message(
        m.chat.id,
        "Send Telegram ID of user to UNBAN:"
    )
    bot.register_next_step_handler(msg, unban_user_process)


def unban_user_process(m):
    if not is_admin(m.from_user.id):
        return

    uid = (m.text or "").strip()
    if uid not in users:
        bot.send_message(m.chat.id, "❌ User not found")
        return

    users[uid]["banned"] = False
    save_users()

    bot.send_message(m.chat.id, f"✅ User {uid} unbanned")
    bot.send_message(int(uid), "✅ You have been unbanned by admin.")

# ================= WITHDRAWAL CHECK =================
@bot.message_handler(func=lambda m: m.text == "💳 WITHDRAWAL CHECK")
def withdrawal_check_start(m):
    if not is_admin(m.from_user.id):
        bot.send_message(m.chat.id, "❌ You are not admin")
        return

    msg = bot.send_message(
        m.chat.id,
        "Enter Withdrawal Request ID (example: 40201):"
    )
    bot.register_next_step_handler(msg, withdrawal_check_process)


def withdrawal_check_process(m):
    if not is_admin(m.from_user.id):
        return

    try:
        wid = int(m.text.strip())
    except:
        bot.send_message(m.chat.id, "❌ Invalid Request ID")
        return

    w = next((x for x in withdraws if x["id"] == wid), None)
    if not w:
        bot.send_message(m.chat.id, "❌ Request not found")
        return

    uid = w["user"]
    bot_id = users.get(uid, {}).get("bot_id", "Unknown")
    invited = users.get(uid, {}).get("invited", 0)

    msg_text = (
        f"💳 WITHDRAWAL DETAILS\n\n"
        f"🧾 Request ID: {w['id']}\n"
        f"👤 User ID: {uid}\n"
        f"🤖 BOT ID: {bot_id}\n"
        f"👥 Referrals: {invited}\n"
        f"💵 Amount: ${w['amount']:.2f}\n"
        f"🏦 Address: {w['address']}\n"
        f"📊 Status: {w['status'].upper()}\n"
        f"⏰ Time: {w['time']}"
    )

    bot.send_message(m.chat.id, msg_text)


# ================= STATS =================
@bot.message_handler(func=lambda m: m.text == "📊 STATS")
def stats_handler(m):
    if not is_admin(m.from_user.id):
        bot.send_message(m.chat.id, "❌ You are not admin")
        return

    total_users = len(users)
    total_balance = sum(u.get("balance", 0.0) for u in users.values())
    total_blocked = sum(u.get("blocked", 0.0) for u in users.values())
    total_withdraws = len(withdraws)
    pending_withdraws = len([w for w in withdraws if w["status"] == "pending"])

    msg = (
        f"📊 BOT STATS\n\n"
        f"👥 Total Users: {total_users}\n"
        f"💰 Total Balance: ${total_balance:.2f}\n"
        f"⏳ Total Blocked: ${total_blocked:.2f}\n"
        f"🧾 Total Withdrawals: {total_withdraws}\n"
        f"⏳ Pending Withdrawals: {pending_withdraws}"
    )

    bot.send_message(m.chat.id, msg)


# ================= BROADCAST =================
@bot.message_handler(func=lambda m: m.text == "📢 BROADCAST")
def broadcast_start(m):
    if not is_admin(m.from_user.id):
        bot.send_message(m.chat.id, "❌ You are not admin")
        return

    msg = bot.send_message(
        m.chat.id,
        "📝 Send the broadcast message to all users:"
    )
    bot.register_next_step_handler(msg, broadcast_send)


def broadcast_send(m):
    if not is_admin(m.from_user.id):
        return

    text = m.text
    count = 0

    for uid in users:
        try:
            bot.send_message(int(uid), text)
            count += 1
        except:
            continue

    bot.send_message(m.chat.id, f"✅ Broadcast sent to {count} users")

# ================= ADD BALANCE =================
@bot.message_handler(func=lambda m: m.text == "➕ ADD BALANCE")
def add_balance_start(m):
    if not is_admin(m.from_user.id):
        bot.send_message(m.chat.id, "❌ You are not admin")
        return

    msg = bot.send_message(
        m.chat.id,
        "Send BOT ID or Telegram ID and amount separated by space:\n"
        "Example:\n123456789 10.5"
    )
    bot.register_next_step_handler(msg, add_balance_process)


def add_balance_process(m):
    if not is_admin(m.from_user.id):
        return

    try:
        uid_str, amt_str = m.text.strip().split()
        amt = float(amt_str)

        # Hubi haddii la isticmaalayo Telegram ID ama BOT ID
        uid = uid_str if uid_str in users else find_user_by_botid(uid_str)

        if not uid or amt <= 0:
            bot.send_message(m.chat.id, "❌ Invalid input")
            return

        users[uid]["balance"] += amt
        save_users()

        bot.send_message(m.chat.id, f"✅ Added ${amt:.2f} to user {uid}")
        bot.send_message(int(uid), f"💰 Your balance increased by ${amt:.2f}")

    except:
        bot.send_message(m.chat.id, "❌ Format error.\nUse:\n<BOT ID or Telegram ID> <amount>")

# ================= REMOVE MONEY =================
@bot.message_handler(func=lambda m: m.text == "➖ REMOVE MONEY")
def remove_balance_start(m):
    if not is_admin(m.from_user.id):
        bot.send_message(m.chat.id, "❌ You are not admin")
        return

    msg = bot.send_message(
        m.chat.id,
        "Send BOT ID or Telegram ID and amount separated by space:\n"
        "Example:\n123456789 5.0"
    )
    bot.register_next_step_handler(msg, remove_balance_process)


def remove_balance_process(m):
    if not is_admin(m.from_user.id):
        return

    try:
        uid_str, amt_str = m.text.strip().split()
        amt = float(amt_str)

        # Hubi haddii la isticmaalayo Telegram ID ama BOT ID
        uid = uid_str if uid_str in users else find_user_by_botid(uid_str)

        if not uid or amt <= 0:
            bot.send_message(m.chat.id, "❌ Invalid input")
            return

        if users[uid]["balance"] < amt:
            bot.send_message(m.chat.id, "❌ Insufficient balance")
            return

        users[uid]["balance"] -= amt
        save_users()

        bot.send_message(m.chat.id, f"✅ Removed ${amt:.2f} from user {uid}")
        bot.send_message(int(uid), f"💸 ${amt:.2f} removed from your balance")

    except:
        bot.send_message(m.chat.id, "❌ Format error.\nUse:\n<BOT ID or Telegram ID> <amount>")

CAPTION_TEXT = "Downloaded by:\n@Downloadvedioytibot"


# ================= URL EXTRACTOR =================
def extract_url(text):
    urls = re.findall(r'https?://[^\s]+', text)
    return urls[0] if urls else None


# ================= SEND VIDEO WITH MUSIC =================
def send_video_with_music(chat_id, file_path):
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🎵 MUSIC", callback_data=f"music|{file_path}"))

    with open(file_path, "rb") as video:
        bot.send_video(chat_id, video, caption=CAPTION_TEXT, reply_markup=kb)


# ================= MEDIA DOWNLOADER =================
def download_media(chat_id, text):
    try:
        url = extract_url(text)
        if not url:
            bot.send_message(chat_id, "❌ Invalid URL")
            return

        # ===== Resolve Pinterest short link =====
        if "pin.it" in url:
            try:
                r = requests.head(url, allow_redirects=True, timeout=10)
                url = r.url
            except:
                pass

        ydl_opts = {
            "format": "bestvideo+bestaudio/best",
            "outtmpl": os.path.join(BASE_DIR, "%(extractor)s_%(id)s.%(ext)s"),
            "quiet": True,
            "noplaylist": True,
            "merge_output_format": "mp4"
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

            # ===== MULTIPLE ENTRIES (TikTok slideshow / Pinterest gallery) =====
            if isinstance(info, dict) and info.get("entries"):
                for entry in info["entries"]:
                    if not entry:
                        continue

                    filename = ydl.prepare_filename(entry)

                    # IMAGE
                    if filename.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                        with open(filename, "rb") as photo:
                            bot.send_photo(chat_id, photo, caption=CAPTION_TEXT)
                        os.remove(filename)

                    # VIDEO
                    else:
                        if not filename.endswith(".mp4"):
                            filename = filename.rsplit(".", 1)[0] + ".mp4"

                        send_video_with_music(chat_id, filename)
                        os.remove(filename)
                return

            # ===== SINGLE FILE =====
            filename = ydl.prepare_filename(info)

            # IMAGE
            if filename.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                with open(filename, "rb") as photo:
                    bot.send_photo(chat_id, photo, caption=CAPTION_TEXT)
                os.remove(filename)

            # VIDEO
            else:
                if not filename.endswith(".mp4"):
                    filename = filename.rsplit(".", 1)[0] + ".mp4"

                send_video_with_music(chat_id, filename)
                os.remove(filename)

    except Exception as e:
        bot.send_message(chat_id, f"❌ Download error:\n{e}")

# ================= MUSIC CONVERSION =================
@bot.callback_query_handler(func=lambda call: call.data.startswith("music|"))
def convert_music(call):
    file_path = call.data.split("|")[1]
    audio_path = file_path.rsplit(".", 1)[0] + ".mp3"

    try:
        subprocess.run(
            ["ffmpeg", "-i", file_path, "-vn", "-ab", "128k", "-ar", "44100", audio_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
        )

        with open(audio_path, "rb") as audio:
            bot.send_audio(
                call.message.chat.id,
                audio,
                title="Downloaded Music",
                performer="DownloadBot",
                caption=CAPTION_TEXT
            )

        os.remove(audio_path)
        os.remove(file_path)

    except Exception as e:
        bot.send_message(call.message.chat.id, f"❌ Music conversion failed:\n{e}")

# ================= LINK HANDLER =================
@bot.message_handler(func=lambda m: m.text and "http" in m.text)
def handle_links(message):
    bot.send_message(message.chat.id, "⏳ Downloading...")
    download_media(message.chat.id, message.text)


# ================= RUN BOT =================
if __name__ == "__main__":
    print("🤖 Bot is running...")
    bot.infinity_polling(skip_pending=True, timeout=60)
