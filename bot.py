import os
import json
import random
from telebot import TeleBot, types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = os.environ.get("TOKEN")
ADMIN_ID = 7983838654

bot = TeleBot(TOKEN)
DATA_FILE = "users.json"

# -------- DATABASE --------
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({}, f)


def load_users():
    with open(DATA_FILE) as f:
        return json.load(f)


def save_users(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)


def gen_bot_id():
    return str(random.randint(1000000000, 9999999999))


def gen_ref():
    return str(random.randint(1000000, 9999999))


# -------- MENU --------
def main_menu(chat_id):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("💰 Balance", "🔗 Referral")
    kb.row("💸 Withdraw", "🆔 Get My ID")
    bot.send_message(chat_id, "📋 Main Menu", reply_markup=kb)


# -------- START --------
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


# -------- MAIN HANDLER --------
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
        bot.send_message(message.chat.id,
                         f"💰 Balance: ${users[uid]['balance']}")

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
        bot.send_message(message.chat.id,
                         "Select withdrawal method", reply_markup=kb)

    # Withdraw method
    elif message.text == "USDT-BEP20":
        msg = bot.send_message(message.chat.id,
                               "Enter withdrawal amount (Min $1)")
        bot.register_next_step_handler(msg, withdraw_amount)

    elif message.text == "❌ Cancel":
        main_menu(message.chat.id)


# -------- WITHDRAW --------
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

    msg = bot.send_message(message.chat.id,
                           "Send USDT-BEP20 address")
    bot.register_next_step_handler(msg, withdraw_address, amount)


def withdraw_address(message, amount):
    users = load_users()
    uid = str(message.from_user.id)

    address = message.text
    wid = random.randint(10000, 99999)

    users[uid]["balance"] -= amount
    save_users(users)

    # Admin buttons Confirm / Reject / Ban
    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton("✅ Confirm",
                             callback_data=f"confirm_{uid}_{amount}_{wid}"),
        InlineKeyboardButton("❌ Reject",
                             callback_data=f"reject_{uid}_{amount}_{wid}")
    )
    kb.row(
        InlineKeyboardButton("🚫 Ban",
                             callback_data=f"ban_{uid}")
    )

    bot.send_message(
        ADMIN_ID,
        f"💸 Withdrawal Request\nUser BOT ID: {users[uid]['bot_id']}\nTelegram ID: {uid}\nAmount: ${amount}\nAddress: {address}\nID: {wid}",
        reply_markup=kb
    )

    bot.send_message(message.chat.id,
                     "⌛ Request sent. It may take 2-12 hours.")


# -------- CALLBACK --------
@bot.callback_query_handler(func=lambda call: True)
def callbacks(call):
    users = load_users()
    data = call.data.split("_")

    if data[0] == "confirm":
        uid, amount, wid = data[1], data[2], data[3]
        bot.send_message(uid,
                         f"✅ Payment Sent\nWithdrawal ID: {wid}\nAmount: ${amount}")

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

    bot.answer_callback_query(call.id)


# -------- ADMIN ADD BALANCE --------
@bot.message_handler(commands=["addbalance"])
def addbalance(message):
    if message.from_user.id != ADMIN_ID:
        return

    try:
        _, bot_id, amount = message.text.split()
        amount = float(amount)
    except:
        bot.send_message(message.chat.id,
                         "Usage: /addbalance BOT_ID AMOUNT")
        return

    users = load_users()

    for u in users:
        if users[u]["bot_id"] == bot_id:
            users[u]["balance"] += amount
            save_users(users)
            bot.send_message(u, f"💰 Admin added ${amount}")
            bot.send_message(message.chat.id, "✅ Balance added")
            return

    bot.send_message(message.chat.id, "❌ User not found")

# -------- ADMIN ADD BALANCE --------
@bot.message_handler(commands=["addbalance"])
def addbalance(message):
    if message.from_user.id != ADMIN_ID:
        return

    try:
        _, bot_id, amount = message.text.split()
        amount = float(amount)
    except:
        bot.send_message(message.chat.id,
                         "Usage: /addbalance BOT_ID AMOUNT")
        return

    users = load_users()
    found = False

    for uid in users:
        if users[uid].get("bot_id") == bot_id:
            users[uid]["balance"] += amount
            save_users(users)
            bot.send_message(uid, f"💰 Admin added ${amount} to your balance")
            bot.send_message(message.chat.id, f"✅ Balance added to BOT ID {bot_id}")
            found = True
            break

    if not found:
        bot.send_message(message.chat.id, "❌ User not found")

# -------- ADMIN RANDOM GIFT --------
@bot.message_handler(commands=["randomgift"])
def randomgift(message):
    if message.from_user.id != ADMIN_ID:
        return

    try:
        amount = float(message.text.split()[1])
    except:
        bot.send_message(message.chat.id, "Usage: /randomgift AMOUNT")
        return

    users = load_users()
    if not users:
        bot.send_message(message.chat.id, "No users found")
        return

    uid = random.choice(list(users.keys()))
    users[uid]["balance"] += amount
    save_users(users)

    # Notify the user
    bot.send_message(uid,
                     f"🎁 Random Gift!\nYou received ${amount}!")
    bot.send_message(message.chat.id,
                     f"✅ Random gift of ${amount} sent to BOT ID {users[uid]['bot_id']}")

# -------- RUN BOT --------
print("Bot Running...")
bot.infinity_polling()
