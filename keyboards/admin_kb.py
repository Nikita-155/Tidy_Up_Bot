from aiogram.types import *

def admin_menu():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="📋 Все заказы")],
        [KeyboardButton(text="🧹 Уборщики")],
        [KeyboardButton(text="🔙 Назад")]
    ], resize_keyboard=True)