# main.py
import os
import logging
import asyncio
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import db
import re

load_dotenv()
TOKEN = os.getenv("TG_BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
DB_PATH = os.getenv("DB_PATH", "data.db")

if not TOKEN:
    raise SystemExit("Set TG_BOT_TOKEN in .env")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=TOKEN, parse_mode="HTML")
dp = Dispatcher()

# Инициализация БД
conn = db.init_db(DB_PATH)

# Главное меню (обычный пользователь)
kb_main = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Общее количество"), KeyboardButton(text="Выдано")],
    ],
    resize_keyboard=True
)

# админские кнопки (подользователь видит +кнопки)
kb_admin = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Общее количество"), KeyboardButton(text="Выдано")],
        [KeyboardButton(text="Добавить данные (админ)")]
    ],
    resize_keyboard=True
)

# inline выбор ИШР/ИСР при запросе "Выдано"
inline_issued = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="ИШР", callback_data="issued:ИШР"),
         InlineKeyboardButton(text="ИСР", callback_data="issued:ИСР")]
    ]
)

# /start
@dp.message(Command(commands=["start"]))
async def cmd_start(message: types.Message):
    is_admin = (message.from_user.id == ADMIN_ID)
    await message.answer(
        f"Привет, <b>{message.from_user.first_name or 'друг'}</b>!\nВыбери действие.",
        reply_markup=kb_admin if is_admin else kb_main
    )

# Общее количество
@dp.message(lambda m: m.text == "Общее количество")
async def total_handler(message: types.Message):
    stocks = db.get_stocks(conn)
    if not stocks:
        await message.answer("Остатков пока нет.")
        return
    lines = ["<b>Текущие остатки:</b>"]
    for fuel, amount in stocks:
        lines.append(f"{fuel}: {amount}")
    await message.answer("\n".join(lines))

# Выдано -> показать inline для выбора ИШР/ИСР
@dp.message(lambda m: m.text == "Выдано")
async def issued_menu(message: types.Message):
    await message.answer("Выбери источник выдач:", reply_markup=inline_issued)

# обработчик inline callback
@dp.callback_query()
async def inline_handler(callback: types.CallbackQuery):
    data = callback.data or ""
    if data.startswith("issued:"):
        source = data.split(":", 1)[1]
        rows = db.get_issues_by_source(conn, source)
        if not rows:
            await callback.message.answer(f"Записей для <b>{source}</b> нет.")
            await callback.answer()
            return
        lines = [f"<b>Выдано — {source}</b>"]
        for r in rows:
            lines.append(f"{r['date']}: {r['fuel']}: {r['amount']}: {r['callsign']}")
        await callback.message.answer("\n".join(lines))
    await callback.answer()

# Админ: добавить данные (вход в режим ввода)
@dp.message(lambda m: m.text == "Добавить данные (админ)")
async def admin_enter_mode(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("У вас нет доступа к этой кнопке.")
        return
    text = (
        "Введи данные в одном из форматов:\n\n"
        "1) Для выдачи (будет уменьшен остаток):\n"
        "   <code>DD.MM.YY: Топливо: Количество: Позывной:Источник</code>\n"
        "   пример: <code>14.09.25: Бензин: 40: Гермес:ИШР</code>\n"
        "   (Источник необязателен — по умолчанию ИШР)\n\n"
        "2) Для установки/пополнения остатка (вклад):\n"
        "   <code>СТОК: Топливо: Количество</code>\n"
        "   пример: <code>СТОК: Дизель: 3000</code>\n\n"
        "После отправки бот сохранит и обновит остатки автоматически."
    )
    await message.answer(text)

# Парсинг любых сообщений от админа — попробуем распарсить добавление
@dp.message()
async def catch_all(message: types.Message):
    text = (message.text or "").strip()
    # если админ — попытаться распарсить добавление данных
    if message.from_user.id == ADMIN_ID:
        # формат выдачи: date: fuel: amount: callsign : source(optional)
        # пример: 14.09.25: Бензин: 40: Гермес:ИШР
        parts = [p.strip() for p in text.split(":")]
        # пополнение/установить запас: СТОК: Топливо: Количество
        if len(parts) == 3 and parts[0].upper() == "СТОК":
            _, fuel, amt = parts
            try:
                amt_f = float(amt.replace(",", "."))
            except:
                await message.answer("Не удалось распознать количество. Используй число, например 3000 или 40.5")
                return
            db.add_stock(conn, fuel, amt_f)
            await message.answer(f"Добавлено к запасу: {fuel} +{amt_f}\nТекущий остаток: {db.get_stock(conn, fuel)}")
            return

        # выдача:
        if len(parts) >= 4:
            date = parts[0]
            fuel = parts[1]
            amt = parts[2]
            callsign = parts[3]
            source = parts[4] if len(parts) >= 5 and parts[4] else "ИШР"
            try:
                amt_f = float(amt.replace(",", "."))
            except:
                await message.answer("Не удалось распознать количество выдачи. Используй число, например 40")
                return
            # Запись в issues
            db.add_issue(conn, date, fuel, amt_f, callsign, source)
            # Уменьшаем запас (если нет запаса, создаём отрицательный)
            db.add_stock(conn, fuel, -amt_f)
            new_stock = db.get_stock(conn, fuel)
            await message.answer(f"Запись добавлена: {date}: {fuel}: {amt_f}: {callsign}: {source}\nТекущий остаток {fuel}: {new_stock}")
            return

    # если не админ или не распарсили — обычное эхо / инструкция
    if text.lower() in ["привет", "hi", "hello"]:
        await message.answer("Привет! Выбери действие в меню.")
        return

    # для обычных пользователей — ничего критичного: отдать подсказку
    await message.answer("Не понял. Используй кнопки меню. Нажми /start для возврата в меню.")

async def on_startup():
    logger.info("Бот запущен")

async def on_shutdown():
    logger.info("Shutting down")
    await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(dp.start_polling(bot, on_startup=on_startup, on_shutdown=on_shutdown))
    finally:
        conn.close()
