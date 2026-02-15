import telebot
from telebot.types import *
import os
import json
import random
import yt_dlp
import requests
from bs4 import BeautifulSoup
from datetime import datetime

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 7983838654

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# ---------------- DATABASE ----------------

def load_json(name, default):
    if not os.path.exists(name):
        return default
    return json.load(open(name))

def save_json(name,data):
    json.dump(data,open(name,"w"),indent=4)

users = load_json("users.json",{})
withdraws = load_json("withdraws.json",[])

# ---------------- MENUS ----------------

def user_menu(uid):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)

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
            "bot_id":str(random.randint(10000000000,99999999999)),
            "month":datetime.now().month,
            "banned":False
        }

        # Referral reward
        if ref:
            for u in users:
                if users[u]["ref"]==ref:
                    users[u]["refs"]+=1
                    users[u]["balance"]+=0.2
                    bot.send_message(int(u),
                    f"🎉 Congratulations!\nNew referral joined.\nYou earned $0.2")

        save_json("users.json",users)

    bot.send_message(m.chat.id,"👋 Welcome",reply_markup=user_menu(uid))

# ---------------- BALANCE ----------------

@bot.message_handler(func=lambda m:m.text=="💰 BALANCE")
def bal(m):
    uid=str(m.from_user.id)
    bot.send_message(m.chat.id,f"💰 Balance: ${users[uid]['balance']:.2f}")

# ---------------- GET ID ----------------

@bot.message_handler(func=lambda m:m.text=="🆔 GET MY ID")
def myid(m):

    uid=str(m.from_user.id)

    bot.send_message(m.chat.id,f"""
🆔 USER ID: {uid}
🤖 BOT ID: {users[uid]['bot_id']}
""")

# ---------------- REFERAL ----------------

@bot.message_handler(func=lambda m:m.text=="👥 REFERAL")
def ref(m):

    uid=str(m.from_user.id)

    link=f"https://t.me/{bot.get_me().username}?start={users[uid]['ref']}"

    bot.send_message(m.chat.id,
    f"🔗 Referral Link:\n{link}\n\n👥 Total referrals: {users[uid]['refs']}")

# ---------------- WITHDRAW ----------------

@bot.message_handler(func=lambda m:m.text=="💸 WITHDRAWAL")
def wd(m):
    msg=bot.send_message(m.chat.id,"Enter USDT BEP20 address")
    bot.register_next_step_handler(msg,wd2)

def wd2(m):

    uid=str(m.from_user.id)
    bal=users[uid]["balance"]

    if not m.text.startswith("0x"):
        return bot.send_message(m.chat.id,"❌ Invalid address")

    if bal<0.5:
        return bot.send_message(m.chat.id,"Minimum withdrawal $0.5")

    wid=random.randint(10000,99999)

    withdraws.append({
        "id":wid,
        "user":uid,
        "amount":bal,
        "status":"pending"
    })

    users[uid]["balance"]=0

    save_json("users.json",users)
    save_json("withdraws.json",withdraws)

    bot.send_message(m.chat.id,f"""
✅ Request #{wid} Sent!
💵 Amount: ${bal:.2f}
💸 Fee (0.00%): -$0.00
🧾 Net Due: ${bal:.2f}
⏳ Your request is pending approval
🕒 Pending time: 6–12 hours
Please be patient 😕
""")

    bot.send_message(ADMIN_ID,f"""
💳 NEW WITHDRAW

User: {uid}
BOT ID: {users[uid]['bot_id']}
Referral: {users[uid]['refs']}
Amount: ${bal}

CONFIRM {wid}
REJECT {wid}
BAN {uid}
""")

# ---------------- ADMIN PANEL ----------------

@bot.message_handler(func=lambda m:m.text=="👑 ADMIN PANEL")
def admin_panel(m):

    if m.from_user.id!=ADMIN_ID:
        return

    kb=InlineKeyboardMarkup()

    kb.add(InlineKeyboardButton("📊 Stats",callback_data="stats"))
    kb.add(InlineKeyboardButton("⭐ Send Rating",callback_data="rate"))
    kb.add(InlineKeyboardButton("📢 Broadcast",callback_data="broadcast"))
    kb.add(InlineKeyboardButton("➕ Add Balance",callback_data="addbal"))

    bot.send_message(m.chat.id,"👑 ADMIN PANEL",reply_markup=kb)

# ---------------- STATS ----------------

@bot.callback_query_handler(func=lambda c:c.data=="stats")
def stats(c):

    total=len(users)
    monthly=sum(1 for u in users if users[u]["month"]==datetime.now().month)
    totalbal=sum(users[u]["balance"] for u in users)

    totalwd=sum(w["amount"] for w in withdraws)

    bot.send_message(c.message.chat.id,f"""
📊 BOT STATS

👥 Users: {total}
📆 Monthly: {monthly}
💰 Total Balance: ${totalbal:.2f}
💳 Total Withdrawn: ${totalwd:.2f}
""")

# ---------------- RATING ----------------

@bot.callback_query_handler(func=lambda c:c.data=="rate")
def send_rate(c):

    kb=InlineKeyboardMarkup()

    for i in range(1,6):
        kb.add(InlineKeyboardButton(f"{i} ⭐",callback_data=f"rate_{i}"))

    for u in users:
        try:
            bot.send_message(int(u),"⭐ Please rate our bot",reply_markup=kb)
        except:
            pass

@bot.callback_query_handler(func=lambda c:c.data.startswith("rate_"))
def rate_recv(c):

    rate=c.data.split("_")[1]
    name=c.from_user.first_name

    bot.send_message(ADMIN_ID,f"⭐ New Rate\nUser: {name}\nRate: {rate}")

    bot.answer_callback_query(c.id,"Thanks your Rate 😍")

# ---------------- BROADCAST ----------------

@bot.callback_query_handler(func=lambda c:c.data=="broadcast")
def bc(c):

    msg=bot.send_message(c.message.chat.id,"Send message")
    bot.register_next_step_handler(msg,bc2)

def bc2(m):

    for u in users:
        try:
            bot.send_message(int(u),m.text)
        except:
            pass

# ---------------- ADD BALANCE ----------------

@bot.callback_query_handler(func=lambda c:c.data=="addbal")
def addbal(c):
    msg=bot.send_message(c.message.chat.id,"Send BOT ID and amount")
    bot.register_next_step_handler(msg,addbal2)

def addbal2(m):

    bid,amt=m.text.split()

    for u in users:
        if users[u]["bot_id"]==bid:
            users[u]["balance"]+=float(amt)
            save_json("users.json",users)

            bot.send_message(int(u),f"💰 Admin added ${amt}")
            bot.send_message(m.chat.id,"Done")

# ---------------- WITHDRAW CONTROL ----------------

@bot.message_handler(func=lambda m:m.text.startswith("CONFIRM"))
def confirm(m):

    if m.from_user.id!=ADMIN_ID:
        return

    wid=int(m.text.split()[1])

    for w in withdraws:
        if w["id"]==wid:
            w["status"]="paid"
            bot.send_message(int(w["user"]),"✅ Withdrawal Approved")

    save_json("withdraws.json",withdraws)

# ---------------- MEDIA DOWNLOADER ----------------

def download_media(chat_id,url):

    try:

        if "tiktok.com" in url:

            html=requests.get(url,headers={"User-Agent":"Mozilla"}).text
            soup=BeautifulSoup(html,"html.parser")

            imgs=soup.find_all("meta",property="og:image")

            for img in imgs:
                link=img["content"]
                data=requests.get(link).content
                open("tt.jpg","wb").write(data)
                bot.send_photo(chat_id,open("tt.jpg","rb"))

            return

        ydl_opts={"outtmpl":"vid.%(ext)s","format":"mp4"}

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info=ydl.extract_info(url,download=True)
            file=ydl.prepare_filename(info)

        bot.send_video(chat_id,open(file,"rb"))
        os.remove(file)

    except Exception as e:
        bot.send_message(chat_id,str(e))

@bot.message_handler(func=lambda m:"http" in m.text)
def links(m):
    bot.send_message(m.chat.id,"⏳ Downloading...")
    download_media(m.chat.id,m.text)

# ---------------- RUN ----------------

bot.infinity_polling()
