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
from flask import Flask, request, jsonify
import threading

# ================= CONFIG =================
# ================= VERIFY SYSTEM =================
VERIFY_MODE = False
pending_verify = {}
verified_users = set()
pending_downloads = {}

BOT2_TOKEN = os.getenv("BOT2_TOKEN")
bot2 = telebot.TeleBot(BOT2_TOKEN)

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [7983838654]  # Liiska admins, waxaad ku dari kartaa ID kale haddii loo baahdo

BASE_DIR = os.getcwd()  # Folder-ka bot-ku ka shaqeeyo

CHANNEL_USERNAME = "tiktokvediodownload"  # Ha lahayn @
POST_CHANNELS = []
pending_links = {}
CHANNEL_WINDOW_OPEN = False

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

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
users = load_json(USERS_FILE, {})
withdraws = load_json(WITHDRAWS_FILE, [])

videos_data = load_json(VIDEOS_FILE, {
    "total": 0,
    "platforms": {
        "tiktok": 0,
        "youtube": 0,
        "facebook": 0,
        "instagram": 0,
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

# ================= VERIFY HELPERS =================
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

def generate_code():
    return str(random.randint(100000, 999999))

def start_verification(user_id):
    code = generate_code()
    pending_verify[str(user_id)] = code

    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton(
            "🔘 GET CODE",
            url="https://t.me/Verifyd_bot?start={}".format(user_id)
        )
    )

    bot.send_message(
        user_id,
        "🔐 Verification Required\n\n"
        "Riix GET CODE si aad u hesho code-ka kadibna halkaan ku soo dir.",
        reply_markup=kb
    )

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
    kb.add("🔥 UN BAN-USER", "📌 POST CHANNEL")
    kb.add("👥 SEE LIST", "🔎 SEARCH USER")
    kb.add("✅ VERIFY", "❌ CLOSE VERIFY")
    kb.add("❌ CLOSE WINDOWS")
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

CHANNEL_USERNAME = "@tiktokvediodownload"

# ================= START HANDLER =================
@bot.message_handler(commands=['start'])
def start_handler(message):
    uid = message.from_user.id
    args = message.text.split()

    # Haddii user cusub, ku dar database
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
        # Referral reward
        if ref:
            ref_user = next((u for u, d in users.items() if d["ref"] == ref), None)
            if ref_user:
                users[ref_user]["balance"] += 0.2
                users[ref_user]["invited"] += 1
                bot.send_message(int(ref_user), "🎉 You earned $0.2 from referral!")

        save_users()

    # Hubinta join
    check_membership(uid)

# ================= BOT2 ================
@bot2.message_handler(commands=['start'])
def bot2_start(m):

    uid = str(m.from_user.id)

    if uid in pending_verify:

        code = pending_verify.get(uid)

        bot2.send_message(
            m.chat.id,
            "🔐 Your Verification Code:\n\n"
            f"`{code}`\n\n"
            "👆 Taabo code-ka si aad u copy garayso kadibna ku celi bot-ka weyn.",
            parse_mode="Markdown"
        )

    else:

        bot2.send_message(
            m.chat.id,
            "ℹ️ Verification lama helin.\n"
            "Marka hore ka bilow bot-ka weyn si aad code u hesho."
        )

# ================= CHECK MEMBERSHIP =================
def check_membership(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)

        if member.status in ["member", "administrator", "creator"]:
            bot.send_message(
                user_id,
                """🎬 Welcome to Video Downloader Bot!

This bot helps you easily download videos and music from many popular platforms directly to Telegram.

With this bot you can download content from platforms like:
• TikTok
• Instagram
• Facebook
• Pinterest
• YouTube
• And many other video links available on the internet.

📥 How to use the bot:

1. Copy the video link from any supported platform.
2. Send the link here in the bot.
3. The bot will automatically download the video for you.
4. You will receive the video file directly in this chat.

⚡ Fast & Easy Downloads
Our system processes your request quickly and sends the highest available quality whenever possible.

💰 Earn Money With Referrals
You can also earn rewards by inviting your friends to use the bot.

Here is how it works:
• Share your personal referral link with others.
• When someone joins the bot using your link, you receive a reward.
• The more people you invite, the more rewards you earn.

🚀 Why use this bot?
• Fast downloading system
• Supports multiple platforms
• Simple and easy to use
• Earn rewards through referrals

📌 Important:
Please make sure you follow the required channel(s) to continue using the bot and to keep the service running.

Now you're ready to start!

👇 Send any video link to begin downloading.""",
                reply_markup=user_menu(is_admin(user_id))
            )
        else:
            send_join_message(user_id)

    except:
        send_join_message(user_id)


# ================= SEND JOIN MESSAGE =================
def send_join_message(user_id):
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("➕ JOIN CHANNEL", url="https://t.me/tiktokvediodownload")
    )
    kb.add(
        InlineKeyboardButton("✅ CONFIRM", callback_data="confirm_join")
    )

    bot.send_message(
        user_id,
        "⚠️ You must join our channel to use this bot.",
        reply_markup=kb
    )


# ================= CONFIRM JOIN =================
@bot.callback_query_handler(func=lambda call: call.data == "confirm_join")
def confirm_join(call):

    user_id = call.from_user.id

    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)

        if member.status in ["member", "administrator", "creator"]:

            # ✅ user waa join gareeyay
            bot.answer_callback_query(call.id, "✅ Join verified")

            # delete message-ka join-ka
            bot.delete_message(
                call.message.chat.id,
                call.message.message_id
            )

            bot.send_message(
                user_id,
                "✅ Join confirmed! Send your video link."
            )

        else:
            # ❌ user ma join garayn
            bot.answer_callback_query(
                call.id,
                "❌ Please join the channel first!",
                show_alert=True
            )

    except Exception as e:
        bot.answer_callback_query(
            call.id,
            "❌ Error checking join status",
            show_alert=True
        )

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

# ================= VERIFY CONTROL =================
@bot.message_handler(func=lambda m: m.text == "✅ VERIFY")
def enable_verify(m):
    global VERIFY_MODE
    if not is_admin(m.from_user.id): return
    VERIFY_MODE = True
    bot.send_message(m.chat.id, "✅ Verification ENABLED")

@bot.message_handler(func=lambda m: m.text == "❌ CLOSE VERIFY")
def disable_verify(m):
    global VERIFY_MODE
    if not is_admin(m.from_user.id): return
    VERIFY_MODE = False
    bot.send_message(m.chat.id, "❌ Verification DISABLED")

    # ================= VERIFY CODE CHECK =================
@bot.message_handler(func=lambda m: m.text.isdigit() and len(m.text) == 6)
def check_verify_code(m):
    uid = str(m.from_user.id)

    if not VERIFY_MODE:
        return

    if uid in verified_users:
        return

    if pending_verify.get(uid) == m.text:
        verified_users.add(uid)
        pending_verify.pop(uid, None)
        bot.send_message(m.chat.id, "✅ Verification Successful!")

        # ===== SOO CELI DOWNLOAD =====
        if uid in pending_downloads:
            old_url = pending_downloads.pop(uid)

            msg = bot.send_message(
                m.chat.id,
                "⬇️ Downloading your previous link..."
            )

            download_media(m.chat.id, old_url)

            try:
                bot.delete_message(
                    m.chat.id,
                    msg.message_id
                )
            except:
                pass
    else:
        bot.send_message(m.chat.id, "❌ Incorrect code.")

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
