import telebot
from telebot.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton
import os, json, random
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import yt_dlp

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 7983838654
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# ================= DATABASE =================
def load_users():
    if not os.path.exists("users.json"): return {}
    return json.load(open("users.json"))

def save_users(data):
    json.dump(data, open("users.json","w"), indent=4)

def load_withdraws():
    if not os.path.exists("withdraws.json"): return []
    return json.load(open("withdraws.json"))

def save_withdraws(data):
    json.dump(data, open("withdraws.json","w"), indent=4)

users = load_users()
withdraws = load_withdraws()

# ================= RANDOM GENERATORS =================
def random_ref(): return str(random.randint(1000000000,9999999999))
def random_botid(): return str(random.randint(10000000000,99999999999))

# ================= KEYBOARDS =================
def user_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("💰 BALANCE","💸 WITHDRAWAL")
    kb.add("👥 REFERRAL","🆔 GET ID")
    kb.add("☎️ CUSTOMER")
    return kb

def admin_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📊 STATS","🎁 RANDOM GIFT")
    kb.add("➕ ADD BALANCE","✅ UNBAN")
    kb.add("📢 BROADCAST")
    return kb

# ================= START =================
@bot.message_handler(commands=['start'])
def start(m):
    uid = str(m.from_user.id)
    args = m.text.split()
    if uid not in users:
        ref = args[1] if len(args)>1 else None
        users[uid] = {
            "balance":0,
            "blocked":0,
            "ref":random_ref(),
            "bot_id":random_botid(),
            "invited":None,
            "banned":False,
            "month":datetime.now().month
        }
        if ref:
            for u in users:
                if users[u]["ref"] == ref:
                    users[u]["balance"] += 0.2
                    users[uid]["invited"] = u
                    bot.send_message(int(u),"🎉 You earned $0.2 from referral!")
        save_users(users)

    bot.send_message(m.chat.id,"👋 Welcome to Media Downloader Bot!", reply_markup=user_menu())

# ================= BALANCE =================
@bot.message_handler(func=lambda m: m.text=="💰 BALANCE")
def balance(m):
    uid = str(m.from_user.id)
    bal = users[uid]["balance"]
    blocked = users[uid].get("blocked",0)
    bot.send_message(m.chat.id,f"💰 Balance: ${bal:.2f}\n🔒 Blocked: ${blocked:.2f}")

# ================= GET ID =================
@bot.message_handler(func=lambda m: m.text=="🆔 GET ID")
def get_id(m):
    uid = str(m.from_user.id)
    bot.send_message(m.chat.id,f"🆔 BOT ID: {users[uid]['bot_id']}\n👤 TELEGRAM ID: {uid}")

# ================= REFERRAL =================
@bot.message_handler(func=lambda m: m.text=="👥 REFERRAL")
def referral(m):
    uid = str(m.from_user.id)
    link = f"https://t.me/{bot.get_me().username}?start={users[uid]['ref']}"
    bot.send_message(m.chat.id,f"🔗 Your referral link:\n{link}")

# ================= CUSTOMER =================
@bot.message_handler(func=lambda m: m.text=="☎️ CUSTOMER")
def customer(m):
    bot.send_message(m.chat.id,"Contact support: @scholes1")

# ================= WITHDRAWAL =================
@bot.message_handler(func=lambda m: m.text=="💸 WITHDRAWAL")
def withdraw_menu(m):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("USDT-BEP20","CANCEL")
    bot.send_message(m.chat.id,"Choose withdrawal type:", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text=="USDT-BEP20")
def withdraw_start(m):
    uid = str(m.from_user.id)
    msg = bot.send_message(m.chat.id,"Enter your USDT BEP20 address (must start with 0x):")
    bot.register_next_step_handler(msg,get_address)

def get_address(m):
    uid = str(m.from_user.id)
    addr = m.text.strip()
    if not addr.startswith("0x"):
        msg = bot.send_message(m.chat.id,"❌ Invalid address. Must start with 0x")
        bot.register_next_step_handler(msg,get_address)
        return
    users[uid]["temp_addr"] = addr
    save_users(users)
    msg = bot.send_message(m.chat.id,f"Enter amount to withdraw (min $1, Balance ${users[uid]['balance']:.2f}):")
    bot.register_next_step_handler(msg,get_amount)

def get_amount(m):
    uid = str(m.from_user.id)
    try:
        amt = float(m.text)
    except:
        msg = bot.send_message(m.chat.id,"❌ Invalid amount")
        bot.register_next_step_handler(msg,get_amount)
        return
    if amt < 1:
        msg = bot.send_message(m.chat.id,"❌ AMOUNT YOU WITHDRAWAL MIN: 1")
        bot.register_next_step_handler(msg,get_amount)
        return
    if amt > users[uid]["balance"]:
        msg = bot.send_message(m.chat.id,"❌ Insufficient balance")
        bot.register_next_step_handler(msg,get_amount)
        return

    wid = random.randint(10000,99999)
    withdraws.append({
        "id": wid,
        "user": uid,
        "amount": amt,
        "blocked": amt,
        "address": users[uid]["temp_addr"],
        "status":"pending",
        "time": str(datetime.now())
    })
    users[uid]["balance"] -= amt
    users[uid]["blocked"] = users[uid].get("blocked",0)+amt
    save_users(users)
    save_withdraws(withdraws)

    # User sees Request ID
    bot.send_message(m.chat.id,
        f"✅ Request #{wid} Sent!\n💵 Amount: ${amt}\n⏳ Pending 6-12 hours",
        reply_markup=user_menu()
    )

    # Send to Admin
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("✅ CONFIRM", callback_data=f"confirm_{wid}"),
        InlineKeyboardButton("❌ REJECT", callback_data=f"reject_{wid}")
    )
    kb.add(InlineKeyboardButton("🚫 BAN", callback_data=f"ban_{uid}"))

    bot.send_message(ADMIN_ID,
        f"💳 NEW WITHDRAW\n\n👤 User: {uid}\n💵 Amount: ${amt}\n🧾 Request ID: {wid}\nAddress: {users[uid]['temp_addr']}\nReferrals: {users[uid].get('invited',0)}",
        reply_markup=kb
    )

    del users[uid]["temp_addr"]
    save_users(users)

# ================= ADMIN PANEL =================
@bot.message_handler(commands=['admin'])
def admin_panel(m):
    if m.from_user.id != ADMIN_ID: return
    bot.send_message(m.chat.id,"👑 ADMIN PANEL",reply_markup=admin_menu())

# ================= ADMIN CALLBACKS =================
@bot.callback_query_handler(func=lambda call: True)
def admin_callbacks(call):
    data = call.data
    if data.startswith("confirm_"):
        wid = int(data.split("_")[1])
        wd = [w for w in withdraws if w["id"]==wid][0]
        wd["status"]="paid"
        users[wd["user"]]["blocked"] -= wd["blocked"]
        users[wd["user"]]["balance"] += 0  # Balance already deducted
        save_users(users)
        save_withdraws(withdraws)
        bot.answer_callback_query(call.id,"✅ Withdrawal confirmed")
        bot.send_message(wd["user"],f"✅ Withdrawal #{wid} approved!")

    elif data.startswith("reject_"):
        wid = int(data.split("_")[1])
        wd = [w for w in withdraws if w["id"]==wid][0]
        wd["status"]="rejected"
        users[wd["user"]]["balance"] += wd["blocked"]
        users[wd["user"]]["blocked"] -= wd["blocked"]
        save_users(users)
        save_withdraws(withdraws)
        bot.answer_callback_query(call.id,"❌ Withdrawal rejected")
        bot.send_message(wd["user"],f"❌ Withdrawal #{wid} rejected")

    elif data.startswith("ban_"):
        uid = data.split("_")[1]
        users[uid]["banned"]=True
        save_users(users)
        bot.answer_callback_query(call.id,"🚫 User banned")

# ================= ADD BALANCE =================
@bot.message_handler(func=lambda m: m.text=="➕ ADD BALANCE")
def add_balance(m):
    if m.from_user.id!=ADMIN_ID: return
    msg = bot.send_message(m.chat.id,"Send BOT ID and amount\nExample: 12345678901 2")
    bot.register_next_step_handler(msg,add_balance_step)

def add_balance_step(m):
    try:
        bid, amt = m.text.split()
        amt = float(amt)
    except:
        bot.send_message(m.chat.id,"❌ Invalid format")
        return
    for u in users:
        if users[u]["bot_id"]==bid:
            users[u]["balance"] += amt
            save_users(users)
            bot.send_message(int(u),f"💰 Admin added ${amt}")
            bot.send_message(m.chat.id,"✅ Done")
            return
    bot.send_message(m.chat.id,"❌ BOT ID not found")

# ================= STATS =================
@bot.message_handler(func=lambda m: m.text=="📊 STATS")
def stats(m):
    if m.from_user.id != ADMIN_ID: return
    total_users = len(users)
    total_balance = sum(users[u]["balance"] for u in users)
    total_withdraw = sum(w["amount"] for w in withdraws if w["status"]=="paid")
    monthly_users = sum(1 for u in users if users[u]["month"]==datetime.now().month)
    bot.send_message(m.chat.id,
        f"📊 Stats\n👥 Total Users: {total_users}\n📆 Monthly Users: {monthly_users}\n💰 Total Balance: ${total_balance:.2f}\n💵 Total Withdraw Paid: ${total_withdraw:.2f}"
    )

# ================= BROADCAST =================
@bot.message_handler(func=lambda m: m.text=="📢 BROADCAST")
def broadcast(m):
    if m.from_user.id!=ADMIN_ID: return
    msg = bot.send_message(m.chat.id,"Send message to broadcast")
    bot.register_next_step_handler(msg,broadcast_step)

def broadcast_step(m):
    for u in users:
        try:
            bot.send_message(int(u),m.text)
        except:
            continue
    bot.send_message(m.chat.id,"✅ Broadcast sent")

# ================= MEDIA DOWNLOAD =================
def download_media(chat_id,url):
    try:
        if "tiktok.com" in url and "/photo/" in url:
            html=requests.get(url,headers={"User-Agent":"Mozilla"}).text
            soup=BeautifulSoup(html,"html.parser")
            img=soup.find("meta",property="og:image")["content"]
            data=requests.get(img).content
            open("tt.jpg","wb").write(data)
            bot.send_photo(chat_id,open("tt.jpg","rb"))
            os.remove("tt.jpg")
            return
        ydl_opts={"outtmpl":"vid.%(ext)s","format":"mp4"}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info=ydl.extract_info(url,download=True)
            file=ydl.prepare_filename(info)
        bot.send_video(chat_id,open(file,"rb"))
        os.remove(file)
    except Exception as e:
        bot.send_message(chat_id,f"Download error: {e}")

@bot.message_handler(func=lambda m:"http" in m.text)
def links(m):
    bot.send_message(m.chat.id,"⏳ Downloading...")
    download_media(m.chat.id,m.text)

bot.infinity_polling()
