import os
import json
import random
from telebot import TeleBot, types

# ---------------- CONFIG ----------------
TOKEN = os.environ.get("TOKEN")
if not TOKEN:
    raise ValueError("❌ Bot token not found! Set TOKEN environment variable.")

ADMIN_ID = 7983838654  # Bedel ID-gaaga Telegram

bot = TeleBot(TOKEN)
DATA_FILE = "users.json"

# ---------------- INIT FILE ----------------
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({}, f)

# ---------------- UTIL FUNCTIONS ----------------
def load_users():
    try:
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
            return data if data else {}
    except:
        return {}

def save_users(users):
    with open(DATA_FILE, "w") as f:
        json.dump(users, f, indent=4)

def gen_bot_id():
    return str(random.randint(1000000000, 9999999999))

def gen_ref():
    return str(random.randint(1000000, 9999999))

# ---------------- MAIN MENU ----------------
def main_menu(chat_id):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("💰 Balance", "🔗 Referral")
    kb.row("💸 Withdraw", "🆔 Get My ID")
    kb.row("❌ Cancel")
    bot.send_message(chat_id, "📋 Main Menu", reply_markup=kb)

    # Admin panel inline buttons
    if chat_id == ADMIN_ID:
        admin_kb = types.InlineKeyboardMarkup()
        admin_kb.row(
            types.InlineKeyboardButton("💰 Add Balance", callback_data="admin_addbalance"),
            types.InlineKeyboardButton("🎁 Random Gift", callback_data="admin_randomgift")
        )
        bot.send_message(chat_id, "Admin Panel", reply_markup=admin_kb)

# ---------------- START ----------------
@bot.message_handler(commands=["start"])
def start(message):
    users = load_users()
    uid = str(message.from_user.id)
    ref = None
    if " " in message.text:
        ref = message.text.split()[1]

    if uid not in users:
        bot_id = gen_bot_id()
        users[uid] = {
            "balance": 0,
            "referrals": 0,
            "bot_id": bot_id,
            "ref_id": gen_ref(),
            "ban": False
        }

        # Referral reward
        if ref:
            for u in users:
                if users[u]["ref_id"] == ref:
                    users[u]["balance"] += 0.5
                    users[u]["referrals"] += 1
                    bot.send_message(u, "🎉 You got $0.5 referral bonus!")

    save_users(users)
    main_menu(message.chat.id)

# ---------------- MAIN HANDLER ----------------
@bot.message_handler(func=lambda m: True)
def handler(message):
    users = load_users()
    uid = str(message.from_user.id)

    if uid not in users:
        return
    if users[uid]["ban"]:
        bot.send_message(message.chat.id, "❌ You are banned")
        return

    # Balance
    if message.text == "💰 Balance":
        bot.send_message(message.chat.id, f"💰 Balance: ${users[uid]['balance']}")

    # Referral
    elif message.text == "🔗 Referral":
        link = f"https://t.me/{bot.get_me().username}?start={users[uid]['ref_id']}"
        bot.send_message(message.chat.id,
                         f"🔗 Your Referral Link\n{link}\n👥 Referrals: {users[uid]['referrals']}\nEarn $0.5 per referral")

    # Get ID
    elif message.text == "🆔 Get My ID":
        bot.send_message(message.chat.id,
                         f"🆔 YOUR IDS\n\nTelegram ID: {uid}\nBOT ID: {users[uid]['bot_id']}")

    # Withdraw menu
    elif message.text == "💸 Withdraw":
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.row("USDT-BEP20")
        kb.row("❌ Cancel")
        bot.send_message(message.chat.id, "Select withdrawal method", reply_markup=kb)

    # Withdraw method
    elif message.text == "USDT-BEP20":
        msg = bot.send_message(message.chat.id, "Enter withdrawal amount (Min $1)")
        bot.register_next_step_handler(msg, withdraw_amount)

    elif message.text == "❌ Cancel":
        main_menu(message.chat.id)

# ---------------- WITHDRAW ----------------
def withdraw_amount(message):
    users = load_users()
    uid = str(message.from_user.id)
    try:
        amount = float(message.text)
    except:
        bot.send_message(message.chat.id, "❌ Invalid amount")
        return

    if amount < 1:
        bot.send_message(message.chat.id, "❌ Minimum withdrawal is $1")
        return
    if users[uid]["balance"] < amount:
        bot.send_message(message.chat.id, "❌ Insufficient balance")
        return

    msg = bot.send_message(message.chat.id, "Send USDT-BEP20 address")
    bot.register_next_step_handler(msg, withdraw_address, amount)

def withdraw_address(message, amount):
    users = load_users()
    uid = str(message.from_user.id)
    address = message.text
    wid = random.randint(10000, 99999)

    users[uid]["balance"] -= amount
    save_users(users)

    # Admin buttons Confirm / Reject / Ban
    kb = types.InlineKeyboardMarkup()
    kb.row(
        types.InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_{uid}_{amount}_{wid}"),
        types.InlineKeyboardButton("❌ Reject", callback_data=f"reject_{uid}_{amount}_{wid}")
    )
    kb.row(
        types.InlineKeyboardButton("🚫 Ban", callback_data=f"ban_{uid}")
    )

    bot.send_message(
        ADMIN_ID,
        f"💸 Withdrawal Request\nUser BOT ID: {users[uid]['bot_id']}\nTelegram ID: {uid}\nAmount: ${amount}\nAddress: {address}\nID: {wid}",
        reply_markup=kb
    )

    bot.send_message(message.chat.id, "⌛ Request sent. It may take 2-12 hours.")

# ---------------- CALLBACK ----------------
@bot.callback_query_handler(func=lambda c: True)
def callbacks(call):
    users = load_users()
    data = call.data.split("_")

    # Withdraw actions
    if data[0] == "confirm":
        uid, amount, wid = data[1], data[2], data[3]
        bot.send_message(uid, f"✅ Payment Sent\nWithdrawal ID: {wid}\nAmount: ${amount}")

    elif data[0] == "reject":
        uid, amount = data[1], float(data[2])
        users[uid]["balance"] += amount
        save_users(users)
        bot.send_message(uid, "❌ Withdrawal rejected. Balance refunded.")

    elif data[0] == "ban":
        uid = data[1]
        users[uid]["ban"] = True
        save_users(users)
        bot.send_message(uid, "🚫 You have been banned.")

    # Admin Panel
    elif data[0] == "admin_addbalance":
        bot.send_message(ADMIN_ID, "Send: BOT_ID AMOUNT")
        bot.register_next_step_handler_by_chat_id(ADMIN_ID, admin_add_balance_step)

    elif data[0] == "admin_randomgift":
        bot.send_message(ADMIN_ID, "Send amount for random gift")
        bot.register_next_step_handler_by_chat_id(ADMIN_ID, admin_random_gift_step)

    bot.answer_callback_query(call.id)

# ---------------- ADMIN ADD BALANCE ----------------
def admin_add_balance_step(message):
    try:
        bot_id, amount = message.text.split()
        amount = float(amount)
    except:
        bot.send_message(ADMIN_ID, "❌ Invalid format. Use: BOT_ID AMOUNT")
        return

    users = load_users()
    found = False
    for uid in users:
        if users[uid].get("bot_id") == bot_id:
            users[uid]["balance"] += amount
            save_users(users)
            bot.send_message(uid, f"💰 Admin added ${amount} to your balance")
            bot.send_message(ADMIN_ID, f"✅ Balance added to BOT ID {bot_id}")
            found = True
            break
    if not found:
        bot.send_message(ADMIN_ID, "❌ User not found")

# ---------------- ADMIN RANDOM GIFT ----------------
def admin_random_gift_step(message):
    try:
        amount = float(message.text)
    except:
        bot.send_message(ADMIN_ID, "❌ Invalid amount")
        return

    users = load_users()
    if not users:
        bot.send_message(ADMIN_ID, "No users found")
        return

    uid = random.choice(list(users.keys()))
    users[uid]["balance"] += amount
    save_users(users)
    bot.send_message(uid, f"🎁 Random Gift!\nYou received ${amount}!")
    bot.send_message(ADMIN_ID, f"✅ Random gift of ${amount} sent to BOT ID {users[uid]['bot_id']}")

# ---------------- RUN BOT ----------------
print("Bot Running...")
bot.infinity_polling()
