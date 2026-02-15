import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import os, json, random
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

# ---------------- KEYBOARDS ----------------
def user_menu(uid):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("💰 BALANCE", "💸 WITHDRAWAL")
    kb.add("👥 REFERRAL", "🆔 GET MY ID")
    kb.add("☎️ CUSTOMER")
    if int(uid)==ADMIN_ID:
        kb.add("👑 ADMIN PANEL")
    return kb

def admin_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📊 STATS", "➕ ADD BALANCE")
    kb.add("📤 BROADCAST", "💳 WITHDRAW CHECK")
    kb.add("💸 UNBAN MONEY", "🔙 BACK")
    return kb

# ---------------- START ----------------
@bot.message_handler(commands=['start'])
def start(m):
    uid = str(m.from_user.id)
    args = m.text.split()

    if uid not in users:
        ref = args[1] if len(args) > 1 else None
        users[uid] = {
            "balance":0,
            "blocked":0,
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
    bot.send_message(m.chat.id,"👋 Welcome!",reply_markup=user_menu(uid))

# ---------------- BALANCE ----------------
@bot.message_handler(func=lambda m:m.text=="💰 BALANCE")
def bal(m):
    uid = str(m.from_user.id)
    b = users[uid]["balance"]
    bl = users[uid]["blocked"]
    bot.send_message(m.chat.id,f"💰 Balance: ${b:.2f}\n⛔ Blocked: ${bl:.2f}")

# ---------------- REFERRAL ----------------
@bot.message_handler(func=lambda m:m.text=="👥 REFERRAL")
def ref(m):
    uid = str(m.from_user.id)
    link = f"https://t.me/{bot.get_me().username}?start={users[uid]['ref']}"
    bot.send_message(m.chat.id,f"🔗 {link}")

# ---------------- GET MY ID ----------------
@bot.message_handler(func=lambda m:m.text=="🆔 GET MY ID")
def gid(m):
    uid=str(m.from_user.id)
    bot.send_message(m.chat.id,
        f"🆔 TELEGRAM ID: {uid}\n🔐 USER TOKEN: {users[uid]['token']}")

# ---------------- CUSTOMER ----------------
@bot.message_handler(func=lambda m:m.text=="☎️ CUSTOMER")
def customer(m):
    bot.send_message(m.chat.id,"Support: @scholes1")

# ---------------- ADMIN PANEL ----------------
@bot.message_handler(func=lambda m:m.text=="👑 ADMIN PANEL")
def admin_panel(m):
    if m.from_user.id!=ADMIN_ID: return
    bot.send_message(m.chat.id,"👑 Admin Panel",reply_markup=admin_menu())

@bot.message_handler(func=lambda m:m.text=="🔙 BACK")
def back(m):
    uid=str(m.from_user.id)
    bot.send_message(m.chat.id,"Back",reply_markup=user_menu(uid))

# ---------------- ADD BALANCE ----------------
@bot.message_handler(func=lambda m:m.text=="➕ ADD BALANCE")
def add_bal(m):
    if m.from_user.id!=ADMIN_ID: return
    msg=bot.send_message(m.chat.id,"Send USER ID and amount\nExample: 123456 2")
    bot.register_next_step_handler(msg, add_bal2)

def add_bal2(m):
    uid, amt = m.text.split()
    amt = float(amt)
    users[uid]["balance"] += amt
    save("users.json",users)
    bot.send_message(int(uid),f"💰 Admin added ${amt}")

# ---------------- WITHDRAWAL ----------------
@bot.message_handler(func=lambda m:m.text=="💸 WITHDRAWAL")
def withdrawal_menu(m):
    uid = str(m.from_user.id)
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("USDT-BEP20"), KeyboardButton("CANCEL"))
    kb.add(KeyboardButton("MAIN MENU"))
    bot.send_message(m.chat.id,"Select withdrawal method", reply_markup=kb)

@bot.message_handler(func=lambda m:m.text=="CANCEL")
def cancel(m):
    bot.send_message(m.chat.id,"Withdrawal cancelled", reply_markup=user_menu(m.from_user.id))

@bot.message_handler(func=lambda m:m.text=="MAIN MENU")
def main_menu(m):
    bot.send_message(m.chat.id,"Main Menu", reply_markup=user_menu(m.from_user.id))

@bot.message_handler(func=lambda m:m.text=="USDT-BEP20")
def usdt_start(m):
    uid=str(m.from_user.id)
    if users[uid]["balance"] < 1:
        bot.send_message(m.chat.id,"❌ AMOUNT YOU WITHDRAWAL MIN: 1")
        return
    msg=bot.send_message(m.chat.id,"Enter your USDT BEP20 address (must start with 0x):")
    bot.register_next_step_handler(msg, get_address)

def get_address(m):
    uid=str(m.from_user.id)
    addr=m.text.strip()
    if not addr.startswith("0x"):
        msg=bot.send_message(m.chat.id,"❌ Invalid address. Must start with 0x")
        bot.register_next_step_handler(msg, get_address)
        return
    users[uid]["temp_addr"]=addr
    save("users.json",users)
    msg=bot.send_message(m.chat.id,f"Enter amount to withdraw (Balance ${users[uid]['balance']:.2f}):")
    bot.register_next_step_handler(msg,get_amount)

def get_amount(m):
    uid=str(m.from_user.id)
    try:
        amt=float(m.text)
    except:
        msg=bot.send_message(m.chat.id,"❌ Invalid amount")
        bot.register_next_step_handler(msg,get_amount)
        return
    if amt>users[uid]["balance"] or amt<1:
        msg=bot.send_message(m.chat.id,"❌ Invalid amount")
        bot.register_next_step_handler(msg,get_amount)
        return

    wid=random.randint(10000,99999)
    withdraws.append({
        "id": wid,
        "user": uid,
        "amount": amt,
        "blocked": amt,
        "address": users[uid]["temp_addr"],
        "status":"pending",
        "time": str(datetime.now())
    })
    users[uid]["balance"]-=amt
    users[uid]["blocked"]+=amt
    save("users.json",users)
    save("withdraws.json",withdraws)

    bot.send_message(m.chat.id,
        f"✅ Request #{wid} Sent!\n💵 Amount: ${amt}\n⏳ Pending 6-12 hours",
        reply_markup=user_menu(uid)
    )

    # ADMIN MESSAGE WITH CONFIRM/REJECT/BAN INLINE
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("✅ CONFIRM", callback_data=f"confirm_{wid}"),
        InlineKeyboardButton("❌ REJECT", callback_data=f"reject_{wid}")
    )
    kb.add(InlineKeyboardButton("🚫 BAN", callback_data=f"ban_{uid}"))

    bot.send_message(ADMIN_ID,
        f"💳 NEW WITHDRAW\n\n👤 User: {uid}\n💵 Amount: ${amt}\n🧾 Request ID: {wid}\nAddress: {users[uid]['temp_addr']}\nReferrals: {users[uid]['refs']}",
        reply_markup=kb
    )
    del users[uid]["temp_addr"]
    save("users.json",users)

# ---------------- ADMIN ACTIONS ----------------
@bot.callback_query_handler(func=lambda c: c.data.startswith("confirm"))
def confirm(c):
    wid=int(c.data.split("_")[1])
    for w in withdraws:
        if w["id"]==wid and w["status"]=="pending":
            w["status"]="paid"
            uid=w["user"]
            users[uid]["blocked"]-=w["blocked"]
            save("users.json",users)
            bot.send_message(int(uid),"✅ Withdrawal Approved")
    save("withdraws.json",withdraws)

@bot.callback_query_handler(func=lambda c: c.data.startswith("reject"))
def reject(c):
    wid=int(c.data.split("_")[1])
    for w in withdraws:
        if w["id"]==wid and w["status"]=="pending":
            uid=w["user"]
            users[uid]["balance"]+=w["blocked"]
            users[uid]["blocked"]-=w["blocked"]
            w["status"]="rejected"
            bot.send_message(int(uid),"❌ Withdrawal Rejected")
    save("users.json",users)
    save("withdraws.json",withdraws)

@bot.callback_query_handler(func=lambda c: c.data.startswith("ban"))
def ban(c):
    uid=c.data.split("_")[1]
    users[uid]["banned"]=True
    save("users.json",users)

# ---------------- UNBAN MONEY ----------------
@bot.message_handler(func=lambda m:m.text=="💸 UNBAN MONEY")
def unban_money(m):
    if m.from_user.id!=ADMIN_ID: return
    msg=bot.send_message(m.chat.id,"Send USER ID to unblock money")
    bot.register_next_step_handler(msg,unban_money2)

def unban_money2(m):
    uid=m.text
    if uid in users:
        amt = users[uid]["blocked"]
        users[uid]["balance"] += amt
        users[uid]["blocked"] = 0
        save("users.json",users)
        bot.send_message(int(uid),f"💰 Your blocked money ${amt} is unblocked and available now.")

# ---------------- WITHDRAW CHECK ----------------
@bot.message_handler(func=lambda m:m.text=="💳 WITHDRAW CHECK")
def wdcheck(m):
    if m.from_user.id!=ADMIN_ID: return
    msg=bot.send_message(m.chat.id,"Send Request ID to check")
    bot.register_next_step_handler(msg,wdcheck2)

def wdcheck2(m):
    wid=int(m.text)
    for w in withdraws:
        if w["id"]==wid:
            bot.send_message(m.chat.id,str(w))

# ---------------- STATS ----------------
@bot.message_handler(func=lambda m:m.text=="📊 STATS")
def stats(m):
    if m.from_user.id!=ADMIN_ID:return
    total_users=len(users)
    total_balance=sum(users[u]["balance"] for u in users)
    total_blocked=sum(users[u]["blocked"] for u in users)
    total_withdraw=sum(w["amount"] for w in withdraws if w["status"]=="paid")
    bot.send_message(m.chat.id,
        f"👥 Total Users: {total_users}\n💰 Total Balance: ${total_balance:.2f}\n⛔ Total Blocked: ${total_blocked:.2f}\n💵 Total Withdraw Paid: ${total_withdraw:.2f}")

# ---------------- BROADCAST ----------------
@bot.message_handler(func=lambda m:m.text=="📤 BROADCAST")
def broadcast(m):
    if m.from_user.id!=ADMIN_ID:return
    msg=bot.send_message(m.chat.id,"Send message to broadcast")
    bot.register_next_step_handler(msg,bc_send)

def bc_send(m):
    for u in users:
        try: bot.copy_message(int(u), m.chat.id, m.message_id)
        except: pass

# ---------------- RUN ----------------
bot.infinity_polling()
