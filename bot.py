import telebot
from telebot.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
import os, json, random, requests
from datetime import datetime
import yt_dlp

# ================= CONFIG =================
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 7983838654
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# ================= DATABASE =================
USERS_FILE = "users.json"
WITHDRAWS_FILE = "withdraws.json"

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

def save_users(): save_json(USERS_FILE, users)
def save_withdraws(): save_json(WITHDRAWS_FILE, withdraws)

# ================= HELPERS =================
def random_ref(): return str(random.randint(1000000000,9999999999))
def random_botid(): return str(random.randint(10000000000,99999999999))
def now_month(): return datetime.now().month
def is_admin(uid): return int(uid) == ADMIN_ID

def user_menu(is_admin_user=False):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("💰 BALANCE","💸 WITHDRAWAL")
    kb.add("👥 REFERRAL","🆔 GET ID")
    kb.add("☎️ CUSTOMER")
    if is_admin_user:
        kb.add("👑 ADMIN PANEL")
    return kb

def admin_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📊 STATS","📢 BROADCAST")
    kb.add("➕ ADD BALANCE","✅ UNBAN MONEY")
    kb.add("💳 WITHDRAWAL CHECK")
    kb.add("🔙 BACK MAIN MENU")
    return kb

def back_main_menu(chat_id, uid):
    bot.send_message(chat_id, "🏠 Main Menu", reply_markup=user_menu(is_admin(uid)))

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

# ================= START =================
@bot.message_handler(commands=['start'])
def start(m):
    uid = str(m.from_user.id)
    args = m.text.split()
    if uid not in users:
        ref = args[1] if len(args) > 1 else None
        users[uid] = {
            "balance":0.0,
            "blocked":0.0,
            "ref":random_ref(),
            "bot_id":random_botid(),
            "invited":0,
            "banned":False,
            "month": now_month()
        }
        if ref:
            for u in users:
                if users[u]["ref"] == ref:
                    users[u]["balance"] += 0.2
                    users[u]["invited"] += 1
                    bot.send_message(int(u),"🎉 You earned $0.2 from referral.")
                    break
        save_users()
    bot.send_message(m.chat.id,"👋 Welcome!", reply_markup=user_menu(is_admin(uid)))

# ================= BALANCE =================
@bot.message_handler(func=lambda m: m.text=="💰 BALANCE")
def balance(m):
    if banned_guard(m): return
    uid = str(m.from_user.id)
    bal = users[uid]["balance"]
    blk = users[uid].get("blocked",0.0)
    bot.send_message(m.chat.id, f"💰 Available: ${bal:.2f}\n🔒 Blocked: ${blk:.2f}")

# ================= GET ID =================
@bot.message_handler(func=lambda m: m.text=="🆔 GET ID")
def get_id(m):
    if banned_guard(m): return
    uid = str(m.from_user.id)
    bot.send_message(m.chat.id, f"🆔 BOT ID: <code>{users[uid]['bot_id']}</code>\n👤 Telegram ID: <code>{uid}</code>")

# ================= REFERRAL =================
@bot.message_handler(func=lambda m: m.text=="👥 REFERRAL")
def referral(m):
    if banned_guard(m): return
    uid = str(m.from_user.id)
    link = f"https://t.me/{bot.get_me().username}?start={users[uid]['ref']}"
    bot.send_message(m.chat.id,f"🔗 Referral link:\n{link}\n👥 Invited: {users[uid].get('invited',0)}")

# ================= CUSTOMER =================
@bot.message_handler(func=lambda m: m.text=="☎️ CUSTOMER")
def customer(m):
    if banned_guard(m): return
    bot.send_message(m.chat.id,"Contact support: @scholes1")

# ================= WITHDRAWAL =================

@bot.message_handler(func=lambda m: m.text == "💸 WITHDRAWAL")
def withdraw_menu(m):
    if banned_guard(m): return

    uid = str(m.from_user.id)

    if users[uid]["balance"] < 1:
        bot.send_message(m.chat.id, "❌ Minimum withdrawal is $1")
        return

    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("USDT-BEP20")
    kb.add("🔙 BACK MAIN MENU")

    bot.send_message(m.chat.id, "Select withdrawal method:", reply_markup=kb)


# ================= SELECT METHOD =================
@bot.message_handler(func=lambda m: m.text == "USDT-BEP20")
def withdraw_address_start(m):
    if banned_guard(m): return

    msg = bot.send_message(
        m.chat.id,
        "Enter USDT BEP20 address (must start with 0x)\nOr press 🔙 BACK MAIN MENU"
    )

    bot.register_next_step_handler(msg, withdraw_address)


# ================= ADDRESS =================
def withdraw_address(m):
    uid = str(m.from_user.id)
    text = (m.text or "").strip()

    if text == "🔙 BACK MAIN MENU":
        back_main_menu(m.chat.id, uid)
        return

    if not text.startswith("0x"):
        msg = bot.send_message(m.chat.id, "❌ Address must start with 0x")
        bot.register_next_step_handler(msg, withdraw_address)
        return

    users[uid]["temp_addr"] = text
    save_users()

    msg = bot.send_message(
        m.chat.id,
        f"Enter amount to withdraw\nMinimum: $1\nBalance: ${users[uid]['balance']:.2f}"
    )

    bot.register_next_step_handler(msg, withdraw_amount)


# ================= AMOUNT =================
def withdraw_amount(m):
    uid = str(m.from_user.id)
    text = (m.text or "").strip()

    if text == "🔙 BACK MAIN MENU":
        back_main_menu(m.chat.id, uid)
        return

    try:
        amt = float(text)
    except:
        msg = bot.send_message(m.chat.id, "❌ Enter valid number")
        bot.register_next_step_handler(msg, withdraw_amount)
        return

    if amt < 1:
        msg = bot.send_message(m.chat.id, "❌ Minimum withdrawal is $1")
        bot.register_next_step_handler(msg, withdraw_amount)
        return

    if amt > users[uid]["balance"]:
        msg = bot.send_message(m.chat.id, "❌ Insufficient balance")
        bot.register_next_step_handler(msg, withdraw_amount)
        return

    # ===== CREATE REQUEST =====
    wid = random.randint(10000, 99999)
    addr = users[uid].pop("temp_addr")

    withdraws.append({
        "id": wid,
        "user": uid,
        "amount": amt,
        "blocked": amt,
        "address": addr,
        "status": "pending",
        "time": str(datetime.now())
    })

    users[uid]["balance"] -= amt
    users[uid]["blocked"] = users[uid].get("blocked", 0.0) + amt

    save_users()
    save_withdraws()

    # ===== USER MESSAGE =====
    bot.send_message(
        m.chat.id,
        f"✅ Withdrawal Request Sent\n\n"
        f"🧾 Request ID: {wid}\n"
        f"💵 Amount: ${amt:.2f}\n"
        f"🏦 Address: {addr}\n"
        f"💰 Balance Left: ${users[uid]['balance']:.2f}\n"
        f"⏳ Processing: 6‑12 hours",
        reply_markup=user_menu(is_admin(uid))
    )

    # ===== ADMIN MESSAGE =====
    admin_msg = (
        f"💳 NEW WITHDRAWAL\n\n"
        f"👤 User: {uid}\n"
        f"🤖 BOT ID: {users[uid]['bot_id']}\n"
        f"👥 Referrals: {users[uid]['invited']}\n"
        f"💵 Amount: ${amt:.2f}\n"
        f"🧾 Request ID: {wid}\n"
        f"🏦 Address: {addr}\n\n"
        f"CONFIRM {wid}\n"
        f"REJECT {wid}\n"
        f"BAN {uid}"
    )

    bot.send_message(ADMIN_ID, admin_msg)

# ================= ADMIN PANEL =================
@bot.message_handler(func=lambda m: m.text=="👑 ADMIN PANEL")
def admin_panel_btn(m):
    if not is_admin(m.from_user.id): return
    bot.send_message(m.chat.id,"👑 ADMIN PANEL", reply_markup=admin_menu())

@bot.message_handler(func=lambda m: m.text=="🔙 BACK MAIN MENU")
def back_main(m):
    back_main_menu(m.chat.id, str(m.from_user.id))

# ================= MEDIA DOWNLOADER =================
def download_media(chat_id,url):
    try:
        # TikTok
        if "tiktok.com" in url:
            try:
                api = f"https://tikwm.com/api/?url={url}"
                res = requests.get(api, timeout=20).json()
                if res.get("code")==0 and "data" in res:
                    data = res["data"]
                    # Photos
                    if data.get("images"):
                        for img in data["images"]:
                            img_data = requests.get(img).content
                            with open("tt.jpg","wb") as f: f.write(img_data)
                            bot.send_photo(chat_id, open("tt.jpg","rb"))
                            os.remove("tt.jpg")
                        return
                    # Video
                    if data.get("play"):
                        vid = requests.get(data["play"]).content
                        with open("tt.mp4","wb") as f: f.write(vid)
                        bot.send_video(chat_id, open("tt.mp4","rb"))
                        os.remove("tt.mp4")
                        return
            except: pass
            # fallback yt-dlp
            try:
                ydl_opts = {"outtmpl":"tiktok.%(ext)s","format":"mp4","quiet":True}
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    if isinstance(info, dict) and info.get("entries"):
                        for e in info["entries"]:
                            f = ydl.prepare_filename(e)
                            bot.send_photo(chat_id, open(f,"rb"))
                            os.remove(f)
                    else:
                        f = ydl.prepare_filename(info)
                        bot.send_video(chat_id, open(f,"rb"))
                        os.remove(f)
                return
            except Exception as e:
                bot.send_message(chat_id,f"TikTok download error: {e}")
                return
        # YouTube
        if "youtube.com" in url or "youtu.be" in url:
            try:
                ydl_opts = {"outtmpl":"youtube.%(ext)s","format":"mp4","quiet":True}
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    f = ydl.prepare_filename(info)
                bot.send_video(chat_id, open(f,"rb"))
                os.remove(f)
                return
            except Exception as e:
                bot.send_message(chat_id,f"YouTube download error: {e}")
                return
        bot.send_message(chat_id,"❌ Unsupported link")
    except Exception as e:
        bot.send_message(chat_id,f"Download error: {e}")

@bot.message_handler(func=lambda m: m.text and "http" in m.text)
def links(m):
    if banned_guard(m): return
    bot.send_message(m.chat.id,"⏳ Downloading...")
    download_media(m.chat.id, m.text)

# ================= RUN =================
bot.infinity_polling(skip_pending=True)
