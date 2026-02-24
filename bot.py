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
    kb.add("🔙 BACK TO MAIN MENU")
    return kb


# ================= MAIN MENU FUNCTION =================
def send_main_menu(chat_id, uid):
    bot.send_message(
        chat_id,
        "🏠 <b>Main Menu</b>",
        reply_markup=user_menu(is_admin(uid))
    )

# ================= BACK HANDLER (GLOBAL FIX) =================
@bot.message_handler(func=lambda m: m.text in ["🔙 CANCEL", "🔙 BACK TO MAIN MENU"])
def global_back_handler(m):
    uid = str(m.from_user.id)
    if banned_guard(m): 
        return
    send_main_menu(m.chat.id, uid)


# ================= ADMIN PANEL BUTTON =================
@bot.message_handler(func=lambda m: m.text=="👑 ADMIN PANEL")
def admin_panel_btn(m):
    uid = str(m.from_user.id)

    if not is_admin(uid):
        bot.send_message(m.chat.id, "❌ You are not admin")
        return

    bot.send_message(
        m.chat.id,
        "👑 <b>Admin Panel</b>",
        reply_markup=admin_menu()
    )


# ================= START HANDLER =================
@bot.message_handler(commands=['start'])
def start(m):
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
            for u in users:
                if users[u]["ref"] == ref:
                    users[u]["balance"] += 0.2
                    users[u]["invited"] += 1
                    bot.send_message(int(u), "🎉 You earned $0.2 from referral.")
                    break

        save_users()

    send_main_menu(m.chat.id, uid)

# ================= BALANCE HANDLER (FIXED DISPLAY) =================
@bot.message_handler(func=lambda m: m.text=="💰 BALANCE")
def balance(m):
    if banned_guard(m): return
    uid = str(m.from_user.id)

    available = users[uid].get("balance", 0.0)
    blocked = users[uid].get("blocked", 0.0)

    pending = sum(
        w["amount"] for w in withdraws
        if w["user"] == uid and w["status"] == "pending"
    )

    msg = (
        f"💰 <b>Your Balance</b>\n\n"
        f"✅ Available: ${available:.2f}\n"
        f"⏳ Pending: ${pending:.2f}\n"
        f"🚫 Blocked: ${blocked:.2f}"
    )

    bot.send_message(m.chat.id, msg)


# ================= WITHDRAWAL MENU =================
@bot.message_handler(func=lambda m: m.text=="💸 WITHDRAWAL")
def withdraw_menu(m):
    if banned_guard(m): return

    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("USDT-BEP20")
    kb.add("🔙 CANCEL")

    bot.send_message(
        m.chat.id,
        "Select withdrawal method:",
        reply_markup=kb
    )


# ================= WITHDRAWAL METHOD =================
@bot.message_handler(func=lambda m: m.text in ["USDT-BEP20"])
def withdraw_method(m):
    uid = str(m.from_user.id)

    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🔙 CANCEL")

    msg = bot.send_message(
        m.chat.id,
        "Enter your USDT BEP20 address (must start with 0x)\nOr press 🔙 CANCEL",
        reply_markup=kb
    )
    bot.register_next_step_handler(msg, withdraw_address_step)


def withdraw_address_step(m):
    uid = str(m.from_user.id)
    text = (m.text or "").strip()

    if text == "🔙 CANCEL":
        send_main_menu(m.chat.id, uid)
        return

    if not text.startswith("0x"):
        msg = bot.send_message(
            m.chat.id,
            "❌ Invalid address. Must start with 0x\nTry again or press 🔙 CANCEL"
        )
        bot.register_next_step_handler(msg, withdraw_address_step)
        return

    users[uid]["temp_addr"] = text
    save_users()

    msg = bot.send_message(
        m.chat.id,
        f"Enter withdrawal amount\nMinimum: $1\nAvailable: ${users[uid]['balance']:.2f}\nOr press 🔙 CANCEL"
    )
    bot.register_next_step_handler(msg, withdraw_amount_step)


def withdraw_amount_step(m):
    uid = str(m.from_user.id)
    text = (m.text or "").strip()

    if text == "🔙 CANCEL":
        send_main_menu(m.chat.id, uid)
        return

    try:
        amt = float(text)
    except:
        msg = bot.send_message(m.chat.id, "❌ Invalid number. Try again:")
        bot.register_next_step_handler(msg, withdraw_amount_step)
        return

    if amt < 1:
        msg = bot.send_message(m.chat.id, "❌ Minimum withdrawal is $1")
        bot.register_next_step_handler(msg, withdraw_amount_step)
        return

    if amt > users[uid]["balance"]:
        msg = bot.send_message(m.chat.id, "❌ Insufficient balance")
        bot.register_next_step_handler(msg, withdraw_amount_step)
        return

    wid = random.randint(10000, 99999)
    addr = users[uid].pop("temp_addr")

    withdraws.append({
        "id": wid,
        "user": uid,
        "amount": amt,
        "address": addr,
        "status": "pending",
        "time": str(datetime.now())
    })

    # lacagta AVAILABLE laga jarayaa
    users[uid]["balance"] -= amt

    save_users()
    save_withdraws()

    bot.send_message(
        m.chat.id,
        f"✅ Withdrawal Request Sent\n"
        f"🧾 ID: {wid}\n"
        f"💵 Amount: ${amt:.2f}\n"
        f"⏳ Status: Pending"
    )

    send_main_menu(m.chat.id, uid)

    # Admin buttons
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("✅ CONFIRM", callback_data=f"confirm_{wid}"),
        InlineKeyboardButton("❌ REJECT", callback_data=f"reject_{wid}"),
    )
    markup.add(
        InlineKeyboardButton("💰 BLOCK MONEY", callback_data=f"block_{wid}")
    )

    bot.send_message(
        ADMIN_ID,
        f"💳 NEW WITHDRAWAL\n"
        f"👤 User: {uid}\n"
        f"💵 Amount: ${amt:.2f}\n"
        f"🧾 ID: {wid}\n"
        f"🏦 Address: {addr}",
        reply_markup=markup
                )

# ================= ADMIN CALLBACKS (FIXED) =================
@bot.callback_query_handler(func=lambda call: call.data.startswith(("confirm_","reject_","block_")))
def admin_callbacks(call):
    data = call.data

    # ===== CONFIRM =====
    if data.startswith("confirm_"):
        wid = int(data.split("_")[1])
        w = next((x for x in withdraws if x["id"] == wid), None)

        if not w or w["status"] != "pending":
            bot.answer_callback_query(call.id, "Already processed")
            return

        w["status"] = "paid"
        save_withdraws()

        bot.answer_callback_query(call.id, "✅ Confirmed")
        bot.send_message(int(w["user"]),
            f"✅ Your withdrawal #{wid} has been approved and paid."
        )


    # ===== REJECT =====
    elif data.startswith("reject_"):
        wid = int(data.split("_")[1])
        w = next((x for x in withdraws if x["id"] == wid), None)

        if not w or w["status"] != "pending":
            bot.answer_callback_query(call.id, "Already processed")
            return

        uid = w["user"]
        amt = w["amount"]

        # lacagta user-ka AVAILABLE ugu celin
        users[uid]["balance"] += amt
        w["status"] = "rejected"

        save_users()
        save_withdraws()

        bot.answer_callback_query(call.id, "❌ Rejected")
        bot.send_message(int(uid),
            f"❌ Your withdrawal #{wid} was rejected.\n"
            f"${amt:.2f} returned to your balance."
        )


    # ===== BLOCK MONEY =====
    elif data.startswith("block_"):
        wid = int(data.split("_")[1])
        w = next((x for x in withdraws if x["id"] == wid), None)

        if not w or w["status"] != "pending":
            bot.answer_callback_query(call.id, "Already processed")
            return

        uid = w["user"]
        amt = w["amount"]

        # 4-digit code
        code = str(random.randint(1000, 9999))

        # lacagta user-ka BLOCKED ku dar
        users[uid]["blocked"] = users[uid].get("blocked", 0.0) + amt

        w["status"] = "blocked"
        w["block_code"] = code

        save_users()
        save_withdraws()

        bot.answer_callback_query(call.id, "💰 Money Blocked")

        bot.send_message(int(uid),
            f"🚫 Your withdrawal of ${amt:.2f} has been BLOCKED by admin.\n\n"
            f"🔐 Your 4-digit code: <code>{code}</code>\n\n"
            f"Contact support and provide this code to release funds."
        )


# ================= UNBLOCK MONEY (ADMIN SIDE) =================
@bot.message_handler(func=lambda m: m.text=="💰 UNBLOCK MONEY")
def unblock_money_start(m):
    if not is_admin(m.from_user.id):
        return

    msg = bot.send_message(
        m.chat.id,
        "Send the 4-digit Block Code to UNBLOCK money\nOr press 🔙 BACK TO MAIN MENU"
    )
    bot.register_next_step_handler(msg, unblock_money_process)


def unblock_money_process(m):
    if not is_admin(m.from_user.id):
        return

    code = (m.text or "").strip()

    if code in ["🔙 BACK TO MAIN MENU", "🔙 CANCEL"]:
        send_main_menu(m.chat.id, str(m.from_user.id))
        return

    # find withdrawal with this code and status blocked
    w = next((x for x in withdraws 
              if x.get("block_code") == code and x.get("status") == "blocked"), None)

    if not w:
        bot.send_message(m.chat.id, "❌ Invalid or already used Block Code")
        return

    uid = w["user"]
    amt = w["amount"]

    # lacagta balance ugu celi
    users[uid]["balance"] += amt

    # blocked ka jar
    users[uid]["blocked"] -= amt

    w["status"] = "unblocked"
    w.pop("block_code", None)

    save_users()
    save_withdraws()

    bot.send_message(int(uid),
        f"✅ Your blocked ${amt:.2f} has been released and added to your balance."
    )

    bot.send_message(m.chat.id,
        f"✅ Money successfully unblocked for user {uid}"
    )

    send_main_menu(m.chat.id, str(m.from_user.id))

# ================= ADMIN STATS (FIXED) =================
@bot.message_handler(func=lambda m: m.text=="📊 STATS")
def admin_stats(m):
    if not is_admin(m.from_user.id):
        return

    total_users = len(users)

    total_available = sum(u.get("balance", 0) for u in users.values())
    total_blocked = sum(u.get("blocked", 0) for u in users.values())

    total_paid = sum(w["amount"] for w in withdraws if w["status"] == "paid")
    total_pending = sum(w["amount"] for w in withdraws if w["status"] == "pending")
    total_blocked_withdraw = sum(w["amount"] for w in withdraws if w["status"] == "blocked")

    banned_users = sum(1 for u in users.values() if u.get("banned"))

    msg = (
        f"📊 <b>ADMIN STATS</b>\n\n"
        f"👥 Total Users: {total_users}\n\n"
        f"💰 Total Available Balance: ${total_available:.2f}\n"
        f"🚫 Total Blocked Balance: ${total_blocked:.2f}\n\n"
        f"💵 Total Paid Withdrawals: ${total_paid:.2f}\n"
        f"⏳ Total Pending Withdrawals: ${total_pending:.2f}\n"
        f"🔒 Total Blocked Withdrawals: ${total_blocked_withdraw:.2f}\n\n"
        f"🚫 Banned Users: {banned_users}"
    )

    bot.send_message(m.chat.id, msg)


# ================= WITHDRAWAL CHECK (ADMIN VIEW) =================
@bot.message_handler(func=lambda m: m.text=="💳 WITHDRAWAL CHECK")
def withdrawal_check(m):
    if not is_admin(m.from_user.id):
        return

    if not withdraws:
        bot.send_message(m.chat.id, "No withdrawals yet.")
        return

    text = "💳 <b>Withdrawal Requests</b>\n\n"

    for w in withdraws[-20:]:  # last 20 only
        text += (
            f"🧾 ID: {w['id']}\n"
            f"👤 User: {w['user']}\n"
            f"💵 Amount: ${w['amount']:.2f}\n"
            f"📌 Status: {w['status']}\n"
            f"━━━━━━━━━━━━━━\n"
        )

    bot.send_message(m.chat.id, text)


# ================= ADMIN BACK FIX =================
@bot.message_handler(func=lambda m: m.text=="🔙 BACK TO MAIN MENU")
def admin_back_to_main(m):
    uid = str(m.from_user.id)

    if not is_admin(uid):
        send_main_menu(m.chat.id, uid)
        return

    send_main_menu(m.chat.id, uid)

# ================= SECURE ADMIN CALLBACK HANDLER =================
@bot.callback_query_handler(func=lambda call: call.data.startswith(("confirm_","reject_","block_","ban_")))
def secure_admin_callbacks(call):

    # 🔐 Admin only protection
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ Not authorized")
        return

    data = call.data


    # ===== BAN USER FROM WITHDRAWAL =====
    if data.startswith("ban_"):
        uid = data.split("_")[1]

        if uid in users:
            users[uid]["banned"] = True
            save_users()

            bot.send_message(int(uid), "🚫 You have been banned by admin.")
            bot.answer_callback_query(call.id, "User banned")


    # ===== CONFIRM =====
    elif data.startswith("confirm_"):
        wid = int(data.split("_")[1])
        w = next((x for x in withdraws if x["id"] == wid), None)

        if not w or w["status"] != "pending":
            bot.answer_callback_query(call.id, "Already processed")
            return

        w["status"] = "paid"
        save_withdraws()

        bot.send_message(int(w["user"]),
            f"✅ Withdrawal #{wid} has been approved and paid."
        )

        bot.answer_callback_query(call.id, "Confirmed")


    # ===== REJECT =====
    elif data.startswith("reject_"):
        wid = int(data.split("_")[1])
        w = next((x for x in withdraws if x["id"] == wid), None)

        if not w or w["status"] != "pending":
            bot.answer_callback_query(call.id, "Already processed")
            return

        uid = w["user"]
        amt = w["amount"]

        users[uid]["balance"] += amt
        w["status"] = "rejected"

        save_users()
        save_withdraws()

        bot.send_message(int(uid),
            f"❌ Withdrawal #{wid} rejected.\n"
            f"${amt:.2f} returned to balance."
        )

        bot.answer_callback_query(call.id, "Rejected")


    # ===== BLOCK MONEY =====
    elif data.startswith("block_"):
        wid = int(data.split("_")[1])
        w = next((x for x in withdraws if x["id"] == wid), None)

        if not w or w["status"] != "pending":
            bot.answer_callback_query(call.id, "Already processed")
            return

        uid = w["user"]
        amt = w["amount"]

        code = str(random.randint(1000, 9999))

        users[uid]["blocked"] = users[uid].get("blocked", 0) + amt

        w["status"] = "blocked"
        w["block_code"] = code

        save_users()
        save_withdraws()

        bot.send_message(int(uid),
            f"🚫 Withdrawal of ${amt:.2f} BLOCKED.\n"
            f"🔐 Code: <code>{code}</code>\n"
            f"Contact support with this code."
        )

        bot.answer_callback_query(call.id, "Money blocked")


# ================= SAFE POLLING =================
if __name__ == "__main__":
    print("🤖 Bot is running...")
    try:
        bot.infinity_polling(skip_pending=True)
    except Exception as e:
        print("Bot crashed:", e)
