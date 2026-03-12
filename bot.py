import telebot
import requests
from telebot.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
import os
import json
import random
from datetime import datetime
import yt_dlp
import subprocess
import re
import shutil
from flask import Flask, request, jsonify
import threading

# ================= CONFIG =================

# ================= VERIFY SYSTEM =================

VERIFY_MODE = False
pending_verify = {}
verified_users = set()
pending_downloads = {}

BOT2_TOKEN = os.getenv("BOT2_TOKEN")
bot2 = telebot.TeleBot(BOT2_TOKEN)

TOKEN = os.getenv("BOT_TOKEN")

ADMIN_IDS = [7983838654]

BASE_DIR = os.getcwd()

CHANNEL_USERNAME = "tiktokvediodownload"

POST_CHANNELS = []
pending_links = {}
CHANNEL_WINDOW_OPEN = False

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# ================= DATABASE FILES =================

USERS_FILE = "users.json"
WITHDRAWS_FILE = "withdraws.json"
VIDEOS_FILE = "videos.json"

# ================= JSON FUNCTIONS =================

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


# ================= LOAD DATA =================

users = load_json(USERS_FILE, {})
withdraws = load_json(WITHDRAWS_FILE, [])

videos_data = load_json(
    VIDEOS_FILE,
    {
        "total": 0,
        "platforms": {
            "tiktok": 0,
            "youtube": 0,
            "facebook": 0,
            "instagram": 0,
            "pinterest": 0,
        },
        "users": {},
    },
)


def save_videos():
    save_json(VIDEOS_FILE, videos_data)


# ================= HELPER FUNCTIONS =================

def random_ref():
    return str(random.randint(1000000000, 9999999999))


def random_botid():
    return str(random.randint(10000000000, 99999999999))


def now_month():
    return datetime.now().month


def is_admin(uid):
    return int(uid) in ADMIN_IDS


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

# ================= VERIFY HELPERS =================

def start_verification(chat_id):

    code = str(random.randint(100000, 999999))
    pending_verify[str(chat_id)] = code

    url = f"https://t.me/Verifyd_bot?start={chat_id}"

    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("🔐 GET CODE", url=url)
    )

    bot.send_message(
        chat_id,
        "🔒 Verification Required\n\n"
        "1️⃣ Click GET CODE\n"
        "2️⃣ Copy the code\n"
        "3️⃣ Send it here",
        reply_markup=kb
    )


@bot2.message_handler(commands=['start'])
def bot2_start(m):

    uid = str(m.from_user.id)

    if uid in pending_verify:

        code = pending_verify[uid]

        bot2.send_message(
            m.chat.id,
            "🔐 Your Verification Code:\n\n"
            f"`{code}`\n\n"
            "👆 Taabo code-ka si aad u copy garayso kadibna ku celi bot-ka weyn.",
            parse_mode="Markdown"
        )

    else:

        bot2.send_message(
            m.chat.id,
            "ℹ️ No verification pending.\nMarka hore ka bilow bot-ka weyn."
        )


@bot.message_handler(func=lambda m: m.text and m.text.isdigit() and len(m.text) == 6)
def check_verify_code(m):

    uid = str(m.from_user.id)

    if not VERIFY_MODE:
        return

    if uid in verified_users:
        return

    if pending_verify.get(uid) == m.text:

        verified_users.add(uid)
        pending_verify.pop(uid, None)

        bot.send_message(
            m.chat.id,
            "✅ Verification Successful!"
        )

        if uid in pending_downloads:

            old_url = pending_downloads.pop(uid)

            bot.send_message(
                m.chat.id,
                "⬇️ Downloading your previous link..."
            )

            download_media(m.chat.id, old_url)

    else:

        bot.send_message(
            m.chat.id,
            "❌ Incorrect code."
        )

# ================= START COMMAND =================

@bot.message_handler(commands=['start'])
def start_handler(message):

    uid = message.from_user.id
    args = message.text.split()

    # Haddii user cusub, ku dar database
    if str(uid) not in users:

        ref = args[1] if len(args) > 1 else None

        users[str(uid)] = {
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

            ref_user = next(
                (u for u, d in users.items() if d["ref"] == ref),
                None
            )

            if ref_user:

                users[ref_user]["balance"] += 0.2
                users[ref_user]["invited"] += 1

                bot.send_message(
                    int(ref_user),
                    "🎉 You earned $0.2 from referral!"
                )

        save_users()

    # SAVE USER TO MONGO
    users_collection.update_one(
        {"user_id": str(uid)},
        {
            "$set": {
                "user_id": str(uid),
                "balance": users[str(uid)]["balance"],
                "referrals": users[str(uid)]["invited"]
            }
        },
        upsert=True
    )

    # Hubinta join
    check_membership(uid)

# ================= BROADCAST =================

@bot.message_handler(func=lambda m: m.text == "📢 BROADCAST")
def broadcast_start(m):

    if not is_admin(m.from_user.id):
        bot.send_message(m.chat.id, "❌ You are not admin")
        return

    msg = bot.send_message(
        m.chat.id,
        "📝 Send the broadcast message to all users:"
    )

    bot.register_next_step_handler(msg, broadcast_send)


def broadcast_send(m):

    if not is_admin(m.from_user.id):
        return

    text = m.text
    count = 0

    for uid in users:

        try:
            bot.send_message(int(uid), text)
            count += 1
        except:
            continue

    bot.send_message(
        m.chat.id,
        f"✅ Broadcast sent to {count} users"
    )


# ================= SEE USERS LIST =================

@bot.message_handler(func=lambda m: m.text == "👥 SEE LIST")
def see_users(m):

    if not is_admin(m.from_user.id):
        return

    total = len(users)
    count = 0

    for uid in users:

        kb = InlineKeyboardMarkup()
        kb.add(
            InlineKeyboardButton(
                "💬 OPEN CHAT",
                url=f"tg://user?id={uid}"
            )
        )

        bot.send_message(
            m.chat.id,
            f"👤 User ID: {uid}",
            reply_markup=kb
        )

        count += 1

        if count >= 20:
            break

    bot.send_message(
        m.chat.id,
        f"📊 Total Users: {total}"
    )

# ================= SEARCH USER =================

@bot.message_handler(func=lambda m: m.text == "🔎 SEARCH USER")
def search_user(m):

    if not is_admin(m.from_user.id):
        return

    msg = bot.send_message(
        m.chat.id,
        "Send User Telegram ID"
    )

    bot.register_next_step_handler(msg, search_user_result)


def search_user_result(m):

    if not is_admin(m.from_user.id):
        return

    uid = m.text.strip()

    if uid in users:

        kb = InlineKeyboardMarkup()

        kb.add(
            InlineKeyboardButton(
                "💬 OPEN CHAT",
                url=f"tg://user?id={uid}"
            )
        )

        kb.add(
            InlineKeyboardButton(
                "✉️ MESSAGE USER",
                callback_data=f"msguser|{uid}"
            )
        )

        bot.send_message(
            m.chat.id,
            f"👤 User Found\nID: {uid}",
            reply_markup=kb
        )

    else:

        bot.send_message(
            m.chat.id,
            "❌ User not found"
        )


# ================= POST CHANNEL =================

@bot.message_handler(func=lambda m: m.text == "📌 POST CHANNEL")
def post_channel_start(m):

    if not is_admin(m.from_user.id):
        bot.send_message(m.chat.id, "❌ You are not admin")
        return

    msg = bot.send_message(
        m.chat.id,
        "Send up to 5 channel usernames separated by space\n"
        "Example:\n@channel1 @channel2"
    )

    bot.register_next_step_handler(msg, post_channels_send)


def post_channels_send(m):

    global POST_CHANNELS, CHANNEL_WINDOW_OPEN

    if not is_admin(m.from_user.id):
        return

    channels = [c.replace("@", "").strip() for c in m.text.split()][:5]

    POST_CHANNELS = channels
    CHANNEL_WINDOW_OPEN = True

    text = "✅ Channels saved:\n" + "\n".join([f"@{c}" for c in channels])

    bot.send_message(
        m.chat.id,
        text
    )

                    # ================= CHECKING DOWNLOAD =================

@bot.message_handler(func=lambda m: m.text and "http" in m.text)
def handle_links(message):

    user_id = message.from_user.id

    if POST_CHANNELS:

        kb = InlineKeyboardMarkup()
        joined_all = True

        for ch in POST_CHANNELS:

            try:

                member = bot.get_chat_member(f"@{ch}", user_id)

                if member.status not in ["member", "administrator", "creator"]:
                    joined_all = False

                    kb.add(
                        InlineKeyboardButton(
                            "📢 JOIN CHANNEL",
                            url=f"https://t.me/{ch}"
                        )
                    )

            except:

                joined_all = False

                kb.add(
                    InlineKeyboardButton(
                        "📢 JOIN CHANNEL",
                        url=f"https://t.me/{ch}"
                    )
                )

        if not joined_all:

            pending_links[user_id] = message.text

            kb.add(
                InlineKeyboardButton(
                    "✅ CONFIRM JOIN",
                    callback_data="multi_checkjoin"
                )
            )

            bot.send_message(
                message.chat.id,
                "⚠️ Please join the required channels first.",
                reply_markup=kb
            )

            return

    download_media(message.chat.id, message.text)


# ================= MULTI CHANNEL CONFIRM =================

@bot.callback_query_handler(func=lambda call: call.data == "multi_checkjoin")
def multi_checkjoin(call):

    user_id = call.from_user.id
    joined_all = True

    for ch in POST_CHANNELS:

        try:

            member = bot.get_chat_member(f"@{ch}", user_id)

            if member.status not in ["member", "administrator", "creator"]:
                joined_all = False
                break

        except:

            joined_all = False
            break

    if joined_all:

        bot.answer_callback_query(call.id, "✅ Join verified")

        if user_id in pending_links:

            link = pending_links[user_id]
            del pending_links[user_id]

            bot.send_message(
                user_id,
                "⬇️ Processing your video..."
            )

            download_media(user_id, link)

        else:

            bot.send_message(
                user_id,
                "Send your video link."
            )

    else:

        bot.answer_callback_query(
            call.id,
            "❌ You must join all channels first!",
            show_alert=True
                    )

# ================= CONFIRM JOIN =================

@bot.callback_query_handler(func=lambda call: call.data == "confirm_join")
def confirm_join(call):

    user_id = call.from_user.id

    try:

        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)

        if member.status in ["member", "administrator", "creator"]:

            bot.answer_callback_query(call.id, "✅ Join verified")

            # Tirtir inline keyboard
            bot.edit_message_reply_markup(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=None
            )

            # Haddii uu hore link u diray
            if user_id in pending_links:

                link = pending_links[user_id]
                del pending_links[user_id]

                download_media(user_id, link)

            else:

                bot.send_message(
                    user_id,
                    "✅ Join confirmed. Send your video link."
                )

        else:

            bot.answer_callback_query(
                call.id,
                "❌ You must join the channel first!",
                show_alert=True
            )

    except Exception:

        bot.answer_callback_query(
            call.id,
            "❌ Please join the channel first!",
            show_alert=True
        )


# ================= CLOSE WINDOWS =================

@bot.message_handler(func=lambda m: m.text == "❌ CLOSE WINDOWS")
def close_channel_windows(m):

    global CHANNEL_WINDOW_OPEN

    if not is_admin(m.from_user.id):
        return

    CHANNEL_WINDOW_OPEN = False

    bot.send_message(
        m.chat.id,
        "✅ Channel join system disabled."
    )


# ================= ADD BALANCE =================

@bot.message_handler(func=lambda m: m.text == "➕ ADD BALANCE")
def add_balance_start(m):

    if not is_admin(m.from_user.id):
        bot.send_message(m.chat.id, "❌ You are not admin")
        return

    msg = bot.send_message(
        m.chat.id,
        "Send BOT ID or Telegram ID and amount separated by space:\n"
        "Example:\n123456789 10.5"
    )

    bot.register_next_step_handler(msg, add_balance_process)


def add_balance_process(m):

    if not is_admin(m.from_user.id):
        return

    try:

        uid_str, amt_str = m.text.strip().split()
        amt = float(amt_str)

        # Hubi Telegram ID ama BOT ID
        uid = uid_str if uid_str in users else find_user_by_botid(uid_str)

        if not uid or amt <= 0:
            bot.send_message(m.chat.id, "❌ Invalid input")
            return

        users[uid]["balance"] += amt
        save_users()

        bot.send_message(
            m.chat.id,
            f"✅ Added ${amt:.2f} to user {uid}"
        )

        bot.send_message(
            int(uid),
            f"💰 Your balance increased by ${amt:.2f}"
        )

    except:

        bot.send_message(
            m.chat.id,
            "❌ Format error.\nUse:\n<BOT ID or Telegram ID> <amount>"
        )

# ================= REMOVE MONEY =================

@bot.message_handler(func=lambda m: m.text == "➖ REMOVE MONEY")
def remove_balance_start(m):

    if not is_admin(m.from_user.id):
        bot.send_message(m.chat.id, "❌ You are not admin")
        return

    msg = bot.send_message(
        m.chat.id,
        "Send BOT ID or Telegram ID and amount separated by space:\n"
        "Example:\n123456789 5.0"
    )

    bot.register_next_step_handler(msg, remove_balance_process)


def remove_balance_process(m):

    if not is_admin(m.from_user.id):
        return

    try:

        uid_str, amt_str = m.text.strip().split()
        amt = float(amt_str)

        # Hubi haddii la isticmaalayo Telegram ID ama BOT ID
        uid = uid_str if uid_str in users else find_user_by_botid(uid_str)

        if not uid or amt <= 0:
            bot.send_message(m.chat.id, "❌ Invalid input")
            return

        if users[uid]["balance"] < amt:
            bot.send_message(m.chat.id, "❌ Insufficient balance")
            return

        users[uid]["balance"] -= amt
        save_users()

        bot.send_message(
            m.chat.id,
            f"✅ Removed ${amt:.2f} from user {uid}"
        )

        bot.send_message(
            int(uid),
            f"💸 ${amt:.2f} removed from your balance"
        )

    except:

        bot.send_message(
            m.chat.id,
            "❌ Format error.\nUse:\n<BOT ID or Telegram ID> <amount>"
        )


# ================= URL EXTRACTOR =================

CAPTION_TEXT = "Downloaded by:\n@Downloadvedioytibot"


def extract_url(text):

    urls = re.findall(r'https?://[^\s]+', text)

    return urls[0] if urls else None


# ================= CLEAN SEND VIDEO FUNCTION =================

def send_video_with_music(chat_id, file_path, platform=None):

    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton(
            "🎵 Convert to Music",
            callback_data=f"music|{file_path}"
        )
    )

    # ===== COUNT VIDEO =====

    uid = str(chat_id)

    videos_data["total"] += 1

    videos_data["users"][uid] = videos_data["users"].get(uid, 0) + 1

    # ===== COUNT PLATFORM =====

    if platform:

        if "platforms" not in videos_data:

            videos_data["platforms"] = {
                "tiktok": 0,
                "youtube": 0,
                "facebook": 0,
                "instagram": 0,
                "pinterest": 0
            }

        videos_data["platforms"][platform] = videos_data["platforms"].get(platform, 0) + 1

    save_videos()

    with open(file_path, "rb") as video:

        bot.send_video(
            chat_id,
            video,
            caption=CAPTION_TEXT,
            reply_markup=kb
        )

    # ================= MEDIA DOWNLOADER =================

def download_media(chat_id, text):

    url = extract_url(text)

    if not url:
        bot.send_message(chat_id, "❌ Invalid link")
        return

    if VERIFY_MODE and str(chat_id) not in verified_users:

        pending_downloads[str(chat_id)] = text
        start_verification(chat_id)
        return

    try:

        msg = bot.send_message(chat_id, "⏳ Downloading...")
        bot.send_chat_action(chat_id, "typing")

        # ================= TIKTOK =================

        if "tiktok.com" in url:

            api = f"https://tikwm.com/api/?url={url}"
            res = requests.get(api).json()

            if res.get("code") == 0:

                data = res["data"]

                # PHOTOS
                if data.get("images"):

                    for i, img in enumerate(data["images"], 1):

                        img_data = requests.get(img).content
                        filename = f"tiktok_{i}.jpg"

                        with open(filename, "wb") as f:
                            f.write(img_data)

                        with open(filename, "rb") as photo:
                            bot.send_photo(chat_id, photo, caption=CAPTION_TEXT)

                        os.remove(filename)

                    bot.delete_message(chat_id, msg.message_id)
                    return

                # VIDEO
                if data.get("play"):

                    video = requests.get(data["play"]).content
                    filename = "tiktok.mp4"

                    with open(filename, "wb") as f:
                        f.write(video)

                    bot.send_chat_action(chat_id, "upload_video")

                    send_video_with_music(chat_id, filename, "tiktok")

                    bot.delete_message(chat_id, msg.message_id)
                    return


        # ================= INSTAGRAM =================

        if "instagram.com" in url:

            ydl_opts = {
                "format": "best",
                "outtmpl": "instagram_%(id)s.%(ext)s",
                "quiet": True
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:

                info = ydl.extract_info(url, download=True)

                if "entries" in info:
                    entries = info["entries"]
                else:
                    entries = [info]

                for entry in entries:

                    file = ydl.prepare_filename(entry)

                    if file.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):

                        with open(file, "rb") as photo:
                            bot.send_photo(chat_id, photo, caption=CAPTION_TEXT)

                        os.remove(file)

                    else:

                        bot.send_chat_action(chat_id, "upload_video")

                        send_video_with_music(chat_id, file, "instagram")

                bot.delete_message(chat_id, msg.message_id)
                return

# ================= PINTEREST =================

        if "pin.it" in url:

            try:
                r = requests.head(url, allow_redirects=True)
                url = r.url
            except:
                pass

        if "pinterest.com" in url:

            ydl_opts = {
                "format": "best",
                "outtmpl": "pinterest_%(id)s.%(ext)s",
                "quiet": True
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:

                info = ydl.extract_info(url, download=True)

                if "entries" in info:
                    entries = info["entries"]
                else:
                    entries = [info]

                for entry in entries:

                    file = ydl.prepare_filename(entry)

                    if file.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):

                        with open(file, "rb") as photo:
                            bot.send_photo(chat_id, photo, caption=CAPTION_TEXT)

                        os.remove(file)

                    else:

                        bot.send_chat_action(chat_id, "upload_video")

                        send_video_with_music(chat_id, file, "pinterest")

                bot.delete_message(chat_id, msg.message_id)
                return


        # ================= FACEBOOK =================

        if "facebook.com" in url or "fb.watch" in url:

            ydl_opts = {
                "format": "best[ext=mp4]",
                "outtmpl": "facebook_%(id)s.%(ext)s",
                "quiet": True
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:

                info = ydl.extract_info(url, download=True)
                file = ydl.prepare_filename(info)

                bot.send_chat_action(chat_id, "upload_video")

                send_video_with_music(chat_id, file, "facebook")

                bot.delete_message(chat_id, msg.message_id)
                return


        # ================= YOUTUBE =================

        if "youtube.com" in url or "youtu.be" in url:

            ydl_opts = {
                "format": "best[ext=mp4]",
                "outtmpl": "youtube_%(id)s.%(ext)s",
                "quiet": True
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:

                info = ydl.extract_info(url, download=True)
                file = ydl.prepare_filename(info)

                bot.send_chat_action(chat_id, "upload_video")

                send_video_with_music(chat_id, file, "youtube")

                bot.delete_message(chat_id, msg.message_id)
                return


        bot.delete_message(chat_id, msg.message_id)

        bot.send_message(
            chat_id,
            "❌ Unsupported link"
        )

    except Exception as e:

        bot.send_message(
            chat_id,
            "❌ Invalid link.\n\n"
            "📥 Send link from:\n"
            "• TikTok\n"
            "• Instagram\n"
            "• Pinterest\n"
            "• YouTube\n"
            "• Facebook"
        )


# ================= MESSAGE USER =================

@bot.callback_query_handler(func=lambda call: call.data.startswith("msguser|"))
def message_user(call):

    if not is_admin(call.from_user.id):
        return

    uid = call.data.split("|")[1]

    msg = bot.send_message(
        call.message.chat.id,
        "Send message for user"
    )

    bot.register_next_step_handler(msg, send_user_message, uid)


def send_user_message(m, uid):

    if not is_admin(m.from_user.id):
        return

    try:

        bot.send_message(int(uid), m.text)

        bot.send_message(
            m.chat.id,
            "✅ Message sent"
        )

    except:

        bot.send_message(
            m.chat.id,
            "❌ Failed to send message"
        )


# ================= MUSIC CONVERSION =================

@bot.callback_query_handler(func=lambda call: call.data.startswith("music|"))
def convert_music(call):

    file_path = call.data.split("|", 1)[1]

    audio_path = file_path.rsplit(".", 1)[0] + ".mp3"

    try:

        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                file_path,
                "-vn",
                "-acodec",
                "mp3",
                "-ab",
                "128k",
                "-ar",
                "44100",
                audio_path
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
        )

        kb = InlineKeyboardMarkup()
        kb.add(
            InlineKeyboardButton(
                "📢 BOT CHANNEL",
                url="https://t.me/tiktokvediodownload"
            )
        )

        with open(audio_path, "rb") as audio:

            bot.send_audio(
                call.message.chat.id,
                audio,
                title="Converted Music",
                performer="DownloadBot",
                caption=CAPTION_TEXT,
                reply_markup=kb
            )

        if os.path.exists(audio_path):
            os.remove(audio_path)

        if os.path.exists(file_path):
            os.remove(file_path)

    except Exception as e:

        bot.send_message(
            call.message.chat.id,
            f"❌ Music conversion failed:\n{e}"
        )


# ================= RUN BOTS SAFELY =================

def run_bot1():

    while True:

        try:

            bot.infinity_polling(
                skip_pending=True,
                timeout=60,
                long_polling_timeout=60
            )

        except Exception as e:

            print(f"Bot1 restart: {e}")


def run_bot2():

    while True:

        try:

            bot2.infinity_polling(
                skip_pending=True,
                timeout=60,
                long_polling_timeout=60
            )

        except Exception as e:

            print(f"Bot2 restart: {e}")


if __name__ == "__main__":

    t1 = threading.Thread(target=run_bot1)
    t2 = threading.Thread(target=run_bot2)

    t1.start()
    t2.start()

    # Flask ha xanibin bots
    app.run(
        host="0.0.0.0",
        port=3000,
        threaded=True
    )
