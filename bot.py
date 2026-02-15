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
def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=4)

USERS_FILE = "users.json"
WITHDRAWS_FILE = "withdraws.json"

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

# ================= START =================
@bot.message_handler(commands=['start'])
def start(m):
    uid = str(m.from_user.id)
    args = m.text.split()

    if uid not in users:
        ref = args[1] if len(args)>1 else None
        users[uid] = {
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
            for u in users:
                if users[u]["ref"] == ref:
                    users[u]["balance"] += 0.2
                    users[u]["invited"] += 1
                    bot.send_message(int(u),"🎉 Congratulations! You earned $0.2 from your referral.")
                    break
        save_users()

    bot.send_message(m.chat.id, "👋 Welcome to Media Downloader Bot!", 
                     reply_markup=user_menu(is_admin(uid)))

# ================= BAN CHECK =================
def banned_guard(m):
    uid = str(m.from_user.id)
    if uid in users and users[uid].get("banned"):
        bot.send_message(m.chat.id, "🚫 You are banned.")
        return True
    return False

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
    bot.send_message(m.chat.id, f"🆔 BOT ID: <code>{users[uid]['bot_id']}</code>\n👤 TELEGRAM ID: <code>{uid}</code>")

# ================= REFERRAL =================
@bot.message_handler(func=lambda m: m.text=="👥 REFERRAL")
def referral(m):
    if banned_guard(m): return
    uid = str(m.from_user.id)
    link = f"https://t.me/{bot.get_me().username}?start={users[uid]['ref']}"
    bot.send_message(m.chat.id, f"🔗 Your referral link:\n{link}\n👥 Invited: {users[uid].get('invited',0)}")

# ================= CUSTOMER =================
@bot.message_handler(func=lambda m: m.text=="☎️ CUSTOMER")
def customer(m):
    if banned_guard(m): return
    bot.send_message(m.chat.id, "Contact support: @scholes1")

# ================= WITHDRAWAL =================
@bot.message_handler(func=lambda m: m.text=="💸 WITHDRAWAL")
def withdraw_menu(m):
    if banned_guard(m): return
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("USDT-BEP20","🔙 BACK MAIN MENU")
    bot.send_message(m.chat.id, "Choose withdrawal type:", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text=="USDT-BEP20")
def withdraw_start(m):
    if banned_guard(m): return
    msg = bot.send_message(m.chat.id, "Enter USDT BEP20 address (must start with 0x):")
    bot.register_next_step_handler(msg, withdraw_address)

def withdraw_address(m):
    uid = str(m.from_user.id)
    # Haddii user-ka taabtay BACK
    if m.text == "🔙 BACK MAIN MENU":
        back_main_menu(m.chat.id, uid)
        return

    addr = (m.text or "").strip()
    if not addr.startswith("0x"):
        msg = bot.send_message(m.chat.id, "❌ Invalid address. Must start with 0x. Try again or tap 🔙 BACK MAIN MENU")
        bot.register_next_step_handler(msg, withdraw_address)
        return

    users[uid]["temp_addr"] = addr
    save_users()
    msg = bot.send_message(m.chat.id, f"Enter amount to withdraw (MIN: $1 | Balance: ${users[uid]['balance']:.2f})")
    bot.register_next_step_handler(msg, withdraw_amount)

def withdraw_amount(m):
    uid = str(m.from_user.id)
    # BACK button
    if m.text == "🔙 BACK MAIN MENU":
        back_main_menu(m.chat.id, uid)
        return

    try:
        amt = float(m.text)
    except:
        msg = bot.send_message(m.chat.id, "❌ Invalid amount. Enter number or tap 🔙 BACK MAIN MENU")
        bot.register_next_step_handler(msg, withdraw_amount)
        return

    if amt < 1:
        msg = bot.send_message(m.chat.id, "❌ AMOUNT YOU WITHDRAWAL MIN: 1\nOr tap 🔙 BACK MAIN MENU")
        bot.register_next_step_handler(msg, withdraw_amount)
        return

    if amt > users[uid]["balance"]:
        msg = bot.send_message(m.chat.id, "❌ Insufficient balance. Or tap 🔙 BACK MAIN MENU")
        bot.register_next_step_handler(msg, withdraw_amount)
        return

    # Haddii sax ah, sii wad
    wid = random.randint(10000,99999)
    addr = users[uid].pop("temp_addr", None)

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
    users[uid]["blocked"] = users[uid].get("blocked",0.0) + amt
    save_users()
    save_withdraws()

    bot.send_message(m.chat.id,
        f"✅ Request #{wid} Sent!\n"
        f"💵 Amount: ${amt:.2f}\n"
        f"💸 Fee (0.00%): -$0.00\n"
        f"🧾 Net Due: ${amt:.2f}\n"
        f"⏳ Your request is pending approval\n"
        f"🕒 Pending time: 6–12 hours\n"
        f"Please be patient 😕",
        reply_markup=user_menu(is_admin(uid))
                    )
    users[uid]["temp_addr"] = addr
    save_users()
    msg = bot.send_message(m.chat.id, f"Enter amount to withdraw (MIN: $1 | Balance: ${users[uid]['balance']:.2f})")
    bot.register_next_step_handler(msg, withdraw_amount)

def withdraw_amount(m):
    if banned_guard(m): return
    uid = str(m.from_user.id)
    try:
        amt = float(m.text)
    except:
        msg = bot.send_message(m.chat.id, "❌ Invalid amount. Enter number:")
        bot.register_next_step_handler(msg, withdraw_amount)
        return

    if amt < 1:
        msg = bot.send_message(m.chat.id, "❌ AMOUNT YOU WITHDRAWAL MIN: 1")
        bot.register_next_step_handler(msg, withdraw_amount)
        return

    if amt > users[uid]["balance"]:
        msg = bot.send_message(m.chat.id, "❌ Insufficient balance")
        bot.register_next_step_handler(msg, withdraw_amount)
        return

    wid = random.randint(10000,99999)
    addr = users[uid].pop("temp_addr", None)

    withdraws.append({
        "id": wid,
        "user": uid,
        "amount": amt,
        "blocked": amt,
        "address": addr,
        "status": "pending",
        "time": str(datetime.now())
    })
# ================= WITHDRAW =================
from datetime import datetime
import random

def back_main_menu(chat_id, uid):
    bot.send_message(chat_id, "🔙 Back to Main Menu", reply_markup=user_menu())

@bot.message_handler(func=lambda m: m.text=="💸 WITHDRAWAL")
def withdraw(m):
    uid = str(m.from_user.id)
    # Hubi balance min 1
    if users[uid]["balance"] < 1:
        bot.send_message(m.chat.id,"❌ Your balance is less than $1, cannot withdraw.")
        return

    # Tusaale menu button: USDT-BEP20 & BACK
    kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("USDT-BEP20")
    kb.add("🔙 BACK MAIN MENU")
    msg = bot.send_message(m.chat.id,"Select your withdrawal method:", reply_markup=kb)
    bot.register_next_step_handler(msg, withdraw_method)

def withdraw_method(m):
    uid = str(m.from_user.id)
    text = m.text

    if text == "🔙 BACK MAIN MENU":
        back_main_menu(m.chat.id, uid)
        return

    if text == "USDT-BEP20":
        msg = bot.send_message(m.chat.id, "Enter your USDT-BEP20 address (must start with 0x):")
        bot.register_next_step_handler(msg, withdraw_address)
        return

    bot.send_message(m.chat.id, "Invalid selection. Tap again.")
    withdraw(m)

def withdraw_address(m):
    uid = str(m.from_user.id)
    text = m.text.strip()

    if text == "🔙 BACK MAIN MENU":
        back_main_menu(m.chat.id, uid)
        return

    if not text.startswith("0x"):
        msg = bot.send_message(m.chat.id,"❌ Invalid address. Must start with 0x. Try again or tap 🔙 BACK MAIN MENU")
        bot.register_next_step_handler(msg, withdraw_address)
        return

    users[uid]["temp_addr"] = text
    save_users(users)
    msg = bot.send_message(m.chat.id,f"Enter withdrawal amount (MIN: $1 | Balance: ${users[uid]['balance']:.2f}):")
    bot.register_next_step_handler(msg, withdraw_amount)

def withdraw_amount(m):
    uid = str(m.from_user.id)
    text = m.text.strip()

    if text == "🔙 BACK MAIN MENU":
        back_main_menu(m.chat.id, uid)
        return

    try:
        amt = float(text)
    except:
        msg = bot.send_message(m.chat.id,"❌ Invalid amount. Enter a number or tap 🔙 BACK MAIN MENU")
        bot.register_next_step_handler(msg, withdraw_amount)
        return

    if amt < 1:
        msg = bot.send_message(m.chat.id,"❌ AMOUNT YOU WITHDRAWAL MIN: 1\nOr tap 🔙 BACK MAIN MENU")
        bot.register_next_step_handler(msg, withdraw_amount)
        return

    if amt > users[uid]["balance"]:
        msg = bot.send_message(m.chat.id,"❌ Insufficient balance. Or tap 🔙 BACK MAIN MENU")
        bot.register_next_step_handler(msg, withdraw_amount)
        return

    wid = random.randint(10000,99999)
    addr = users[uid].pop("temp_addr", None)

    withdraws = load_withdraws()
    withdraws.append({
        "id": wid,
        "user": uid,
        "amount": amt,
        "blocked": amt,
        "address": addr,
        "status": "pending",
        "time": str(datetime.now())
    })
    save_withdraws(withdraws)

    # Update user balance
    users[uid]["balance"] -= amt
    users[uid]["blocked"] = users[uid].get("blocked",0.0) + amt
    save_users(users)

    # Message user
    bot.send_message(m.chat.id,
        f"✅ Request #{wid} Sent!\n"
        f"💵 Amount: ${amt:.2f}\n"
        f"💸 Fee (0.00%): -$0.00\n"
        f"🧾 Net Due: ${amt:.2f}\n"
        f"⏳ Your request is pending approval\n"
# ================= WITHDRAW =================
from datetime import datetime
import random
import telebot

def back_main_menu(chat_id, uid):
    bot.send_message(chat_id, "🔙 Back to Main Menu", reply_markup=user_menu())

@bot.message_handler(func=lambda m: m.text=="💸 WITHDRAWAL")
def withdraw(m):
    uid = str(m.from_user.id)
    if users[uid]["balance"] < 1:
        bot.send_message(m.chat.id,"❌ Your balance is less than $1, cannot withdraw.")
        return

    kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("USDT-BEP20")
    kb.add("🔙 BACK MAIN MENU")
    msg = bot.send_message(m.chat.id,"Select your withdrawal method:", reply_markup=kb)
    bot.register_next_step_handler(msg, withdraw_method)

def withdraw_method(m):
    uid = str(m.from_user.id)
    text = m.text
    if text == "🔙 BACK MAIN MENU":
        back_main_menu(m.chat.id, uid)
        return
    if text == "USDT-BEP20":
        msg = bot.send_message(m.chat.id, "Enter your USDT-BEP20 address (must start with 0x):")
        bot.register_next_step_handler(msg, withdraw_address)
        return
    bot.send_message(m.chat.id, "Invalid selection. Tap again.")
    withdraw(m)

def withdraw_address(m):
    uid = str(m.from_user.id)
    text = m.text.strip()
    if text == "🔙 BACK MAIN MENU":
        back_main_menu(m.chat.id, uid)
        return
    if not text.startswith("0x"):
        msg = bot.send_message(m.chat.id,"❌ Invalid address. Must start with 0x. Try again or tap 🔙 BACK MAIN MENU")
        bot.register_next_step_handler(msg, withdraw_address)
        return
    users[uid]["temp_addr"] = text
    save_users(users)
    msg = bot.send_message(m.chat.id,f"Enter withdrawal amount (MIN: $1 | Balance: ${users[uid]['balance']:.2f}):")
    bot.register_next_step_handler(msg, withdraw_amount)

def withdraw_amount(m):
    uid = str(m.from_user.id)
    text = m.text.strip()
    if text == "🔙 BACK MAIN MENU":
        back_main_menu(m.chat.id, uid)
        return
    try:
        amt = float(text)
    except:
        msg = bot.send_message(m.chat.id,"❌ Invalid amount. Enter a number or tap 🔙 BACK MAIN MENU")
        bot.register_next_step_handler(msg, withdraw_amount)
        return
    if amt < 1:
        msg = bot.send_message(m.chat.id,"❌ AMOUNT YOU WITHDRAWAL MIN: 1\nOr tap 🔙 BACK MAIN MENU")
        bot.register_next_step_handler(msg, withdraw_amount)
        return
    if amt > users[uid]["balance"]:
        msg = bot.send_message(m.chat.id,"❌ Insufficient balance. Or tap 🔙 BACK MAIN MENU")
        bot.register_next_step_handler(msg, withdraw_amount)
        return

    # Haddii sax ah
    wid = random.randint(10000,99999)
    addr = users[uid].pop("temp_addr", None)

    withdraws = load_withdraws()
    withdraws.append({
        "id": wid,
        "user": uid,
        "amount": amt,
        "blocked": amt,
        "address": addr,
        "status": "pending",
        "time": str(datetime.now())
    })
    save_withdraws(withdraws)

    # Update user balance and blocked money
    users[uid]["balance"] -= amt
    users[uid]["blocked"] = users[uid].get("blocked",0.0) + amt
    save_users(users)

    # Message user
    bot.send_message(m.chat.id,
        f"✅ Request #{wid} Sent!\n"
        f"💵 Amount: ${amt:.2f}\n"
        f"💸 Fee (0.00%): -$0.00\n"
        f"🧾 Net Due: ${amt:.2f}\n"
        f"⏳ Your request is pending approval\n"
        f"🕒 Pending time: 6–12 hours\n"
        f"Please be patient 😕",
        reply_markup=user_menu()
    )

    # Message Admin
    referrals_count = len([x for x in users if users[x].get("invited") == uid])
    admin_msg = f"""
💳 NEW WITHDRAWAL

👤 User: {uid}
🤖 BOT ID: {users[uid]['bot_id']}
👥 Referrals: {referrals_count}
💵 Amount: ${amt:.2f}
🧾 Request ID: {wid}
🏦 Address: {addr}
Blocked: ${amt:.2f}

Reply with:
CONFIRM {wid}
REJECT {wid}
BAN {uid}
"""
    bot.send_message(ADMIN_ID, admin_msg)
# ================= ADMIN PANEL =================
@bot.message_handler(func=lambda m: m.text=="👑 ADMIN PANEL")
def admin_panel_btn(m):
    if not is_admin(m.from_user.id): return
    bot.send_message(m.chat.id, "👑 ADMIN PANEL", reply_markup=admin_menu())

@bot.message_handler(func=lambda m: m.text=="🔙 BACK MAIN MENU")
def back_main(m):
    back_main_menu(m.chat.id, str(m.from_user.id))

# ================= ADMIN CALLBACKS =================
@bot.callback_query_handler(func=lambda c: True)
def admin_callbacks(call):
    data = call.data

    if data.startswith("confirm_"):
        wid = int(data.split("_")[1])
        w = next((x for x in withdraws if x["id"]==wid), None)
        if not w: return bot.answer_callback_query(call.id, "Not found")
        if w["status"]!="pending":
            return bot.answer_callback_query(call.id, "Already processed")

        w["status"] = "paid"
        users[w["user"]]["blocked"] -= w["blocked"]
        save_users(); save_withdraws()

        bot.answer_callback_query(call.id, "✅ Confirmed")
        bot.send_message(int(w["user"]), f"✅ Withdrawal #{wid} approved!")

    elif data.startswith("reject_"):
        wid = int(data.split("_")[1])
        w = next((x for x in withdraws if x["id"]==wid), None)
        if not w: return bot.answer_callback_query(call.id, "Not found")
        if w["status"]!="pending":
            return bot.answer_callback_query(call.id, "Already processed")

        w["status"] = "rejected"
        users[w["user"]]["balance"] += w["blocked"]
        users[w["user"]]["blocked"] -= w["blocked"]
        save_users(); save_withdraws()

        bot.answer_callback_query(call.id, "❌ Rejected")
        bot.send_message(int(w["user"]), f"❌ Withdrawal #{wid} rejected")

    elif data.startswith("ban_"):
        uid = data.split("_")[1]
        if uid in users:
            users[uid]["banned"] = True
            save_users()
        bot.answer_callback_query(call.id, "🚫 User banned")

# ================= ADD BALANCE =================
@bot.message_handler(func=lambda m: m.text=="➕ ADD BALANCE")
def add_balance(m):
    if not is_admin(m.from_user.id): return
    msg = bot.send_message(m.chat.id, "Send BOT ID and amount\nExample: 12345678901 2.5")
    bot.register_next_step_handler(msg, add_balance_step)

def add_balance_step(m):
    if not is_admin(m.from_user.id): return
    try:
        bid, amt = m.text.split()
        amt = float(amt)
    except:
        return bot.send_message(m.chat.id, "❌ Invalid format")

    uid = find_user_by_botid(bid)
    if not uid:
        return bot.send_message(m.chat.id, "❌ BOT ID not found")

    users[uid]["balance"] += amt
    save_users()
    bot.send_message(int(uid), f"💰 Admin added ${amt:.2f}")
    bot.send_message(m.chat.id, "✅ Done")

# ================= UNBAN MONEY =================
@bot.message_handler(func=lambda m: m.text=="✅ UNBAN MONEY")
def unban_money(m):
    if not is_admin(m.from_user.id): return
    msg = bot.send_message(m.chat.id, "Send BOT ID to release blocked money:")
    bot.register_next_step_handler(msg, unban_money_step)

def unban_money_step(m):
    if not is_admin(m.from_user.id): return
    bid = m.text.strip()
    uid = find_user_by_botid(bid)
    if not uid:
        return bot.send_message(m.chat.id, "❌ BOT ID not found")

    amt = users[uid].get("blocked",0.0)
    users[uid]["balance"] += amt
    users[uid]["blocked"] = 0.0
    save_users()

    bot.send_message(m.chat.id, f"✅ Released ${amt:.2f} to user")
    bot.send_message(int(uid), f"💵 Your blocked money ${amt:.2f} has been released")

# ================= WITHDRAWAL CHECK =================
@bot.message_handler(func=lambda m: m.text=="💳 WITHDRAWAL CHECK")
def withdrawal_check(m):
    if not is_admin(m.from_user.id): return
    msg = bot.send_message(m.chat.id, "Send Request ID:")
    bot.register_next_step_handler(msg, withdrawal_check_step)

def withdrawal_check_step(m):
    if not is_admin(m.from_user.id): return
    try:
        wid = int(m.text)
    except:
        return bot.send_message(m.chat.id, "❌ Invalid ID")

    w = next((x for x in withdraws if x["id"]==wid), None)
    if not w:
        return bot.send_message(m.chat.id, "❌ Request not found")

    bot.send_message(m.chat.id,
        f"🧾 Request #{w['id']}\n"
        f"👤 User: {w['user']}\n"
        f"💵 Amount: ${w['amount']:.2f}\n"
        f"🏦 Address: {w['address']}\n"
        f"📌 Status: {w['status']}\n"
        f"🕒 Time: {w['time']}"
    )

# ================= STATS =================
@bot.message_handler(func=lambda m: m.text=="📊 STATS")
def stats(m):
    if not is_admin(m.from_user.id): return
    total_users = len(users)
    total_balance = sum(users[u]["balance"] for u in users)
    total_withdraw_paid = sum(w["amount"] for w in withdraws if w["status"]=="paid")
    monthly_users = sum(1 for u in users if users[u]["month"]==now_month())

    bot.send_message(m.chat.id,
        f"📊 Stats\n"
        f"👥 Total Users: {total_users}\n"
        f"📆 Monthly Users: {monthly_users}\n"
        f"💰 Total Balance: ${total_balance:.2f}\n"
        f"💵 Total Withdraw Paid: ${total_withdraw_paid:.2f}"
    )

# ================= BROADCAST =================
@bot.message_handler(func=lambda m: m.text=="📢 BROADCAST")
def broadcast(m):
    if not is_admin(m.from_user.id): return
    msg = bot.send_message(m.chat.id, "Send message to broadcast:")
    bot.register_next_step_handler(msg, broadcast_step)

def broadcast_step(m):
    if not is_admin(m.from_user.id): return
    sent = 0
    for u in users:
        try:
            bot.send_message(int(u), m.text)
            sent += 1
        except:
            pass
    bot.send_message(m.chat.id, f"✅ Broadcast sent to {sent} users")

# ================= MEDIA DOWNLOADER (PRO) =================
def download_media(chat_id, url):
    try:
        # ---- TikTok via API (photos + video, often no watermark) ----
        if "tiktok.com" in url:
            try:
                api = f"https://tikwm.com/api/?url={url}"
                res = requests.get(api, timeout=20).json()

                if res.get("code")==0 and "data" in res:
                    data = res["data"]

                    # photos / slideshow
                    if data.get("images"):
                        for img in data["images"]:
                            img_data = requests.get(img, timeout=20).content
                            with open("tt.jpg","wb") as f: f.write(img_data)
                            bot.send_photo(chat_id, open("tt.jpg","rb"))
                            os.remove("tt.jpg")
                        return

                    # video
                    if data.get("play"):
                        vid = requests.get(data["play"], timeout=60).content
                        with open("tt.mp4","wb") as f: f.write(vid)
                        bot.send_video(chat_id, open("tt.mp4","rb"))
                        os.remove("tt.mp4")
                        return
            except:
                pass

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
                bot.send_message(chat_id, f"TikTok download error: {e}")
                return

        # ---- YouTube ----
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
                bot.send_message(chat_id, f"YouTube download error: {e}")
                return

        bot.send_message(chat_id, "❌ Unsupported link")

    except Exception as e:
        bot.send_message(chat_id, f"Download error: {e}")

@bot.message_handler(func=lambda m: m.text and "http" in m.text)
def links(m):
    if banned_guard(m): return
    bot.send_message(m.chat.id, "⏳ Downloading...")
    download_media(m.chat.id, m.text)

# ================= RUN =================
bot.infinity_polling(skip_pending=True)
