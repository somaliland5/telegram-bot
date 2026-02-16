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
    bot.send_message(m.chat.id,"👋 Welcome! To Vedio Downloader Download Video Using Link Or shere 🎬🫵", 
    reply_markup=user_menu(is_admin(uid)))
                     
# ================= BALANCE =================
@bot.message_handler(func=lambda m: m.text=="💰 BALANCE")
def balance(m):
    if banned_guard(m): return
    uid = str(m.from_user.id)
    bal = users[uid]["balance"]
    blk = users[uid].get("blocked",0.0)
    bot.send_message(m.chat.id, f"💰 Available: ${bal:.2f}\n⏰️ Blocked: ${blk:.2f}")

# ================= GET ID =================
@bot.message_handler(func=lambda m: m.text=="🆔 GET ID")
def get_id(m):
    if banned_guard(m): return
    uid = str(m.from_user.id)
    bot.send_message(m.chat.id, f"🆔 BOT ID: <code>{users[uid]['bot_id']}</code>\n👤 Telegram ID: <code>{uid}</code>")

# ================= REFERRAL =================
from telebot.types import ReplyKeyboardMarkup

@bot.message_handler(func=lambda m: m.text=="👥 REFERRAL")
def referral(m):
    if banned_guard(m):
        return
    uid = str(m.from_user.id)

    # Samee referral link gaar ah
    link = f"https://t.me/{bot.get_me().username}?start={users[uid]['ref']}"

    # Tirada dadka uu casuumay
    invited = users[uid].get("invited", 0)

    # Fariinta user-ka
    msg_text = (
        f"🔗 Your referral link:\n{link}\n"
        f"👥 Invited: {invited}\n\n"
        f"🎁 Each new user who joins using your link will automatically give you $0.2!"
    )

    # Buttonka dib ugu noqo Main Menu
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🔙 BACK MAIN MENU")

    bot.send_message(m.chat.id, msg_text, reply_markup=kb)

# ================= CUSTOMER =================
@bot.message_handler(func=lambda m: m.text=="☎️ CUSTOMER")
def customer(m):
    if banned_guard(m): return
    bot.send_message(m.chat.id,"Contact support: @scholes1")

# ================= WITHDRAWAL =================
from telebot.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton

@bot.message_handler(func=lambda m: m.text == "💸 WITHDRAWAL")
def withdraw_menu(m):
    if banned_guard(m): return
    uid = str(m.from_user.id)
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("USDT-BEP20")
    kb.add("🔙 CANCEL")
    bot.send_message(m.chat.id, "Select withdrawal method:", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text in ["USDT-BEP20", "🔙 CANCEL"])
def withdraw_method(m):
    uid = str(m.from_user.id)
    if m.text == "🔙 CANCEL":
        back_main_menu(m.chat.id, uid)
        return
    if m.text == "USDT-BEP20":
        msg = bot.send_message(m.chat.id,"Enter your USDT BEP20 address (must start with 0x) or press 🔙 CANCEL")
        bot.register_next_step_handler(msg, withdraw_address)

def withdraw_address(m):
    uid = str(m.from_user.id)
    text = (m.text or "").strip()
    if text == "🔙 CANCEL":
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
    if text == "🔙 CANCEL":
        back_main_menu(m.chat.id, uid)
        return
    try:
        amt = float(text)
    except:
        msg = bot.send_message(m.chat.id,"❌ Invalid number. Enter again or press 🔙 CANCEL")
        bot.register_next_step_handler(msg, withdraw_amount)
        return
    if amt < 1:
        msg = bot.send_message(m.chat.id,f"❌ Minimum withdrawal is $1\nBalance: ${users[uid]['balance']:.2f}\nTry again or press 🔙 CANCEL")
        bot.register_next_step_handler(msg, withdraw_amount)
        return
    if amt > users[uid]["balance"]:
        msg = bot.send_message(m.chat.id,f"❌ Insufficient balance\nBalance: ${users[uid]['balance']:.2f}\nTry again or press 🔙 CANCEL")
        bot.register_next_step_handler(msg, withdraw_amount)
        return
    wid = random.randint(10000,99999)
    addr = users[uid].pop("temp_addr")
    withdraws.append({"id":wid,"user":uid,"amount":amt,"blocked":amt,"address":addr,"status":"pending","time":str(datetime.now())})
    users[uid]["balance"] -= amt
    users[uid]["blocked"] = users[uid].get("blocked",0.0)+amt
    save_users(); save_withdraws()
    # ===== USER MSG =====
    bot.send_message(m.chat.id,
        f"✅ Withdrawal Request Sent\n🧾 Request ID: {wid}\n💵 Amount: ${amt:.2f}\n🏦 Address: {addr}\n💰 Balance Left: ${users[uid]['balance']:.2f}\n⏳ Status: Pending (6–12h)",
        reply_markup=user_menu(is_admin(uid))
    )
    # ===== ADMIN INLINE BUTTON MSG =====
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("✅ CONFIRM", callback_data=f"confirm_{wid}"),
        InlineKeyboardButton("❌ REJECT", callback_data=f"reject_{wid}"),
        InlineKeyboardButton("🚫 BAN", callback_data=f"ban_{uid}")
    )
    bot.send_message(ADMIN_ID,
        f"💳 NEW WITHDRAWAL\n\n👤 User: {uid}\n🤖 BOT ID: {users[uid]['bot_id']}\n👥 Referrals: {users[uid]['invited']}\n💵 Amount: ${amt:.2f}\n🧾 Request ID: {wid}\n🏦 Address: {addr}",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: True)
def admin_callbacks(call):
    data = call.data
    if data.startswith("confirm_"):
        wid = int(data.split("_")[1])
        w = next((x for x in withdraws if x["id"]==wid), None)
        if not w or w["status"] != "pending": return
        w["status"] = "paid"
        users[w["user"]]["blocked"] -= w["blocked"]
        save_users(); save_withdraws()
        bot.answer_callback_query(call.id,"✅ Confirmed")
        bot.send_message(int(w["user"]), f"✅ Withdrawal #{wid} approved!")
    elif data.startswith("reject_"):
        wid = int(data.split("_")[1])
        w = next((x for x in withdraws if x["id"]==wid), None)
        if not w or w["status"] != "pending": return
        w["status"] = "rejected"
        users[w["user"]]["balance"] += w["blocked"]
        users[w["user"]]["blocked"] -= w["blocked"]
        save_users(); save_withdraws()
        bot.answer_callback_query(call.id,"❌ Rejected")
        bot.send_message(int(w["user"]), f"❌ Withdrawal #{wid} rejected")
    elif data.startswith("ban_"):
        uid = data.split("_")[1]
        if uid in users:
            users[uid]["banned"] = True
            save_users()
            bot.answer_callback_query(call.id,"🚫 User banned")

# ================= ADMIN PANEL =================
@bot.message_handler(func=lambda m: m.text=="👑 ADMIN PANEL")
def admin_panel_btn(m):
    if not is_admin(m.from_user.id):
        bot.send_message(m.chat.id,"❌ You are not admin")
        return
    bot.send_message(m.chat.id,"👑 ADMIN PANEL", reply_markup=admin_menu())

@bot.message_handler(func=lambda m: m.text=="🔙 BACK MAIN MENU")
def back_main(m):
    back_main_menu(m.chat.id, str(m.from_user.id))

# ================= ADD BALANCE =================
@bot.message_handler(func=lambda m: m.text=="➕ ADD BALANCE")
def add_balance(m):
    # Hubi admin
    if not is_admin(m.from_user.id):
        return
    msg = bot.send_message(
        m.chat.id,
        "Send BOT ID and amount to add.\nExample: 12345678901 2.5"
    )
    bot.register_next_step_handler(msg, add_balance_step)


def add_balance_step(m):
    # Hubi admin
    if not is_admin(m.from_user.id):
        return

    try:
        bid, amt = m.text.split()
        amt = float(amt)
    except:
        return bot.send_message(
            m.chat.id,
            "❌ Invalid format! Please send like: BOT_ID AMOUNT"
        )

    # Hel user ka ku jira BOT ID
    uid = find_user_by_botid(bid)
    if not uid:
        return bot.send_message(m.chat.id, "❌ BOT ID not found!")

    # Cusbooneysii balance-ka
    users[uid]["balance"] += amt
    save_users()

    bot.send_message(int(uid), f"💰 Admin added ${amt:.2f} to your balance!")
    bot.send_message(m.chat.id, f"✅ Successfully added ${amt:.2f} to BOT ID {bid}")

# ================= WITHDRAWAL CHECK =================
@bot.message_handler(func=lambda m: m.text == "💳 WITHDRAWAL CHECK")
def withdrawal_check_start(m):
    if not is_admin(m.from_user.id):
        return

    msg = bot.send_message(
        m.chat.id,
        "Enter Withdrawal Request ID\nExample: 402000"
    )
    bot.register_next_step_handler(msg, withdrawal_check_process)


def withdrawal_check_process(m):
    if not is_admin(m.from_user.id):
        return

    try:
        wid = int(m.text.strip())
    except:
        bot.send_message(m.chat.id, "❌ Invalid Request ID")
        return

    # Raadi withdrawal-ka
    w = next((x for x in withdraws if x["id"] == wid), None)

    if not w:
        bot.send_message(m.chat.id, "❌ Request ID not found")
        return

    uid = w["user"]

    # Soo saar user info
    bot_id = users.get(uid, {}).get("bot_id", "Unknown")
    invited = users.get(uid, {}).get("invited", 0)

    msg_text = (
        f"💳 WITHDRAWAL DETAILS\n\n"
        f"🧾 Request ID: {w['id']}\n"
        f"👤 User ID: {uid}\n"
        f"🤖 BOT ID: {bot_id}\n"
        f"👥 Referrals: {invited}\n"
        f"💵 Amount: ${w['amount']:.2f}\n"
        f"🏦 Address: {w['address']}\n"
        f"📊 Status: {w['status'].upper()}\n"
        f"⏰ Time: {w['time']}"
    )

    bot.send_message(m.chat.id, msg_text)

# ================= UNBAN USER =================
@bot.message_handler(func=lambda m: m.text == "✅ UNBAN MONEY")
def unban_start(m):
    if not is_admin(m.from_user.id):
        return
    msg = bot.send_message(
        m.chat.id,
        "Send BOT ID or Telegram ID to UNBAN"
    )
    bot.register_next_step_handler(msg, unban_process)

def unban_process(m):
    if not is_admin(m.from_user.id):
        return

    text = m.text.strip()

    # ===== Try Telegram ID first =====
    if text in users:
        users[text]["banned"] = False
        save_users()

        bot.send_message(int(text), "✅ You are unbanned. You can use the bot again.")
        bot.send_message(m.chat.id, "✅ User unbanned successfully")
        return

    # ===== Try BOT ID =====
    uid = find_user_by_botid(text)
    if uid:
        users[uid]["banned"] = False
        save_users()

        bot.send_message(int(uid), "✅ You are unbanned. You can use the bot again.")
        bot.send_message(m.chat.id, f"✅ BOT ID {text} unbanned successfully")
        return

    bot.send_message(m.chat.id, "❌ User not found")

# ================= BROADCAST =================
@bot.message_handler(func=lambda m: m.text=="📢 BROADCAST")
def broadcast_start(m):
    if not is_admin(m.from_user.id): 
        return
    msg = bot.send_message(m.chat.id, "📢 Send message / photo / video / link to broadcast")
    bot.register_next_step_handler(msg, broadcast_send)

def broadcast_send(m):
    if not is_admin(m.from_user.id): 
        return

    sent = 0
    failed = 0

    # Loop over all users in your 'users' variable
    for uid in users:
        try:
            # Check the type of message
            if m.content_type == 'text':
                bot.send_message(int(uid), m.text)
            elif m.content_type == 'photo':
                bot.send_photo(int(uid), m.photo[-1].file_id, caption=m.caption)
            elif m.content_type == 'video':
                bot.send_video(int(uid), m.video.file_id, caption=m.caption)
            elif m.content_type == 'document':
                bot.send_document(int(uid), m.document.file_id, caption=m.caption)
            else:
                bot.send_message(int(uid), "📢 New message available!")
            sent += 1
        except:
            failed += 1

    bot.send_message(m.chat.id, f"✅ Broadcast Finished\n📤 Sent: {sent}\n❌ Failed: {failed}")

# ================= MEDIA DOWNLOADER =================
def send_video_with_music(chat_id, file):
    from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🎵 MUSIC", callback_data=f"music|{file}"))

    bot.send_video(
        chat_id,
        open(file, "rb"),
        caption="Downloaded by:\n@Downloadvedioytibot",
        reply_markup=kb
    )


def download_media(chat_id, url):
    try:
        # ================= TIKTOK (API FIRST) =================
        if "tiktok.com" in url:

            # ---- Try TikWM API (no watermark, photos + video) ----
            try:
                api = f"https://tikwm.com/api/?url={url}"
                res = requests.get(api, timeout=20).json()

                if res.get("code") == 0 and "data" in res:
                    data = res["data"]

                    # slideshow photos
                    if data.get("images"):
                        for img in data["images"]:
                            img_data = requests.get(img, timeout=20).content
                            with open("tt.jpg","wb") as f:
                                f.write(img_data)
                            bot.send_photo(chat_id, open("tt.jpg","rb"),
                                           caption="Downloaded by:\n@Downloadvedioytibot")
                            os.remove("tt.jpg")
                        return

                    # video no watermark
                    if data.get("play"):
                        vid_url = data["play"]
                        vid_data = requests.get(vid_url, timeout=60).content
                        with open("tt.mp4","wb") as f:
                            f.write(vid_data)
                        send_video_with_music(chat_id, "tt.mp4")
                        os.remove("tt.mp4")
                        return
            except:
                pass

            # ---- Fallback yt-dlp (video/shorts) ----
            try:
                ydl_opts = {
                    "outtmpl": "tiktok.%(ext)s",
                    "format": "mp4",
                    "quiet": True
                }
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    # slideshow entries fallback
                    if isinstance(info, dict) and info.get("entries"):
                        for entry in info["entries"]:
                            file = ydl.prepare_filename(entry)
                            bot.send_photo(chat_id, open(file,"rb"),
                                           caption="Downloaded by:\n@Downloadvedioytibot")
                            os.remove(file)
                    else:
                        file = ydl.prepare_filename(info)
                        send_video_with_music(chat_id, file)
                        os.remove(file)
                return
            except Exception as e:
                bot.send_message(chat_id, f"TikTok download error: {e}")
                return

        # ================= YOUTUBE =================
        if "youtube.com" in url or "youtu.be" in url:
            try:
                ydl_opts = {
                    "outtmpl": "youtube.%(ext)s",
                    "format": "mp4",
                    "quiet": True
                }
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    file = ydl.prepare_filename(info)

                send_video_with_music(chat_id, file)
                os.remove(file)
                return
            except Exception as e:
                bot.send_message(chat_id, f"YouTube download error: {e}")
                return

        bot.send_message(chat_id, "❌ Unsupported link")

    except Exception as e:
        bot.send_message(chat_id, f"Download error: {e}")

# ================= MUSIC BUTTON HANDLER =================
@bot.callback_query_handler(func=lambda call: call.data.startswith("music|"))
def convert_music(call):
    import subprocess
    file = call.data.split("|")[1]
    audio_file = file.replace(".mp4", ".mp3")
    try:
        subprocess.run(["ffmpeg", "-i", file, audio_file])
        bot.send_audio(call.message.chat.id, open(audio_file, "rb"))
        os.remove(audio_file)
    except Exception as e:
        bot.send_message(call.message.chat.id, "❌ Music conversion failed")

# ========= LINK HANDLER =========
@bot.message_handler(func=lambda m: "http" in m.text)
def handle_links(message):
    # 🚀 Reaction
    try:
        bot.set_message_reaction(
            chat_id=message.chat.id,
            message_id=message.message_id,
            reaction=[{"type": "emoji", "emoji": "❤️"}]
        )
    except:
        pass

    bot.send_message(message.chat.id, "⏳ Downloading...")
    download_media(message.chat.id, message.text)
