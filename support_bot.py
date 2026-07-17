import os
import json
import telebot
from openai import OpenAI

BOT_TOKEN = os.getenv("SUPPORT_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
client = OpenAI(api_key=OPENAI_API_KEY)

ADMIN_IDS = [7983838654]

USERS_FILE = "users.json"
WITHDRAWS_FILE = "withdraws.json"
VIDEOS_FILE = "videos.json"

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
videos = load_json(VIDEOS_FILE, {})

SYSTEM_PROMPT = """
You are the official AI Support of Video Downloader Bot.

You know:
- Referral system
- Balance
- Withdrawals
- Ban system
- Downloader errors
- TikTok
- YouTube
- Facebook
- Pinterest
- Verification
- Force Join

If user asks something requiring admin action,
reply politely and tell the system what action is needed.

Never invent balances.
Only use database information.
"""

@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(
        message.chat.id,
        "🤖 Welcome to AI Support.\n\n"
        "Tell me your problem and I'll help you."
    )

def get_user_data(uid):
    uid = str(uid)

    if uid not in users:
        return "User not found."

    u = users[uid]

    return f"""
Telegram ID: {uid}
Balance: {u.get("balance",0)}
Blocked: {u.get("blocked",0)}
Invited: {u.get("invited",0)}
Bot ID: {u.get("bot_id")}
Banned: {u.get("banned")}
Verified: {u.get("verified")}
"""

@bot.message_handler(func=lambda m: True)
def ai_support(message):

    uid = str(message.from_user.id)

    user_info = get_user_data(uid)

    prompt = f"""
User Database

{user_info}

User Message:

{message.text}

If user wants:

Ban himself
Unban
Withdrawal
Balance
Referral
Video problem
Verification
Support

Answer correctly.

If admin action is required, start your answer with:

ACTION:

Then explain.
"""

    try:

        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {
                    "role":"system",
                    "content":SYSTEM_PROMPT
                },
                {
                    "role":"user",
                    "content":prompt
                }
            ]
        )

        text=response.choices[0].message.content

        bot.send_message(
            message.chat.id,
            text
        )

    except Exception as e:

        bot.send_message(
            message.chat.id,
            f"AI Error\n\n{e}"
        )

# ========= AI ACTIONS =========

def notify_admin(text):
    for admin in ADMIN_IDS:
        try:
            bot.send_message(admin, text)
        except:
            pass


@bot.message_handler(func=lambda m: True)
def ai_support(message):

    uid = str(message.from_user.id)
    text = message.text.lower()

    # ===== Balance =====
    if "balance" in text:
        bal = users.get(uid, {}).get("balance", 0)
        blocked = users.get(uid, {}).get("blocked", 0)

        bot.send_message(
            message.chat.id,
            f"💰 Balance: ${bal:.2f}\n⏳ Blocked: ${blocked:.2f}"
        )
        return

    # ===== Referral =====
    if "referral" in text or "invite" in text:
        invited = users.get(uid, {}).get("invited", 0)

        bot.send_message(
            message.chat.id,
            f"👥 Referrals: {invited}"
        )
        return

    # ===== Ban Myself =====
    if "ban me" in text or "iga ban garee" in text:

        users[uid]["banned"] = True
        save_json(USERS_FILE, users)

        bot.send_message(
            message.chat.id,
            "🚫 Your account has been banned."
        )
        return

    # ===== Unban Request =====
    if "unban" in text or "iga fur" in text or "ban iga qaad" in text:

        notify_admin(
            f"🔔 UNBAN REQUEST\n\nUser: {uid}"
        )

        bot.send_message(
            message.chat.id,
            "✅ Your request has been sent to the admin."
        )
        return

    # ===== Withdrawal =====
    if "withdraw" in text or "balance ii saar" in text:

        bal = users.get(uid, {}).get("balance", 0)

        if bal < 1:
            bot.send_message(
                message.chat.id,
                "❌ Minimum withdrawal is $1."
            )
            return

        notify_admin(
            f"💰 Withdrawal Request\n\nUser: {uid}\nBalance: ${bal}"
        )

        bot.send_message(
            message.chat.id,
            "✅ Withdrawal request sent to admin."
        )
        return

    # ===== AI =====
    user_info = get_user_data(uid)

    prompt = f"""
User Data

{user_info}

Question:

{message.text}
"""

    try:

        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role":"system","content":SYSTEM_PROMPT},
                {"role":"user","content":prompt}
            ]
        )

        bot.send_message(
            message.chat.id,
            response.choices[0].message.content
        )

    except Exception as e:

        bot.send_message(
            message.chat.id,
            str(e)
        )

# ========= START BOT =========

if __name__ == "__main__":
    print("🤖 AI Support Bot is running...")

    try:
        bot.infinity_polling(
            skip_pending=True,
            timeout=60,
            long_polling_timeout=60
        )

    except Exception as e:
        print("Bot stopped:", e)
