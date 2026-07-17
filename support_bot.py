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
