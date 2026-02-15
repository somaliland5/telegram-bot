import telebot
from telebot.types import *
import os
import json
import random
import yt_dlp
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# ================= TOKEN =================

TOKEN = os.environ.get("BOT_TOKEN")

if not TOKEN:
    raise Exception("BOT_TOKEN not found in Railway Variables")

ADMIN_ID = 7983838654

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# ================= DATABASE SAFE =================

def load_json(name, default):
    if not os.path.exists(name):
        with open(name,"w") as f:
            json.dump(default,f)
        return default
    return json.load(open(name))

def save_json(name, data):
    with open(name,"w") as f:
        json.dump(data,f,indent=4)

users = load_json("users.json", {})
withdraws = load_json("withdraws.json", [])
ratings = load_json("ratings.json", [])

# ================= MENUS =================

def user_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("💰 BALANCE","💸 WITHDRAWAL")
    kb.add("👥 REFERAL","🆔 GET MY ID")
    kb.add("☎️ COSTUMER")
    return kb

def admin_panel():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("📊 Stats",callback_data="stats"))
    kb.add(InlineKeyboardButton("⭐ Send Rate",callback_data="rate_send"))
    kb.add(InlineKeyboardButton("📢 Broadcast",callback_data="broadcast"))
    return kb

# ================= START =================

@bot.message_handler(commands=['start'])
def start(m):

    uid=str(m.from_user.id)
    args=m.text.split()

    if uid not in users:

        users[uid]={
            "balance":0,
            "ref":str(random.randint(100000,999999)),
            "bot_id":str(random.randint(10000000000,99999999999)),
            "refs":0,
            "month":datetime.now().month
        }

        # Referral
        if len(args)>1:
            ref=args[1]

            for u in users:
                if users[u]["ref"]==ref:
                    users[u]["balance"]+=0.2
                    users[u]["refs"]+=1

                    bot.send_message(int(u),
                    "🎉 Congratulations!\nYou invited new user & earned $0.2")

        save_json("users.json",users)

    bot.send_message(m.chat.id,"👋 Welcome",reply_markup=user_menu())

    if m.from_user.id==ADMIN_ID:
        bot.send_message(m.chat.id,"👑 Admin Panel",reply_markup=admin_panel())

# ================= BALANCE =================

@bot.message_handler(func=lambda m:m.text=="💰 BALANCE")
def bal(m):
    uid=str(m.from_user.id)
    bot.send_message(m.chat.id,f"💰 Balance: ${users[uid]['balance']:.2f}")

# ================= GET ID =================

@bot.message_handler(func=lambda m:m.text=="🆔 GET MY ID")
def myid(m):
    uid=str(m.from_user.id)

    bot.send_message(m.chat.id,f"""
👤 TELEGRAM ID: <code>{uid}</code>
🆔 BOT USER ID: <code>{users[uid]['bot_id']}</code>
""")

# ================= REFERRAL =================

@bot.message_handler(func=lambda m:m.text=="👥 REFERAL")
def ref(m):
    uid=str(m.from_user.id)

    link=f"https://t.me/{bot.get_me().username}?start={users[uid]['ref']}"

    bot.send_message(m.chat.id,f"""
🔗 Referral Link:
{link}

👥 Invited: {users[uid]['refs']}
""")

# ================= WITHDRAW =================

@bot.message_handler(func=lambda m:m.text=="💸 WITHDRAWAL")
def withdraw(m):
    msg=bot.send_message(m.chat.id,"Send USDT BEP20 address")
    bot.register_next_step_handler(msg,withdraw2)

def withdraw2(m):

    uid=str(m.from_user.id)
    address=m.text

    if not address.startswith("0x"):
        bot.send_message(m.chat.id,"❌ Invalid address")
        return

    bal=users[uid]["balance"]

    if bal < 0.5:
        bot.send_message(m.chat.id,"Minimum withdrawal $0.5")
        return

    wid=random.randint(10000,99999)

    withdraws.append({
        "id":wid,
        "user":uid,
        "amount":bal,
        "address":address
    })

    users[uid]["balance"]=0

    save_json("withdraws.json",withdraws)
    save_json("users.json",users)

    # USER MESSAGE
    bot.send_message(m.chat.id,f"""
✅ Request #{wid} Sent!

💵 Amount: ${bal:.2f}
💸 Fee (0.00%): -$0.00
🧾 Net Due: ${bal:.2f}
⏳ Pending approval
🕒 Pending time: 6–12 hours
""")

    # ADMIN MESSAGE
    bot.send_message(ADMIN_ID,f"""
📤 Withdrawal Request

🆔 Request ID: {wid}
👤 User: {uid}
🤖 Bot ID: {users[uid]['bot_id']}
👥 Referral: {users[uid]['refs']}
💵 Amount: ${bal}
""")

# ================= RATING =================

@bot.callback_query_handler(func=lambda c:c.data=="rate_send")
def send_rate(c):

    if c.from_user.id!=ADMIN_ID:
        return

    kb=InlineKeyboardMarkup(row_width=5)

    for i in range(1,6):
        kb.add(InlineKeyboardButton("⭐"*i,callback_data=f"rate_{i}"))

    for u in users:
        try:
            bot.send_message(int(u),"⭐ Rate our bot",reply_markup=kb)
        except:
            pass

@bot.callback_query_handler(func=lambda c:c.data.startswith("rate_"))
def save_rate(c):

    rate=int(c.data.split("_")[1])
    name=c.from_user.first_name

    ratings.append({
        "name":name,
        "rate":rate
    })

    save_json("ratings.json",ratings)

    bot.answer_callback_query(c.id,"Thanks your Rate 😍")

    bot.send_message(ADMIN_ID,
    f"⭐ New Rate\nUser: {name}\nRate: {rate}")

# ================= STATS =================

@bot.callback_query_handler(func=lambda c:c.data=="stats")
def stats(c):

    if c.from_user.id!=ADMIN_ID:
        return

    total_users=len(users)
    monthly=sum(1 for u in users if users[u]["month"]==datetime.now().month)
    total_bal=sum(users[u]["balance"] for u in users)

    bot.send_message(c.message.chat.id,f"""
📊 BOT STATS

👥 Total Users: {total_users}
📆 Monthly Users: {monthly}
💰 Total Balance: ${total_bal:.2f}
⭐ Total Ratings: {len(ratings)}
""")

# ================= BROADCAST =================

@bot.callback_query_handler(func=lambda c:c.data=="broadcast")
def bc(c):

    if c.from_user.id!=ADMIN_ID:
        return

    msg=bot.send_message(c.message.chat.id,"Send message or media")
    bot.register_next_step_handler(msg,bc2)

def bc2(m):

    for u in users:
        try:
            bot.copy_message(int(u),m.chat.id,m.message_id)
        except:
            pass

# ================= MEDIA DOWNLOADER =================

def download_media(chat_id,url):

    try:
        # TikTok photo
        if "photo" in url and "tiktok" in url:
            html=requests.get(url,headers={"User-Agent":"Mozilla"}).text
            soup=BeautifulSoup(html,"html.parser")
            img=soup.find("meta",property="og:image")["content"]

            data=requests.get(img).content
            open("img.jpg","wb").write(data)

            bot.send_photo(chat_id,open("img.jpg","rb"))
            os.remove("img.jpg")
            return

        # Video / Shorts
        ydl_opts={"outtmpl":"video.%(ext)s","format":"mp4"}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info=ydl.extract_info(url,download=True)
            file=ydl.prepare_filename(info)

        bot.send_video(chat_id,open(file,"rb"))
        os.remove(file)

    except Exception as e:
        bot.send_message(chat_id,str(e))

@bot.message_handler(func=lambda m:m.text and "http" in m.text)
def links(m):
    bot.send_message(m.chat.id,"⏳ Downloading...")
    download_media(m.chat.id,m.text)

# ================= RUN BOT =================

print("Bot Started...")

bot.infinity_polling(skip_pending=True)
