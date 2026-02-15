import telebot
from telebot.types import *
import os, json, random, requests, yt_dlp
from bs4 import BeautifulSoup
from datetime import datetime

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 7983838654

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# ---------------- DATABASE ----------------
def load(name, default):
    if not os.path.exists(name):
        return default
    return json.load(open(name))

def save(name, data):
    json.dump(data, open(name,"w"), indent=4)

users = load("users.json", {})
withdraws = load("withdraws.json", [])

# ---------------- MENUS ----------------
def user_menu(uid):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("💰 BALANCE","💸 WITHDRAWAL")
    kb.add("👥 REFERAL","🆔 GET MY ID")
    kb.add("☎️ COSTUMER")
    if int(uid)==ADMIN_ID:
        kb.add("👑 ADMIN PANEL")
    return kb

def admin_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📊 STATS","➕ ADD BALANCE")
    kb.add("📤 BROADCAST","💳 WITHDRAW CHECK")
    kb.add("🚫 UNBAN","🔙 BACK")
    return kb

# ---------------- START ----------------
@bot.message_handler(commands=['start'])
def start(m):
    uid=str(m.from_user.id)
    args=m.text.split()

    if uid not in users:
        ref=args[1] if len(args)>1 else None

        users[uid]={
            "balance":0,
            "refs":0,
            "ref":str(random.randint(100000,999999)),
            "token":str(random.randint(1000000000,9999999999)),
            "banned":False,
            "month":datetime.now().month
        }

        # referral reward
        if ref:
            for u in users:
                if users[u]["ref"]==ref:
                    users[u]["refs"]+=1
                    users[u]["balance"]+=0.2
                    bot.send_message(int(u),"🎉 New referral joined! You earned $0.2")

        save("users.json",users)

    bot.send_message(m.chat.id,"👋 Welcome",reply_markup=user_menu(uid))

# ---------------- BALANCE ----------------
@bot.message_handler(func=lambda m:m.text=="💰 BALANCE")
def bal(m):
    uid=str(m.from_user.id)
    bot.send_message(m.chat.id,f"💰 Balance: ${users[uid]['balance']:.2f}")

# ---------------- REFERAL ----------------
@bot.message_handler(func=lambda m:m.text=="👥 REFERAL")
def ref(m):
    uid=str(m.from_user.id)
    link=f"https://t.me/{bot.get_me().username}?start={users[uid]['ref']}"
    bot.send_message(m.chat.id,f"🔗 {link}")

# ---------------- GET ID ----------------
@bot.message_handler(func=lambda m:m.text=="🆔 GET MY ID")
def gid(m):
    uid=str(m.from_user.id)
    bot.send_message(m.chat.id,
    f"""
🆔 TELEGRAM ID: {uid}
🔐 USER TOKEN: {users[uid]['token']}
""")

# ---------------- COSTUMER ----------------
@bot.message_handler(func=lambda m:m.text=="☎️ COSTUMER")
def cus(m):
    bot.send_message(m.chat.id,"Support: @scholes1")

# ---------------- ADMIN PANEL ----------------
@bot.message_handler(func=lambda m:m.text=="👑 ADMIN PANEL")
def admin_panel(m):
    if m.from_user.id!=ADMIN_ID:
        return
    bot.send_message(m.chat.id,"👑 Admin Panel",reply_markup=admin_menu())

@bot.message_handler(func=lambda m:m.text=="🔙 BACK")
def back(m):
    uid=str(m.from_user.id)
    bot.send_message(m.chat.id,"Back",reply_markup=user_menu(uid))

# ---------------- ADD BALANCE ----------------
@bot.message_handler(func=lambda m:m.text=="➕ ADD BALANCE")
def addbal(m):
    if m.from_user.id!=ADMIN_ID:return
    msg=bot.send_message(m.chat.id,"Send USER ID and amount\nExample:\n123456 2")
    bot.register_next_step_handler(msg,addbal2)

def addbal2(m):
    uid,amt=m.text.split()
    users[uid]["balance"]+=float(amt)
    save("users.json",users)
    bot.send_message(int(uid),f"💰 Admin added ${amt}")

# ---------------- WITHDRAW MENU ----------------
@bot.message_handler(func=lambda m:m.text=="💸 WITHDRAWAL")
def wd(m):
    kb=InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("USDT-BEP20",callback_data="usdt"),
        InlineKeyboardButton("CANCEL",callback_data="cancel")
    )
    bot.send_message(m.chat.id,"Choose method",reply_markup=kb)

@bot.callback_query_handler(func=lambda c:c.data=="cancel")
def cancel(c):
    bot.edit_message_text("Cancelled",c.message.chat.id,c.message.message_id)

# ---------------- WITHDRAW PROCESS ----------------
@bot.callback_query_handler(func=lambda c:c.data=="usdt")
def usdt(c):
    uid=str(c.from_user.id)
    if users[uid]["balance"]<0.5:
        bot.answer_callback_query(c.id,"Minimum $0.5")
        return
    msg=bot.send_message(c.message.chat.id,"Send USDT address starting with 0x")
    bot.register_next_step_handler(msg,get_address)

def get_address(m):
    uid=str(m.from_user.id)
    addr=m.text.strip()

    if not addr.startswith("0x"):
        msg=bot.send_message(m.chat.id,"Invalid address. Must start with 0x")
        bot.register_next_step_handler(msg,get_address)
        return

    users[uid]["temp_addr"]=addr
    save("users.json",users)

    msg=bot.send_message(m.chat.id,f"Enter amount (Balance ${users[uid]['balance']:.2f})")
    bot.register_next_step_handler(msg,get_amount)

def get_amount(m):
    uid=str(m.from_user.id)

    try:
        amt=float(m.text)
    except:
        msg=bot.send_message(m.chat.id,"Invalid amount")
        bot.register_next_step_handler(msg,get_amount)
        return

    if amt>users[uid]["balance"] or amt<0.5:
        msg=bot.send_message(m.chat.id,"Invalid amount")
        bot.register_next_step_handler(msg,get_amount)
        return

    wid=random.randint(10000,99999)

    withdraws.append({
        "id":wid,
        "user":uid,
        "amount":amt,
        "address":users[uid]["temp_addr"],
        "status":"pending",
        "time":str(datetime.now())
    })

    users[uid]["balance"]-=amt

    save("users.json",users)
    save("withdraws.json",withdraws)

    bot.send_message(m.chat.id,
    f"""
✅ Request #{wid} Sent!
💵 Amount: ${amt}
⏳ Pending 6-12 hours
""")

    # ADMIN MESSAGE
    kb=InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("✅ CONFIRM",callback_data=f"confirm_{wid}"),
        InlineKeyboardButton("❌ REJECT",callback_data=f"reject_{wid}")
    )
    kb.add(InlineKeyboardButton("🚫 BAN",callback_data=f"ban_{uid}"))

    bot.send_message(ADMIN_ID,
    f"""
💳 NEW WITHDRAW

User: {uid}
Amount: ${amt}
Request ID: {wid}
Referrals: {users[uid]['refs']}
Address: {users[uid]['temp_addr']}
""",reply_markup=kb)

    del users[uid]["temp_addr"]
    save("users.json",users)

# ---------------- ADMIN WITHDRAW ACTION ----------------
@bot.callback_query_handler(func=lambda c:c.data.startswith("confirm"))
def confirm(c):
    wid=int(c.data.split("_")[1])
    for w in withdraws:
        if w["id"]==wid:
            w["status"]="paid"
            bot.send_message(int(w["user"]),"✅ Withdrawal Approved")
    save("withdraws.json",withdraws)

@bot.callback_query_handler(func=lambda c:c.data.startswith("reject"))
def reject(c):
    wid=int(c.data.split("_")[1])
    for w in withdraws:
        if w["id"]==wid:
            users[w["user"]]["balance"]+=w["amount"]
            w["status"]="rejected"
            bot.send_message(int(w["user"]),"❌ Withdrawal Rejected")
    save("users.json",users)
    save("withdraws.json",withdraws)

@bot.callback_query_handler(func=lambda c:c.data.startswith("ban"))
def ban(c):
    uid=c.data.split("_")[1]
    users[uid]["banned"]=True
    save("users.json",users)

# ---------------- WITHDRAW CHECK ----------------
@bot.message_handler(func=lambda m:m.text=="💳 WITHDRAW CHECK")
def wdcheck(m):
    if m.from_user.id!=ADMIN_ID:return
    msg=bot.send_message(m.chat.id,"Send Request ID")
    bot.register_next_step_handler(msg,wdcheck2)

def wdcheck2(m):
    wid=int(m.text)
    for w in withdraws:
        if w["id"]==wid:
            bot.send_message(m.chat.id,str(w))

# ---------------- UNBAN ----------------
@bot.message_handler(func=lambda m:m.text=="🚫 UNBAN")
def unban(m):
    if m.from_user.id!=ADMIN_ID:return
    msg=bot.send_message(m.chat.id,"Send User ID")
    bot.register_next_step_handler(msg,unban2)

def unban2(m):
    users[m.text]["banned"]=False
    save("users.json",users)

# ---------------- BROADCAST ----------------
@bot.message_handler(func=lambda m:m.text=="📤 BROADCAST")
def bc(m):
    if m.from_user.id!=ADMIN_ID:return
    msg=bot.send_message(m.chat.id,"Send message or media")
    bot.register_next_step_handler(msg,bc2)

def bc2(m):
    for u in users:
        try:
            bot.copy_message(int(u),m.chat.id,m.message_id)
        except:
            pass

# ---------------- STATS ----------------
@bot.message_handler(func=lambda m:m.text=="📊 STATS")
def stats(m):
    if m.from_user.id!=ADMIN_ID:return
    total=len(users)
    totalbal=sum(users[u]["balance"] for u in users)
    bot.send_message(m.chat.id,f"Users: {total}\nTotal Balance: ${totalbal}")

# ---------------- TIKTOK DOWNLOAD ----------------
def download(chat,url):
    try:
        if "/photo/" in url:
            html=requests.get(url).text
            soup=BeautifulSoup(html,"html.parser")
            img=soup.find("meta",property="og:image")["content"]
            bot.send_photo(chat,img)
            return

        ydl_opts={"outtmpl":"vid.%(ext)s","format":"mp4"}
        with yt_dlp.YoutubeDL(ydl_opts) as y:
            info=y.extract_info(url,download=True)
            file=y.prepare_filename(info)

        bot.send_video(chat,open(file,"rb"))
        os.remove(file)

    except Exception as e:
        bot.send_message(chat,f"Error: {e}")

@bot.message_handler(func=lambda m:"tiktok.com" in m.text)
def tiktok(m):
    bot.send_message(m.chat.id,"Downloading...")
    download(m.chat.id,m.text)

# ---------------- RUN ----------------
bot.infinity_polling()
