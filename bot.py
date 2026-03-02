import telebot
import requests
from telebot.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
import os, json, random
from datetime import datetime
import yt_dlp
import subprocess
import os
import re
import shutil
import time

# ================= CONFIG =================
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [7983838654]

BASE_DIR = os.getcwd()
CHANNEL_USERNAME = "tiktokvediodownload"

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# ================= GLOBAL STATES =================
ASK_MODE = {}
bot_closed_until = 0

# ================= DATABASE FILES =================
USERS_FILE = "users.json"
WITHDRAWS_FILE = "withdraws.json"
VIDEOS_FILE = "videos.json"

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

# ================= LOAD DATA =================
videos_data = load_json(VIDEOS_FILE, {
    "total": 0,
    "platforms": {
        "tiktok": 0,
        "youtube": 0,
        "facebook": 0,
        "pinterest": 0
    },
    "users": {}
})

def save_videos():
    save_json(VIDEOS_FILE, videos_data)

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

# ================= BOT CLOSED GUARD =================
def bot_closed_guard(chat_id):
    global bot_closed_until
    if time.time() < bot_closed_until:
        bot.send_message(chat_id, "🚫 This bot is temporarily closed by admin.")
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
    kb.add("🚫 BAN USER MANUAL", "💳 WITHDRAWAL CHECK")
    kb.add("💰 UNBLOCK MONEY", "🔍 RAADI")
    kb.add("🔥 UN BAN-USER")
    kb.add("💌 GAVE", "🛑 STOP BOT", "💬 CHAT")
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
def start_handler(message):
    if bot_closed_guard(message.chat.id):
        return

    uid = message.from_user.id
    args = message.text.split()

    if str(uid) not in users:
        ref = args[1] if len(args) > 1 else None
        users[str(uid)] = {
            "balance": 0.0,
            "blocked": 0.0,
            "ref": random_ref(),
            "bot_id": random_botid(),
            "invited": 0,
            "banned": False,
            "month": now_month()
        }
        if ref:
            ref_user = next((u for u, d in users.items() if d["ref"] == ref), None)
            if ref_user:
                users[ref_user]["balance"] += 0.2
                users[ref_user]["invited"] += 1
                bot.send_message(int(ref_user), "🎉 You earned $0.2 from referral!")
        save_users()

    check_membership(uid)

def check_membership(user_id):
    try:
        member = bot.get_chat_member(tiktokvediodownload, user_id)
        # Hubi haddii user-ka uu ku jiro channel
        if member.status in ["member", "administrator", "creator"]:
            bot.send_message(user_id, "✅ Bot is ready.\nSend your download link.", reply_markup=user_menu(is_admin(user_id)))
            return True
        else:
            send_join_message(user_id)
            return False
    except Exception as e:
        print(f"Error checking membership: {e}")
        send_join_message(user_id)
        return False

def send_join_message(user_id):
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("➕ JOIN CHANNEL", url=f"https://t.me/{CHANNEL_USERNAME}"))
    kb.add(InlineKeyboardButton("✅ CONFIRM", callback_data="confirm_join"))
    bot.send_message(
        user_id,
        "⚠️ You must join our channel to use this bot.",
        reply_markup=kb
    )

@bot.callback_query_handler(func=lambda call: call.data == "confirm_join")
def confirm_join(call):
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, call.from_user.id)
        if member.status in ["member", "administrator", "creator"]:
            bot.answer_callback_query(call.id, "✅ Verified!")
            bot.send_message(
                call.from_user.id,
                "🎉 Welcome! Now send your download link.",
                reply_markup=user_menu(is_admin(call.from_user.id))
            )
        else:
            bot.answer_callback_query(call.id, "❌ You must join the channel first!", show_alert=True)
    except:
        bot.answer_callback_query(call.id, "❌ Join the channel first!", show_alert=True)

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

# ================= ASK SYSTEM =================
ASK_MODE = {}

@bot.message_handler(func=lambda m: m.text == "❓ ASK")
def ask_user(m):
    if banned_guard(m):
        return
    msg = bot.send_message(m.chat.id, "✍️ Send your message to admin:")
    ASK_MODE[m.from_user.id] = True

@bot.message_handler(func=lambda m: True)
def handle_ask_message(m):
    uid = m.from_user.id
    if ASK_MODE.get(uid):
        for admin in ADMIN_IDS:
            bot.send_message(admin, f"✉️ Message from {uid}:\n\n{m.text}")
        bot.send_message(uid, "✅ Your message has been sent to admin!")
        ASK_MODE.pop(uid)

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
    for admin in ADMIN_IDS:
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
@bot.message_handler(func=lambda m: m.text == "🔥 UN BAN-USER")
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

# ================= MANUAL BAN =================
@bot.message_handler(func=lambda m: m.text == "🚫 BAN USER MANUAL")
def manual_ban_start(m):
    if not is_admin(m.from_user.id):
        bot.send_message(m.chat.id, "❌ You are not admin")
        return

    msg = bot.send_message(
        m.chat.id,
        "Send Telegram ID or BOT ID to BAN user:"
    )
    bot.register_next_step_handler(msg, manual_ban_process)


def manual_ban_process(m):
    if not is_admin(m.from_user.id):
        return

    uid_input = (m.text or "").strip()

    uid = uid_input if uid_input in users else find_user_by_botid(uid_input)

    if not uid:
        bot.send_message(m.chat.id, "❌ User not found")
        return

    users[uid]["banned"] = True
    save_users()

    bot.send_message(m.chat.id, f"🚫 User {uid} banned")
    bot.send_message(int(uid), "🚫 You have been banned by admin.")

# ================= RAADI (DOWNLOAD STATS) =================
@bot.message_handler(func=lambda m: m.text == "🔍 RAADI")
def raadi_stats(m):
    if not is_admin(m.from_user.id):
        bot.send_message(m.chat.id, "❌ You are not admin")
        return

    total_videos = videos_data.get("total", 0)
    platform_stats = videos_data.get("platforms", {"tiktok": 0, "youtube": 0, "facebook": 0, "pinterest": 0})
    users_stats = videos_data.get("users", {})

    if not users_stats:
        bot.send_message(m.chat.id, "❌ No video data found yet.")
        return

    # Top downloader
    top_user_id, top_count = max(users_stats.items(), key=lambda x: x[1])

    # Build message
    msg_lines = [
        f"🔍 DOWNLOAD ANALYTICS\n",
        f"🎬 Total Videos Downloaded: {total_videos}",
        f"🏆 Top Downloader: <a href='tg://user?id={top_user_id}'>{top_user_id}</a> ({top_count} videos)\n",
        "📊 Downloads by Platform:",
        f"• TikTok: {platform_stats.get('tiktok',0)}",
        f"• YouTube: {platform_stats.get('youtube',0)}",
        f"• Facebook: {platform_stats.get('facebook',0)}",
        f"• Pinterest: {platform_stats.get('pinterest',0)}\n",
        "🥇 Top 3 Users:"
    ]

    # Top 3 users
    sorted_users = sorted(users_stats.items(), key=lambda x: x[1], reverse=True)
    for i, (uid, count) in enumerate(sorted_users[:3], start=1):
        bot_id = users.get(str(uid), {}).get("bot_id", "N/A")
        msg_lines.append(f"{i}. 👤 <a href='tg://user?id={uid}'>{uid}</a> - 🎬 {count} videos | 🤖 BOT ID: {bot_id}")

    msg_text = "\n".join(msg_lines)
    bot.send_message(m.chat.id, msg_text, parse_mode="HTML")

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

# ================= ADMIN PANEL EXTENSIONS =================
@bot.message_handler(func=lambda m: m.text == "GAVE")
def gave_broadcast_start(m):
    if not is_admin(m.from_user.id):
        bot.send_message(m.chat.id, "❌ You are not admin")
        return
    msg = bot.send_message(
        m.chat.id,
        "📝 Send the broadcast message to ALL users (including old & new users):"
    )
    bot.register_next_step_handler(msg, gave_broadcast_send)

def gave_broadcast_send(m):
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
    bot.send_message(m.chat.id, f"✅ GAVE broadcast sent to {count} users")

# ================= ADMIN STOP BOT =================
STOPPED_BOT = {"active": False, "timer": None}

@bot.message_handler(func=lambda m: m.text == "STOP")
def stop_bot_start(m):
    if not is_admin(m.from_user.id):
        bot.send_message(m.chat.id, "❌ You are not admin")
        return
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("⏹️ CANCEL", callback_data="stop_cancel"))
    msg = bot.send_message(
        m.chat.id,
        "⏸️ Bot STOP command activated. Send time in minutes or press CANCEL",
        reply_markup=kb
    )
    bot.register_next_step_handler(msg, stop_bot_timer)

def stop_bot_timer(m):
    if not is_admin(m.from_user.id):
        return
    text = m.text.strip()
    if text.lower() == "cancel":
        bot.send_message(m.chat.id, "❌ Stop canceled")
        return
    try:
        minutes = int(text)
        STOPPED_BOT["active"] = True
        bot.send_message(m.chat.id, f"⏸️ Bot stopped for {minutes} minute(s). Users see: 'Bot admin closed'")
        # Start timer
        from threading import Timer
        def resume_bot():
            STOPPED_BOT["active"] = False
            bot.send_message(m.chat.id, "✅ Bot resumed automatically after stop period")
        STOPPED_BOT["timer"] = Timer(minutes*60, resume_bot)
        STOPPED_BOT["timer"].start()
    except:
        bot.send_message(m.chat.id, "❌ Invalid number. Cancel or send integer minutes")

@bot.callback_query_handler(func=lambda call: call.data == "stop_cancel")
def stop_cancel(call):
    if not is_admin(call.from_user.id):
        return
    if STOPPED_BOT["timer"]:
        STOPPED_BOT["timer"].cancel()
    STOPPED_BOT["active"] = False
    bot.answer_callback_query(call.id, "❌ Stop canceled")
    bot.send_message(call.message.chat.id, "❌ Stop canceled successfully")

# ================= ASK REPLY =================
ASK_MODE = {}

@bot.message_handler(func=lambda m: m.text == "❓ ASK")
def ask_user(m):
    if banned_guard(m):
        return
    msg = bot.send_message(m.chat.id, "✍️ Send your message to admin:")
    ASK_MODE[m.from_user.id] = True

@bot.message_handler(func=lambda m: True)
def handle_ask_message(m):
    uid = m.from_user.id
    if ASK_MODE.get(uid):
        for admin in ADMIN_IDS:
            bot.send_message(admin, f"✉️ Message from {uid}:\n\n{m.text}")
        bot.send_message(uid, "✅ Your message has been sent to admin!")
        ASK_MODE.pop(uid)
        return

# ================= INLINE WORK BUTTON =================
WORKING_USERS = set()

@bot.message_handler(func=lambda m: m.text == "WORK")
def admin_work_button(m):
    if not is_admin(m.from_user.id):
        bot.send_message(m.chat.id, "❌ You are not admin")
        return
    for uid in users:
        WORKING_USERS.add(uid)
        bot.send_message(uid, "⚡ Bot is working! Admin activated WORK mode")
    bot.send_message(m.chat.id, f"✅ WORK message sent to {len(WORKING_USERS)} users")
    WORKING_USERS.clear()

# ================= URL EXTRACTOR =================
def extract_url(text):
    urls = re.findall(r'https?://[^\s]+', text)
    return urls[0] if urls else None

# ================= CLEAN SEND VIDEO FUNCTION =================
def send_video_with_music(chat_id, file_path, platform=None):
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🎵 Convert to Music", callback_data=f"music|{file_path}"))

    # ===== COUNT VIDEO =====
    uid = str(chat_id)
    videos_data["total"] += 1
    videos_data["users"][uid] = videos_data["users"].get(uid, 0) + 1

    # ===== COUNT PLATFORM =====
    if platform:
        if "platforms" not in videos_data:
            videos_data["platforms"] = {
                "tiktok": 0,
                "youtube": 0,
                "facebook": 0,
                "pinterest": 0
            }
        videos_data["platforms"][platform] = videos_data["platforms"].get(platform, 0) + 1

    save_videos()

    with open(file_path, "rb") as video:
        bot.send_video(
            chat_id,
            video,
            caption=CAPTION_TEXT,
            reply_markup=kb
        )

# ================= MEDIA DOWNLOADER =================
def download_media(chat_id, text):
    try:
        url = extract_url(text)
        if not url:
            bot.send_message(chat_id, "❌ Invalid link")
            return

        # ================= TIKTOK (PHOTO + VIDEO) =================
        if "tiktok.com" in url:
            try:
                api = f"https://tikwm.com/api/?url={url}"
                res = requests.get(api, timeout=30).json()

                if res.get("code") == 0:
                    data = res["data"]

                    # ===== TIKTOK PHOTOS =====
                    if data.get("images"):
                        for i, img in enumerate(data["images"], start=1):
                            img_data = requests.get(img, timeout=30).content
                            filename = f"tiktok_{i}.jpg"

                            with open(filename, "wb") as f:
                                f.write(img_data)

                            with open(filename, "rb") as photo:
                                bot.send_photo(
                                    chat_id,
                                    photo,
                                    caption=f"📸 Photo {i}\n{CAPTION_TEXT}"
                                )

                            os.remove(filename)
                        return

                    # ===== TIKTOK VIDEO =====
                    if data.get("play"):
                        video_data = requests.get(data["play"], timeout=60).content
                        filename = "tiktok_video.mp4"

                        with open(filename, "wb") as f:
                            f.write(video_data)

                        send_video_with_music(chat_id, filename, "tiktok")
                        return
            except Exception as e:
                bot.send_message(chat_id, f"❌ TikTok error:\n{e}")
                return

# ================= PINTEREST =================
        if "pin.it" in url:
            try:
                r = requests.head(url, allow_redirects=True, timeout=10)
                url = r.url
            except Exception:
                pass

        if "pinterest.com" in url:
            try:
                ydl_opts = {
                    "format": "bv*+ba/b",
                    "outtmpl": "pinterest_%(id)s.%(ext)s",
                    "quiet": True,
                    "noplaylist": False,
                    "merge_output_format": "mp4"
                }

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)

                    # ===== haddii ay tahay carousel =====
                    if "entries" in info:
                        entries = info["entries"]
                    else:
                        entries = [info]

                    for entry in entries:
                        file = ydl.prepare_filename(entry)

                        # ===== PHOTO =====
                        if file.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                            with open(file, "rb") as photo:
                                bot.send_photo(chat_id, photo, caption=CAPTION_TEXT)

                        # ===== VIDEO =====
                        else:
                            send_video_with_music(chat_id, file, "pinterest")

                        # delete file
                        try:
                            os.remove(file)
                        except Exception:
                            pass

                return

            except Exception as e:
                bot.send_message(chat_id, f"❌ Download error:\n{e}")
                return

        # ================= FACEBOOK =================
        if "facebook.com" in url or "fb.watch" in url:
            ydl_opts = {
                "format": "bestvideo+bestaudio/best",
                "outtmpl": "facebook_%(id)s.%(ext)s",
                "merge_output_format": "mp4",
                "quiet": True
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                file = ydl.prepare_filename(info)

            send_video_with_music(chat_id, file, "facebook")
            return

        # ================= YOUTUBE =================
        if "youtube.com" in url or "youtu.be" in url:
            ydl_opts = {
                "format": "bestvideo+bestaudio/best",
                "outtmpl": "youtube_%(id)s.%(ext)s",
                "merge_output_format": "mp4",
                "quiet": True
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                file = ydl.prepare_filename(info)

            send_video_with_music(chat_id, file, "youtube")
            return

        bot.send_message(chat_id, "❌ Unsupported link")

    except Exception:
        bot.send_message(
            chat_id,
            "❌ Incorrect Tik Tok link.\n\n"
            "To download the video, send the link in the Tiktok, Facebook, Pinterest, YouTube."
        )
        return


# ================= MUSIC CONVERSION =================
@bot.callback_query_handler(func=lambda call: call.data.startswith("music|"))
def convert_music(call):

    file_path = call.data.split("|", 1)[1]
    audio_path = file_path.rsplit(".", 1)[0] + ".mp3"

    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", file_path, "-vn", "-acodec", "mp3", "-ab", "128k", "-ar", "44100", audio_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
        )

        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("📢 BOT CHANNEL", url="https://t.me/tiktokvediodownload"))

        with open(audio_path, "rb") as audio:
            bot.send_audio(
                call.message.chat.id,
                audio,
                title="Converted Music",
                performer="DownloadBot",
                caption=CAPTION_TEXT,
                reply_markup=kb
            )

        if os.path.exists(audio_path):
            os.remove(audio_path)

        # video tirtir ka dib conversion
        if os.path.exists(file_path):
            os.remove(file_path)

    except Exception as e:
        bot.send_message(call.message.chat.id, f"❌ Music conversion failed:\n{e}")

# ================= LINK HANDLER =================
@bot.message_handler(func=lambda m: m.text and "http" in m.text)
def handle_links(message):
    bot.send_message(message.chat.id, "⏳ Downloading...")
    download_media(message.chat.id, message.text)

# ================= FINAL BOT START =================
if __name__ == "__main__":
    print("🤖 Bot is running...")
    bot.infinity_polling(skip_pending=True, timeout=60)
