import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aiogram import *
from aiogram.filters import *
from aiogram.fsm.context import *
from aiogram.types import *
from loguru import logger
from database import get_user, create_user
from keyboards.reply_kb import role_kb, start_kb
from keyboards.cleaner_kb import cleaner_menu, is_cleaner_logged_in

router = Router()


@router.message(Command("start"))
async def start(msg: Message):
    user = get_user(msg.from_user.id)
    if not user:
        create_user(msg.from_user.id, msg.from_user.username, msg.from_user.first_name)
        logger.info(f"Новый пользователь: {msg.from_user.id}")

    await msg.answer(
        f"👋 Привет, {msg.from_user.first_name}!\n\n"
        f"Я бот клининговой компании TidyUp.\n"
        f"Кто вы?",
        reply_markup=role_kb()
    )


@router.message(F.text == "👤 Клиент")
async def role_client(msg: Message, state: FSMContext):
    await msg.answer(
        "Вы вошли как клиент",
        reply_markup=start_kb()
    )


@router.message(F.text == "🧹 Уборщик")
async def role_cleaner(msg: Message, state: FSMContext):
    if is_cleaner_logged_in(msg.from_user.id):
        text = "Панель уборщика."
    else:
        text = (
            "Панель уборщика.\n\n"
            "Нажмите «🔐 Войти» и введите пароль.\n"
            "Или команда: /cleaner пароль"
        )
    await msg.answer(text, reply_markup=cleaner_menu(msg.from_user.id))


@router.message(F.text == "👨‍💼 Администратор")
async def role_admin(msg: Message, state: FSMContext):
    await msg.answer(
        "Введите пароль для входа:\n"
        "Формат: /admin пароль"
    )