from aiogram.types import *

def role_kb():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="👤 Клиент")],
        [KeyboardButton(text="🧹 Уборщик")],
        [KeyboardButton(text="👨‍💼 Администратор")]
    ], resize_keyboard=True)

def start_kb():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🧹 Заказать уборку")],
        [KeyboardButton(text="📋 Мои заказы"), KeyboardButton(text="📞 Контакты")]
    ], resize_keyboard=True)

def phone_kb():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📱 Отправить номер", request_contact=True)]
    ], resize_keyboard=True)

def types_kb(selected):
    types = [
        ("type_support", "Поддерживающая"), ("type_deep", "Генеральная"),
        ("type_windows", "Мойка окон"), ("type_dry_cleaning", "Химчистка"),
        ("type_after_repair", "После ремонта"), ("type_office", "Офисная"),
        ("type_moving", "После переезда"), ("type_chandelier", "Мытье люстр"),
        ("type_territory", "Уборка территории")
    ]
    kb = []
    for cb, txt in types:
        prefix = "✅ " if cb in selected else ""
        kb.append([InlineKeyboardButton(text=f"{prefix}{txt}", callback_data=cb)])
    btns = []
    if selected:
        btns.append(InlineKeyboardButton(text="✅ Готово", callback_data="types_done"))
    btns.append(InlineKeyboardButton(text="❌ Очистить", callback_data="types_clear"))
    kb.append(btns)
    return InlineKeyboardMarkup(inline_keyboard=kb)

def confirm_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_order"),
         InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_order")]
    ])

def skip_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏩ Пропустить", callback_data="skip_notes")]
    ])