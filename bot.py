import telebot
from telebot.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
import os, json, random, requests, yt_dlp
from bs4 import BeautifulSoup
from datetime import datetime

# ---------------- CONFIG ----------------
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 7983838654

if not TOKEN:
    raise Exception("BOT_TOKEN missing in Railway Variables")

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# ---------------- DATABASE ----------------
def load_json(name, default):
    if not os.path.exists(name):
        return default
    with open(name, "r") as f:
        return json.load(f)

def save_json(name, data):
    with open(name, "w") as f:
        json.dump(data, f, indent=4)

users = load_json("users.json", {})
withdraws = load_json("withdraws.json", [])

# ---------------- MENUS ----------------
def user_menu(uid):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("💰 BALANCE", "💸 WITHDRAWAL")
    kb.add("👥 REFERAL", "🆔 GET MY ID")
    kb.add("☎️ COSTUMER")
    if int(uid) == ADMIN_ID:
        kb.add("👑 ADMIN PANEL")
    return kb

# ---------------- HELPERS ----------------
def is_banned(uid):
    return users.get(uid, {}).get("banned", False)

def ensure_user(uid, ref=None):
    if uid in users:
        return
    users[uid] = {
        "balance": 0.0,
        "refs": 0,
        "ref": str(random.randint(100000, 999999)),
        "bot_id": str(random.randint(10000000000, 99999999999)),
        "month": datetime.now().month,
        "banned": False
    }
    # Referral reward
    if ref:
        for u in users:
            if users[u]["ref"] == ref:
                users[u]["refs"] += 1
                users[u]["balance"] += 0.2
                try:
                    bot.send_message(int(u),
                        "🎉 <b>Congratulations!</b>\nNew referral joined.\nYou earned <b>$0.2</b>")
                except:
                    pass
                break
    save_json("users.json", users)

# ---------------- START ----------------
@bot.message_handler(commands=['start'])
def start(m):
    uid = str(m.from_user.id)
    args = m.text.split()
    ref = args[1] if len(args) > 1 else None

    ensure_user(uid, ref)

    if is_banned(uid):
        return bot.send_message(m.chat.id, "🚫 You are banned from using this bot.")

    bot.send_message(m.chat.id, "👋 <b>Welcome</b>", reply_markup=user_menu(uid))

# ---------------- BALANCE ----------------
@bot.message_handler(func=lambda m: m.text == "💰 BALANCE")
def balance(m):
    uid = str(m.from_user.id)
    if is_banned(uid): return
    bot.send_message(m.chat.id, f"💰 Your Balance: <b>${users[uid]['balance']:.2f}</b>")

# ---------------- GET MY ID ----------------
@bot.message_handler(func=lambda m: m.text == "🆔 GET MY ID")
def get_my_id(m):
    uid = str(m.from_user.id)
    if is_banned(uid): return
    bot.send_message(m.chat.id, f"""
<b>🆔 TELEGRAM ID:</b> {uid}
<b>🤖 USER BOT ID:</b> {users[uid]['bot_id']}
""")

# ---------------- REFERAL ----------------
@bot.message_handler(func=lambda m: m.text == "👥 REFERAL")
def referal(m):
    uid = str(m.from_user.id)
    if is_banned(uid): return
    link = f"https://t.me/{bot.get_me().username}?start={users[uid]['ref']}"
    bot.send_message(m.chat.id,
        f"🔗 <b>Your Referral Link</b>\n{link}\n\n👥 Total referrals: <b>{users[uid]['refs']}</b>")

# ---------------- WITHDRAW ----------------
@bot.message_handler(func=lambda m: m.text == "💸 WITHDRAWAL")
def withdraw(m):
    uid = str(m.from_user.id)
    if is_banned(uid): return
    msg = bot.send_message(m.chat.id, "Enter USDT BEP20 address starting with 0x")
    bot.register_next_step_handler(msg, withdraw_address)

def withdraw_address(m):
    uid = str(m.from_user.id)
    if is_banned(uid): return
    address = m.text.strip()
    bal = users[uid]["balance"]

    if not address.startswith("0x"):
        return bot.send_message(m.chat.id, "❌ Invalid address")

    if bal < 0.5:
        return bot.send_message(m.chat.id, "Minimum withdrawal $0.5")

    wid = random.randint(10000, 99999)

    withdraws.append({
        "id": wid,
        "user": uid,
        "amount": bal,
        "address": address,
        "status": "pending"
    })

    users[uid]["balance"] = 0.0
    save_json("users.json", users)
    save_json("withdraws.json", withdraws)

    bot.send_message(m.chat.id, f"""
✅ Request #{wid} Sent!
💵 Amount: ${bal:.2f}
💸 Fee (0.00%): -$0.00
🧾 Net Due: ${bal:.2f}
⏳ Your request is pending approval
🕒 Pending time: 6–12 hours
Please be patient 😕
""")

    bot.send_message(ADMIN_ID, f"""
💳 <b>NEW WITHDRAW</b>

👤 User: <code>{uid}</code>
🤖 BOT ID: <code>{users[uid]['bot_id']}</code>
👥 Referrals: <b>{users[uid]['refs']}</b>
💵 Amount: <b>${bal:.2f}</b>
🧾 Request ID: <b>{wid}</b>

Reply with:
CONFIRM {wid}
REJECT {wid}
BAN {uid}
""")

# ---------------- ADMIN PANEL (BUTTON) ----------------
@bot.message_handler(func=lambda m: m.text == "👑 ADMIN PANEL")
def admin_panel(m):
    if m.from_user.id != ADMIN_ID:
        return
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("📊 Stats", callback_data="stats"))
    kb.add(InlineKeyboardButton("⭐ Send Rating", callback_data="rate"))
    kb.add(InlineKeyboardButton("📢 Broadcast", callback_data="broadcast"))
    kb.add(InlineKeyboardButton("➕ Add Balance", callback_data="addbal"))
    kb.add(InlineKeyboardButton("🚫 Ban", callback_data="ban"))
    kb.add(InlineKeyboardButton("✅ Unban", callback_data="unban"))
    bot.send_message(m.chat.id, "👑 <b>ADMIN PANEL</b>", reply_markup=kb)

# ---------------- STATS ----------------
@bot.callback_query_handler(func=lambda c: c.data == "stats")
def stats(c):
    total = len(users)
    monthly = sum(1 for u in users if users[u]["month"] == datetime.now().month)
    totalbal = sum(users[u]["balance"] for u in users)
    totalwd = sum(w["amount"] for w in withdraws if w.get("status") == "paid")

    bot.send_message(c.message.chat.id, f"""
📊 <b>BOT STATS</b>

👥 Total Users: {total}
📆 Monthly Users: {monthly}
💰 Total Balance: ${totalbal:.2f}
💳 Total Withdrawn: ${totalwd:.2f}
""")

# ---------------- RATING ----------------
@bot.callback_query_handler(func=lambda c: c.data == "rate")
def send_rating(c):
    kb = InlineKeyboardMarkup(row_width=5)
    buttons = [InlineKeyboardButton(f"{i} ⭐", callback_data=f"rate_{i}") for i in range(1, 6)]
    kb.add(*buttons)

    for u in users:
        try:
            bot.send_message(int(u), "⭐ Please rate our bot", reply_markup=kb)
        except:
            pass

@bot.callback_query_handler(func=lambda c: c.data.startswith("rate_"))
def rating_receive(c):
    rate = c.data.split("_")[1]
    name = c.from_user.first_name or "NoName"
    uid = c.from_user.id

    bot.send_message(ADMIN_ID, f"⭐ <b>New Rate</b>\nUser: {name}\nID: {uid}\nRate: {rate}")
    bot.answer_callback_query(c.id, "Thanks your Rate 😍")

# ---------------- BROADCAST ----------------
@bot.callback_query_handler(func=lambda c: c.data == "broadcast")
def broadcast_start(c):
    if c.from_user.id != ADMIN_ID: return
    msg = bot.send_message(c.message.chat.id, "Send message or forward video/photo")
    bot.register_next_step_handler(msg, broadcast_send)

def broadcast_send(m):
    if m.from_user.id != ADMIN_ID: return
    for u in users:
        try:
            bot.copy_message(int(u), m.chat.id, m.message_id)
        except:
            pass

# ---------------- ADD BALANCE ----------------
@bot.callback_query_handler(func=lambda c: c.data == "addbal")
def add_balance_start(c):
    msg = bot.send_message(c.message.chat.id, "Send BOT ID and amount\nExample: 12345678901 2")
    bot.register_next_step_handler(msg, add_balance_do)

def add_balance_do(m):
    try:
        bid, amt = m.text.split()
        amt = float(amt)
    except:
        return bot.send_message(m.chat.id, "Invalid format")

    for u in users:
        if users[u]["bot_id"] == bid:
            users[u]["balance"] += amt
            save_json("users.json", users)
            try:
                bot.send_message(int(u), f"💰 Admin added ${amt}")
            except:
                pass
            return bot.send_message(m.chat.id, "Done")

    bot.send_message(m.chat.id, "BOT ID not found")

# ---------------- BAN / UNBAN ----------------
@bot.callback_query_handler(func=lambda c: c.data == "ban")
def ban_start(c):
    msg = bot.send_message(c.message.chat.id, "Send BOT ID or TELEGRAM ID to BAN")
    bot.register_next_step_handler(msg, ban_do)

def ban_do(m):
    target = m.text.strip()
    for u in users:
        if u == target or users[u]["bot_id"] == target:
            users[u]["banned"] = True
            save_json("users.json", users)
            return bot.send_message(m.chat.id, "User banned")
    bot.send_message(m.chat.id, "User not found")

@bot.callback_query_handler(func=lambda c: c.data == "unban")
def unban_start(c):
    msg = bot.send_message(c.message.chat.id, "Send BOT ID or TELEGRAM ID to UNBAN")
    bot.register_next_step_handler(msg, unban_do)

def unban_do(m):
    target = m.text.strip()
    for u in users:
        if u == target or users[u]["bot_id"] == target:
            users[u]["banned"] = False
            save_json("users.json", users)
            return bot.send_message(m.chat.id, "User unbanned")
    bot.send_message(m.chat.id, "User not found")

# ---------------- WITHDRAW CONTROL ----------------
@bot.message_handler(func=lambda m: m.text and m.text.startswith("CONFIRM"))
def wd_confirm(m):
    if m.from_user.id != ADMIN_ID: return
    wid = int(m.text.split()[1])
    for w in withdraws:
        if w["id"] == wid:
            w["status"] = "paid"
            save_json("withdraws.json", withdraws)
            try:
                bot.send_message(int(w["user"]), "✅ Withdrawal Approved")
            except:
                pass
            return bot.send_message(m.chat.id, "Marked as PAID")

@bot.message_handler(func=lambda m: m.text and m.text.startswith("REJECT"))
def wd_reject(m):
    if m.from_user.id != ADMIN_ID: return
    wid = int(m.text.split()[1])
    for w in withdraws:
        if w["id"] == wid:
            w["status"] = "rejected"
            # refund
            uid = w["user"]
            users[uid]["balance"] += w["amount"]
            save_json("users.json", users)
            save_json("withdraws.json", withdraws)
            try:
                bot.send_message(int(uid), "❌ Withdrawal Rejected. Amount refunded to your balance.")
            except:
                pass
            return bot.send_message(m.chat.id, "Rejected & Refunded")

@bot.message_handler(func=lambda m: m.text and m.text.startswith("BAN "))
def admin_ban_direct(m):
    if m.from_user.id != ADMIN_ID: return
    uid = m.text.split()[1]
    if uid in users:
        users[uid]["banned"] = True
        save_json("users.json", users)
        bot.send_message(m.chat.id, "User banned")

# ---------------- MEDIA DOWNLOADER ----------------
def download_media(chat_id, url):
    try:
        # TikTok photo(s) + video fallback
        if "tiktok.com" in url:
            html = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}).text
            soup = BeautifulSoup(html, "html.parser")

            imgs = soup.find_all("meta", property="og:image")
            sent_any = False
            for i, img in enumerate(imgs):
                link = img.get("content")
                if not link: continue
                data = requests.get(link).content
                fname = f"tt_{i}.jpg"
                with open(fname, "wb") as f:
                    f.write(data)
                with open(fname, "rb") as f:
                    bot.send_photo(chat_id, f)
                os.remove(fname)
                sent_any = True

            # try video with yt-dlp as well
            ydl_opts = {"outtmpl": "tt_vid.%(ext)s", "format": "mp4"}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                file = ydl.prepare_filename(info)
            if os.path.exists(file):
                with open(file, "rb") as f:
                    bot.send_video(chat_id, f)
                os.remove(file)
                sent_any = True

            if not sent_any:
                bot.send_message(chat_id, "Could not extract TikTok media.")
            return

        # YouTube / Shorts
        ydl_opts = {"outtmpl": "yt_vid.%(ext)s", "format": "mp4"}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file = ydl.prepare_filename(info)

        with open(file, "rb") as f:
            bot.send_video(chat_id, f)
        os.remove(file)

    except Exception as e:
        bot.send_message(chat_id, f"Download error: {e}")

@bot.message_handler(func=lambda m: m.text and "http" in m.text)
def links(m):
    uid = str(m.from_user.id)
    if is_banned(uid): return
    bot.send_message(m.chat.id, "⏳ Downloading...")
    download_media(m.chat.id, m.text)

# ---------------- RUN ----------------
bot.infinity_polling(skip_pending=True)
