import telebot
from telebot.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
import os, json, random, requests, subprocess
from datetime import datetime
import yt_dlp

# ================= CONFIG =================
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 7983838654
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# ================= DATABASE =================
USERS_FILE = "users.json"
WITHDRAWS_FILE = "withdraws.json"

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

# ================= HELPERS =================
def random_ref():
    return str(random.randint(1000000000,9999999999))

def random_botid():
    return str(random.randint(10000000000,99999999999))

def now_month():
    return datetime.now().month

def is_admin(uid):
    return int(uid) == ADMIN_ID

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
    kb.add("💰 BALANCE","💸 WITHDRAWAL")
    kb.add("👥 REFERRAL","🆔 GET ID")
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

# ================= START HANDLER =================
@bot.message_handler(commands=['start'])
def start(m):
    uid = str(m.from_user.id)
    args = m.text.split()
    
    if uid not in users:
        ref = args[1] if len(args) > 1 else None
        users[uid] = {
            "balance":0.0,
            "blocked":0.0,
            "ref":random_ref(),
            "bot_id":random_botid(),
            "invited":0,
            "banned":False,
            "month": now_month()
        }
        # Referral reward
        if ref:
            for u in users:
                if users[u]["ref"] == ref:
                    users[u]["balance"] += 0.2
                    users[u]["invited"] += 1
                    bot.send_message(int(u), "🎉 You earned $0.2 from referral.")
                    break
        save_users()
    
    bot.send_message(
        m.chat.id,
        "👋 Welcome! Send Video Link to Download 🎬",
        reply_markup=user_menu(is_admin(uid))
    )

# ================= BALANCE HANDLER =================
@bot.message_handler(func=lambda m: m.text=="💰 BALANCE")
def balance(m):
    if banned_guard(m): return
    uid = str(m.from_user.id)
    bal = users[uid]["balance"]
    blk = users[uid].get("blocked",0.0)
    bot.send_message(
        m.chat.id,
        f"💰 Available: ${bal:.2f}\n⏳ Blocked: ${blk:.2f}"
    )

# ================= GET ID HANDLER =================
@bot.message_handler(func=lambda m: m.text=="🆔 GET ID")
def get_id(m):
    if banned_guard(m): return
    uid = str(m.from_user.id)
    bot.send_message(
        m.chat.id,
        f"🆔 BOT ID: <code>{users[uid]['bot_id']}</code>\n👤 Telegram ID: <code>{uid}</code>"
    )

# ================= REFERRAL HANDLER =================
@bot.message_handler(func=lambda m: m.text=="👥 REFERRAL")
def referral(m):
    if banned_guard(m): return
    uid = str(m.from_user.id)
    # Samee referral link gaar ah
    link = f"https://t.me/{bot.get_me().username}?start={users[uid]['ref']}"
    invited = users[uid].get("invited", 0)
    msg_text = (
        f"🔗 Your referral link:\n{link}\n"
        f"👥 Invited: {invited}\n\n"
        f"🎁 Each new user who joins using your link will automatically give you $0.2!"
    )
    bot.send_message(m.chat.id, msg_text)

# ================= CUSTOMER SUPPORT =================
@bot.message_handler(func=lambda m: m.text=="☎️ CUSTOMER")
def customer(m):
    if banned_guard(m): return
    bot.send_message(m.chat.id,"Contact support: @scholes1")

# ================= WITHDRAWAL MENU =================
@bot.message_handler(func=lambda m: m.text=="💸 WITHDRAWAL")
def withdraw_menu(m):
    if banned_guard(m): return
    uid = str(m.from_user.id)
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("USDT-BEP20")
    kb.add("🔙 CANCEL")
    bot.send_message(m.chat.id,"Select withdrawal method:", reply_markup=kb)

# ================= WITHDRAWAL PROCESSING =================
@bot.message_handler(func=lambda m: m.text in ["USDT-BEP20","🔙 CANCEL"])
def withdraw_method(m):
    uid = str(m.from_user.id)
    if m.text=="🔙 CANCEL":
        back_main_menu(m.chat.id, uid)
        return
    if m.text=="USDT-BEP20":
        kb = ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add("🔙 CANCEL")
        msg = bot.send_message(
            m.chat.id,
            "Enter your USDT BEP20 address (must start with 0x) or press 🔙 CANCEL",
            reply_markup=kb
        )
        bot.register_next_step_handler(msg, withdraw_address_step)

def withdraw_address_step(m):
    uid = str(m.from_user.id)
    text = (m.text or "").strip()
    if text=="🔙 CANCEL":
        back_main_menu(m.chat.id, uid)
        return
    if not text.startswith("0x"):
        kb = ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add("🔙 CANCEL")
        msg = bot.send_message(
            m.chat.id,
            "❌ Invalid address. Must start with 0x. Try again or press 🔙 CANCEL",
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
        f"Enter withdrawal amount\nMinimum: $1 | Balance: ${users[uid]['balance']:.2f}\nOr press 🔙 CANCEL",
        reply_markup=kb
    )
    bot.register_next_step_handler(msg, withdraw_amount_step)

def withdraw_amount_step(m):
    uid = str(m.from_user.id)
    text = (m.text or "").strip()
    if text=="🔙 CANCEL":
        back_main_menu(m.chat.id, uid)
        return
    try:
        amt = float(text)
    except:
        kb = ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add("🔙 CANCEL")
        msg = bot.send_message(
            m.chat.id,
            "❌ Invalid number. Enter again or press 🔙 CANCEL",
            reply_markup=kb
        )
        bot.register_next_step_handler(msg, withdraw_amount_step)
        return
    if amt<1:
        kb = ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add("🔙 CANCEL")
        msg = bot.send_message(
            m.chat.id,
            f"❌ Minimum withdrawal is $1\nBalance: ${users[uid]['balance']:.2f}",
            reply_markup=kb
        )
        bot.register_next_step_handler(msg, withdraw_amount_step)
        return
    if amt>users[uid]["balance"]:
        kb = ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add("🔙 CANCEL")
        msg = bot.send_message(
            m.chat.id,
            f"❌ Insufficient balance\nBalance: ${users[uid]['balance']:.2f}",
            reply_markup=kb
        )
        bot.register_next_step_handler(msg, withdraw_amount_step)
        return

    # Create withdrawal request
    wid = random.randint(10000,99999)
    addr = users[uid].pop("temp_addr")
    withdraws.append({
        "id": wid,
        "user": uid,
        "amount": amt,
        "blocked": amt,
        "address": addr,
        "status": "pending",
        "time": str(datetime.now())
    })
    users[uid]["balance"] -= amt
    users[uid]["blocked"] = users[uid].get("blocked",0.0)+amt
    save_users(); save_withdraws()

    # User confirmation message
    bot.send_message(
        m.chat.id,
        f"✅ Withdrawal Request Sent\n🧾 Request ID: {wid}\n💵 Amount: ${amt:.2f}\n🏦 Address: {addr}\n💰 Balance Left: ${users[uid]['balance']:.2f}\n⏳ Status: Pending",
        reply_markup=user_menu(is_admin(uid))
    )

    # Send request to admin with inline buttons
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("✅ CONFIRM", callback_data=f"confirm_{wid}"),
        InlineKeyboardButton("❌ REJECT", callback_data=f"reject_{wid}"),
        InlineKeyboardButton("🚫 BAN USER", callback_data=f"ban_{uid}"),
        InlineKeyboardButton("💰 BLOCK MONEY", callback_data=f"block_{wid}")
    )
    bot.send_message(
        ADMIN_ID,
        f"💳 NEW WITHDRAWAL\n👤 User: {uid}\n🤖 BOT ID: {users[uid]['bot_id']}\n👥 Referrals: {users[uid]['invited']}\n💵 Amount: ${amt:.2f}\n🧾 Request ID: {wid}\n🏦 Address: {addr}",
        reply_markup=markup
    )

# ================= ADMIN INLINE CALLBACKS =================
@bot.callback_query_handler(func=lambda call: call.data.startswith(("confirm_","reject_","ban_","block_")))
def admin_callbacks(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ You are not admin!")
        return
    data = call.data

    # CONFIRM
    if data.startswith("confirm_"):
        wid = int(data.split("_")[1])
        w = next((x for x in withdraws if x["id"]==wid), None)
        if not w or w["status"] != "pending": return
        w["status"] = "paid"
        users[w["user"]]["blocked"] -= w["blocked"]
        save_users(); save_withdraws()
        bot.answer_callback_query(call.id,"✅ Confirmed")
        bot.send_message(int(w["user"]), f"✅ Withdrawal #{wid} approved!")

    # REJECT
    elif data.startswith("reject_"):
        wid = int(data.split("_")[1])
        w = next((x for x in withdraws if x["id"]==wid), None)
        if not w or w["status"] != "pending": return
        w["status"] = "rejected"
        users[w["user"]]["balance"] += w["blocked"]
        users[w["user"]]["blocked"] -= w["blocked"]
        save_users(); save_withdraws()
        bot.answer_callback_query(call.id,"❌ Rejected")
        bot.send_message(int(w["user"]), f"❌ Withdrawal #{wid} rejected")

    # BAN USER
    elif data.startswith("ban_"):
        uid = data.split("_")[1]
        if uid in users:
            users[uid]["banned"] = True
            save_users()
            bot.answer_callback_query(call.id,"🚫 User banned")
            bot.send_message(int(uid),"🚫 You have been banned by admin.")

    # BLOCK MONEY
    elif data.startswith("block_"):
        wid = int(data.split("_")[1])
        w = next((x for x in withdraws if x["id"]==wid), None)
        if not w or w["status"] != "pending": return
        uid = w["user"]
        amt = w["blocked"]
        w["status"] = "blocked"
        code = str(random.randint(1000,9999))
        w["block_code"] = code
        users[uid]["blocked"] -= amt
        save_users(); save_withdraws()
        bot.answer_callback_query(call.id,"💰 Money Blocked")
        bot.send_message(
            int(uid),
            f"🚫 Your withdrawal of ${amt:.2f} is BLOCKED by admin.\n💳 Code: {code}\nContact support to release funds."
    )

# ================= UNBLOCK MONEY =================
@bot.message_handler(func=lambda m: m.text=="💳 UNBLOCK MONEY")
def unblock_money_start(m):
    if not is_admin(m.from_user.id): return
    msg = bot.send_message(m.chat.id,"🔢 Send 4-digit Block Code to UNBLOCK the money")
    bot.register_next_step_handler(msg, unblock_money_process)

def unblock_money_process(m):
    if not is_admin(m.from_user.id): return
    code = m.text.strip()
    # Find withdrawal with this block code
    w = next((x for x in withdraws if x.get("block_code") == code), None)
    if not w:
        bot.send_message(m.chat.id,"❌ Invalid Block Code")
        return
    uid = w["user"]
    amt = w["blocked"]
    users[uid]["balance"] += amt
    w["status"] = "unblocked"
    w.pop("block_code", None)
    save_users(); save_withdraws()
    bot.send_message(int(uid), f"✅ Your blocked ${amt:.2f} is now available in balance!")
    bot.send_message(m.chat.id,f"✅ Money unblocked for user {uid}")

# ================= WITHDRAWAL CHECK =================
@bot.message_handler(func=lambda m: m.text=="💳 WITHDRAWAL CHECK")
def withdrawal_check_start(m):
    if not is_admin(m.from_user.id): return
    msg = bot.send_message(m.chat.id,"Enter Withdrawal Request ID to check\nExample: 402000")
    bot.register_next_step_handler(msg, withdrawal_check_process)

def withdrawal_check_process(m):
    if not is_admin(m.from_user.id): return
    try:
        wid = int(m.text.strip())
    except:
        bot.send_message(m.chat.id,"❌ Invalid Request ID")
        return
    w = next((x for x in withdraws if x["id"]==wid), None)
    if not w:
        bot.send_message(m.chat.id,"❌ Request ID not found")
        return
    uid = w["user"]
    bot_id = users.get(uid, {}).get("bot_id","Unknown")
    invited = users.get(uid, {}).get("invited",0)
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

# ================= ADMIN PANEL FIX =================
@bot.message_handler(func=lambda m: m.text=="👑 ADMIN PANEL")
def open_admin_panel(m):
    if not is_admin(m.from_user.id):
        bot.send_message(m.chat.id,"❌ You are not admin")
        return
    # Show admin menu with all options including UNBLOCK MONEY and WITHDRAWAL CHECK
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📊 STATS", "📢 BROADCAST")
    kb.add("➕ ADD BALANCE", "➖ REMOVE MONEY")
    kb.add("✅ UNBAN USER", "💳 WITHDRAWAL CHECK")
    kb.add("💰 UNBLOCK MONEY")
    kb.add("🔙 BACK MAIN MENU")
    bot.send_message(m.chat.id,"👑 Admin Panel", reply_markup=kb)

# ================= ADD BALANCE =================
@bot.message_handler(func=lambda m: m.text=="➕ ADD BALANCE")
def add_balance_start(m):
    if not is_admin(m.from_user.id): return
    msg = bot.send_message(
        m.chat.id,
        "Send BOT ID or Telegram ID and amount separated by space:\nExample: 123456789 10.5"
    )
    bot.register_next_step_handler(msg, add_balance_process)

def add_balance_process(m):
    if not is_admin(m.from_user.id): return
    try:
        uid_str, amt_str = m.text.strip().split()
        amt = float(amt_str)
        # Telegram ID first
        uid = uid_str if uid_str in users else find_user_by_botid(uid_str)
        if not uid or amt <= 0:
            bot.send_message(m.chat.id,"❌ Invalid input")
            return
        users[uid]["balance"] += amt
        save_users()
        bot.send_message(m.chat.id,f"✅ Added ${amt:.2f} to user {uid}")
        bot.send_message(int(uid), f"💰 Your balance has been increased by ${amt:.2f}")
    except:
        bot.send_message(m.chat.id,"❌ Error. Use format: <BOT ID or Telegram ID> <amount>")

# ================= REMOVE MONEY =================
@bot.message_handler(func=lambda m: m.text=="➖ REMOVE MONEY")
def remove_balance_start(m):
    if not is_admin(m.from_user.id): return
    msg = bot.send_message(
        m.chat.id,
        "Send BOT ID or Telegram ID and amount separated by space:\nExample: 123456789 5.0"
    )
    bot.register_next_step_handler(msg, remove_balance_process)

def remove_balance_process(m):
    if not is_admin(m.from_user.id): return
    try:
        uid_str, amt_str = m.text.strip().split()
        amt = float(amt_str)
        # Telegram ID first
        uid = uid_str if uid_str in users else find_user_by_botid(uid_str)
        if not uid or amt <= 0 or users[uid]["balance"] < amt:
            bot.send_message(m.chat.id,"❌ Invalid input or insufficient balance")
            return
        users[uid]["balance"] -= amt
        save_users()
        bot.send_message(m.chat.id,f"✅ Removed ${amt:.2f} from user {uid}")
        bot.send_message(int(uid), f"💸 ${amt:.2f} has been removed from your balance")
    except:
        bot.send_message(m.chat.id,"❌ Error. Use format: <BOT ID or Telegram ID> <amount>")

# ================= BALANCE HANDLER =================
@bot.message_handler(func=lambda m: m.text=="💰 BALANCE")
def balance_handler(m):
    if banned_guard(m): return
    uid = str(m.from_user.id)
    bal = users[uid]["balance"]
    blk = users[uid].get("blocked",0.0)
    bot.send_message(
        m.chat.id,
        f"💰 Available Balance: ${bal:.2f}\n⏳ Blocked: ${blk:.2f}"
    )

# ================= GET ID HANDLER =================
@bot.message_handler(func=lambda m: m.text=="🆔 GET ID")
def get_id_handler(m):
    if banned_guard(m): return
    uid = str(m.from_user.id)
    bot.send_message(
        m.chat.id,
        f"🆔 BOT ID: <code>{users[uid]['bot_id']}</code>\n👤 Telegram ID: <code>{uid}</code>"
    )

# ================= REFERRAL HANDLER =================
@bot.message_handler(func=lambda m: m.text=="👥 REFERRAL")
def referral_handler(m):
    if banned_guard(m): return
    uid = str(m.from_user.id)
    link = f"https://t.me/{bot.get_me().username}?start={users[uid]['ref']}"
    invited = users[uid].get("invited",0)
    bot.send_message(
        m.chat.id,
        f"🔗 Your referral link:\n{link}\n"
        f"👥 Invited: {invited}\n\n"
        f"🎁 Each new user joining via your link gives you $0.2!"
    )

# ================= CUSTOMER SUPPORT =================
@bot.message_handler(func=lambda m: m.text=="☎️ CUSTOMER")
def customer_support_handler(m):
    if banned_guard(m): return
    bot.send_message(
        m.chat.id,
        "☎️ Contact support: @scholes1"
    )

# ================= START HANDLER =================
@bot.message_handler(commands=['start'])
def start_handler(m):
    uid = str(m.from_user.id)
    args = m.text.split()
    if uid not in users:
        ref = args[1] if len(args) > 1 else None
        users[uid] = {
            "balance":0.0,
            "blocked":0.0,
            "ref":random_ref(),
            "bot_id":random_botid(),
            "invited":0,
            "banned":False,
            "month": now_month()
        }
        # Referral reward
        if ref:
            ref_user = next((u for u,d in users.items() if d["ref"]==ref), None)
            if ref_user:
                users[ref_user]["balance"] += 0.2
                users[ref_user]["invited"] += 1
                bot.send_message(int(ref_user), "🎉 You earned $0.2 from referral!")
        save_users()
    bot.send_message(
        m.chat.id,
        "👋 Welcome! Send Video Link to Download 🎬",
        reply_markup=user_menu(is_admin(uid))
    )

# ================= USER MENU =================
def user_menu(show_admin=False):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("💰 BALANCE","💸 WITHDRAWAL")
    kb.add("👥 REFERRAL","🆔 GET ID")
    kb.add("☎️ CUSTOMER")
    if show_admin:
        kb.add("👑 ADMIN PANEL")
    return kb

# ================= ADMIN PANEL =================
def admin_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📊 STATS","📢 BROADCAST")
    kb.add("➕ ADD BALANCE","➖ REMOVE MONEY")
    kb.add("✅ UNBAN USER","💳 WITHDRAWAL CHECK")
    kb.add("💰 UNBLOCK MONEY")
    kb.add("🔙 BACK MAIN MENU")
    return kb

@bot.message_handler(func=lambda m: m.text=="👑 ADMIN PANEL")
def open_admin_panel(m):
    if not is_admin(m.from_user.id):
        bot.send_message(m.chat.id,"❌ You are not admin")
        return
    bot.send_message(m.chat.id,"👑 Admin Panel", reply_markup=admin_menu())

# ================= WITHDRAWAL CHECK =================
@bot.message_handler(func=lambda m: m.text=="💳 WITHDRAWAL CHECK")
def withdrawal_check_start(m):
    if not is_admin(m.from_user.id): return
    msg = bot.send_message(m.chat.id,"Enter Withdrawal Request ID (e.g., 40201):")
    bot.register_next_step_handler(msg, withdrawal_check_process)

def withdrawal_check_process(m):
    if not is_admin(m.from_user.id): return
    try:
        wid = int(m.text.strip())
    except:
        bot.send_message(m.chat.id,"❌ Invalid Request ID")
        return
    w = next((x for x in withdraws if x["id"]==wid), None)
    if not w:
        bot.send_message(m.chat.id,"❌ Request ID not found")
        return
    uid = w["user"]
    bot_id = users.get(uid, {}).get("bot_id","Unknown")
    invited = users.get(uid, {}).get("invited",0)
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
    bot.send_message(m.chat.id,msg_text)

# ================= UNBLOCK MONEY =================
@bot.message_handler(func=lambda m: m.text=="💰 UNBLOCK MONEY")
def unblock_money_start(m):
    if not is_admin(m.from_user.id): return
    msg = bot.send_message(m.chat.id,"🔢 Send 4-digit Block Code to UNBLOCK funds:")
    bot.register_next_step_handler(msg, unblock_money_process)

def unblock_money_process(m):
    if not is_admin(m.from_user.id): return
    code = m.text.strip()
    w = next((x for x in withdraws if x.get("block_code") == code), None)
    if not w:
        bot.send_message(m.chat.id,"❌ Invalid Block Code")
        return
    uid = w["user"]
    amt = w["blocked"]
    users[uid]["balance"] += amt
    w["status"] = "unblocked"
    w.pop("block_code",None)
    save_users(); save_withdraws()
    bot.send_message(int(uid),f"✅ Your blocked ${amt:.2f} is now available in balance!")
    bot.send_message(m.chat.id,f"✅ Money unblocked for user {uid}")

  # ================= MEDIA DOWNLOADER =================
def send_video_with_music(chat_id, file):
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🎵 MUSIC", callback_data=f"music|{file}"))
    bot.send_video(
        chat_id,
        open(file, "rb"),
        caption="Downloaded by @Downloadvedioytibot",
        reply_markup=kb
    )

def download_media(chat_id, url):
    try:
        # ===== TIKTOK =====
        if "tiktok.com" in url:
            res = requests.get(f"https://tikwm.com/api/?url={url}", timeout=20).json()
            if res.get("code") == 0:
                data = res["data"]
                # Images
                if data.get("images"):
                    for i, img in enumerate(data["images"], 1):
                        img_data = requests.get(img, timeout=20).content
                        filename = f"tt_{i}.jpg"
                        with open(filename,"wb") as f: f.write(img_data)
                        bot.send_photo(chat_id, open(filename,"rb"), caption=f"📸 Photo {i}")
                        os.remove(filename)
                    return
                # Video
                if data.get("play"):
                    vid_data = requests.get(data["play"], timeout=60).content
                    with open("tt_video.mp4","wb") as f: f.write(vid_data)
                    send_video_with_music(chat_id, "tt_video.mp4")
                    return

        # ===== YOUTUBE =====
        if "youtube.com" in url or "youtu.be" in url:
            ydl_opts = {"outtmpl":"youtube.%(ext)s","format":"mp4","quiet":True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                file = ydl.prepare_filename(info)
            send_video_with_music(chat_id, file)
            return

        bot.send_message(chat_id,"❌ Unsupported link")
    except Exception as e:
        bot.send_message(chat_id,f"Download error: {e}")

# ================= MUSIC CONVERSION =================
@bot.callback_query_handler(func=lambda call: call.data.startswith("music|"))
def convert_music(call):
    file = call.data.split("|")[1]
    audio = file.replace(".mp4",".mp3")
    try:
        subprocess.run(
            ["ffmpeg","-i",file,"-vn","-ab","128k","-ar","44100",audio],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("📢 BOT CHANNEL", url="https://t.me/tiktokvediodownload"))
        bot.send_audio(
            call.message.chat.id,
            open(audio,"rb"),
            title="Downloaded Music",
            performer="Downloadvedioytibot",
            caption="Downloaded via @Downloadvedioytibot",
            reply_markup=kb
        )
        os.remove(audio)
    except:
        bot.send_message(call.message.chat.id,"❌ Music conversion failed")

# ================= LINK HANDLER =================
@bot.message_handler(func=lambda m: m.text and "http" in m.text)
def handle_links(message):
    bot.send_message(message.chat.id,"⏳ Downloading...")
    download_media(message.chat.id, message.text)

# ================= RUN BOT =================
if __name__ == "__main__":
    print("🤖 Bot is running...")
    try:
        bot.infinity_polling(skip_pending=True)
    except Exception as e:
        print("❌ Bot crashed:", e)
