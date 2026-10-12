import asyncio
import logging
import os
from html import escape

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message, ReplyKeyboardMarkup, KeyboardButton,
    ReplyKeyboardRemove
)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
ADMIN_ID_RAW = os.getenv("ADMIN_ID", "").strip()

if not BOT_TOKEN or not ADMIN_ID_RAW:
    raise RuntimeError("Set BOT_TOKEN and ADMIN_ID environment variables.")

ADMIN_ID = int(ADMIN_ID_RAW)

logging.basicConfig(level=logging.INFO)
dp = Dispatcher()

MODELS = [
    "iPhone 11", "iPhone 11 Pro", "iPhone 11 Pro Max",
    "iPhone 12", "iPhone 12 mini", "iPhone 12 Pro", "iPhone 12 Pro Max",
    "iPhone 13", "iPhone 13 mini", "iPhone 13 Pro", "iPhone 13 Pro Max",
    "iPhone 14", "iPhone 14 Plus", "iPhone 14 Pro", "iPhone 14 Pro Max",
    "iPhone 15", "iPhone 15 Plus", "iPhone 15 Pro", "iPhone 15 Pro Max",
    "iPhone 16", "iPhone 16 Plus", "iPhone 16 Pro", "iPhone 16 Pro Max",
    "iPhone 17", "iPhone 17 Pro", "iPhone 17 Pro Max",
    "Другая модель"
]

def keyboard(items, columns=2):
    rows = []
    for i in range(0, len(items), columns):
        rows.append([KeyboardButton(text=x) for x in items[i:i + columns]])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)

def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Продать iPhone")]],
        resize_keyboard=True
    )

class SaleForm(StatesGroup):
    model = State()
    storage = State()
    condition = State()
    battery = State()
    issues = State()
    photos = State()
    price = State()
    contact = State()
    confirm = State()

@dp.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Привет! 👋\n\nЗдесь можно оставить заявку на продажу iPhone. "
        "Ответь на несколько вопросов, прикрепи фото и укажи желаемую цену.\n\n"
        "Нажми кнопку ниже, чтобы начать.",
        reply_markup=main_menu()
    )

@dp.message(Command("cancel"))
async def cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Заявка отменена. Чтобы начать заново, нажми «📱 Продать iPhone».",
                         reply_markup=main_menu())

@dp.message(F.text == "📱 Продать iPhone")
async def begin(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(SaleForm.model)
    await message.answer("Какая у тебя модель iPhone?", reply_markup=keyboard(MODELS, 2))

@dp.message(SaleForm.model)
async def get_model(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("Выбери модель кнопкой или напиши её текстом.")
        return
    await state.update_data(model=message.text.strip())
    await state.set_state(SaleForm.storage)
    await message.answer("Какой объём памяти?", reply_markup=keyboard(
        ["64 ГБ", "128 ГБ", "256 ГБ", "512 ГБ", "1 ТБ", "2 ТБ", "Не знаю"], 2))

@dp.message(SaleForm.storage)
async def get_storage(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("Напиши объём памяти, например 256 ГБ.")
        return
    await state.update_data(storage=message.text.strip())
    await state.set_state(SaleForm.condition)
    await message.answer("В каком состоянии телефон?", reply_markup=keyboard(
        ["Как новый", "Хорошее", "Есть заметные следы", "Повреждён", "Не работает"], 2))

@dp.message(SaleForm.condition)
async def get_condition(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("Опиши состояние текстом.")
        return
    await state.update_data(condition=message.text.strip())
    await state.set_state(SaleForm.battery)
    await message.answer("Какой процент состояния аккумулятора? Напиши число от 1 до 100 или «Не знаю».",
                         reply_markup=ReplyKeyboardRemove())

@dp.message(SaleForm.battery)
async def get_battery(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("Напиши процент аккумулятора или «Не знаю».")
        return
    await state.update_data(battery=message.text.strip())
    await state.set_state(SaleForm.issues)
    await message.answer("Есть ли неисправности, ремонт или замена деталей? Напиши детали или «Нет».")

@dp.message(SaleForm.issues)
async def get_issues(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("Напиши детали текстом или «Нет».")
        return
    await state.update_data(issues=message.text.strip(), photos=[])
    await state.set_state(SaleForm.photos)
    await message.answer(
        "Теперь отправь фотографии iPhone (можно несколько сообщений). "
        "Покажи, пожалуйста, экран, заднюю крышку и возможные дефекты.\n\n"
        "Когда закончишь, нажми «✅ Фото готовы».",
        reply_markup=keyboard(["✅ Фото готовы"], 1)
    )

@dp.message(SaleForm.photos, F.photo)
async def get_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    photos = data.get("photos", [])
    photos.append(message.photo[-1].file_id)
    await state.update_data(photos=photos)
    await message.answer(f"Фото добавлено ({len(photos)}). Можешь отправить ещё или нажать «✅ Фото готовы».")

@dp.message(SaleForm.photos, F.text == "✅ Фото готовы")
async def photos_done(message: Message, state: FSMContext):
    data = await state.get_data()
    if not data.get("photos"):
        await message.answer("Пока нет фотографий. Отправь хотя бы одно фото или нажми /cancel, чтобы отменить.")
        return
    await state.set_state(SaleForm.price)
    await message.answer("За какую сумму хочешь продать iPhone? Укажи сумму и валюту, например 450 €.",
                         reply_markup=ReplyKeyboardRemove())

@dp.message(SaleForm.photos)
async def photos_other(message: Message):
    await message.answer("Отправь фотографию или нажми «✅ Фото готовы».")

@dp.message(SaleForm.price)
async def get_price(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("Напиши желаемую цену текстом.")
        return
    await state.update_data(price=message.text.strip())
    await state.set_state(SaleForm.contact)
    await message.answer("Как с тобой связаться? Отправь @username или напиши «Напишу здесь».")

@dp.message(SaleForm.contact)
async def get_contact(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("Отправь @username или напиши «Напишу здесь».")
        return
    await state.update_data(contact=message.text.strip())
    data = await state.get_data()
    summary = (
        "Проверь заявку:\n\n"
        f"📱 Модель: {data['model']}\n"
        f"💾 Память: {data['storage']}\n"
        f"🧼 Состояние: {data['condition']}\n"
        f"🔋 Аккумулятор: {data['battery']}\n"
        f"🛠 Неисправности/ремонт: {data['issues']}\n"
        f"💶 Желаемая цена: {data['price']}\n"
        f"☎️ Контакт: {data['contact']}\n"
        f"📸 Фото: {len(data.get('photos', []))}"
    )
    await state.set_state(SaleForm.confirm)
    await state.update_data(summary=summary)
    await message.answer(summary + "\n\nОтправить заявку?",
                         reply_markup=keyboard(["✅ Отправить", "❌ Изменить/отменить"], 1))

@dp.message(SaleForm.confirm, F.text == "❌ Изменить/отменить")
async def reject(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Заявка не отправлена. Если захочешь, начни заново.",
                         reply_markup=main_menu())

@dp.message(SaleForm.confirm, F.text == "✅ Отправить")
async def submit(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    user = message.from_user
    username = f"@{user.username}" if user and user.username else "не указан"
    admin_text = (
        "🆕 <b>Новая заявка на покупку iPhone</b>\n\n"
        f"📱 <b>Модель:</b> {escape(data['model'])}\n"
        f"💾 <b>Память:</b> {escape(data['storage'])}\n"
        f"🧼 <b>Состояние:</b> {escape(data['condition'])}\n"
        f"🔋 <b>Аккумулятор:</b> {escape(data['battery'])}\n"
        f"🛠 <b>Неисправности/ремонт:</b> {escape(data['issues'])}\n"
        f"💶 <b>Желаемая цена:</b> {escape(data['price'])}\n"
        f"☎️ <b>Контакт от продавца:</b> {escape(data['contact'])}\n"
        f"👤 <b>Telegram:</b> {escape(username)}\n"
        f"🆔 <b>User ID:</b> <code>{user.id if user else 'unknown'}</code>\n"
        f"📸 <b>Фотографий:</b> {len(data.get('photos', []))}"
    )
    try:
        await bot.send_message(ADMIN_ID, admin_text)
        for file_id in data.get("photos", []):
            await bot.send_photo(ADMIN_ID, file_id)
    except Exception:
        logging.exception("Could not deliver application to admin")
        await message.answer("Не получилось отправить заявку. Попробуй позже или свяжись с администратором.")
        return
    await state.clear()
    await message.answer("✅ Готово! Заявка отправлена. С тобой свяжутся, если появится предложение.",
                         reply_markup=main_menu())

@dp.message(SaleForm.confirm)
async def confirm_other(message: Message):
    await message.answer("Нажми «✅ Отправить» или «❌ Изменить/отменить».")

async def main():
    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
