import telebot
from telebot.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
import json, os, random
from datetime import datetime
import yt_dlp

# ================= CONFIG =================
TOKEN = "YOUR_BOT_TOKEN"
ADMIN_ID = 7983838654 
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

USERS_FILE = "users.json"
WITHDRAWS_FILE = "withdraws.json"

# ================= DATABASE =================
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
def is_admin(uid):
    return int(uid) == ADMIN_ID

def random_ref():
    return str(random.randint(100000,999999))

def random_botid():
    return str(random.randint(10000000000,99999999999))

def find_user_by_botid(bid):
    for u,data in users.items():
        if data.get("bot_id")==bid:
            return u
    return None

def banned_guard(m):
    uid=str(m.from_user.id)
    if uid in users and users[uid].get("banned"):
        bot.send_message(m.chat.id,"🚫 You are banned.")
        return True
    return False

# ================= MENUS =================
def user_menu(uid):
    kb=ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("💰 BALANCE","💸 WITHDRAWAL")
    kb.add("👥 REFERRAL","🆔 GET ID")
    kb.add("🎬 MEDIA DOWNLOAD","☎️ CUSTOMER")
    if is_admin(uid):
        kb.add("👑 ADMIN PANEL")
    return kb

def admin_menu():
    kb=ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📊 STATS","📢 BROADCAST")
    kb.add("➕ ADD BALANCE","➖ REMOVE MONEY")
    kb.add("💳 WITHDRAWAL CHECK")
    kb.add("💰 UNBLOCK MONEY")
    kb.add("🚫 BAN USER","✅ UNBAN USER")
    kb.add("🔙 BACK MAIN MENU")
    return kb

def send_main(chat_id,uid):
    bot.send_message(chat_id,"🏠 <b>Main Menu</b>",reply_markup=user_menu(uid))

# ================= START =================
@bot.message_handler(commands=['start'])
def start(m):
    uid=str(m.from_user.id)
    args=m.text.split()

    if uid not in users:
        users[uid]={
            "balance":0.0,
            "blocked":0.0,
            "ref":random_ref(),
            "bot_id":random_botid(),
            "invited":0,
            "banned":False
        }

        # Referral reward
        if len(args)>1:
            ref=args[1]
            for u in users:
                if users[u]["ref"]==ref:
                    users[u]["balance"]+=0.2
                    users[u]["invited"]+=1
                    bot.send_message(int(u),"🎉 You earned $0.2 referral bonus!")
                    break

        save_users()

    send_main(m.chat.id,uid)

# ================= BALANCE =================
@bot.message_handler(func=lambda m: m.text=="💰 BALANCE")
def balance(m):
    if banned_guard(m): return
    uid=str(m.from_user.id)

    available=users[uid].get("balance",0)
    blocked=users[uid].get("blocked",0)
    pending=sum(w["amount"] for w in withdraws if w["user"]==uid and w["status"]=="pending")

    msg=(
        f"💰 <b>Your Wallet</b>\n\n"
        f"✅ Available: ${available:.2f}\n"
        f"⏳ Pending: ${pending:.2f}\n"
        f"🚫 Blocked: ${blocked:.2f}"
    )
    bot.send_message(m.chat.id,msg)

# ================= REFERRAL =================
@bot.message_handler(func=lambda m: m.text=="👥 REFERRAL")
def referral(m):
    uid=str(m.from_user.id)
    link=f"https://t.me/{bot.get_me().username}?start={users[uid]['ref']}"
    bot.send_message(
        m.chat.id,
        f"👥 <b>Your Referral Link</b>\n\n{link}\n\n"
        f"Invited: {users[uid]['invited']}\n"
        f"Reward: $0.2 per user"
    )

# ================= GET ID =================
@bot.message_handler(func=lambda m: m.text=="🆔 GET ID")
def getid(m):
    uid=str(m.from_user.id)
    bot.send_message(
        m.chat.id,
        f"🆔 Telegram ID: <code>{uid}</code>\n"
        f"🤖 BOT ID: <code>{users[uid]['bot_id']}</code>"
    )

# ================= MEDIA DOWNLOADER =================
@bot.message_handler(func=lambda m: m.text=="🎬 MEDIA DOWNLOAD")
def media_start(m):
    if banned_guard(m): return
    msg=bot.send_message(m.chat.id,"Send video URL (YouTube, TikTok, etc)")
    bot.register_next_step_handler(msg,media_process)

def media_process(m):
    url=m.text
    try:
        ydl_opts={"format":"best","outtmpl":"video.%(ext)s"}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info=ydl.extract_info(url,download=True)
            filename=ydl.prepare_filename(info)
        with open(filename,"rb") as f:
            bot.send_video(m.chat.id,f)
        os.remove(filename)
    except:
        bot.send_message(m.chat.id,"❌ Failed to download.")

# ================= ADMIN PANEL =================
@bot.message_handler(func=lambda m: m.text=="👑 ADMIN PANEL")
def admin_panel(m):
    uid=str(m.from_user.id)
    if not is_admin(uid):
        return
    bot.send_message(m.chat.id,"👑 <b>Admin Panel</b>",reply_markup=admin_menu())

# ================= BACK =================
@bot.message_handler(func=lambda m: m.text=="🔙 BACK MAIN MENU")
def back_main(m):
    uid=str(m.from_user.id)
    send_main(m.chat.id,uid)

# ================= WITHDRAWAL MENU =================
@bot.message_handler(func=lambda m: m.text=="💸 WITHDRAWAL")
def withdraw_menu(m):
    if banned_guard(m): return

    kb=ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("USDT-BEP20")
    kb.add("🔙 BACK MAIN MENU")

    bot.send_message(m.chat.id,"Select withdrawal method:",reply_markup=kb)

# ================= WITHDRAWAL METHOD =================
@bot.message_handler(func=lambda m: m.text=="USDT-BEP20")
def withdraw_address(m):
    uid=str(m.from_user.id)

    msg=bot.send_message(
        m.chat.id,
        "Enter USDT BEP20 address (must start with 0x)\nOr press 🔙 BACK MAIN MENU"
    )
    bot.register_next_step_handler(msg,withdraw_amount_step)

def withdraw_amount_step(m):
    uid=str(m.from_user.id)
    text=(m.text or "").strip()

    if text=="🔙 BACK MAIN MENU":
        send_main(m.chat.id,uid)
        return

    if not text.startswith("0x"):
        msg=bot.send_message(m.chat.id,"❌ Invalid address. Must start with 0x")
        bot.register_next_step_handler(msg,withdraw_amount_step)
        return

    users[uid]["temp_addr"]=text
    save_users()

    msg=bot.send_message(
        m.chat.id,
        f"Enter amount\nMinimum: $1\nAvailable: ${users[uid]['balance']:.2f}"
    )
    bot.register_next_step_handler(msg,withdraw_final_step)

def withdraw_final_step(m):
    uid=str(m.from_user.id)
    text=(m.text or "").strip()

    try:
        amt=float(text)
    except:
        msg=bot.send_message(m.chat.id,"❌ Invalid amount. Enter number.")
        bot.register_next_step_handler(msg,withdraw_final_step)
        return

    if amt<1:
        msg=bot.send_message(m.chat.id,"❌ Minimum withdrawal is $1")
        bot.register_next_step_handler(msg,withdraw_final_step)
        return

    if amt>users[uid]["balance"]:
        msg=bot.send_message(m.chat.id,"❌ Insufficient balance")
        bot.register_next_step_handler(msg,withdraw_final_step)
        return

    wid=random.randint(10000,99999)
    addr=users[uid].pop("temp_addr")

    withdraws.append({
        "id":wid,
        "user":uid,
        "amount":amt,
        "address":addr,
        "status":"pending",
        "time":str(datetime.now())
    })

    users[uid]["balance"]-=amt

    save_users()
    save_withdraws()

    # ===== USER CONFIRMATION =====
    bot.send_message(
        m.chat.id,
        f"✅ <b>Withdrawal Request Sent</b>\n\n"
        f"🧾 ID: {wid}\n"
        f"💵 Amount: ${amt:.2f}\n"
        f"🏦 Address: {addr}\n"
        f"⏳ Status: Pending"
    )

    send_main(m.chat.id,uid)

    # ===== ADMIN INLINE BUTTONS =====
    markup=InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("✅ CONFIRM",callback_data=f"confirm_{wid}"),
        InlineKeyboardButton("❌ REJECT",callback_data=f"reject_{wid}")
    )
    markup.add(
        InlineKeyboardButton("🚫 BAN USER",callback_data=f"ban_{uid}"),
        InlineKeyboardButton("💰 BAN MONEY",callback_data=f"block_{wid}")
    )

    bot.send_message(
        ADMIN_ID,
        f"💳 <b>NEW WITHDRAWAL</b>\n\n"
        f"👤 User ID: {uid}\n"
        f"🤖 BOT ID: {users[uid]['bot_id']}\n"
        f"💵 Amount: ${amt:.2f}\n"
        f"🧾 Request ID: {wid}\n"
        f"🏦 Address: {addr}\n"
        f"📅 Time: {datetime.now()}",
        reply_markup=markup
    )

# ================= ADMIN CALLBACK HANDLER =================
@bot.callback_query_handler(func=lambda call: call.data.startswith(("confirm_","reject_","ban_","block_")))
def admin_actions(call):

    # Admin protection
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id,"❌ Not authorized")
        return

    data=call.data

    # ===== CONFIRM WITHDRAWAL =====
    if data.startswith("confirm_"):
        wid=int(data.split("_")[1])
        w=next((x for x in withdraws if x["id"]==wid),None)

        if not w or w["status"]!="pending":
            bot.answer_callback_query(call.id,"Already processed")
            return

        w["status"]="paid"
        save_withdraws()

        bot.send_message(
            int(w["user"]),
            f"✅ Withdrawal #{wid} approved and paid."
        )

        bot.answer_callback_query(call.id,"Confirmed")


    # ===== REJECT WITHDRAWAL =====
    elif data.startswith("reject_"):
        wid=int(data.split("_")[1])
        w=next((x for x in withdraws if x["id"]==wid),None)

        if not w or w["status"]!="pending":
            bot.answer_callback_query(call.id,"Already processed")
            return

        uid=w["user"]
        amt=w["amount"]

        users[uid]["balance"]+=amt
        w["status"]="rejected"

        save_users()
        save_withdraws()

        bot.send_message(
            int(uid),
            f"❌ Withdrawal #{wid} rejected.\n${amt:.2f} returned to balance."
        )

        bot.answer_callback_query(call.id,"Rejected")


    # ===== BAN USER =====
    elif data.startswith("ban_"):
        uid=data.split("_")[1]

        if uid in users:
            users[uid]["banned"]=True
            save_users()

            bot.send_message(int(uid),"🚫 You have been banned by admin.")
            bot.answer_callback_query(call.id,"User banned")


    # ===== BAN MONEY (BLOCK SYSTEM) =====
    elif data.startswith("block_"):
        wid=int(data.split("_")[1])
        w=next((x for x in withdraws if x["id"]==wid),None)

        if not w or w["status"]!="pending":
            bot.answer_callback_query(call.id,"Already processed")
            return

        uid=w["user"]
        amt=w["amount"]

        # 4 digit code
        code=str(random.randint(1000,9999))

        # lacagta blocked ku dar
        users[uid]["blocked"]=users[uid].get("blocked",0)+amt

        w["status"]="blocked"
        w["block_code"]=code

        save_users()
        save_withdraws()

        bot.send_message(
            int(uid),
            f"🚫 Your withdrawal of ${amt:.2f} has been BLOCKED.\n\n"
            f"🔐 Your Code: <code>{code}</code>\n\n"
            f"Contact support and provide this code."
        )

        bot.answer_callback_query(call.id,"Money blocked")

# ================= UNBLOCK MONEY =================
@bot.message_handler(func=lambda m: m.text=="💰 UNBLOCK MONEY")
def unblock_money_start(m):
    if not is_admin(m.from_user.id):
        bot.send_message(m.chat.id,"❌ You are not admin")
        return
    msg = bot.send_message(m.chat.id,"Send 4-digit Block Code to UNBLOCK the money")
    bot.register_next_step_handler(msg, unblock_money_process)

def unblock_money_process(m):
    if not is_admin(m.from_user.id):
        bot.send_message(m.chat.id,"❌ You are not admin")
        return

    code = m.text.strip()

    # Find blocked withdrawal
    w = next((x for x in withdraws if x.get("block_code") == code), None)
    if not w:
        bot.send_message(m.chat.id,"❌ Invalid Block Code")
        return

    uid = w["user"]
    amt = w["amount"]

    # Update balances
    users[uid]["balance"] += amt
    users[uid]["blocked"] -= amt
    w["status"] = "unblocked"
    w.pop("block_code", None)

    save_users()
    save_withdraws()

    bot.send_message(int(uid), f"✅ Your blocked ${amt:.2f} is now available in balance!")
    bot.send_message(m.chat.id, f"✅ Money unblocked for user {uid}")


# ================= ADMIN STATS =================
@bot.message_handler(func=lambda m: m.text=="📊 STATS")
def admin_stats(m):
    if not is_admin(m.from_user.id):
        return
    total_users = len(users)
    total_balance = sum(u.get("balance",0) for u in users.values())
    total_paid = sum(w["amount"] for w in withdraws if w["status"]=="paid")
    total_pending = sum(w["amount"] for w in withdraws if w["status"]=="pending")
    total_blocked = sum(u.get("blocked",0) for u in users.values())
    banned_users = sum(1 for u in users.values() if u.get("banned"))

    msg = (
        f"📊 <b>ADMIN STATS</b>\n\n"
        f"👥 TOTAL USERS: {total_users}\n"
        f"💰 TOTAL BALANCE: ${total_balance:.2f}\n"
        f"💵 TOTAL WITHDRAWAL PAID: ${total_paid:.2f}\n"
        f"⏳ TOTAL PENDING: ${total_pending:.2f}\n"
        f"🚫 BLOCKED: ${total_blocked:.2f}\n"
        f"🚫 BANNED USERS: {banned_users}"
    )
    bot.send_message(m.chat.id, msg)


# ================= WITHDRAWAL CHECK =================
@bot.message_handler(func=lambda m: m.text=="💳 WITHDRAWAL CHECK")
def withdrawal_check_start(m):
    if not is_admin(m.from_user.id):
        return
    msg = bot.send_message(m.chat.id,"Enter Withdrawal Request ID")
    bot.register_next_step_handler(msg, withdrawal_check_process)

def withdrawal_check_process(m):
    if not is_admin(m.from_user.id):
        return
    try:
        wid=int(m.text.strip())
    except:
        bot.send_message(m.chat.id,"❌ Invalid Request ID")
        return
    w = next((x for x in withdraws if x["id"]==wid), None)
    if not w:
        bot.send_message(m.chat.id,"❌ Request ID not found")
        return

    uid = w["user"]
    bot_id = users.get(uid, {}).get("bot_id","Unknown")
    invited = users.get(uid, {}).get("invited",0)

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


# ================= RUN BOT =================
if __name__=="__main__":
    print("🤖 Bot is running...")
    bot.infinity_polling(skip_pending=True)
