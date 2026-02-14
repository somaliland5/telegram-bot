import os, json, random, time, re, requests
from datetime import datetime
from telebot import TeleBot, types
import yt_dlp

TOKEN = os.getenv("TOKEN")
ADMIN_ID = 7983838654
DATA_FILE = "users.json"

bot = TeleBot(TOKEN)

# ---------------- DATABASE ----------------
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE,"w") as f:
        json.dump({"users":{}, "week_reset":time.time()},f)

def load_db():
    with open(DATA_FILE) as f:
        return json.load(f)

def save_db(db):
    with open(DATA_FILE,"w") as f:
        json.dump(db,f,indent=4)

def create_user(uid):
    return {
        "balance":0,"points":0,"weekly_points":0,
        "referrals":0,"bot_id":str(random.randint(1000000000,9999999999)),
        "last_bonus":0,"banned":False,"joined":datetime.now().strftime("%Y-%m-%d")
    }

def get_rank(points):
    if points >= 500: return "💎 Diamond"
    if points >= 250: return "🥇 Gold"
    if points >= 100: return "🥈 Silver"
    if points >= 50: return "🥉 Bronze"
    return "🆕 Newbie"

# ---------------- MENU ----------------
def main_menu(chat, admin=False):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("💰 Balance","🔗 Referral")
    kb.add("💸 Withdraw","🎁 Random Bonus")
    kb.add("🏆 Weekly Rank","👤 Profile")
    kb.add("🆔 Get My ID","📞 Customer")
    if admin: kb.add("⚙️ Admin Panel")
    bot.send_message(chat,"Main Menu",reply_markup=kb)

# ---------------- START ----------------
@bot.message_handler(commands=['start'])
def start(m):
    db = load_db()
    uid = str(m.from_user.id)
    ref = m.text.split()[1] if len(m.text.split())>1 else None
    if uid not in db["users"]:
        db["users"][uid]=create_user(uid)
        if ref and ref in db["users"] and ref != uid:
            db["users"][ref]["balance"]+=0.5
            db["users"][ref]["points"]+=5
            db["users"][ref]["weekly_points"]+=5
            db["users"][ref]["referrals"]+=1
            bot.send_message(ref,"🎉 You earned $0.5 + 5 Points")
    save_db(db)
    bot.send_message(uid,"👋 Welcome Downloader Reward Bot PRO")
    main_menu(uid,m.from_user.id==ADMIN_ID)

# ---------------- PROFILE ----------------
@bot.message_handler(func=lambda m:m.text=="👤 Profile")
def profile(m):
    db=load_db()
    u=db["users"][str(m.from_user.id)]
    bot.send_message(m.chat.id,f"""
👤 USER PROFILE
💰 Balance: ${u['balance']}
⭐ Points: {u['points']}
🏅 Rank: {get_rank(u['points'])}
👥 Referrals: {u['referrals']}
📅 Joined: {u['joined']}
""")

# ---------------- BALANCE ----------------
@bot.message_handler(func=lambda m:m.text=="💰 Balance")
def balance(m):
    db=load_db()
    u=db["users"][str(m.from_user.id)]
    bot.send_message(m.chat.id,f"💰 Balance: ${u['balance']}")

# ---------------- REFERRAL ----------------
@bot.message_handler(func=lambda m:m.text=="🔗 Referral")
def referral(m):
    db=load_db()
    uid=str(m.from_user.id)
    link=f"https://t.me/{bot.get_me().username}?start={uid}"
    bot.send_message(m.chat.id,f"{link}\nReferrals: {db['users'][uid]['referrals']}")

# ---------------- RANDOM BONUS ----------------
@bot.message_handler(func=lambda m:m.text=="🎁 Random Bonus")
def bonus(m):
    db=load_db()
    uid=str(m.from_user.id)
    if time.time()-db["users"][uid]["last_bonus"]<43200:
        return bot.send_message(m.chat.id,"❌ Only every 12 hours")
    amount=round(random.uniform(0.01,0.1),2)
    db["users"][uid]["balance"]+=amount
    db["users"][uid]["last_bonus"]=time.time()
    save_db(db)
    bot.send_message(m.chat.id,f"🎁 You won ${amount}")

# ---------------- WEEKLY RANK ----------------
@bot.message_handler(func=lambda m:m.text=="🏆 Weekly Rank")
def weekly_rank(m):
    db=load_db()
    top=sorted(db["users"].items(),key=lambda x:x[1]["weekly_points"],reverse=True)[:10]
    msg="🏆 Weekly Leaderboard\n"
    for i,(uid,data) in enumerate(top,1):
        msg+=f"{i}. {uid} — {data['weekly_points']} pts\n"
    bot.send_message(m.chat.id,msg)

# ---------------- WITHDRAW ----------------
@bot.message_handler(func=lambda m:m.text=="💸 Withdraw")
def withdraw_menu(m):
    kb=types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("USDT-BEP20","Cancel")
    bot.send_message(m.chat.id,"Select Method",reply_markup=kb)

@bot.message_handler(func=lambda m:m.text=="USDT-BEP20")
def ask_amount(m):
    msg=bot.send_message(m.chat.id,"Enter Amount")
    bot.register_next_step_handler(msg,withdraw_amount)

def withdraw_amount(m):
    db=load_db()
    uid=str(m.from_user.id)
    try: amount=float(m.text)
    except: return bot.send_message(m.chat.id,"Invalid number")
    if db["users"][uid]["balance"]<amount:
        return bot.send_message(m.chat.id,"❌ Insufficient balance")
    msg=bot.send_message(m.chat.id,"Enter USDT Address starting with 0x")
    bot.register_next_step_handler(msg,withdraw_address,amount)

def withdraw_address(m,amount):
    if not m.text.startswith("0x"):
        return bot.send_message(m.chat.id,"❌ Invalid address")
    db=load_db()
    uid=str(m.from_user.id)
    db["users"][uid]["balance"]-=amount
    db["users"][uid]["points"]+=10
    db["users"][uid]["weekly_points"]+=10
    save_db(db)
    wid=random.randint(10000,99999)
    kb=types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("CONFIRM",callback_data=f"c_{uid}_{amount}_{wid}"))
    kb.add(types.InlineKeyboardButton("REJECT",callback_data=f"r_{uid}_{amount}_{wid}"))
    kb.add(types.InlineKeyboardButton("BAN",callback_data=f"b_{uid}"))
    bot.send_message(ADMIN_ID,f"💸 Withdrawal\nUser:{uid}\nAmount:${amount}\nID:{wid}\nAddress:{m.text}",reply_markup=kb)
    bot.send_message(uid,"✅ Request sent (2‑12 hours)")

# ---------------- CALLBACK ----------------
@bot.callback_query_handler(func=lambda c:True)
def callback(c):
    db=load_db()
    d=c.data.split("_")
    if d[0]=="c":
        bot.send_message(d[1],f"💸 Payment Sent ${d[2]} ID:{d[3]}")
    if d[0]=="r":
        db["users"][d[1]]["balance"]+=float(d[2])
        save_db(db)
        bot.send_message(d[1],"❌ Rejected")
    if d[0]=="b":
        db["users"][d[1]]["banned"]=True
        save_db(db)

# ---------------- DOWNLOAD ----------------
def download_media(url,chat):
    try:
        opts={"format":"best","outtmpl":"media_%(id)s.%(ext)s","quiet":True,"noplaylist":False}
        with yt_dlp.YoutubeDL(opts) as ydl:
            info=ydl.extract_info(url,download=True)
        files=[]
        if "entries" in info:
            for e in info["entries"]:
                files.append(ydl.prepare_filename(e))
        else:
            files.append(ydl.prepare_filename(info))
        for f in files:
            if f.endswith(("jpg","jpeg","png","webp")):
                bot.send_photo(chat,open(f,"rb"))
            else:
                bot.send_video(chat,open(f,"rb"))
            os.remove(f)
    except:
        # fallback slideshow
        html=requests.get(url,headers={"User-Agent":"Mozilla/5.0"}).text
        imgs=re.findall(r'https://[^"]+\.jpg',html)
        if imgs:
            for i in imgs[:10]:
                bot.send_photo(chat,requests.get(i).content)
        else:
            bot.send_message(chat,"❌ Download failed")

@bot.message_handler(func=lambda m:m.text.startswith("http"))
def link(m):
    bot.send_message(m.chat.id,"⏳ Downloading...")
    download_media(m.text,m.chat.id)

# ---------------- ADMIN PANEL ----------------
@bot.message_handler(func=lambda m:m.text=="⚙️ Admin Panel")
def admin_panel(m):
    if m.from_user.id!=ADMIN_ID:return
    kb=types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📊 Stats","🔙 Back")
    bot.send_message(m.chat.id,"Admin Panel",reply_markup=kb)

@bot.message_handler(func=lambda m:m.text=="📊 Stats")
def stats(m):
    if m.from_user.id!=ADMIN_ID:return
    db=load_db()
    bot.send_message(m.chat.id,f"Users: {len(db['users'])}")

@bot.message_handler(func=lambda m:m.text=="🔙 Back")
def back(m):
    main_menu(m.chat.id,True)

@bot.message_handler(func=lambda m:m.text=="📞 Customer")
def customer(m):
    bot.send_message(m.chat.id,"Contact 👉 @scholes1")

@bot.message_handler(func=lambda m:m.text=="🆔 Get My ID")
def getid(m):
    db=load_db()
    u=db["users"][str(m.from_user.id)]
    bot.send_message(m.chat.id,f"Telegram ID: {m.from_user.id}\nBOT ID: {u['bot_id']}")

print("BOT PRO RUNNING")
bot.infinity_polling()
