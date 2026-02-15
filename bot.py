import telebot
from telebot.types import *
import os, json, random, yt_dlp, requests
from bs4 import BeautifulSoup
from datetime import datetime

TOKEN=os.getenv("BOT_TOKEN")
ADMIN_ID=7983838654

bot=telebot.TeleBot(TOKEN,parse_mode="HTML")

# ---------------- DATABASE ----------------

def load(name,default):
    if not os.path.exists(name):
        return default
    return json.load(open(name))

def save(name,data):
    json.dump(data,open(name,"w"),indent=4)

users=load("users.json",{})
withdraws=load("withdraws.json",[])

# ---------------- MENU ----------------

def menu(uid):
    kb=ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("💰 BALANCE","💸 WITHDRAWAL")
    kb.add("👥 REFERAL","🆔 GET MY ID")
    kb.add("☎️ COSTUMER")

    if int(uid)==ADMIN_ID:
        kb.add("👑 ADMIN PANEL")

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

        if ref:
            for u in users:
                if users[u]["ref"]==ref:
                    users[u]["refs"]+=1
                    users[u]["balance"]+=0.2
                    bot.send_message(int(u),"🎉 New referral joined! You earned $0.2")

        save("users.json",users)

    bot.send_message(m.chat.id,"👋 Welcome",reply_markup=menu(uid))

# ---------------- BALANCE ----------------

@bot.message_handler(func=lambda m:m.text=="💰 BALANCE")
def bal(m):
    uid=str(m.from_user.id)
    bot.send_message(m.chat.id,f"💰 Balance: ${users[uid]['balance']}")

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
    bot.send_message(m.chat.id,f"""
🆔 TELEGRAM ID: {uid}
🔐 USER TOKEN: {users[uid]['token']}
""")

# ---------------- COSTUMER ----------------

@bot.message_handler(func=lambda m:m.text=="☎️ COSTUMER")
def cus(m):
    bot.send_message(m.chat.id,"Support: @scholes1")

# ---------------- WITHDRAW MENU ----------------

@bot.message_handler(func=lambda m:m.text=="💸 WITHDRAWAL")
def wdmenu(m):

    kb=InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("USDT-BEP20",callback_data="usdt"),
        InlineKeyboardButton("CANCEL",callback_data="cancel")
    )

    bot.send_message(m.chat.id,"Select method",reply_markup=kb)

@bot.callback_query_handler(func=lambda c:c.data=="cancel")
def cancel(c):
    bot.edit_message_text("❌ Cancelled",c.message.chat.id,c.message.message_id)

# ---------------- WITHDRAW PROCESS ----------------

@bot.callback_query_handler(func=lambda c:c.data=="usdt")
def usdt(c):

    uid=str(c.from_user.id)

    if users[uid]["balance"]<0.5:
        return bot.answer_callback_query(c.id,"Minimum $0.5")

    msg=bot.send_message(c.message.chat.id,"Send USDT Address")
    bot.register_next_step_handler(msg,wdaddress)

def wdaddress(m):

    uid=str(m.from_user.id)
    bal=users[uid]["balance"]
    wid=random.randint(10000,99999)

    withdraws.append({
        "id":wid,
        "user":uid,
        "amount":bal,
        "time":str(datetime.now()),
        "status":"pending"
    })

    users[uid]["balance"]=0
    save("users.json",users)
    save("withdraws.json",withdraws)

    bot.send_message(m.chat.id,f"""
✅ Request #{wid} Sent!
💵 Amount: ${bal}
🧾 Net Due: ${bal}
⏳ Pending approval
🕒 6–12 hours
""")

    kb=InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("✅ CONFIRM",callback_data=f"confirm_{wid}"),
        InlineKeyboardButton("❌ REJECT",callback_data=f"reject_{wid}")
    )
    kb.add(InlineKeyboardButton("🚫 BAN",callback_data=f"ban_{uid}"))

    bot.send_message(ADMIN_ID,f"""
💳 NEW WITHDRAW

User: {uid}
Amount: ${bal}
Request ID: {wid}
Referrals: {users[uid]['refs']}
""",reply_markup=kb)

# ---------------- ADMIN PANEL BUTTON ----------------

@bot.message_handler(func=lambda m:m.text=="👑 ADMIN PANEL")
def admin(m):

    if m.from_user.id!=ADMIN_ID:
        return

    kb=InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("📊 Stats",callback_data="stats"))
    kb.add(InlineKeyboardButton("📢 Broadcast",callback_data="broadcast"))
    kb.add(InlineKeyboardButton("⭐ Send Rating",callback_data="rating"))
    kb.add(InlineKeyboardButton("💳 Withdrawal Check",callback_data="wdcheck"))
    kb.add(InlineKeyboardButton("🚫 Unban",callback_data="unban"))

    bot.send_message(m.chat.id,"Admin Panel",reply_markup=kb)

# ---------------- ADMIN ACTIONS ----------------

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
            w["status"]="rejected"
            users[w["user"]]["balance"]+=w["amount"]
            bot.send_message(int(w["user"]),"❌ Withdrawal Rejected")
    save("withdraws.json",withdraws)
    save("users.json",users)

@bot.callback_query_handler(func=lambda c:c.data.startswith("ban"))
def ban(c):
    uid=c.data.split("_")[1]
    users[uid]["banned"]=True
    save("users.json",users)

# ---------------- WITHDRAW CHECK ----------------

@bot.callback_query_handler(func=lambda c:c.data=="wdcheck")
def wdcheck(c):
    msg=bot.send_message(c.message.chat.id,"Send Request ID")
    bot.register_next_step_handler(msg,wdcheck2)

def wdcheck2(m):
    wid=int(m.text)
    for w in withdraws:
        if w["id"]==wid:
            bot.send_message(m.chat.id,str(w))

# ---------------- UNBAN ----------------

@bot.callback_query_handler(func=lambda c:c.data=="unban")
def unban(c):
    msg=bot.send_message(c.message.chat.id,"Send User ID")
    bot.register_next_step_handler(msg,unban2)

def unban2(m):
    users[m.text]["banned"]=False
    save("users.json",users)

# ---------------- STATS ----------------

@bot.callback_query_handler(func=lambda c:c.data=="stats")
def stats(c):

    total=len(users)
    totalbal=sum(users[u]["balance"] for u in users)

    bot.send_message(c.message.chat.id,f"""
Users: {total}
Total Balance: ${totalbal}
""")

# ---------------- RATING ----------------

@bot.callback_query_handler(func=lambda c:c.data=="rating")
def rating(c):

    kb=InlineKeyboardMarkup()
    for i in range(1,6):
        kb.add(InlineKeyboardButton(f"{i} ⭐",callback_data=f"rate_{i}"))

    for u in users:
        try:
            bot.send_message(int(u),"Rate our bot",reply_markup=kb)
        except:
            pass

@bot.callback_query_handler(func=lambda c:c.data.startswith("rate_"))
def rate(c):
    r=c.data.split("_")[1]
    bot.send_message(ADMIN_ID,f"{c.from_user.first_name} rated {r}⭐")
    bot.answer_callback_query(c.id,"Thanks 😍")

# ---------------- BROADCAST ----------------

@bot.callback_query_handler(func=lambda c:c.data=="broadcast")
def bc(c):
    msg=bot.send_message(c.message.chat.id,"Send message")
    bot.register_next_step_handler(msg,bc2)

def bc2(m):
    for u in users:
        try:
            bot.copy_message(int(u),m.chat.id,m.message_id)
        except:
            pass

# ---------------- DOWNLOADER ----------------

def download(chat,url):

    if "tiktok.com" in url and "/photo/" in url:
        html=requests.get(url).text
        soup=BeautifulSoup(html,"html.parser")
        img=soup.find("meta",property="og:image")["content"]
        bot.send_photo(chat,img)
        return

    ydl={"outtmpl":"vid.%(ext)s","format":"mp4"}
    with yt_dlp.YoutubeDL(ydl) as y:
        info=y.extract_info(url,download=True)
        file=y.prepare_filename(info)

    bot.send_video(chat,open(file,"rb"))
    os.remove(file)

@bot.message_handler(func=lambda m:"http" in m.text)
def link(m):
    bot.send_message(m.chat.id,"Downloading...")
    download(m.chat.id,m.text)

# ---------------- RUN ----------------

bot.infinity_polling()
