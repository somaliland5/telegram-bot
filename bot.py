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

bot = telebot.TeleBot(TOKEN)

# ================= DATABASE =================

def load_json(name, default):
    if not os.path.exists(name):
        return default
    return json.load(open(name))

def save_json(name, data):
    json.dump(data, open(name,"w"), indent=4)

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

# ================= ADMIN PANEL =================

def admin_panel():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("📊 Stats",callback_data="stats"))
    kb.add(InlineKeyboardButton("⭐ Rating",callback_data="rate_send"))
    kb.add(InlineKeyboardButton("📢 Broadcast",callback_data="broadcast"))
    kb.add(InlineKeyboardButton("➕ Add Balance",callback_data="addbal"))
    kb.add(InlineKeyboardButton("🚫 Ban",callback_data="ban"))
    kb.add(InlineKeyboardButton("✅ Unban",callback_data="unban"))
    kb.add(InlineKeyboardButton("💳 Withdrawal Check",callback_data="wdcheck"))
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
            "invited":None,
            "banned":False,
            "month":datetime.now().month,
            "refs":0
        }

        # Referral
        if len(args)>1:
            ref=args[1]

            for u in users:
                if users[u]["ref"]==ref:
                    users[u]["balance"]+=0.2
                    users[u]["refs"]+=1
                    bot.send_message(int(u),
                    f"🎉 Congratulations!\nYou invited a new user and earned $0.2")
                    users[uid]["invited"]=u

        save_json("users.json",users)

    bot.send_message(m.chat.id,"Welcome 😊",reply_markup=user_menu())

    # ADMIN BUTTON
    if m.from_user.id==ADMIN_ID:
        bot.send_message(m.chat.id,"Admin Panel",reply_markup=admin_panel())

# ================= GET ID =================

@bot.message_handler(func=lambda m:m.text=="🆔 GET MY ID")
def myid(m):
    uid=str(m.from_user.id)

    bot.send_message(m.chat.id,f"""
👤 TELEGRAM ID: {uid}
🆔 USER BOT ID: {users[uid]['bot_id']}
""")

# ================= BALANCE =================

@bot.message_handler(func=lambda m:m.text=="💰 BALANCE")
def bal(m):
    uid=str(m.from_user.id)
    bot.send_message(m.chat.id,f"💰 Balance: ${users[uid]['balance']:.2f}")

# ================= REFERRAL =================

@bot.message_handler(func=lambda m:m.text=="👥 REFERAL")
def ref(m):
    uid=str(m.from_user.id)
    link=f"https://t.me/{bot.get_me().username}?start={users[uid]['ref']}"

    bot.send_message(m.chat.id,f"""
🔗 Your Link:
{link}

👥 Total Invited: {users[uid]['refs']}
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
        bot.send_message(m.chat.id,"Invalid address")
        return

    bal=users[uid]["balance"]
    if bal<0.5:
        bot.send_message(m.chat.id,"Minimum withdrawal $0.5")
        return

    wid=random.randint(10000,99999)

    withdraws.append({
        "id":wid,
        "user":uid,
        "amount":bal,
        "address":address,
        "status":"pending"
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
⏳ Your request is pending approval
🕒 Pending time: 6–12 hours
Please be patient 😕
""")

    # ADMIN MESSAGE
    bot.send_message(ADMIN_ID,f"""
📤 Withdrawal Request

Request ID: {wid}
User: {uid}
Bot ID: {users[uid]['bot_id']}
Referral Count: {users[uid]['refs']}
Amount: ${bal}

Reply:
CONFIRM {wid}
REJECT {wid}
BAN {uid}
""")

# ================= ADMIN ACTIONS =================

@bot.message_handler(func=lambda m:m.text.startswith("CONFIRM"))
def confirm(m):
    if m.from_user.id!=ADMIN_ID:return
    wid=int(m.text.split()[1])

    for w in withdraws:
        if w["id"]==wid:
            w["status"]="paid"
            save_json("withdraws.json",withdraws)
            bot.send_message(int(w["user"]),"✅ Withdrawal Approved")

@bot.message_handler(func=lambda m:m.text.startswith("REJECT"))
def reject(m):
    if m.from_user.id!=ADMIN_ID:return
    wid=int(m.text.split()[1])

    for w in withdraws:
        if w["id"]==wid:
            bot.send_message(int(w["user"]),"❌ Withdrawal Rejected")

@bot.message_handler(func=lambda m:m.text.startswith("BAN"))
def banuser(m):
    if m.from_user.id!=ADMIN_ID:return
    uid=m.text.split()[1]
    users[uid]["banned"]=True
    save_json("users.json",users)

# ================= RATING =================

@bot.callback_query_handler(func=lambda c:c.data=="rate_send")
def send_rate(c):
    if c.from_user.id!=ADMIN_ID:return

    kb=InlineKeyboardMarkup(row_width=5)
    for i in range(1,6):
        kb.add(InlineKeyboardButton("⭐"*i,callback_data=f"rate_{i}"))

    for u in users:
        try:
            bot.send_message(int(u),"Rate our bot 👇",reply_markup=kb)
        except:pass

@bot.callback_query_handler(func=lambda c:c.data.startswith("rate_"))
def rate_save(c):

    rate=int(c.data.split("_")[1])
    name=c.from_user.first_name
    uid=str(c.from_user.id)

    ratings.append({"user":uid,"name":name,"rate":rate})
    save_json("ratings.json",ratings)

    bot.answer_callback_query(c.id,"Thanks your Rate 😍")

    bot.send_message(ADMIN_ID,f"""
⭐ New Rating

User: {name}
ID: {uid}
Rate: {rate}⭐
""")

# ================= STATS =================

@bot.callback_query_handler(func=lambda c:c.data=="stats")
def stats(c):
    if c.from_user.id!=ADMIN_ID:return

    total_users=len(users)
    total_bal=sum(users[u]["balance"] for u in users)
    total_wd=len(withdraws)
    monthly=sum(1 for u in users if users[u]["month"]==datetime.now().month)

    bot.send_message(c.message.chat.id,f"""
📊 BOT STATS

👥 Total Users: {total_users}
📆 Monthly Users: {monthly}
💰 Total Balance: ${total_bal:.2f}
💳 Total Withdrawals: {total_wd}
⭐ Total Ratings: {len(ratings)}
""")

# ================= BROADCAST =================

@bot.callback_query_handler(func=lambda c:c.data=="broadcast")
def bc(c):
    if c.from_user.id!=ADMIN_ID:return
    msg=bot.send_message(c.message.chat.id,"Send message or media")
    bot.register_next_step_handler(msg,bc2)

def bc2(m):
    for u in users:
        try:
            bot.copy_message(int(u),m.chat.id,m.message_id)
        except:pass

# ================= TIKTOK + YOUTUBE =================

def download_media(chat_id,url):
    try:

        # TIKTOK PHOTO
        if "photo" in url and "tiktok" in url:

            html=requests.get(url,headers={"User-Agent":"Mozilla"}).text
            soup=BeautifulSoup(html,"html.parser")

            img=soup.find("meta",property="og:image")["content"]
            data=requests.get(img).content

            open("img.jpg","wb").write(data)
            bot.send_photo(chat_id,open("img.jpg","rb"))
            os.remove("img.jpg")
            return

        # VIDEO + SHORTS
        ydl_opts={"outtmpl":"vid.%(ext)s","format":"mp4"}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info=ydl.extract_info(url,download=True)
            file=ydl.prepare_filename(info)

        bot.send_video(chat_id,open(file,"rb"))
        os.remove(file)

    except Exception as e:
        bot.send_message(chat_id,str(e))

@bot.message_handler(func=lambda m:"http" in m.text)
def link(m):
    bot.send_message(m.chat.id,"Downloading...")
    download_media(m.chat.id,m.text)

bot.infinity_polling()
