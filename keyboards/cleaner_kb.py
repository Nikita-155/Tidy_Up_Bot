from aiogram.types import *

_cleaner_logged_in: set[int] = set()


def mark_cleaner_logged_in(telegram_id: int) -> None:
    _cleaner_logged_in.add(telegram_id)


def is_cleaner_logged_in(telegram_id: int) -> bool:
    return telegram_id in _cleaner_logged_in


def cleaner_menu_guest():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔐 Войти")],
            [KeyboardButton(text="🚪 Выйти на смену")],
            [KeyboardButton(text="📋 Мои заказы"), KeyboardButton(text="📊 Моя статистика")],
        ],
        resize_keyboard=True,
    )


def cleaner_menu_active():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🚪 Выйти на смену")],
            [KeyboardButton(text="📋 Мои заказы"), KeyboardButton(text="📊 Моя статистика")],
        ],
        resize_keyboard=True,
    )


def cleaner_menu(telegram_id: int | None = None):
    if telegram_id is not None and is_cleaner_logged_in(telegram_id):
        return cleaner_menu_active()
    return cleaner_menu_guest()


def shift_kb():
    return shift_kb_with_orders(None)


def shift_kb_with_orders(cleaner_id: int | None):
    from database import get_cleaner_orders

    rows = [
        [KeyboardButton(text="📋 Доступные заказы")],
        [KeyboardButton(text="📋 Мои заказы"), KeyboardButton(text="📊 Моя статистика")],
        [KeyboardButton(text="🏠 Закончить смену")],
    ]
    if cleaner_id is not None:
        orders = get_cleaner_orders(cleaner_id)
        for o in orders:
            if o.status == "accepted":
                rows.append([KeyboardButton(text=f"📍 Прибыл #{o.id}")])
            elif o.status == "in_progress":
                rows.append([KeyboardButton(text=f"✅ Завершить #{o.id}")])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)
