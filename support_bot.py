# ================= IMPORTS =================

import os
import json
import time
import threading

import telebot

from groq import Groq

import google.generativeai as genai

from PIL import Image



# ================= ENV =================

BOT_TOKEN = os.getenv("SUPPORT_BOT_TOKEN")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")



if not BOT_TOKEN:
    raise Exception("❌ SUPPORT_BOT_TOKEN missing")


if not GROQ_API_KEY:
    raise Exception("❌ GROQ_API_KEY missing")


if not GEMINI_API_KEY:
    raise Exception("❌ GEMINI_API_KEY missing")




# ================= TELEGRAM =================


bot = telebot.TeleBot(
    BOT_TOKEN,
    parse_mode="HTML"
)




# ================= AI SETUP =================


# Groq AI (Text)

groq_client = Groq(
    api_key=GROQ_API_KEY
)



# Gemini AI (Vision)

genai.configure(
    api_key=GEMINI_API_KEY
)


vision_model = genai.GenerativeModel(
    "gemini-2.5-flash"
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


    try:

        with open(path, "r") as f:

            return json.load(f)

    except:

        return default





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





# ================= SYSTEM =================


SYSTEM_PROMPT = """

You are the official AI Support of Video Downloader Bot.

Help users with:

- TikTok downloader
- YouTube downloader
- Facebook downloader
- Pinterest downloader
- Referral
- Balance
- Withdrawals
- Verification
- Force Join
- Bot errors


Rules:

Never invent balance.
Use database information only.

Be professional and friendly.

"""





# ================= USER DATA =================


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





# ================= ADMIN NOTIFY =================


def notify_admin(text):

    for admin in ADMIN_IDS:

        try:

            bot.send_message(
                admin,
                text
            )

        except:

            pass





# ================= GROQ TEXT AI =================


def ask_groq(question):


    response = groq_client.chat.completions.create(


        model="llama-3.3-70b-versatile",


        messages=[


            {
                "role":"system",
                "content":SYSTEM_PROMPT
            },


            {
                "role":"user",
                "content":question
            }


        ],


        temperature=0.3

    )



    return response.choices[0].message.content





# ================= GEMINI IMAGE AI =================


def analyze_image(image_path, question):


    image = Image.open(
        image_path
    )


    response = vision_model.generate_content(

        [
            question,
            image
        ]

    )


    return response.text

# ================= START =================


@bot.message_handler(commands=["start"])
def start(message):

    bot.send_message(
        message.chat.id,
        "🤖 Welcome to AI Support.\n\n"
        "Send your problem or screenshot and I will help you."
    )





# ================= IMAGE SUPPORT =================


@bot.message_handler(content_types=["photo"])
def image_support(message):

    try:

        uid = str(message.from_user.id)


        bot.send_message(
            message.chat.id,
            "🔍 AI is checking your image..."
        )


        file_info = bot.get_file(
            message.photo[-1].file_id
        )


        downloaded = bot.download_file(
            file_info.file_path
        )


        image_path = f"error_{uid}.jpg"



        with open(image_path,"wb") as f:

            f.write(downloaded)



        result = analyze_image(

            image_path,

            """
            Analyze this screenshot.

            If it is a Video Downloader Bot problem:
            - Find the error
            - Explain the reason
            - Give the solution

            Answer in simple language.
            """

        )



        bot.send_message(

            message.chat.id,

            "🤖 AI Analysis:\n\n" + result

        )



        notify_admin(

            f"📸 Image Error Report\n\nUser: {uid}"

        )



        os.remove(
            image_path
        )



    except Exception as e:


        bot.send_message(

            message.chat.id,

            f"❌ Image AI Error: {e}"

        )







# ================= TEXT SUPPORT =================


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

            f"""
💰 Withdrawal Request

User: {uid}

Balance: ${bal}
"""

        )



        bot.send_message(

            message.chat.id,

            "✅ Withdrawal request sent."

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






    # AI QUESTION


    prompt = f"""

User Data:

{get_user_data(uid)}



User Question:

{message.text}

"""



    try:


        answer = ask_groq(
            prompt
        )



        bot.send_message(

            message.chat.id,

            answer

        )



    except Exception as e:


        bot.send_message(

            message.chat.id,

            f"❌ AI Error: {e}"

        )






# ================= RUN =================


def run_support_bot():


    while True:


        try:


            print(
                "🤖 AI Support Bot Started..."
            )



            bot.infinity_polling(

                skip_pending=True,

                timeout=60,

                long_polling_timeout=60

            )



        except Exception as e:


            print(
                "Bot Restart:",
                e
            )


            time.sleep(5)






if __name__ == "__main__":


    thread = threading.Thread(

        target=run_support_bot

    )


    thread.start()


    thread.join()
