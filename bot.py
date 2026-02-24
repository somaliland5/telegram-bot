# ================= BOT PART 1/4 =================
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
    return str(random.randint(1000000000, 9999999999))

def random_botid():
    return str(random.randint(10000000000, 99999999999))

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
    kb.add("💰 BALANCE", "💸 WITHDRAWAL")
    kb.add("👥 REFERRAL", "🆔 GET ID")
    kb.add("☎️ CUSTOMER")
    if show_admin:
        kb.add("👑 ADMIN PANEL")
    return kb

def admin_panel_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("➕ ADD BALANCE", "➖ MINUS MONEY")
    kb.add("✅ UNBAN USER", "💳 UNBLOCK MONEY")
    kb.add("📊 STATS", "📢 BROADCAST", "💳 WITHDRAWAL CHECK")
    kb.add("🔙 BACK TO MAIN MENU")
    return kb

# ================= START HANDLER =================
@bot.message_handler(commands=['start'])
def start(m):
    uid = str(m.from_user.id)
    args = m.text.split()
    
    # New user registration
    if uid not in users:
        ref = args[1] if len(args) > 1 else None
        users[uid] = {
            "balance": 0.0,
            "pending": 0.0,
            "blocked": 0.0,
            "ref": random_ref(),
            "bot_id": random_botid(),
            "invited": 0,
            "banned": False,
            "month": now_month()
        }
        # Referral reward
        if ref:
            for u in users:
                if users[u]["ref"] == ref:
                    users[u]["balance"] += 0.2
                    users[u]["invited"] += 1
                    bot.send_message(int(u), "🎉 You earned $0.2 from referral.")
                    break
        save_users()
    
    # Show user menu; admin sees extra button
    bot.send_message(
        m.chat.id,
        "👋 Welcome! Send a video link to download 🎬",
        reply_markup=user_menu(is_admin(uid))
    )

# ================= BACK MAIN MENU =================
def back_main_menu(chat_id, uid, context=None):
    """
    context=None or "user" → user menu
    context="admin" → admin panel
    """
    if is_admin(uid) and context == "admin":
        bot.send_message(chat_id, "👑 Admin Panel", reply_markup=admin_panel_menu())
    else:
        bot.send_message(chat_id, "🏠 Main Menu", reply_markup=user_menu(is_admin(uid)))

@bot.message_handler(func=lambda m: m.text=="🔙 BACK TO MAIN MENU")
def back_main(m):
    uid = str(m.from_user.id)
    if banned_guard(m): return
    if is_admin(uid):
        back_main_menu(m.chat.id, uid, context="admin")
    else:
        back_main_menu(m.chat.id, uid, context="user")

# ================= BOT PART 2/4 =================
# ================= BALANCE =================
@bot.message_handler(func=lambda m: m.text=="💰 BALANCE")
def balance(m):
    if banned_guard(m): return
    uid = str(m.from_user.id)
    bal = users[uid]["balance"]
    pending = users[uid].get("pending", 0.0)
    blocked = users[uid].get("blocked", 0.0)
    bot.send_message(
        m.chat.id,
        f"💰 Available: ${bal:.2f}\n✋️ Pending: ${pending:.2f}\n🚫 Blocked: ${blocked:.2f}"
    )

# ================= GET ID =================
@bot.message_handler(func=lambda m: m.text=="🆔 GET ID")
def get_id(m):
    if banned_guard(m): return
    uid = str(m.from_user.id)
    bot.send_message(
        m.chat.id,
        f"🆔 BOT ID: <code>{users[uid]['bot_id']}</code>\n👤 Telegram ID: <code>{uid}</code>"
    )

# ================= REFERRAL =================
@bot.message_handler(func=lambda m: m.text=="👥 REFERRAL")
def referral(m):
    if banned_guard(m): return
    uid = str(m.from_user.id)
    link = f"https://t.me/{bot.get_me().username}?start={users[uid]['ref']}"
    invited = users[uid].get("invited", 0)
    bot.send_message(
        m.chat.id,
        f"🔗 Your referral link:\n{link}\n👥 Invited: {invited}\n\n"
        "🎁 Each new user who joins using your link will automatically give you $0.2!"
    )

# ================= CUSTOMER SUPPORT =================
@bot.message_handler(func=lambda m: m.text=="☎️ CUSTOMER")
def customer(m):
    if banned_guard(m): return
    bot.send_message(m.chat.id,"📞 Contact support: @scholes1")

# ================= WITHDRAWAL MENU =================
@bot.message_handler(func=lambda m: m.text=="💸 WITHDRAWAL")
def withdraw_menu(m):
    if banned_guard(m): return
    uid = str(m.from_user.id)
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("USDT-BEP20")
    kb.add("🔙 CANCEL")
    bot.send_message(m.chat.id,"Select withdrawal method:", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text in ["USDT-BEP20","🔙 CANCEL"])
def withdraw_method(m):
    uid = str(m.from_user.id)
    if banned_guard(m): return
    if m.text=="🔙 CANCEL":
        back_main_menu(m.chat.id, uid, context="user")
        return
    if m.text=="USDT-BEP20":
        kb = ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add("🔙 CANCEL")
        msg = bot.send_message(
            m.chat.id,
            "Enter your USDT BEP20 address (must start with 0x) or press 🔙 CANCEL",
            reply_markup=kb
        )
        bot.register_next_step_handler(msg, withdraw_address)

def withdraw_address(m):
    uid = str(m.from_user.id)
    if banned_guard(m): return
    text = (m.text or "").strip()
    if text=="🔙 CANCEL":
        back_main_menu(m.chat.id, uid, context="user")
        return
    if not text.startswith("0x"):
        kb = ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add("🔙 CANCEL")
        msg = bot.send_message(
            m.chat.id,
            "❌ Invalid address. Must start with 0x. Try again or press 🔙 CANCEL",
            reply_markup=kb
        )
        bot.register_next_step_handler(msg, withdraw_address)
        return
    users[uid]["temp_addr"] = text
    save_users()
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🔙 CANCEL")
    msg = bot.send_message(
        m.chat.id,
        f"Enter withdrawal amount\nMinimum: $1 | Balance: ${users[uid]['balance']:.2f}\nOr press 🔙 CANCEL",
        reply_markup=kb
    )
    bot.register_next_step_handler(msg, withdraw_amount)

def withdraw_amount(m):
    uid = str(m.from_user.id)
    if banned_guard(m): return
    text = (m.text or "").strip()
    if text=="🔙 CANCEL":
        back_main_menu(m.chat.id, uid, context="user")
        return
    try:
        amt = float(text)
    except:
        kb = ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add("🔙 CANCEL")
        msg = bot.send_message(m.chat.id,"❌ Invalid amount. Enter a number:", reply_markup=kb)
        bot.register_next_step_handler(msg, withdraw_amount)
        return
    if amt < 1:
        kb = ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add("🔙 CANCEL")
        msg = bot.send_message(m.chat.id,"❌ Minimum withdrawal is $1", reply_markup=kb)
        bot.register_next_step_handler(msg, withdraw_amount)
        return
    if users[uid]["balance"] < amt:
        kb = ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add("🔙 CANCEL")
        msg = bot.send_message(m.chat.id,"❌ Insufficient balance", reply_markup=kb)
        bot.register_next_step_handler(msg, withdraw_amount)
        return
    # Save withdrawal request
    wid = len(withdraws)+1
    withdraws.append({
        "id": wid,
        "user": uid,
        "amount": amt,
        "address": users[uid]["temp_addr"],
        "status": "pending"
    })
    users[uid]["balance"] -= amt
    users[uid]["pending"] += amt
    users[uid].pop("temp_addr", None)
    save_users()
    save_withdraws()
    bot.send_message(m.chat.id,f"✅ Withdrawal request submitted!\nID: {wid}\nAmount: ${amt:.2f}\nStatus: Pending")

# ================= BOT PART 3/4 =================
# ================= ADMIN PANEL CALLBACKS =================
@bot.callback_query_handler(func=lambda call: call.data.startswith(("confirm_","reject_","ban_","banmoney_")))
def admin_callbacks(call):
    data = call.data
    uid_admin = str(call.from_user.id)
    if not is_admin(uid_admin):
        bot.answer_callback_query(call.id, "❌ You are not admin")
        return

    # ===== CONFIRM WITHDRAWAL =====
    if data.startswith("confirm_"):
        wid = int(data.split("_")[1])
        w = next((x for x in withdraws if x["id"]==wid), None)
        if not w or w["status"]!="pending":
            bot.answer_callback_query(call.id,"❌ Already processed")
            return
        w["status"] = "paid"
        uid = w["user"]
        users[uid]["pending"] -= w["amount"]
        save_users(); save_withdraws()
        bot.answer_callback_query(call.id,"✅ Withdrawal Confirmed")
        bot.send_message(int(uid),f"✅ Your withdrawal #{wid} of ${w['amount']:.2f} is approved and paid!")

    # ===== REJECT WITHDRAWAL =====
    elif data.startswith("reject_"):
        wid = int(data.split("_")[1])
        w = next((x for x in withdraws if x["id"]==wid), None)
        if not w or w["status"]!="pending":
            bot.answer_callback_query(call.id,"❌ Already processed")
            return
        w["status"] = "rejected"
        uid = w["user"]
        users[uid]["balance"] += w["amount"]
        users[uid]["pending"] -= w["amount"]
        save_users(); save_withdraws()
        bot.answer_callback_query(call.id,"❌ Withdrawal Rejected")
        bot.send_message(int(uid),f"❌ Your withdrawal #{wid} of ${w['amount']:.2f} has been rejected. Funds returned to balance.")

    # ===== BAN USER =====
    elif data.startswith("ban_"):
        uid = data.split("_")[1]
        if uid in users:
            users[uid]["banned"] = True
            save_users()
            bot.answer_callback_query(call.id,"🚫 User Banned")
            bot.send_message(int(uid),"🚫 You have been banned by admin.")

    # ===== BLOCK MONEY =====
    elif data.startswith("banmoney_"):
        wid = int(data.split("_")[1])
        w = next((x for x in withdraws if x["id"]==wid), None)
        if not w or w["status"]!="pending":
            bot.answer_callback_query(call.id,"❌ Already processed")
            return
        uid = w["user"]
        amt = w["amount"]
        users[uid]["pending"] -= amt
        users[uid]["blocked"] = users[uid].get("blocked",0.0)+amt
        w["status"] = "blocked"
        code = str(random.randint(1000,9999))
        w["block_code"] = code
        save_users(); save_withdraws()
        bot.answer_callback_query(call.id,"💰 Money Blocked")
        bot.send_message(int(uid),f"🚫 Your ${amt:.2f} is blocked.\n💳 Block Code: {code}")

# ================= ADD BALANCE =================
@bot.message_handler(func=lambda m: m.text=="➕ ADD BALANCE")
def add_balance(m):
    if not is_admin(m.from_user.id): return
    msg = bot.send_message(m.chat.id,"Send BOT ID or Telegram ID and amount to ADD\nExample: 12345678901 2.5")
    bot.register_next_step_handler(msg, add_balance_step)

def add_balance_step(m):
    if not is_admin(m.from_user.id): return
    try:
        uid_or_bid, amt = m.text.split()
        amt = float(amt)
    except:
        return bot.send_message(m.chat.id,"❌ Invalid format! Use: BOT_ID/Telegram_ID AMOUNT")
    uid = uid_or_bid if uid_or_bid in users else find_user_by_botid(uid_or_bid)
    if not uid: return bot.send_message(m.chat.id,"❌ User not found")
    users[uid]["balance"] += amt
    save_users()
    bot.send_message(int(uid), f"💰 Admin added ${amt:.2f} to your balance!")
    bot.send_message(m.chat.id, f"✅ Added ${amt:.2f} to user {uid}")

# ================= MINUS MONEY =================
@bot.message_handler(func=lambda m: m.text=="➖ MINES MONEY")
def remove_money(m):
    if not is_admin(m.from_user.id): return
    msg = bot.send_message(m.chat.id,"Send BOT ID or Telegram ID and amount to REMOVE\nExample: 12345678901 1.5")
    bot.register_next_step_handler(msg, remove_money_step)

def remove_money_step(m):
    if not is_admin(m.from_user.id): return
    try:
        uid_or_bid, amt = m.text.split()
        amt = float(amt)
    except:
        return bot.send_message(m.chat.id,"❌ Invalid format! Use: BOT_ID/Telegram_ID AMOUNT")
    uid = uid_or_bid if uid_or_bid in users else find_user_by_botid(uid_or_bid)
    if not uid: return bot.send_message(m.chat.id,"❌ User not found")
    if users[uid]["balance"] < amt: return bot.send_message(m.chat.id,"❌ Insufficient balance")
    users[uid]["balance"] -= amt
    save_users()
    bot.send_message(int(uid), f"💸 Admin removed ${amt:.2f} from your balance!")
    bot.send_message(m.chat.id, f"✅ Removed ${amt:.2f} from user {uid}")

# ================= UNBAN USER =================
@bot.message_handler(func=lambda m: m.text=="✅ UNBAN USER")
def unban_start(m):
    if not is_admin(m.from_user.id): return
    msg = bot.send_message(m.chat.id,"Send BOT ID or Telegram ID to UNBAN")
    bot.register_next_step_handler(msg, unban_process)

def unban_process(m):
    if not is_admin(m.from_user.id): return
    text = m.text.strip()
    uid = text if text in users else find_user_by_botid(text)
    if not uid: return bot.send_message(m.chat.id,"❌ User not found")
    users[uid]["banned"] = False
    save_users()
    bot.send_message(int(uid),"✅ You are unbanned. You can use the bot again.")
    bot.send_message(m.chat.id,"✅ User unbanned successfully")

# ================= UNBLOCK MONEY =================
@bot.message_handler(func=lambda m: m.text=="💳 UNBLOCK MONEY")
def unblock_money_start(m):
    if not is_admin(m.from_user.id): return
    msg = bot.send_message(m.chat.id,"Send 4-digit Block Code to UNBLOCK money")
    bot.register_next_step_handler(msg, unblock_money_process)

def unblock_money_process(m):
    if not is_admin(m.from_user.id): return
    code = m.text.strip()
    w = next((x for x in withdraws if x.get("block_code") == code), None)
    if not w: return bot.send_message(m.chat.id,"❌ Invalid Block Code")
    uid = w["user"]
    amt = w["amount"]
    users[uid]["balance"] += amt
    users[uid]["blocked"] -= amt
    w["status"] = "unblocked"
    w.pop("block_code", None)
    save_users(); save_withdraws()
    bot.send_message(int(uid), f"✅ Your blocked ${amt:.2f} is now available in balance!")
    bot.send_message(m.chat.id, f"✅ Money unblocked for user {uid}")

# ================= BOT PART 4/4 =================
# ================= STATS =================
@bot.message_handler(func=lambda m: m.text=="📊 STATS")
def admin_stats(m):
    if not is_admin(m.from_user.id): return
    total_users = len(users)
    total_balance = sum(u.get("balance",0) for u in users.values())
    total_pending = sum(u.get("pending",0) for u in users.values())
    total_blocked = sum(u.get("blocked",0) for u in users.values())
    total_paid = sum(w["amount"] for w in withdraws if w["status"]=="paid")
    banned_users = sum(1 for u in users.values() if u.get("banned"))
    msg = (
        f"📊 <b>ADMIN STATS</b>\n\n"
        f"👥 TOTAL USERS: {total_users}\n"
        f"💰 TOTAL BALANCE: ${total_balance:.2f}\n"
        f"✋️ PENDING: ${total_pending:.2f}\n"
        f"🚫 BLOCKED: ${total_blocked:.2f}\n"
        f"💵 TOTAL WITHDRAWAL PAID: ${total_paid:.2f}\n"
        f"🚫 BANNED USERS: {banned_users}"
    )
    bot.send_message(m.chat.id, msg)

# ================= BROADCAST =================
@bot.message_handler(func=lambda m: m.text=="📢 BROADCAST")
def admin_broadcast(m):
    if not is_admin(m.from_user.id): return
    msg = bot.send_message(m.chat.id,"Send the message you want to broadcast to all users:")
    bot.register_next_step_handler(msg, broadcast_send)

def broadcast_send(m):
    if not is_admin(m.from_user.id): return
    text = m.text
    count = 0
    for uid in users:
        try:
            bot.send_message(int(uid), text)
            count += 1
        except: pass
    bot.send_message(m.chat.id, f"✅ Broadcast sent to {count} users.")

# ================= WITHDRAWAL CHECK =================
@bot.message_handler(func=lambda m: m.text=="💳 WITHDRAWAL CHECK")
def admin_withdrawals(m):
    if not is_admin(m.from_user.id): return
    if not withdraws:
        return bot.send_message(m.chat.id,"No withdrawals yet.")
    msg = "<b>Pending Withdrawals:</b>\n\n"
    for w in withdraws:
        if w["status"]=="pending":
            msg += f"🧾 ID: {w['id']} | User: {w['user']} | Amount: ${w['amount']:.2f} | Address: {w['address']}\n"
    bot.send_message(m.chat.id, msg or "No pending withdrawals.")

# ================= MEDIA DOWNLOADER =================
def send_video_with_music(chat_id, file):
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🎵 MUSIC", callback_data=f"music|{file}"))
    bot.send_video(chat_id, open(file,"rb"), caption="Downloaded by @Downloadvedioytibot", reply_markup=kb)

def download_media(chat_id, url):
    try:
        # ===== TIKTOK =====
        if "tiktok.com" in url:
            res = requests.get(f"https://tikwm.com/api/?url={url}", timeout=20).json()
            if res.get("code")==0:
                data = res["data"]
                # Images
                if data.get("images"):
                    for i,img in enumerate(data["images"],1):
                        img_data = requests.get(img, timeout=20).content
                        filename = f"tt_{i}.jpg"
                        with open(filename,"wb") as f: f.write(img_data)
                        bot.send_photo(chat_id, open(filename,"rb"), caption=f"📸 Photo {i}")
                        os.remove(filename)
                    return
                # Video
                if data.get("play"):
                    vid_data = requests.get(data["play"], timeout=60).content
                    with open("tt_video.mp4","wb") as f: f.write(vid_data)
                    send_video_with_music(chat_id, "tt_video.mp4")
                    return
        # ===== YOUTUBE =====
        if "youtube.com" in url or "youtu.be" in url:
            ydl_opts = {"outtmpl":"youtube.%(ext)s","format":"mp4","quiet":True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                file = ydl.prepare_filename(info)
            send_video_with_music(chat_id, file)
            return
        bot.send_message(chat_id,"❌ Unsupported link")
    except Exception as e:
        bot.send_message(chat_id,f"Download error: {e}")

# ================= MUSIC CONVERSION =================
@bot.callback_query_handler(func=lambda call: call.data.startswith("music|"))
def convert_music(call):
    file = call.data.split("|")[1]
    audio = file.replace(".mp4",".mp3")
    try:
        subprocess.run(
            ["ffmpeg","-i",file,"-vn","-ab","128k","-ar","44100",audio],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
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
