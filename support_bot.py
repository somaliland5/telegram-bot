import os
import json
import time
import threading
import telebot
from openai import OpenAI


# ================= ENV =================

BOT_TOKEN = os.getenv("SUPPORT_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not BOT_TOKEN:
    raise Exception("❌ SUPPORT_BOT_TOKEN missing")

if not OPENAI_API_KEY:
    raise Exception("❌ OPENAI_API_KEY missing")


bot = telebot.TeleBot(
    BOT_TOKEN,
    parse_mode="HTML"
)

client = OpenAI(
    api_key=OPENAI_API_KEY
)


# ================= ADMIN =================

ADMIN_IDS = [
    7983838654
]


# ================= DATABASE =================

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
        json.dump(
            data,
            f,
            indent=4
        )



users = load_json(
    USERS_FILE,
    {}
)

withdraws = load_json(
    WITHDRAWS_FILE,
    []
)

videos = load_json(
    VIDEOS_FILE,
    {}
)



# ================= AI =================

SYSTEM_PROMPT = """
You are the official AI Support of Video Downloader Bot.

Help users with:
- Downloader problems
- TikTok
- YouTube
- Facebook
- Pinterest
- Referral
- Balance
- Withdrawals
- Verification
- Force Join

Never invent user balance.
Use database information only.
"""



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



def notify_admin(text):

    for admin in ADMIN_IDS:

        try:
            bot.send_message(
                admin,
                text
            )

        except Exception:
            pass



# ================= START =================


@bot.message_handler(commands=["start"])
def start(message):

    bot.send_message(
        message.chat.id,
        "🤖 Welcome to AI Support.\n\nSend your problem and I will help you."
    )



# ================= MAIN SUPPORT =================


@bot.message_handler(func=lambda m: True)
def support(message):

    uid = str(message.from_user.id)

    text = message.text.lower()


    # Balance

    if "balance" in text:

        bal = users.get(uid,{}).get(
            "balance",
            0
        )

        bot.send_message(
            message.chat.id,
            f"💰 Balance: ${bal}"
        )

        return



    # Referral

    if "referral" in text or "invite" in text:

        invited = users.get(uid,{}).get(
            "invited",
            0
        )

        bot.send_message(
            message.chat.id,
            f"👥 Referrals: {invited}"
        )

        return



    # Ban

    if "ban me" in text or "iga ban garee" in text:


        if uid in users:

            users[uid]["banned"] = True

            save_json(
                USERS_FILE,
                users
            )


        bot.send_message(
            message.chat.id,
            "🚫 Account banned."
        )

        return



    # Unban


    if "unban" in text or "ban iga qaad" in text:


        notify_admin(
            f"🔔 UNBAN REQUEST\n\nUser: {uid}"
        )


        bot.send_message(
            message.chat.id,
            "✅ Request sent to admin."
        )

        return



    # Withdraw


    if "withdraw" in text or "balance ii saar" in text:


        bal = users.get(uid,{}).get(
            "balance",
            0
        )


        if bal < 1:

            bot.send_message(
                message.chat.id,
                "❌ Minimum withdrawal is $1"
            )

            return



        notify_admin(
            f"💰 Withdrawal\n\nUser: {uid}\nBalance: ${bal}"
        )


        bot.send_message(
            message.chat.id,
            "✅ Withdrawal request sent."
        )

        return



    # AI


    prompt = f"""

User Data:

{get_user_data(uid)}


Question:

{message.text}

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


        bot.send_message(
            message.chat.id,
            response.choices[0].message.content
        )


    except Exception as e:


        bot.send_message(
            message.chat.id,
            f"AI Error: {e}"
        )



# ================= RUN =================


def run_support_bot():

    while True:

        try:

            print(
                "🤖 Support Bot Started..."
            )


            bot.infinity_polling(
                skip_pending=True,
                timeout=60,
                long_polling_timeout=60
            )


        except Exception as e:

            print(
                "Support Bot Restart:",
                e
            )

            time.sleep(5)



if __name__ == "__main__":

    thread = threading.Thread(
        target=run_support_bot
    )

    thread.start()

    thread.join()
