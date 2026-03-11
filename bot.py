import telebot
import requests
from telebot.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
import os, json, random
from datetime import datetime
import yt_dlp
import subprocess
import re
import shutil
from flask import Flask, request, jsonify
import threading

# ================= VERIFY SYSTEM =================
VERIFY_MODE = False
verified_users = set()
pending_codes = {}

BOT2_TOKEN = os.getenv("BOT2_TOKEN")
BOT2_USERNAME = "@Verifyd_bot"
bot2 = telebot.TeleBot(BOT2_TOKEN)

def generate_code():
    return str(random.randint(100000, 999999))

def start_verification(user_id):
    code = generate_code()
    pending_codes[str(user_id)] = code

    bot.send_message(
        user_id,
        "🔐 Verification Required\n\n"
        f"1️⃣ Fur bot-kan: {BOT2_USERNAME}\n"
        "2️⃣ Riix START\n"
        "3️⃣ Code-ka halkaas ka hel kadib halkan ku soo dir"
    )

    try:
        bot2.send_message(
            user_id,
            f"🔐 Your verification code:\n\n<code>{code}</code>\n\nDo not share."
        )
    except:
        bot.send_message(
            user_id,
            "⚠️ Marka hore fur bot-ka verification kadib isku day mar kale."
        )

# ================= CONFIG =================
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

videos_data = load_json(VIDEOS_FILE, {
    "total": 0,
    "platforms": {
        "tiktok": 0,
        "youtube": 0,
        "facebook": 0,
        "instagram": 0,
        "pinterest": 0
    },
    "users": {}
})

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

# ================= USER MANAGEMENT =================
def ensure_user(uid):
    uid = str(uid)
    if uid not in users:
        users[uid] = {
            "points": 0,
            "joined": str(datetime.now()),
            "bot_id": random_botid(),
            "banned": False,
            "history": [],
            "withdraw_total": 0,
            "referrals": 0,
            "referred_by": None,
            "verified": False
        }
        save_users()

def add_points(uid, pts):
    uid = str(uid)
    ensure_user(uid)
    users[uid]["points"] += pts
    save_users()

def deduct_points(uid, pts):
    uid = str(uid)
    ensure_user(uid)
    users[uid]["points"] -= pts
    save_users()

# ================= KEYBOARDS =================
def user_menu(admin=False):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("🎬 Download Video", "🎵 Convert Music")
    kb.row("👤 My Account", "💰 Withdraw")
    kb.row("📜 History", "🔗 Referral")
    if admin:
        kb.row("🛠 Admin Panel")
    return kb

def admin_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("📊 Stats", "👥 Users")
    kb.row("🚫 Ban User", "✅ Unban User")
    kb.row("💳 Withdraw Requests")
    kb.row("🔐 Verify ON", "🔓 Verify OFF")
    kb.row("🔙 Back")
    return kb

# ================= START COMMAND =================
@bot.message_handler(commands=['start'])
def start_cmd(message):
    uid = str(message.from_user.id)

    # VERIFY CHECK
    if VERIFY_MODE and uid not in verified_users:
        start_verification(uid)
        return

    ensure_user(uid)

    args = message.text.split()
    if len(args) > 1:
        ref = args[1]
        ref_uid = find_user_by_botid(ref)
        if ref_uid and ref_uid != uid and not users[uid]["referred_by"]:
            users[uid]["referred_by"] = ref_uid
            users[ref_uid]["points"] += 5
            users[ref_uid]["referrals"] += 1
            save_users()
            bot.send_message(ref_uid, "🎉 New referral joined!")

    bot.send_message(
        message.chat.id,
        "👋 Welcome to the Media Bot!\n\nDownload videos & convert music easily.",
        reply_markup=user_menu(is_admin(uid))
    )

# ================= ACCOUNT =================
@bot.message_handler(func=lambda m: m.text == "👤 My Account")
def my_account(m):
    if banned_guard(m): return
    uid = str(m.from_user.id)
    ensure_user(uid)
    data = users[uid]

    txt = (
        "👤 <b>Your Account</b>\n\n"
        f"🆔 ID: <code>{uid}</code>\n"
        f"🤖 Bot ID: <code>{data['bot_id']}</code>\n"
        f"💰 Points: <b>{data['points']}</b>\n"
        f"👥 Referrals: {data['referrals']}\n"
        f"💸 Withdrawn: {data['withdraw_total']}\n"
    )

    bot.send_message(m.chat.id, txt)

# ================= HISTORY =================
@bot.message_handler(func=lambda m: m.text == "📜 History")
def history_cmd(m):
    if banned_guard(m): return
    uid = str(m.from_user.id)
    ensure_user(uid)
    hist = users[uid]["history"][-10:]

    if not hist:
        bot.send_message(m.chat.id, "📭 No history yet.")
        return

    msg = "📜 <b>Recent Activity</b>\n\n"
    for h in hist:
        msg += f"• {h}\n"

    bot.send_message(m.chat.id, msg)

# ================= REFERRAL =================
@bot.message_handler(func=lambda m: m.text == "🔗 Referral")
def referral_cmd(m):
    if banned_guard(m): return
    uid = str(m.from_user.id)
    ensure_user(uid)

    link = f"https://t.me/{bot.get_me().username}?start={users[uid]['bot_id']}"

    bot.send_message(
        m.chat.id,
        "🔗 <b>Your Referral Link</b>\n\n"
        f"{link}\n\n"
        "👥 Earn 5 points per referral."
    )

# ================= WITHDRAW SYSTEM =================
@bot.message_handler(func=lambda m: m.text == "💰 Withdraw")
def withdraw_cmd(m):
    if banned_guard(m): return
    uid = str(m.from_user.id)
    ensure_user(uid)

    pts = users[uid]["points"]
    if pts < 50:
        bot.send_message(m.chat.id, "❌ Minimum withdraw is 50 points.")
        return

    msg = bot.send_message(
        m.chat.id,
        "💳 Send your EVC number to withdraw points.\n\n"
        "Example: 25261xxxxxxx"
    )
    bot.register_next_step_handler(msg, process_withdraw)

def process_withdraw(m):
    if banned_guard(m): return
    uid = str(m.from_user.id)
    number = m.text.strip()

    if not re.match(r"^25261\d{7}$", number):
        bot.send_message(m.chat.id, "❌ Invalid number format.")
        return

    pts = users[uid]["points"]
    users[uid]["points"] = 0
    users[uid]["withdraw_total"] += pts

    req = {
        "user": uid,
        "number": number,
        "points": pts,
        "date": str(datetime.now())
    }
    withdraws.append(req)

    save_users()
    save_withdraws()

    bot.send_message(m.chat.id, "✅ Withdraw request sent.")

    for admin in ADMIN_IDS:
        bot.send_message(
            admin,
            f"💳 Withdraw Request\n\n"
            f"User: {uid}\nNumber: {number}\nPoints: {pts}"
        )

# ================= ADMIN PANEL =================
@bot.message_handler(func=lambda m: m.text == "🛠 Admin Panel")
def admin_panel(m):
    uid = str(m.from_user.id)
    if not is_admin(uid): return
    bot.send_message(m.chat.id, "🛠 Admin Panel", reply_markup=admin_menu())

# ================= ADMIN STATS =================
@bot.message_handler(func=lambda m: m.text == "📊 Stats")
def admin_stats(m):
    uid = str(m.from_user.id)
    if not is_admin(uid): return

    total_users = len(users)
    total_withdraws = len(withdraws)
    total_points = sum(u["points"] for u in users.values())

    txt = (
        "📊 <b>Bot Statistics</b>\n\n"
        f"👥 Users: {total_users}\n"
        f"💳 Withdraw Requests: {total_withdraws}\n"
        f"💰 Total Points: {total_points}\n"
        f"🎬 Videos Downloaded: {videos_data['total']}\n"
    )
    bot.send_message(m.chat.id, txt)

# ================= ADMIN USERS =================
@bot.message_handler(func=lambda m: m.text == "👥 Users")
def admin_users(m):
    uid = str(m.from_user.id)
    if not is_admin(uid): return

    msg = "👥 <b>Users List</b>\n\n"
    for u in list(users.keys())[:50]:
        msg += f"• {u} | 💰 {users[u]['points']}\n"

    bot.send_message(m.chat.id, msg)

# ================= BAN USER =================
@bot.message_handler(func=lambda m: m.text == "🚫 Ban User")
def ban_user_prompt(m):
    uid = str(m.from_user.id)
    if not is_admin(uid): return
    msg = bot.send_message(m.chat.id, "Send User ID to ban:")
    bot.register_next_step_handler(msg, ban_user)

def ban_user(m):
    uid = m.text.strip()
    if uid in users:
        users[uid]["banned"] = True
        save_users()
        bot.send_message(m.chat.id, "✅ User banned.")
    else:
        bot.send_message(m.chat.id, "❌ User not found.")

# ================= UNBAN USER =================
@bot.message_handler(func=lambda m: m.text == "✅ Unban User")
def unban_user_prompt(m):
    uid = str(m.from_user.id)
    if not is_admin(uid): return
    msg = bot.send_message(m.chat.id, "Send User ID to unban:")
    bot.register_next_step_handler(msg, unban_user)

def unban_user(m):
    uid = m.text.strip()
    if uid in users:
        users[uid]["banned"] = False
        save_users()
        bot.send_message(m.chat.id, "✅ User unbanned.")
    else:
        bot.send_message(m.chat.id, "❌ User not found.")

# ================= VERIFY ADMIN CONTROL =================
@bot.message_handler(func=lambda m: m.text == "🔐 Verify ON")
def verify_on(m):
    uid = str(m.from_user.id)
    if not is_admin(uid): return
    global VERIFY_MODE
    VERIFY_MODE = True
    bot.send_message(m.chat.id, "✅ Verification system ENABLED.")

@bot.message_handler(func=lambda m: m.text == "🔓 Verify OFF")
def verify_off(m):
    uid = str(m.from_user.id)
    if not is_admin(uid): return
    global VERIFY_MODE
    VERIFY_MODE = False
    bot.send_message(m.chat.id, "❌ Verification system DISABLED.")

# ================= VERIFY CODE HANDLER =================
@bot.message_handler(func=lambda m: m.text and m.text.isdigit() and len(m.text) == 6)
def verify_code_handler(m):
    uid = str(m.from_user.id)

    if not VERIFY_MODE:
        return

    if uid in verified_users:
        return

    if pending_codes.get(uid) == m.text:
        verified_users.add(uid)
        pending_codes.pop(uid, None)
        users[uid]["verified"] = True
        save_users()
        bot.send_message(
            m.chat.id,
            "✅ Verification Successful!",
            reply_markup=user_menu(is_admin(uid))
        )
    else:
        bot.send_message(m.chat.id, "❌ Incorrect verification code.")

# ================= ADMIN WITHDRAW REQUESTS =================
@bot.message_handler(func=lambda m: m.text == "💳 Withdraw Requests")
def withdraw_requests(m):
    uid = str(m.from_user.id)
    if not is_admin(uid): return

    if not withdraws:
        bot.send_message(m.chat.id, "📭 No withdraw requests.")
        return

    msg = "💳 <b>Withdraw Requests</b>\n\n"
    for i, w in enumerate(withdraws[-20:], 1):
        msg += (
            f"{i}. 👤 {w['user']}\n"
            f"📱 {w['number']}\n"
            f"💰 {w['points']} pts\n"
            f"📅 {w['date']}\n\n"
        )

    bot.send_message(m.chat.id, msg)

# ================= ADMIN BACK =================
@bot.message_handler(func=lambda m: m.text == "🔙 Back")
def admin_back(m):
    uid = str(m.from_user.id)
    if not is_admin(uid): return
    bot.send_message(
        m.chat.id,
        "↩️ Back to user menu",
        reply_markup=user_menu(True)
    )

    # ================= VIDEO DOWNLOADER =================
@bot.message_handler(func=lambda m: m.text == "🎬 Download Video")
def download_video_prompt(m):
    if banned_guard(m): return
    msg = bot.send_message(
        m.chat.id,
        "📥 Send video link from:\n\n"
        "• TikTok\n• YouTube\n• Facebook\n• Instagram\n• Pinterest"
    )
    bot.register_next_step_handler(msg, process_video_link)

def detect_platform(url):
    url = url.lower()
    if "tiktok" in url: return "tiktok"
    if "youtu" in url: return "youtube"
    if "facebook" in url or "fb.watch" in url: return "facebook"
    if "instagram" in url: return "instagram"
    if "pinterest" in url: return "pinterest"
    return "unknown"

def process_video_link(m):
    if banned_guard(m): return
    url = m.text.strip()
    uid = str(m.from_user.id)
    ensure_user(uid)

    platform = detect_platform(url)
    if platform == "unknown":
        bot.send_message(m.chat.id, "❌ Unsupported platform.")
        return

    msg = bot.send_message(m.chat.id, "⏳ Downloading video...")

    try:
        filename = f"downloads/{uid}_{random.randint(1000,9999)}.mp4"
        os.makedirs("downloads", exist_ok=True)

        ydl_opts = {
            "outtmpl": filename,
            "format": "mp4/best",
            "quiet": True
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        bot.delete_message(m.chat.id, msg.message_id)

        with open(filename, "rb") as vid:
            bot.send_video(m.chat.id, vid)

        os.remove(filename)

        users[uid]["history"].append(f"Downloaded {platform} video")
        videos_data["total"] += 1
        videos_data["platforms"][platform] += 1
        videos_data["users"].setdefault(uid, 0)
        videos_data["users"][uid] += 1

        save_users()
        save_videos()

        add_points(uid, 2)

    except Exception as e:
        bot.edit_message_text(
            f"❌ Error downloading video.\n\n{str(e)}",
            m.chat.id,
            msg.message_id
        )

# ================= BULK LINK DETECTOR =================
@bot.message_handler(func=lambda m: "http" in m.text.lower())
def auto_link_detect(m):
    if banned_guard(m): return
    if "tiktok.com" in m.text or "youtu" in m.text:
        process_video_link(m)

# ================= MUSIC CONVERTER =================
@bot.message_handler(func=lambda m: m.text == "🎵 Convert Music")
def convert_music_prompt(m):
    if banned_guard(m): return
    msg = bot.send_message(
        m.chat.id,
        "🎵 Send YouTube link to convert into MP3 music."
    )
    bot.register_next_step_handler(msg, process_music_link)

def process_music_link(m):
    if banned_guard(m): return
    url = m.text.strip()
    uid = str(m.from_user.id)
    ensure_user(uid)

    if "youtu" not in url:
        bot.send_message(m.chat.id, "❌ Only YouTube links allowed.")
        return

    msg = bot.send_message(m.chat.id, "⏳ Converting to MP3...")

    try:
        os.makedirs("music", exist_ok=True)
        filename = f"music/{uid}_{random.randint(1000,9999)}.mp3"

        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': filename,
            'quiet': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        bot.delete_message(m.chat.id, msg.message_id)

        with open(filename, "rb") as aud:
            bot.send_audio(m.chat.id, aud)

        os.remove(filename)

        users[uid]["history"].append("Converted YouTube to MP3")
        save_users()
        add_points(uid, 3)

    except Exception as e:
        bot.edit_message_text(
            f"❌ Conversion failed.\n\n{str(e)}",
            m.chat.id,
            msg.message_id
        )

# ================= AUDIO UPLOAD CONVERTER =================
@bot.message_handler(content_types=['audio', 'voice'])
def audio_to_mp3(m):
    if banned_guard(m): return
    uid = str(m.from_user.id)
    ensure_user(uid)

    msg = bot.send_message(m.chat.id, "⏳ Processing audio...")

    try:
        file_info = bot.get_file(m.audio.file_id if m.audio else m.voice.file_id)
        downloaded = bot.download_file(file_info.file_path)

        os.makedirs("uploads", exist_ok=True)
        src = f"uploads/{uid}_{random.randint(1000,9999)}.ogg"
        dst = src.replace(".ogg", ".mp3")

        with open(src, "wb") as f:
            f.write(downloaded)

        subprocess.run(["ffmpeg", "-i", src, dst], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        bot.delete_message(m.chat.id, msg.message_id)

        with open(dst, "rb") as a:
            bot.send_audio(m.chat.id, a)

        os.remove(src)
        os.remove(dst)

        users[uid]["history"].append("Converted uploaded audio to MP3")
        save_users()
        add_points(uid, 2)

    except:
        bot.edit_message_text("❌ Audio conversion failed.", m.chat.id, msg.message_id)

        # ================= FILE CLEANER =================
def clean_folder(folder, max_age_hours=6):
    try:
        now = datetime.now().timestamp()
        for fname in os.listdir(folder):
            path = os.path.join(folder, fname)
            if os.path.isfile(path):
                age = (now - os.path.getmtime(path)) / 3600
                if age > max_age_hours:
                    os.remove(path)
    except:
        pass

def periodic_cleanup():
    while True:
        clean_folder("downloads")
        clean_folder("music")
        clean_folder("uploads")
        time.sleep(3600)

# ================= AUTO CREATE FOLDERS =================
def ensure_dirs():
    os.makedirs("downloads", exist_ok=True)
    os.makedirs("music", exist_ok=True)
    os.makedirs("uploads", exist_ok=True)

ensure_dirs()

# ================= LOGGING SYSTEM =================
LOG_FILE = "bot.log"

def log_event(text):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now()}] {text}\n")

# ================= ERROR HANDLER =================
@bot.middleware_handler(update_types=['message'])
def global_logger(bot_instance, message):
    try:
        uid = message.from_user.id
        name = message.from_user.first_name
        log_event(f"User:{uid} Name:{name} Msg:{message.text}")
    except:
        pass

# ================= SAFE SEND =================
def safe_send(chat_id, text, **kwargs):
    try:
        bot.send_message(chat_id, text, **kwargs)
    except:
        pass

# ================= BROADCAST SYSTEM =================
@bot.message_handler(commands=['broadcast'])
def broadcast_cmd(m):
    uid = str(m.from_user.id)
    if not is_admin(uid): return

    msg = bot.send_message(m.chat.id, "Send broadcast message:")
    bot.register_next_step_handler(msg, process_broadcast)

def process_broadcast(m):
    sent = 0
    for uid in users.keys():
        try:
            bot.send_message(uid, m.text)
            sent += 1
        except:
            pass

    bot.send_message(m.chat.id, f"✅ Broadcast sent to {sent} users.")

# ================= FORCE JOIN SYSTEM =================
def is_joined(uid):
    try:
        member = bot.get_chat_member(f"@{CHANNEL_USERNAME}", uid)
        return member.status in ["member", "administrator", "creator"]
    except:
        return True

def join_guard(m):
    uid = m.from_user.id
    if not is_joined(uid):
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{CHANNEL_USERNAME}"))
        bot.send_message(
            m.chat.id,
            "📢 You must join our channel to use the bot.",
            reply_markup=kb
        )
        return False
    return True

# ================= FLASK SERVER (KEEP ALIVE) =================
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

@app.route('/health')
def health():
    return {"status": "ok"}

def run_web():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

# ================= THREADING =================
def run_bot():
    log_event("Bot polling started")
    bot.infinity_polling(timeout=60, long_polling_timeout=60)

# ================= START SERVICES =================
def start_services():
    t1 = threading.Thread(target=run_bot)
    t2 = threading.Thread(target=run_web)
    t3 = threading.Thread(target=periodic_cleanup)

    t1.start()
    t2.start()
    t3.start()

# ================= SHUTDOWN CLEANUP =================
def cleanup_on_exit():
    try:
        shutil.rmtree("downloads", ignore_errors=True)
        shutil.rmtree("music", ignore_errors=True)
        shutil.rmtree("uploads", ignore_errors=True)
    except:
        pass

# ================= SIGNAL HANDLING =================
import signal
import sys
import time

def signal_handler(sig, frame):
    log_event("Bot stopped.")
    cleanup_on_exit()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# ================= BOT START =================
if __name__ == "__main__":
    try:
        log_event("Starting services...")
        start_services()
    except Exception as e:
        log_event(f"Fatal Error: {e}")

# ================= BOT2 (VERIFICATION BOT) =================
@bot2.message_handler(commands=['start'])
def bot2_start(m):
    uid = str(m.from_user.id)

    if uid in pending_codes:
        code = pending_codes[uid]
        bot2.send_message(
            m.chat.id,
            f"🔐 Your verification code:\n\n<code>{code}</code>\n\nSend this to main bot."
        )
    else:
        bot2.send_message(
            m.chat.id,
            "ℹ️ No pending verification.\nStart main bot first."
        )

# ================= BOT2 POLLING =================
def run_bot2():
    bot2.infinity_polling(timeout=60, long_polling_timeout=60)

threading.Thread(target=run_bot2).start()
