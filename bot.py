import os
import json
import random
from telebot import TeleBot, types
import yt_dlp

TOKEN = "7991131193:AAEfHWU_FmkrwNLVpuW3axsEKbsqWf8WzOQ"
bot = TeleBot(TOKEN)

DATA_FILE = "users.json"

if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({}, f)

ADMIN_ID = 7983838654

def load_users():
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(DATA_FILE, "w") as f:
        json.dump(users, f, indent=4)

def generate_ref_id():
    return str(random.randint(1000000, 10000000))

def main_menu(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("💰 Balance", "🔗 Referral Link", "💸 Withdraw")
    bot.send_message(chat_id, "Main Menu", reply_markup=markup)

@bot.message_handler(commands=['start'])
def start(message):
    users = load_users()
    user_id = str(message.from_user.id)

    if user_id not in users:
        users[user_id] = {
            "balance": 0,
            "referrals": 0,
            "ref_id": generate_ref_id()
        }
        save_users(users)

    main_menu(message.chat.id)

@bot.message_handler(func=lambda m: True)
def handler(message):
    users = load_users()
    user_id = str(message.from_user.id)

    if message.text == "💰 Balance":
        bot.send_message(message.chat.id, f"Balance: ${users[user_id]['balance']}")

    elif message.text == "🔗 Referral Link":
        ref = users[user_id]["ref_id"]
        link = f"https://t.me/{bot.get_me().username}?start={ref}"
        bot.send_message(message.chat.id, link)

    elif message.text.startswith("http"):
        bot.send_message(message.chat.id, "Downloading...")

        try:
            ydl_opts = {'format': 'best', 'outtmpl': 'video.mp4'}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([message.text])

            with open("video.mp4", "rb") as f:
                bot.send_video(message.chat.id, f)

            os.remove("video.mp4")

        except:
            bot.send_message(message.chat.id, "Download failed")

print("Bot Running")
bot.infinity_polling()
