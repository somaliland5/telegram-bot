import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
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

def load_users():
    if not os.path.exists("users.json"):
        return {}
    with open("users.json","r") as f:
        return json.load(f)

def save_users(data):
    with open("users.json","w") as f:
        json.dump(data,f,indent=4)

def load_withdraws():
    if not os.path.exists("withdraws.json"):
        return []
    return json.load(open("withdraws.json"))

def save_withdraws(data):
    json.dump(data, open("withdraws.json","w"), indent=4)

users = load_users()

# ================= RANDOM GENERATORS =================

def random_ref():
    return str(random.randint(1000000000,9999999999))

def random_botid():
    return str(random.randint(10000000000,99999999999))

# ================= KEYBOARDS =================

def user_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("💰 BALANCE","💸 WITHDRAWAL")
    kb.add("👥 REFERAL","🆔 GET ID")
    kb.add("☎️ COSTUMER")
    return kb

def admin_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📊 STATS","🎁 RANDOM GIFT")
    kb.add("➕ ADD BALANCE","🚫 BAN","✅ UNBAN")
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
            "ref":random_ref(),
            "bot_id":random_botid(),
            "invited":None,
            "banned":False,
            "month":datetime.now().month
        }

        # Referral reward
        if ref:
            for u in users:
                if users[u]["ref"] == ref:
                    users[u]["balance"] += 0.2
                    bot.send_message(int(u),"🎉 You earned $0.2 from referral!")
                    users[uid]["invited"] = u

        save_users(users)

    msg = """
👋 Welcome to Media Downloader Bot!

✅ Download TikTok Videos & Photos  
✅ Download YouTube Shorts & Videos  
✅ Earn money using referral system  

Use buttons below to navigate.
"""

    bot.send_message(m.chat.id,msg,reply_markup=user_menu())

    # -------- Inline ADMIN PANEL Button --------
    if m.from_user.id == ADMIN_ID:
        im = InlineKeyboardMarkup()
        im.add(InlineKeyboardButton("🛠 ADMIN PANEL", callback_data="admin_panel_inline"))
        bot.send_message(m.chat.id, "Admin Quick Panel:", reply_markup=im)

# ================= INLINE ADMIN PANEL =================

@bot.callback_query_handler(func=lambda c: c.data == "admin_panel_inline")
def inline_admin_panel(c):
    if c.from_user.id != ADMIN_ID:
        return
    im = InlineKeyboardMarkup()
    im.add(InlineKeyboardButton("⭐ Send Rating", callback_data="send_rate"))
    bot.send_message(c.message.chat.id, "Inline Admin Control:", reply_markup=im)

# ================= RATING SYSTEM =================

@bot.callback_query_handler(func=lambda c: c.data == "send_rate")
def send_rate(c):
    if c.from_user.id != ADMIN_ID:
        return

    im = InlineKeyboardMarkup(row_width=5)
    im.add(
        InlineKeyboardButton("⭐", callback_data="rate_1"),
        InlineKeyboardButton("⭐⭐", callback_data="rate_2"),
        InlineKeyboardButton("⭐⭐⭐", callback_data="rate_3"),
        InlineKeyboardButton("⭐⭐⭐⭐", callback_data="rate_4"),
        InlineKeyboardButton("⭐⭐⭐⭐⭐", callback_data="rate_5"),
    )

    for u in users:
        try:
            bot.send_message(int(u), "Fadlan Bot-ka qiimee 👇", reply_markup=im)
        except:
            pass

    bot.answer_callback_query(c.id, "Rating Sent")

@bot.callback_query_handler(func=lambda c: c.data.startswith("rate_"))
def rate_click(c):
    # user taabtay star
    bot.answer_callback_query(c.id, "Thanks your Rate 😍")

# ================= BALANCE =================

@bot.message_handler(func=lambda m: m.text=="💰 BALANCE")
def balance(m):
    uid=str(m.from_user.id)
    bal=users[uid]["balance"]
    bot.send_message(m.chat.id,f"💰 Your Balance: ${bal:.2f}")

# ================= GET ID =================

@bot.message_handler(func=lambda m: m.text=="🆔 GET ID")
def getid(m):
    uid=str(m.from_user.id)
    bot.send_message(m.chat.id,
    f"""
🆔 BOT ID: {users[uid]["bot_id"]}
👤 TELEGRAM ID: {uid}
""")

# ================= REFERAL =================

@bot.message_handler(func=lambda m: m.text=="👥 REFERAL")
def ref(m):
    uid=str(m.from_user.id)
    link=f"https://t.me/{bot.get_me().username}?start={users[uid]['ref']}"
    bot.send_message(m.chat.id,f"🔗 Your Referral Link:\n{link}")

# ================= COSTUMER =================

@bot.message_handler(func=lambda m: m.text=="☎️ COSTUMER")
def cust(m):
    bot.send_message(m.chat.id,"Contact support: @scholes1")

# ================= WITHDRAW =================

@bot.message_handler(func=lambda m: m.text=="💸 WITHDRAWAL")
def withdraw(m):
    msg=bot.send_message(m.chat.id,"Enter USDT BEP20 address starting with 0x")
    bot.register_next_step_handler(msg,withdraw_address)

def withdraw_address(m):
    address=m.text
    uid=str(m.from_user.id)

    if not address.startswith("0x"):
        bot.send_message(m.chat.id,"❌ Invalid address")
        return

    bal=users[uid]["balance"]
    if bal<0.5:
        bot.send_message(m.chat.id,"Minimum withdrawal $0.5")
        return

    wid=random.randint(10000,99999)

    withdraws=load_withdraws()
    withdraws.append({
        "id":wid,
        "user":uid,
        "bot_id":users[uid]["bot_id"],
        "amount":bal,
        "address":address,
        "status":"pending"
    })
    save_withdraws(withdraws)

    users[uid]["balance"]=0
    save_users(users)

    bot.send_message(m.chat.id,f"""
✅ Request #{wid} Sent!

💵 Amount: ${bal}
⏳ Pending approval
""")

    bot.send_message(ADMIN_ID,
    f"""
📤 Withdrawal Request

ID: {wid}
User: {uid}
BOT ID: {users[uid]["bot_id"]}
Amount: ${bal}
Address: {address}

Reply:
CONFIRM {wid}
REJECT {wid}
""")

# ================= DOWNLOADER =================

def download_media(chat_id,url):

    try:
        # TIKTOK PHOTO FIX
        if "tiktok.com" in url and "/photo/" in url:

            html=requests.get(url,headers={"User-Agent":"Mozilla"}).text
            soup=BeautifulSoup(html,"html.parser")
            img=soup.find("meta",property="og:image")["content"]

            data=requests.get(img).content
            open("tt.jpg","wb").write(data)

            bot.send_photo(chat_id,open("tt.jpg","rb"))
            os.remove("tt.jpg")
            return

        # VIDEO
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

# ================= ADMIN PANEL =================

@bot.message_handler(commands=['admin'])
def admin(m):
    if m.from_user.id==ADMIN_ID:
        bot.send_message(m.chat.id,"Admin Panel",reply_markup=admin_menu())

# STATS
@bot.message_handler(func=lambda m:m.text=="📊 STATS")
def stats(m):
    if m.from_user.id!=ADMIN_ID:return
    total=len(users)
    monthly=sum(1 for u in users if users[u]["month"]==datetime.now().month)
    totalbal=sum(users[u]["balance"] for u in users)

    bot.send_message(m.chat.id,
    f"""
👥 Users: {total}
📆 Monthly Users: {monthly}
💰 Total Balance: ${totalbal}
""")

# ADD BALANCE
@bot.message_handler(func=lambda m:m.text=="➕ ADD BALANCE")
def addbal(m):
    if m.from_user.id!=ADMIN_ID:return
    msg=bot.send_message(m.chat.id,"Send BOT ID and amount\nExample: 12345678901 2")
    bot.register_next_step_handler(msg,addbal2)

def addbal2(m):
    bid,amt=m.text.split()
    for u in users:
        if users[u]["bot_id"]==bid:
            users[u]["balance"]+=float(amt)
            save_users(users)
            bot.send_message(int(u),f"💰 Admin added ${amt}")
            bot.send_message(m.chat.id,"Done")
            return

# RANDOM GIFT
@bot.message_handler(func=lambda m:m.text=="🎁 RANDOM GIFT")
def gift(m):
    if m.from_user.id!=ADMIN_ID:return
    u=random.choice(list(users.keys()))
    users[u]["balance"]+=0.1
    save_users(users)
    bot.send_message(int(u),"🎁 You received random $0.1")

# BAN / UNBAN
@bot.message_handler(func=lambda m:m.text=="🚫 BAN")
def ban(m):
    if m.from_user.id!=ADMIN_ID:return
    msg=bot.send_message(m.chat.id,"Send BOT ID")
    bot.register_next_step_handler(msg,ban2)

def ban2(m):
    bid=m.text
    for u in users:
        if users[u]["bot_id"]==bid:
            users[u]["banned"]=True
            save_users(users)

@bot.message_handler(func=lambda m:m.text=="✅ UNBAN")
def unban(m):
    if m.from_user.id!=ADMIN_ID:return
    msg=bot.send_message(m.chat.id,"Send BOT ID")
    bot.register_next_step_handler(msg,unban2)

def unban2(m):
    bid=m.text
    for u in users:
        if users[u]["bot_id"]==bid:
            users[u]["banned"]=False
            save_users(users)

# BROADCAST (existing)
@bot.message_handler(func=lambda m:m.text=="📢 BROADCAST")
def bc(m):
    if m.from_user.id!=ADMIN_ID:return
    msg=bot.send_message(m.chat.id,"Send message")
    bot.register_next_step_handler(msg,bc2)

def bc2(m):
    for u in users:
        try:
            bot.send_message(int(u),m.text)
        except:
            pass

# WITHDRAW CONFIRM
@bot.message_handler(func=lambda m:m.text.startswith("CONFIRM"))
def confirm(m):
    if m.from_user.id!=ADMIN_ID:return
    wid=int(m.text.split()[1])
    wd=load_withdraws()

    for w in wd:
        if w["id"]==wid:
            w["status"]="paid"
            save_withdraws(wd)
            bot.send_message(int(w["user"]),"✅ Withdrawal Approved")

bot.infinity_polling()
