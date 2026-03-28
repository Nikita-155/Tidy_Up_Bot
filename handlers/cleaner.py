import re
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aiogram import *
from aiogram.filters import *
from loguru import logger
from aiogram.fsm.context import *
from aiogram.fsm.state import *
from aiogram.types import *
from database import (
    get_user, get_cleaner, create_cleaner, update_cleaner_status,
    get_available_orders, get_cleaner_orders, assign_order,
    update_order_status, complete_order, get_order, get_user_by_id,
    get_admin_notify_telegram_ids,
)
from keyboards.cleaner_kb import (
    cleaner_menu, cleaner_menu_active,
    mark_cleaner_logged_in, is_cleaner_logged_in, shift_kb_with_orders,
)
from config import CLEANER_PASSWORD

router = Router()


class CleanerStates(StatesGroup):
    auth = State()
    register_name = State()
    register_phone = State()
    waiting = State()
    photo = State()


def _parse_order_id_from_button(text: str) -> int | None:
    m = re.search(r"#(\d+)", text)
    return int(m.group(1)) if m else None


def _kb_for_cleaner(telegram_id: int) -> object:
    user = get_user(telegram_id)
    if not user:
        return shift_kb_with_orders(None)
    cleaner = get_cleaner(user.id)
    if not cleaner:
        return shift_kb_with_orders(None)
    return shift_kb_with_orders(cleaner.id)


@router.message(Command("start"))
async def start(msg: Message, state: FSMContext):
    user = get_user(msg.from_user.id)
    if not user:
        from database import create_user
        user = create_user(msg.from_user.id, msg.from_user.username, msg.from_user.first_name)

    cleaner = get_cleaner(user.id)

    if cleaner and cleaner.full_name:
        kb = cleaner_menu(msg.from_user.id)
        await msg.answer(
            f"👋 С возвращением, {cleaner.full_name}!\n\n"
            f"Статус: {'🟢 На смене' if cleaner.status == 'active' else '⚪ Не на смене'}\n"
            f"✅ Выполнено заказов: {cleaner.completed_orders}",
            reply_markup=kb,
        )
    else:
        await msg.answer(
            "📝 Добро пожаловать!\n\n"
            "Для работы уборщиком введите ваше полное имя и фамилию:"
        )
        await state.set_state(CleanerStates.register_name)


@router.message(StateFilter(CleanerStates.register_name))
async def register_name(msg: Message, state: FSMContext):
    if len(msg.text.split()) < 2:
        await msg.answer("❌ Введите имя и фамилию (например: Иван Петров)")
        return

    await state.update_data(full_name=msg.text)
    await msg.answer("📱 Введите номер телефона (например: +79001234567):")
    await state.set_state(CleanerStates.register_phone)


@router.message(StateFilter(CleanerStates.register_phone))
async def register_phone(msg: Message, state: FSMContext):
    phone = re.sub(r'\D', '', msg.text)
    if len(phone) not in [10, 11]:
        await msg.answer("❌ Неверный формат. Введите номер (например: +79001234567)")
        return

    data = await state.get_data()
    full_name = data.get('full_name')

    user = get_user(msg.from_user.id)
    if not user:
        from database import create_user
        user = create_user(msg.from_user.id, msg.from_user.username, msg.from_user.first_name)

    create_cleaner(user.id, full_name, phone)
    mark_cleaner_logged_in(msg.from_user.id)

    await msg.answer(
        f"✅ Регистрация завершена!\n\n"
        f"👤 {full_name}\n"
        f"📱 {phone}\n\n"
        f"Используйте «Выйти на смену», чтобы принимать заказы.",
        reply_markup=cleaner_menu_active(),
    )
    await state.clear()


@router.message(Command("cleaner"))
async def cmd_cleaner(msg: Message, state: FSMContext):
    parts = msg.text.split(maxsplit=1)
    if len(parts) == 2 and parts[1].strip() == CLEANER_PASSWORD:
        user = get_user(msg.from_user.id)
        if user:
            cleaner = get_cleaner(user.id)
            if cleaner:
                mark_cleaner_logged_in(msg.from_user.id)
                await msg.answer(
                    f"✅ Добро пожаловать, {cleaner.full_name}!",
                    reply_markup=cleaner_menu(msg.from_user.id),
                )
                await state.clear()
            else:
                await msg.answer(
                    "❌ Вы не зарегистрированы как уборщик. Нажмите /start для регистрации."
                )
        else:
            await msg.answer("❌ Сначала нажмите /start")
    elif msg.text.strip() == "/cleaner":
        await msg.answer("Использование: /cleaner ваш_пароль")
    else:
        await msg.answer("❌ Неверный пароль. Попробуйте еще раз.")


@router.message(F.text == "🔐 Войти")
async def login(msg: Message, state: FSMContext):
    if is_cleaner_logged_in(msg.from_user.id):
        await msg.answer("Вы уже вошли.", reply_markup=cleaner_menu_active())
        return
    await msg.answer("🔑 Введите пароль:")
    await state.set_state(CleanerStates.auth)


@router.message(StateFilter(CleanerStates.auth))
async def auth_cleaner(msg: Message, state: FSMContext):
    if msg.text == CLEANER_PASSWORD:
        user = get_user(msg.from_user.id)
        if user:
            cleaner = get_cleaner(user.id)
            if cleaner:
                mark_cleaner_logged_in(msg.from_user.id)
                await msg.answer(
                    f"✅ Добро пожаловать, {cleaner.full_name}!",
                    reply_markup=cleaner_menu(msg.from_user.id),
                )
                await state.clear()
            else:
                await msg.answer("❌ Профиль не найден. Нажмите /start для регистрации")
        else:
            await msg.answer("❌ Пользователь не найден. Нажмите /start")
    else:
        await msg.answer("❌ Неверный пароль. Попробуйте еще раз:")


@router.message(F.text == "🚪 Выйти на смену")
async def start_shift(msg: Message, state: FSMContext):
    user = get_user(msg.from_user.id)
    if not user:
        await msg.answer("❌ Сначала нажмите /start")
        return

    cleaner = get_cleaner(user.id)
    if not cleaner:
        await msg.answer("❌ Сначала зарегистрируйтесь. Нажмите /start")
        return

    update_cleaner_status(cleaner.id, "active")
    await msg.answer(
        "✅ Вы на смене!\n\n"
        "Доступные заказы — кнопка выше. Действия по принятым заказам — внизу экрана.",
        reply_markup=shift_kb_with_orders(cleaner.id),
    )
    await state.set_state(CleanerStates.waiting)


@router.message(F.text == "🏠 Закончить смену")
async def end_shift(msg: Message, state: FSMContext):
    user = get_user(msg.from_user.id)
    cleaner = get_cleaner(user.id) if user else None
    if cleaner:
        update_cleaner_status(cleaner.id, "inactive")
    await state.clear()
    await msg.answer("❌ Смена завершена", reply_markup=cleaner_menu(msg.from_user.id))


@router.message(F.text == "📋 Доступные заказы")
async def check_orders(msg: Message):
    orders = get_available_orders()
    if not orders:
        await msg.answer("Нет доступных заказов")
        return

    for order in orders[:20]:
        text = (
            f"🚨 ЗАКАЗ #{order.id}\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"📋 Тип: {order.cleaning_type}\n"
            f"📏 Площадь: {order.area} м²\n"
            f"📍 Адрес: {order.address}\n"
            f"📅 Дата: {order.date} {order.time}\n"
            f"📝 Пожелания: {order.notes}\n"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Взять заказ", callback_data=f"take_{order.id}")]
        ])
        await msg.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("take_"))
async def take_order(call: CallbackQuery, state: FSMContext):
    order_id = int(call.data.split("_")[1])
    user = get_user(call.from_user.id)
    cleaner = get_cleaner(user.id)

    result = assign_order(order_id, cleaner.id)
    if result:
        order = get_order(order_id)
        await call.message.edit_text(f"✅ Заказ #{order_id} взят!")
        await call.message.answer(
            f"🚗 Заказ #{order_id}\n\n"
            f"📋 {order.cleaning_type}\n"
            f"📍 {order.address}\n"
            f"📅 {order.date} {order.time}\n\n"
            f"👇 Когда приедете на объект, нажмите кнопку внизу экрана:\n"
            f"«📍 Прибыл #{order_id}»\n\n"
            f"Можно взять ещё заказы в «📋 Доступные заказы».",
            reply_markup=shift_kb_with_orders(cleaner.id),
        )
    else:
        await call.answer("❌ Заказ уже кто-то взял", show_alert=True)
    await call.answer()


async def _notify_arrive_client(order_id: int, bot):
    order = get_order(order_id)
    if order and order.client_id:
        client = get_user_by_id(order.client_id)
        if client:
            await bot.send_message(
                client.telegram_id,
                f"🧹 Уборщик прибыл на место!\n\nЗаказ #{order_id}\nНачинаем уборку.",
            )


@router.callback_query(F.data.startswith("arrive_"))
async def arrive_callback(call: CallbackQuery):
    order_id = int(call.data.split("_")[1])
    user = get_user(call.from_user.id)
    cleaner = get_cleaner(user.id)
    order = get_order(order_id)
    if not order or order.cleaner_id != cleaner.id or order.status != "accepted":
        await call.answer("Недоступно", show_alert=True)
        return
    update_order_status(order_id, "in_progress")
    await _notify_arrive_client(order_id, call.bot)
    await call.message.edit_text(f"✅ По заказу #{order_id} отмечено прибытие.")
    await call.message.answer(
        f"Заказ #{order_id}: уборка идёт.\n\n"
        f"👇 По завершении нажмите внизу: «✅ Завершить #{order_id}»",
        reply_markup=shift_kb_with_orders(cleaner.id),
    )
    await call.answer()


@router.message(F.text.regexp(r"^📍 Прибыл #\d+$"))
async def arrive_text(msg: Message):
    order_id = _parse_order_id_from_button(msg.text)
    if order_id is None:
        return
    user = get_user(msg.from_user.id)
    cleaner = get_cleaner(user.id)
    order = get_order(order_id)
    if not order or order.cleaner_id != cleaner.id or order.status != "accepted":
        await msg.answer("❌ Заказ недоступен или уже в работе.")
        return
    update_order_status(order_id, "in_progress")
    await _notify_arrive_client(order_id, msg.bot)
    await msg.answer(
        f"✅ Заказ #{order_id}: вы на объекте, уборка начата.\n\n"
        f"👇 По завершении нажмите: «✅ Завершить #{order_id}»",
        reply_markup=shift_kb_with_orders(cleaner.id),
    )


async def _start_finish_flow(order_id: int, state: FSMContext, msg_or_call) -> str | None:
    user = get_user(msg_or_call.from_user.id)
    cleaner = get_cleaner(user.id)
    order = get_order(order_id)
    if not order or order.cleaner_id != cleaner.id:
        return "Заказ не найден или не ваш"
    if order.status != "in_progress":
        return "Сначала отметьте прибытие на объект"
    cur = await state.get_state()
    if cur == CleanerStates.photo:
        data = await state.get_data()
        prev = data.get("order_id")
        if prev is not None and int(prev) != int(order_id):
            return f"Сначала завершите фотоотчёт по заказу #{prev} (/done)"
    await state.update_data(order_id=order_id, photos=[])
    text = (
        f"📸 Заказ #{order_id}\n"
        f"Отправьте минимум 2 фото результата.\n"
        f"Затем нажмите /done"
    )
    if isinstance(msg_or_call, CallbackQuery):
        await msg_or_call.message.answer(text, reply_markup=shift_kb_with_orders(cleaner.id))
    else:
        await msg_or_call.answer(text, reply_markup=shift_kb_with_orders(cleaner.id))
    await state.set_state(CleanerStates.photo)
    return None


@router.callback_query(F.data.startswith("finish_"))
async def finish_callback(call: CallbackQuery, state: FSMContext):
    order_id = int(call.data.split("_")[1])
    err = await _start_finish_flow(order_id, state, call)
    if err:
        await call.answer(err, show_alert=True)
    else:
        await call.answer()


@router.message(F.text.regexp(r"^✅ Завершить #\d+$"))
async def finish_text(msg: Message, state: FSMContext):
    order_id = _parse_order_id_from_button(msg.text)
    if order_id is None:
        return
    err = await _start_finish_flow(order_id, state, msg)
    if err:
        await msg.answer(f"❌ {err}")


def _photo_caption(order, index: int, total: int) -> str:
    base = f"📍 Объект: {order.address}\n📦 Заказ #{order.id}\n📸 Фотоотчёт"
    if total > 1:
        base += f"\n({index}/{total})"
    return base[:1024]


async def _send_photo_report(bot, order, file_ids: list[str]):
    admin_ids = get_admin_notify_telegram_ids()
    total = len(file_ids)
    for i, fid in enumerate(file_ids, start=1):
        cap = _photo_caption(order, i, total)
        if order.client_id:
            client = get_user_by_id(order.client_id)
            if client:
                try:
                    await bot.send_photo(client.telegram_id, fid, caption=cap)
                except Exception as e:
                    logger.warning(f"Не удалось отправить фото клиенту {client.telegram_id}: {e}")
        for tid in admin_ids:
            try:
                await bot.send_photo(tid, fid, caption=cap)
            except Exception as e:
                logger.warning(f"Не удалось отправить фото админу {tid}: {e}")


@router.message(StateFilter(CleanerStates.photo), F.photo)
async def handle_photo(msg: Message, state: FSMContext):
    data = await state.get_data()
    photos = list(data.get("photos", []))
    photos.append(msg.photo[-1].file_id)
    oid = data.get("order_id")
    await state.update_data(photos=photos, order_id=oid)
    n = len(photos)
    await msg.answer(f"📸 Получено фото: {n}. Отправьте ещё или /done (или «готово»)")


@router.message(
    StateFilter(CleanerStates.photo),
    or_f(
        Command("done"),
        F.text.regexp(r"^/done(@\w+)?$", flags=re.IGNORECASE),
        F.text.casefold() == "готово",
    ),
)
async def done_photos(msg: Message, state: FSMContext):
    try:
        data = await state.get_data()
        order_id = data.get("order_id")
        photos = data.get("photos", [])

        if order_id is None:
            await msg.answer("❌ Сессия сброшена. Начните завершение заказа снова (кнопка «Завершить»).")
            await state.clear()
            return

        if len(photos) < 2:
            await msg.answer("❌ Нужно минимум 2 фото")
            return

        order = get_order(order_id)
        if not order:
            await msg.answer("❌ Заказ не найден")
            await state.clear()
            return

        await _send_photo_report(msg.bot, order, photos)

        if order.client_id:
            client = get_user_by_id(order.client_id)
            if client:
                try:
                    await msg.bot.send_message(
                        client.telegram_id,
                        f"✅ Заказ #{order_id} завершён.\n📍 {order.address}\n\nСпасибо, что выбрали нас!",
                    )
                except Exception as e:
                    logger.warning(f"Не удалось уведомить клиента: {e}")

        complete_order(order_id, photos)

        user = get_user(msg.from_user.id)
        cleaner = get_cleaner(user.id) if user else None
        if cleaner:
            await msg.answer(
                f"✅ Заказ #{order_id} завершён.\n"
                f"Всего выполнено заказов: {cleaner.completed_orders}",
                reply_markup=_kb_for_cleaner(msg.from_user.id),
            )
        else:
            await msg.answer("✅ Заказ завершён.", reply_markup=shift_kb_with_orders(None))
        await state.clear()
    except Exception as e:
        logger.exception(f"Ошибка при завершении заказа: {e}")
        await msg.answer(
            "❌ Ошибка при завершении. Попробуйте ещё раз: /done или напишите «готово»."
        )


@router.message(F.text == "📋 Мои заказы")
async def my_cleaner_orders(msg: Message):
    user = get_user(msg.from_user.id)
    if not user:
        await msg.answer("❌ Нажмите /start")
        return

    cleaner = get_cleaner(user.id)
    if not cleaner:
        await msg.answer("❌ Вы не зарегистрированы как уборщик")
        return

    orders = get_cleaner_orders(cleaner.id)
    if not orders:
        await msg.answer(
            "Нет активных заказов.",
            reply_markup=shift_kb_with_orders(cleaner.id),
        )
        return

    lines = ["📋 Ваши активные заказы:\n"]
    for order in orders:
        st = {"accepted": "ожидает прибытия", "in_progress": "в работе"}.get(order.status, order.status)
        lines.append(f"• #{order.id} — {order.address}\n  ({st})")
    lines.append("\n👇 Действия — кнопки внизу экрана.")
    await msg.answer("\n".join(lines), reply_markup=shift_kb_with_orders(cleaner.id))


@router.message(F.text == "📊 Моя статистика")
async def my_stats(msg: Message):
    user = get_user(msg.from_user.id)
    cleaner = get_cleaner(user.id)
    if cleaner:
        await msg.answer(
            f"📊 СТАТИСТИКА\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"👤 {cleaner.full_name}\n"
            f"✅ Завершено заказов: {cleaner.completed_orders}\n"
            f"📞 Телефон: {cleaner.phone}"
        )
