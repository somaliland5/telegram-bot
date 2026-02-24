import telebot
from telebot.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
import os, json, random, requests, subprocess
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

def save_users():
    save_json(USERS_FILE, users)

def save_withdraws():
    save_json(WITHDRAWS_FILE, withdraws)

# ================= HELPERS =================
def random_ref():
    return str(random.randint(1000000000,9999999999))

def random_botid():
    return str(random.randint(10000000000,99999999999))

def random_code():
    return str(random.randint(10000,99999))  # 5-digit code for Ban Money

def now_month():
    return datetime.now().month

def is_admin(uid):
    return int(uid) == ADMIN_ID

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

# ================= MENUS =================
def user_menu(show_admin=False):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("💰 BALANCE","💸 WITHDRAWAL")
    kb.add("👥 REFERRAL","🆔 GET ID")
    kb.add("☎️ CUSTOMER")
    if show_admin:
        kb.add("👑 ADMIN PANEL")
    return kb

def admin_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📊 STATS","📢 BROADCAST")
    kb.add("➕ ADD BALANCE","➖ REMOVE MONEY")
    kb.add("✅ UNBAN USER","💳 WITHDRAWAL CHECK")
    kb.add("🔙 BACK MAIN MENU")
    return kb

def back_main_menu(chat_id, uid):
    bot.send_message(chat_id, "🏠 Main Menu", reply_markup=user_menu(is_admin(uid)))

# ================= START HANDLER =================
@bot.message_handler(commands=['start'])
def start(m):
    uid = str(m.from_user.id)
    args = m.text.split()
    
    if uid not in users:
        ref = args[1] if len(args) > 1 else None
        users[uid] = {
            "balance":0.0,
            "blocked":0.0,
            "pending":0.0,
            "ref":random_ref(),
            "bot_id":random_botid(),
            "invited":0,
            "banned":False,
            "ban_code": None,  # For Ban Money feature
            "month": now_month()
        }
        if ref:
            for u in users:
                if users[u]["ref"] == ref:
                    users[u]["balance"] += 0.2
                    users[u]["invited"] += 1
                    bot.send_message(int(u), "🎉 You earned $0.2 from referral.")
                    break
        save_users()
    
    bot.send_message(
        m.chat.id,
        "👋 Welcome! Send Video Link to Download 🎬",
        reply_markup=user_menu(is_admin(uid))
    )

# ================= BALANCE HANDLER =================
@bot.message_handler(func=lambda m: m.text=="💰 BALANCE")
def balance(m):
    if banned_guard(m): return
    uid = str(m.from_user.id)
    bal = users[uid]["balance"]
    blk = users[uid].get("blocked",0.0)
    pend = users[uid].get("pending",0.0)
    msg = (
        f"💰 <b>Balance Info</b>\n\n"
        f"💰 Available: ${bal:.2f}\n"
        f"✋️ Pending: ${pend:.2f}\n"
        f"🚫 Blocked: ${blk:.2f}"
    )
    bot.send_message(m.chat.id, msg)

# ================= GET ID HANDLER =================
@bot.message_handler(func=lambda m: m.text=="🆔 GET ID")
def get_id(m):
    if banned_guard(m): return
    uid = str(m.from_user.id)
    bot.send_message(
        m.chat.id,
        f"🆔 BOT ID: <code>{users[uid]['bot_id']}</code>\n👤 Telegram ID: <code>{uid}</code>"
    )

# ================= REFERRAL HANDLER =================
@bot.message_handler(func=lambda m: m.text=="👥 REFERRAL")
def referral(m):
    if banned_guard(m): return
    uid = str(m.from_user.id)
    link = f"https://t.me/{bot.get_me().username}?start={users[uid]['ref']}"
    invited = users[uid].get("invited", 0)
    msg_text = (
        f"🔗 Your referral link:\n{link}\n"
        f"👥 Invited: {invited}\n\n"
        f"🎁 Each new user who joins using your link gives you $0.2!"
    )
    bot.send_message(m.chat.id, msg_text)

# ================= CUSTOMER SUPPORT =================
@bot.message_handler(func=lambda m: m.text=="☎️ CUSTOMER")
def customer(m):
    if banned_guard(m): return
    bot.send_message(m.chat.id,"Contact support: @scholes1")

# ================= WITHDRAWAL MENU =================
@bot.message_handler(func=lambda m: m.text == "💸 WITHDRAWAL")
def withdraw_menu(m):
    if banned_guard(m): return
    uid = str(m.from_user.id)
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("USDT-BEP20")
    kb.add("🔙 CANCEL")
    bot.send_message(m.chat.id, "Select withdrawal method:", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text in ["USDT-BEP20","🔙 CANCEL"])
def withdraw_method(m):
    uid = str(m.from_user.id)
    if m.text=="🔙 CANCEL":
        back_main_menu(m.chat.id, uid)
        return
    if m.text=="USDT-BEP20":
        msg = bot.send_message(m.chat.id,"Enter your USDT BEP20 address (must start with 0x) or press 🔙 CANCEL")
        bot.register_next_step_handler(msg, withdraw_address)

def withdraw_address(m):
    uid = str(m.from_user.id)
    text = (m.text or "").strip()
    if text=="🔙 CANCEL":
        back_main_menu(m.chat.id, uid)
        return
    if not text.startswith("0x"):
        msg = bot.send_message(m.chat.id,"❌ Invalid address. Must start with 0x. Try again or press 🔙 CANCEL")
        bot.register_next_step_handler(msg, withdraw_address)
        return
    users[uid]["temp_addr"] = text
    save_users()
    msg = bot.send_message(m.chat.id,f"Enter withdrawal amount\nMinimum: $1 | Balance: ${users[uid]['balance']:.2f}\nOr press 🔙 CANCEL")
    bot.register_next_step_handler(msg, withdraw_amount)

def withdraw_amount(m):
    uid = str(m.from_user.id)
    text = (m.text or "").strip()
    if text=="🔙 CANCEL":
        back_main_menu(m.chat.id, uid)
        return
    try:
        amt = float(text)
    except:
        msg = bot.send_message(m.chat.id,"❌ Invalid number. Enter again or press 🔙 CANCEL")
        bot.register_next_step_handler(msg, withdraw_amount)
        return
    if amt < 1:
        msg = bot.send_message(m.chat.id,f"❌ Minimum withdrawal is $1\nBalance: ${users[uid]['balance']:.2f}")
        bot.register_next_step_handler(msg, withdraw_amount)
        return
    if amt > users[uid]["balance"]:
        msg = bot.send_message(m.chat.id,f"❌ Insufficient balance\nBalance: ${users[uid]['balance']:.2f}")
        bot.register_next_step_handler(msg, withdraw_amount)
        return

    wid = random.randint(10000,99999)
    addr = users[uid].pop("temp_addr")
    users[uid]["balance"] -= amt
    users[uid]["pending"] = users[uid].get("pending",0.0)+amt
    withdraws.append({
        "id": wid,
        "user": uid,
        "amount": amt,
        "blocked": 0.0,
        "address": addr,
        "status": "pending",
        "time": str(datetime.now())
    })
    save_users()
    save_withdraws()

    bot.send_message(m.chat.id,
        f"✅ Withdrawal Request Sent\n🧾 Request ID: {wid}\n💵 Amount: ${amt:.2f}\n🏦 Address: {addr}\n💰 Balance Left: ${users[uid]['balance']:.2f}\n✋️ Pending: ${users[uid]['pending']:.2f}\n⏳ Status: Pending",
        reply_markup=user_menu(is_admin(uid))
    )

    # Admin inline buttons
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("✅ CONFIRM", callback_data=f"confirm_{wid}"),
        InlineKeyboardButton("❌ REJECT", callback_data=f"reject_{wid}"),
        InlineKeyboardButton("🚫 BAN", callback_data=f"ban_{uid}"),
        InlineKeyboardButton("💣 BAN-MONEY", callback_data=f"banmoney_{uid}")
    )
    bot.send_message(ADMIN_ID,
        f"💳 NEW WITHDRAWAL\n👤 User: {uid}\n🤖 BOT ID: {users[uid]['bot_id']}\n👥 Referrals: {users[uid]['invited']}\n💵 Amount: ${amt:.2f}\n🧾 Request ID: {wid}\n🏦 Address: {addr}",
        reply_markup=markup
                    )

    # ================= ADMIN CALLBACKS =================
@bot.callback_query_handler(func=lambda call: call.data.startswith(("confirm_","reject_","ban_","banmoney_","unblock_")))
def admin_callbacks(call):
    data = call.data
    # ================= CONFIRM WITHDRAWAL =================
    if data.startswith("confirm_"):
        wid = int(data.split("_")[1])
        w = next((x for x in withdraws if x["id"]==wid), None)
        if not w or w["status"] != "pending":
            bot.answer_callback_query(call.id,"❌ Already processed")
            return
        w["status"] = "paid"
        uid = w["user"]
        users[uid]["pending"] -= w["amount"]
        save_users(); save_withdraws()
        bot.answer_callback_query(call.id,"✅ Confirmed")
        bot.send_message(int(uid), f"✅ Withdrawal #{wid} approved!\n💰 Pending: ${users[uid]['pending']:.2f}")

    # ================= REJECT WITHDRAWAL =================
    elif data.startswith("reject_"):
        wid = int(data.split("_")[1])
        w = next((x for x in withdraws if x["id"]==wid), None)
        if not w or w["status"] != "pending":
            bot.answer_callback_query(call.id,"❌ Already processed")
            return
        w["status"] = "rejected"
        uid = w["user"]
        users[uid]["balance"] += w["amount"]
        users[uid]["pending"] -= w["amount"]
        save_users(); save_withdraws()
        bot.answer_callback_query(call.id,"❌ Rejected")
        bot.send_message(int(uid), f"❌ Withdrawal #{wid} rejected!\n💰 Balance: ${users[uid]['balance']:.2f}\n✋️ Pending: ${users[uid]['pending']:.2f}")

    # ================= BAN USER =================
    elif data.startswith("ban_"):
        uid = data.split("_")[1]
        if uid in users:
            users[uid]["banned"] = True
            save_users()
            bot.answer_callback_query(call.id,"🚫 User banned")
            bot.send_message(int(uid),"🚫 You are banned by admin!")

    # ================= BAN MONEY =================
    elif data.startswith("banmoney_"):
        uid = data.split("_")[1]
        if uid in users:
            # Create 5-digit code
            code = str(random.randint(10000,99999))
            users[uid]["ban_money_code"] = code
            users[uid]["blocked"] += users[uid].get("pending",0.0)
            users[uid]["pending"] = 0.0
            save_users()
            bot.answer_callback_query(call.id,"💣 Money Blocked with Code")
            bot.send_message(int(uid), f"🚫 Your money has been blocked by admin!\n💣 Code: {code}")

    # ================= UNBLOCK MONEY =================
    elif data.startswith("unblock_"):
        uid = data.split("_")[1]
        if uid in users:
            # Reset blocked money
            users[uid]["balance"] += users[uid].get("blocked",0.0)
            users[uid]["blocked"] = 0.0
            save_users()
            bot.answer_callback_query(call.id,"💰 Money Unblocked")
            bot.send_message(int(uid), f"💰 Your blocked money has been unblocked by admin!")

# ================= ADMIN PANEL =================
@bot.message_handler(func=lambda m: m.text=="👑 ADMIN PANEL")
def admin_panel_btn(m):
    if not is_admin(m.from_user.id):
        bot.send_message(m.chat.id,"❌ You are not admin")
        return
    bot.send_message(m.chat.id,"👑 Admin Menu", reply_markup=admin_panel_menu())

# ================= BACK MAIN MENU =================
@bot.message_handler(func=lambda m: m.text=="🔙 BACK MAIN MENU")
def back_main(m):
    uid = str(m.from_user.id)
    if banned_guard(m): return
    bot.send_message(m.chat.id, "🏠 Main Menu", reply_markup=user_menu(is_admin(uid)))

# ================= ADD BALANCE =================
@bot.message_handler(func=lambda m: m.text=="➕ ADD BALANCE")
def add_balance(m):
    if not is_admin(m.from_user.id): return
    msg = bot.send_message(m.chat.id,"Send BOT ID / Telegram ID and amount to ADD\nExample: 12345678901 2.5")
    bot.register_next_step_handler(msg, add_balance_step)

def add_balance_step(m):
    if not is_admin(m.from_user.id): return
    try:
        uid_or_bid, amt = m.text.split()
        amt = float(amt)
    except:
        return bot.send_message(m.chat.id,"❌ Invalid format! Use: BOT_ID / Telegram_ID AMOUNT")

    uid = uid_or_bid if uid_or_bid in users else find_user_by_botid(uid_or_bid)
    if not uid:
        return bot.send_message(m.chat.id,"❌ User not found")

    users[uid]["balance"] += amt
    save_users()
    bot.send_message(int(uid), f"💰 Admin added ${amt:.2f} to your balance!")
    bot.send_message(m.chat.id, f"✅ Added ${amt:.2f} to user {uid}")

# ================= REMOVE MONEY =================
@bot.message_handler(func=lambda m: m.text=="➖ REMOVE MONEY")
def remove_money(m):
    if not is_admin(m.from_user.id): return
    msg = bot.send_message(m.chat.id,"Send BOT ID / Telegram ID and amount to REMOVE\nExample: 12345678901 1.5")
    bot.register_next_step_handler(msg, remove_money_step)

def remove_money_step(m):
    if not is_admin(m.from_user.id): return
    try:
        uid_or_bid, amt = m.text.split()
        amt = float(amt)
    except:
        return bot.send_message(m.chat.id,"❌ Invalid format! Use: BOT_ID / Telegram_ID AMOUNT")

    uid = uid_or_bid if uid_or_bid in users else find_user_by_botid(uid_or_bid)
    if not uid:
        return bot.send_message(m.chat.id,"❌ User not found")
    if users[uid]["balance"] < amt:
        return bot.send_message(m.chat.id,"❌ Insufficient balance")

    users[uid]["balance"] -= amt
    save_users()
    bot.send_message(int(uid), f"💸 Admin removed ${amt:.2f} from your balance!")
    bot.send_message(m.chat.id, f"✅ Removed ${amt:.2f} from user {uid}")

# ================= UNBAN USER =================
@bot.message_handler(func=lambda m: m.text=="✅ UNBAN USER")
def unban_start(m):
    if not is_admin(m.from_user.id): return
    msg = bot.send_message(m.chat.id,"Send BOT ID / Telegram ID to UNBAN")
    bot.register_next_step_handler(msg, unban_process)

def unban_process(m):
    if not is_admin(m.from_user.id): return
    text = m.text.strip()
    uid = text if text in users else find_user_by_botid(text)
    if not uid:
        return bot.send_message(m.chat.id,"❌ User not found")

    users[uid]["banned"] = False
    if "ban_money_code" in users[uid]:
        del users[uid]["ban_money_code"]
    users[uid]["blocked"] = 0.0
    save_users()
    bot.send_message(int(uid),"✅ You are unbanned and blocked money cleared!")
    bot.send_message(m.chat.id,"✅ User unbanned successfully")

# ================= BROADCAST =================
@bot.message_handler(func=lambda m: m.text=="📢 BROADCAST")
def broadcast_start(m):
    if not is_admin(m.from_user.id): return
    msg = bot.send_message(m.chat.id,"📢 Send message / photo / video / link to broadcast")
    bot.register_next_step_handler(msg, broadcast_send)

def broadcast_send(m):
    if not is_admin(m.from_user.id): return
    sent, failed = 0, 0
    for uid in users:
        try:
            if m.content_type == 'text':
                bot.send_message(int(uid), m.text)
            elif m.content_type == 'photo':
                bot.send_photo(int(uid), m.photo[-1].file_id, caption=m.caption)
            elif m.content_type == 'video':
                bot.send_video(int(uid), m.video.file_id, caption=m.caption)
            elif m.content_type == 'document':
                bot.send_document(int(uid), m.document.file_id, caption=m.caption)
            else:
                bot.send_message(int(uid),"📢 New message available!")
            sent += 1
        except:
            failed += 1
    bot.send_message(m.chat.id,f"✅ Broadcast Finished\n📤 Sent: {sent}\n❌ Failed: {failed}")

# ================= MEDIA DOWNLOADER =================
def send_video_with_music(chat_id, file):
    """
    Video user-ka loo diro kadib download,
    isla markaana Music button lagu daro.
    """
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🎵 MUSIC", callback_data=f"music|{file}"))
    bot.send_video(
        chat_id,
        open(file, "rb"),
        caption="Downloaded by @Downloadvedioytibot",
        reply_markup=kb
    )

def download_media(chat_id, url):
    """
    Download TikTok / YouTube media.
    TikTok: images ama video
    YouTube: video mp4
    """
    try:
        # ===== TIKTOK =====
        if "tiktok.com" in url:
            res = requests.get(f"https://tikwm.com/api/?url={url}", timeout=20).json()
            if res.get("code") == 0:
                data = res["data"]

                # Images
                if data.get("images"):
                    for i, img in enumerate(data["images"], 1):
                        img_data = requests.get(img, timeout=20).content
                        filename = f"tt_{i}.jpg"
                        with open(filename, "wb") as f:
                            f.write(img_data)
                        bot.send_photo(chat_id, open(filename, "rb"), caption=f"📸 Photo {i}")
                        os.remove(filename)
                    return

                # Video
                if data.get("play"):
                    vid_data = requests.get(data["play"], timeout=60).content
                    with open("tt_video.mp4", "wb") as f:
                        f.write(vid_data)
                    send_video_with_music(chat_id, "tt_video.mp4")
                    return

        # ===== YOUTUBE =====
        if "youtube.com" in url or "youtu.be" in url:
            ydl_opts = {
                "outtmpl": "youtube.%(ext)s",
                "format": "mp4",
                "quiet": True
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                file = ydl.prepare_filename(info)
            send_video_with_music(chat_id, file)
            return

        bot.send_message(chat_id, "❌ Unsupported link")

    except Exception as e:
        bot.send_message(chat_id, f"Download error: {e}")

# ================= MUSIC BUTTON =================
@bot.callback_query_handler(func=lambda call: call.data.startswith("music|"))
def convert_music(call):
    """
    Convert downloaded video MP4 → MP3 audio
    """
    file = call.data.split("|")[1]
    audio = file.replace(".mp4", ".mp3")
    try:
        subprocess.run(
            ["ffmpeg","-i",file,"-vn","-ab","128k","-ar","44100",audio],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("📢 BOT CHANNEL", url="https://t.me/tiktokvediodownload"))

        bot.send_audio(
            call.message.chat.id,
            open(audio,"rb"),
            title="Downloaded Music",
            performer="Downloadvedioytibot",
            caption="Downloaded via @Downloadvedioytibot",
            reply_markup=kb
        )

        os.remove(audio)

    except:
        bot.send_message(call.message.chat.id,"❌ Music conversion failed")

# ================= LINK HANDLER =================
@bot.message_handler(func=lambda m: m.text and "http" in m.text)
def handle_links(message):
    bot.send_message(message.chat.id,"⏳ Downloading...")
    download_media(message.chat.id, message.text)

# ================= RUN BOT =================
if __name__ == "__main__":
    print("🤖 Bot is running...")
    bot.infinity_polling(skip_pending=True)
