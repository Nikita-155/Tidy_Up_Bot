import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aiogram import *
from aiogram.filters import *
from aiogram.types import *
from database import get_user, get_all_orders, get_all_cleaners
from keyboards.admin_kb import admin_menu
from config import ADMIN_PASSWORD, ADMIN_IDS

router = Router()

_admin_sessions: set[int] = set()


def is_admin(user_id: int) -> bool:
    return user_id in _admin_sessions or user_id in ADMIN_IDS


@router.message(Command("admin"))
async def admin_auth(msg: Message):
    parts = msg.text.split(maxsplit=1)
    if len(parts) == 2 and parts[1].strip() == ADMIN_PASSWORD:
        user = get_user(msg.from_user.id)
        if not user:
            await msg.answer("Сначала нажмите /start")
            return
        _admin_sessions.add(msg.from_user.id)
        await msg.answer("👨‍💼 Панель администратора", reply_markup=admin_menu())
    elif msg.text.strip() == "/admin":
        await msg.answer("Введите пароль: /admin ваш_пароль")
    else:
        await msg.answer("Неверный пароль")


@router.message(F.text == "📊 Статистика")
async def stats(msg: Message):
    if not is_admin(msg.from_user.id):
        return
    orders = get_all_orders()
    cleaners = get_all_cleaners()

    total = len(orders)
    new = len([o for o in orders if o.status == "new"])
    completed = len([o for o in orders if o.status == "completed"])
    active_cleaners = len([c for c in cleaners if c.status == "active"])

    text = f"📊 СТАТИСТИКА\n"
    text += f"━━━━━━━━━━━━━━━━\n"
    text += f"📦 Всего заказов: {total}\n"
    text += f"🆕 Новых: {new}\n"
    text += f"✅ Завершено: {completed}\n"
    text += f"🧹 Активных уборщиков: {active_cleaners}\n"
    await msg.answer(text)


@router.message(F.text == "📋 Все заказы")
async def all_orders(msg: Message):
    if not is_admin(msg.from_user.id):
        return
    orders = get_all_orders()
    if not orders:
        await msg.answer("Заказов нет")
        return

    text = "📋 ПОСЛЕДНИЕ ЗАКАЗЫ\n"
    text += "━━━━━━━━━━━━━━━━\n"
    for o in orders[:10]:
        status = {"new": "🆕", "accepted": "✅", "in_progress": "🔄", "completed": "⭐"}.get(o.status, "📌")
        text += f"{status} #{o.id} | {o.cleaning_type[:15]} | {o.date}\n"
    await msg.answer(text)


@router.message(F.text == "🧹 Уборщики")
async def all_cleaners(msg: Message):
    if not is_admin(msg.from_user.id):
        return
    cleaners = get_all_cleaners()
    if not cleaners:
        await msg.answer("Нет уборщиков")
        return

    text = "🧹 СПИСОК УБОРЩИКОВ\n"
    text += "━━━━━━━━━━━━━━━━\n"
    for c in cleaners:
        status = "🟢 Активен" if c.status == "active" else "⚪ Не активен"
        text += f"👤 {c.full_name}\n"
        text += f"   Статус: {status}\n"
        text += f"   ✅ Заказов завершено: {c.completed_orders}\n\n"
    await msg.answer(text)


@router.message(F.text == "🔙 Назад")
async def back(msg: Message):
    if not is_admin(msg.from_user.id):
        return
    await msg.answer("Выберите действие:", reply_markup=admin_menu())