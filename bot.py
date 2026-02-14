import telebot
import json
import random
import os

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

bot = telebot.TeleBot(TOKEN)

USERS_FILE = "users.json"


# ---------------- DATABASE ---------------- #

def load_users():
    try:
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    except:
        return {}


def save_users(data):
    with open(USERS_FILE, "w") as f:
        json.dump(data, f, indent=4)


users = load_users()


def random_bot_id():
    return str(random.randint(1000000000, 9999999999))


# ---------------- USER CREATE ---------------- #

def create_user(uid, ref=None):

    uid = str(uid)

    if uid not in users:

        bot_id = random_bot_id()

        users[uid] = {
            "bot_id": bot_id,
            "balance": 0,
            "banned": False
        }

        # Referral reward
        if ref:
            for u in users:
                if users[u]["bot_id"] == ref:
                    users[u]["balance"] += 0.25

        save_users(users)


# ---------------- START ---------------- #

@bot.message_handler(commands=["start"])
def start(message):

    args = message.text.split()
    ref = args[1] if len(args) > 1 else None

    create_user(message.from_user.id, ref)

    if users[str(message.from_user.id)]["banned"]:
        return

    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)

    markup.add("💰 Balance", "👥 Referral")
    markup.add("🆔 Get BOT ID", "💸 Withdraw")

    if message.from_user.id == ADMIN_ID:
        markup.add("⚙️ Admin Panel")

    bot.send_message(message.chat.id, "Welcome!", reply_markup=markup)


# ---------------- BALANCE ---------------- #

@bot.message_handler(func=lambda m: m.text == "💰 Balance")
def balance(message):

    bal = users[str(message.from_user.id)]["balance"]

    bot.send_message(message.chat.id, f"💰 Balance: ${bal}")


# ---------------- REFERRAL ---------------- #

@bot.message_handler(func=lambda m: m.text == "👥 Referral")
def referral(message):

    uid = str(message.from_user.id)

    link = f"https://t.me/{bot.get_me().username}?start={users[uid]['bot_id']}"

    bot.send_message(message.chat.id, f"🔗 Referral Link:\n{link}")


# ---------------- BOT ID ---------------- #

@bot.message_handler(func=lambda m: m.text == "🆔 Get BOT ID")
def get_id(message):

    uid = str(message.from_user.id)

    bot.send_message(message.chat.id, f"🆔 BOT ID: {users[uid]['bot_id']}")


# ---------------- WITHDRAW ---------------- #

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
        bot.send_message(message.chat.id, "Send USDT BEP20 Address:")

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
💸 Fee (0.00%): -$0.00
🧾 Net Due: ${amount}

⏳ Your request is pending approval
🕒 Pending time: 6–12 hours
🙏 Please be patient 🙂
""")

    bot.send_message(ADMIN_ID, f"""
📤 Withdrawal Request

User: {uid}
BOT ID: {users[uid]['bot_id']}
Amount: ${amount}
Address: {address}

Commands:
CONFIRM {uid}
REJECT {uid}
BAN {uid}
""")


# ---------------- ADMIN PANEL ---------------- #

@bot.message_handler(func=lambda m: m.text == "⚙️ Admin Panel")
def admin_panel(message):

    if message.from_user.id != ADMIN_ID:
        return

    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)

    markup.add("➕ Add Balance", "🚫 Ban User")
    markup.add("✅ Unban User", "🎁 Random Gift")
    markup.add("📢 Broadcast")

    bot.send_message(message.chat.id, "Admin Panel", reply_markup=markup)


# ---------------- ADD BALANCE ---------------- #

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


# ---------------- BAN ---------------- #

@bot.message_handler(func=lambda m: m.text == "🚫 Ban User")
def ban_user(message):

    if message.from_user.id != ADMIN_ID:
        return

    bot.send_message(message.chat.id, "Send user_id")
    bot.register_next_step_handler(message, process_ban)


def process_ban(message):

    uid = message.text
    users[uid]["banned"] = True
    save_users(users)

    bot.send_message(message.chat.id, "🚫 User Banned")


# ---------------- UNBAN ---------------- #

@bot.message_handler(func=lambda m: m.text == "✅ Unban User")
def unban_user(message):

    if message.from_user.id != ADMIN_ID:
        return

    bot.send_message(message.chat.id, "Send user_id")
    bot.register_next_step_handler(message, process_unban)


def process_unban(message):

    uid = message.text
    users[uid]["banned"] = False
    save_users(users)

    bot.send_message(message.chat.id, "✅ User Unbanned")


# ---------------- RANDOM GIFT ---------------- #

@bot.message_handler(func=lambda m: m.text == "🎁 Random Gift")
def random_gift(message):

    if message.from_user.id != ADMIN_ID:
        return

    user = random.choice(list(users.keys()))
    users[user]["balance"] += 1
    save_users(users)

    bot.send_message(message.chat.id, f"🎁 Gift sent to {user}")


# ---------------- BROADCAST ---------------- #

@bot.message_handler(func=lambda m: m.text == "📢 Broadcast")
def broadcast(message):

    if message.from_user.id != ADMIN_ID:
        return

    bot.send_message(message.chat.id, "Send message / photo / video")
    bot.register_next_step_handler(message, process_broadcast)


def process_broadcast(message):

    for uid in users:

        try:
            if message.text:
                bot.send_message(uid, message.text)

            elif message.photo:
                bot.send_photo(uid, message.photo[-1].file_id, caption=message.caption)

            elif message.video:
                bot.send_video(uid, message.video.file_id, caption=message.caption)

        except:
            pass

    bot.send_message(message.chat.id, "✅ Broadcast Sent")


# ---------------- ADMIN COMMANDS ---------------- #

@bot.message_handler(func=lambda m: m.text.startswith("CONFIRM"))
def confirm_withdraw(message):

    if message.from_user.id != ADMIN_ID:
        return

    uid = message.text.split()[1]

    bot.send_message(uid, "✅ Withdrawal Confirmed")


@bot.message_handler(func=lambda m: m.text.startswith("REJECT"))
def reject_withdraw(message):

    if message.from_user.id != ADMIN_ID:
        return

    uid = message.text.split()[1]

    bot.send_message(uid, "❌ Withdrawal Rejected")


@bot.message_handler(func=lambda m: m.text.startswith("BAN"))
def ban_cmd(message):

    if message.from_user.id != ADMIN_ID:
        return

    uid = message.text.split()[1]
    users[uid]["banned"] = True
    save_users(users)

    bot.send_message(message.chat.id, "User banned")


# ---------------- RUN ---------------- #

print("Bot Running...")
bot.infinity_polling()
