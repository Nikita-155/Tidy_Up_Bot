import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aiogram import *
from aiogram.filters import *
from aiogram.fsm.context import *
from aiogram.fsm.state import *
from aiogram.types import *
from loguru import logger
from database import get_user, create_user, update_user_phone, create_order, get_user_orders
from keyboards.reply_kb import start_kb, phone_kb, types_kb, confirm_kb, skip_kb
from utils.validators import validate_phone, validate_area, format_phone
from aiogram_calendar import *

router = Router()

class OrderStates(StatesGroup):
    cleaning_type = State()
    area = State()
    address = State()
    date = State()
    time = State()
    phone = State()
    notes = State()
    confirm = State()

@router.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name

    user = get_user(user_id)
    if not user:
        create_user(user_id, username, first_name)
        logger.info(f"Новый пользователь: {user_id} - {first_name}")

    welcome_text = (
        f"👋 Привет, {first_name}!\n\n"
        f"Я бот клининговой компании TidyUp.\n"
        f"Помогу быстро и удобно заказать уборку.\n\n"
        f"Выберите действие:"
    )

    await message.answer(welcome_text, reply_markup=start_kb())

@router.message(F.text == "🧹 Заказать уборку")
async def order_start(message: Message, state: FSMContext):
    await message.answer(
        "📋 **Выберите типы уборки** (можно несколько):\n\n"
        "✅ — выбранный тип\n"
        "Нажимайте на нужные типы, затем нажмите «Готово»",
        reply_markup=types_kb([])
    )
    await state.set_state(OrderStates.cleaning_type)
    await state.update_data(selected_types=[])

@router.callback_query(StateFilter(OrderStates.cleaning_type), F.data.startswith(("type_", "types_")))
async def process_cleaning_type(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected_types = data.get('selected_types', [])

    cleaning_types_names = {
        "type_support": "🧹 Поддерживающая уборка",
        "type_deep": "✨ Генеральная уборка",
        "type_windows": "🪟 Мойка окон",
        "type_dry_cleaning": "🧺 Химчистка мебели",
        "type_after_repair": "🏭 Уборка после ремонта",
        "type_office": "🏢 Офисная уборка",
        "type_moving": "📦 Уборка после переезда",
        "type_chandelier": "🧽 Мытье люстр",
        "type_territory": "🌳 Уборка территории"
    }

    if callback.data == "types_done":
        if not selected_types:
            await callback.answer("❌ Выберите хотя бы один тип уборки", show_alert=True)
            return

        selected_names = [cleaning_types_names[t] for t in selected_types]
        await state.update_data(cleaning_type=selected_names, selected_types=selected_types)

        selected_text = "\n".join([f"• {name}" for name in selected_names])
        await callback.message.edit_text(
            f"✅ **Выбраны типы уборки:**\n{selected_text}\n\n"
            f"📏 Теперь укажите примерную площадь помещения (в м²):"
        )
        await callback.answer()
        await state.set_state(OrderStates.area)

    elif callback.data == "types_clear":
        await state.update_data(selected_types=[])
        await callback.message.edit_text(
            "🔄 Выберите типы уборки (можно несколько):",
            reply_markup=types_kb([])
        )
        await callback.answer()

    else:
        if callback.data in selected_types:
            selected_types.remove(callback.data)
        else:
            selected_types.append(callback.data)

        await state.update_data(selected_types=selected_types)
        await callback.message.edit_text(
            "📋 Выберите типы уборки (можно несколько):\n"
            "✅ — выбранный тип\n"
            "Нажмите «Готово» когда закончите:",
            reply_markup=types_kb(selected_types)
        )
        await callback.answer()

@router.message(StateFilter(OrderStates.area))
async def process_area(message: Message, state: FSMContext):
    if not validate_area(message.text):
        await message.answer("❌ Введите корректное число (например: 45, 67.5)")
        return

    area = float(message.text)
    await state.update_data(area=area)
    await message.answer(f"Площадь: {area} м²\n\n📍 Введите адрес уборки (улица, дом, квартира):")
    await state.set_state(OrderStates.address)

@router.message(StateFilter(OrderStates.address))
async def process_address(message: Message, state: FSMContext):
    if len(message.text) < 5:
        await message.answer("❌ Слишком короткий адрес. Введите полный адрес:")
        return

    await state.update_data(address=message.text)
    await message.answer("📅 Выберите дату уборки:", reply_markup=await SimpleCalendar().start_calendar())
    await state.set_state(OrderStates.date)

@router.callback_query(StateFilter(OrderStates.date), SimpleCalendarCallback.filter())
async def process_date(callback: CallbackQuery, callback_data: SimpleCalendarCallback, state: FSMContext):
    calendar = SimpleCalendar()
    selected, date = await calendar.process_selection(callback, callback_data)

    if selected:
        date_str = date.strftime("%d.%m.%Y")
        await state.update_data(date=date_str)

        time_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🕐 9:00-11:00", callback_data="time_9:00-11:00"),
             InlineKeyboardButton(text="🕐 11:00-13:00", callback_data="time_11:00-13:00"),
             InlineKeyboardButton(text="🕐 13:00-15:00", callback_data="time_13:00-15:00")],
            [InlineKeyboardButton(text="🕐 15:00-17:00", callback_data="time_15:00-17:00"),
             InlineKeyboardButton(text="🕐 17:00-19:00", callback_data="time_17:00-19:00")]
        ])

        await callback.message.edit_text(
            f"📅 Выбрана дата: {date_str}\n\n🕐 Выберите время:",
            reply_markup=time_keyboard
        )
        await state.set_state(OrderStates.time)

    await callback.answer()

@router.callback_query(StateFilter(OrderStates.time), F.data.startswith("time_"))
async def process_time(callback: CallbackQuery, state: FSMContext):
    time_str = callback.data.replace("time_", "")
    await state.update_data(time=time_str)

    data = await state.get_data()
    date_str = data.get('date', '')
    user = get_user(callback.from_user.id)

    if user and user.phone:
        await state.update_data(phone=user.phone)
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Да", callback_data="use_existing_phone"),
             InlineKeyboardButton(text="🔄 Новый", callback_data="new_phone")]
        ])
        await callback.message.edit_text(
            f"📅 {date_str} | 🕐 {time_str}\n\n📞 {format_phone(user.phone)}\n\nИспользовать?",
            reply_markup=keyboard
        )
    else:
        await callback.message.edit_text(
            f"📅 {date_str} | 🕐 {time_str}\n\n📱 Отправьте номер:",
            reply_markup=phone_kb()
        )
    await state.set_state(OrderStates.phone)
    await callback.answer()

@router.callback_query(StateFilter(OrderStates.phone), F.data == "use_existing_phone")
async def use_existing_phone(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("📝 Доп. пожелания?", reply_markup=skip_kb())
    await callback.answer()
    await state.set_state(OrderStates.notes)

@router.callback_query(StateFilter(OrderStates.phone), F.data == "new_phone")
async def new_phone(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("📱 Отправьте номер:", reply_markup=phone_kb())
    await callback.answer()

@router.message(StateFilter(OrderStates.phone), F.contact)
async def process_phone_contact(message: Message, state: FSMContext):
    phone = message.contact.phone_number
    if not phone.startswith('+'):
        phone = '+' + phone
    await state.update_data(phone=phone)
    update_user_phone(message.from_user.id, phone)
    await message.answer("📝 Доп. пожелания?", reply_markup=skip_kb())
    await state.set_state(OrderStates.notes)

@router.message(StateFilter(OrderStates.phone), F.text)
async def process_phone_manual(message: Message, state: FSMContext):
    if not validate_phone(message.text):
        await message.answer("❌ Неверный формат. Введите +7XXXXXXXXXX")
        return
    await state.update_data(phone=message.text)
    update_user_phone(message.from_user.id, message.text)
    await message.answer("📝 Доп. пожелания?", reply_markup=skip_kb())
    await state.set_state(OrderStates.notes)

@router.callback_query(StateFilter(OrderStates.notes), F.data == "skip_notes")
async def skip_notes(callback: CallbackQuery, state: FSMContext):
    await state.update_data(notes="Нет")
    await callback.answer()
    await show_order_summary(callback.message, state)

@router.message(StateFilter(OrderStates.notes))
async def process_notes(message: Message, state: FSMContext):
    await state.update_data(notes=message.text)
    await show_order_summary(message, state)

async def show_order_summary(message: Message, state: FSMContext):
    data = await state.get_data()

    base_price = {
        "🧹 Поддерживающая уборка": 40, "✨ Генеральная уборка": 70,
        "🪟 Мойка окон": 30, "🧺 Химчистка мебели": 100,
        "🏭 Уборка после ремонта": 90, "🏢 Офисная уборка": 50,
        "📦 Уборка после переезда": 80, "🧽 Мытье люстр": 150,
        "🌳 Уборка территории": 60
    }

    cleaning_types = data.get('cleaning_type', [])
    area = data.get('area', 0)

    total_price = 0
    for ct in cleaning_types:
        total_price += area * base_price.get(ct, 50)

    types_text = "\n".join([f"• {ct}" for ct in cleaning_types])

    summary = (
        f"📋 **Проверьте заказ:**\n\n"
        f"**Типы:**\n{types_text}\n"
        f"**Площадь:** {area} м²\n"
        f"**Адрес:** {data.get('address')}\n"
        f"**Дата:** {data.get('date')} {data.get('time')}\n"
        f"**Телефон:** {format_phone(data.get('phone'))}\n"
        f"**Пожелания:** {data.get('notes', 'Нет')}\n\n"
        f"💰 {total_price:.0f} ₽\n\n"
        f"Всё верно?"
    )

    await state.set_state(OrderStates.confirm)
    await message.answer(summary, reply_markup=confirm_kb())

@router.callback_query(StateFilter(OrderStates.confirm), F.data == "confirm_order")
async def confirm_order(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    user = get_user(callback.from_user.id)
    if not user:
        user = create_user(
            callback.from_user.id,
            callback.from_user.username,
            callback.from_user.first_name,
        )

    cleaning_types = data.get("cleaning_type", [])
    if not cleaning_types:
        await callback.message.answer("❌ Данные заказа устарели. Начните оформление заново: «Заказать уборку».")
        await state.clear()
        return

    try:
        order = create_order(user.id, {
            "cleaning_type": ", ".join(cleaning_types),
            "area": data.get("area"),
            "address": data.get("address"),
            "date": data.get("date"),
            "time": data.get("time"),
            "phone": data.get("phone"),
            "notes": data.get("notes", "Нет"),
        })
    except Exception as e:
        logger.exception(e)
        await callback.message.answer("❌ Не удалось сохранить заказ. Попробуйте ещё раз или /start")
        return

    await state.clear()
    try:
        await callback.message.edit_text(
            f"✅ Заказ #{order.id} оформлен!\n\nСтатус можно отслеживать в «Мои заказы»"
        )
    except Exception:
        await callback.message.answer(
            f"✅ Заказ #{order.id} оформлен!\n\nСтатус можно отслеживать в «Мои заказы»"
        )
    await callback.message.answer("Выберите действие:", reply_markup=start_kb())

@router.callback_query(StateFilter(OrderStates.confirm), F.data == "cancel_order")
async def cancel_order(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    try:
        await callback.message.edit_text("❌ Отменено")
    except Exception:
        await callback.message.answer("❌ Отменено")
    await callback.message.answer("Выберите действие:", reply_markup=start_kb())

@router.message(F.text == "📋 Мои заказы")
async def my_orders(message: Message):
    user = get_user(message.from_user.id)
    if not user:
        await message.answer("Сначала /start")
        return

    orders = get_user_orders(message.from_user.id)
    if not orders:
        await message.answer("У вас пока нет заказов.\nНажмите «Заказать уборку»")
        return

    status_emoji = {'new': '🆕', 'accepted': '✅', 'in_progress': '🔄',
                    'completed': '⭐', 'confirmed': '👍', 'cancelled': '❌'}
    status_text = {'new': 'Новый', 'accepted': 'Принят', 'in_progress': 'В работе',
                   'completed': 'Завершен', 'confirmed': 'Подтвержден', 'cancelled': 'Отменен'}

    text = "📋 Ваши заказы:\n\n"
    for order in orders[:5]:
        text += f"{status_emoji.get(order.status, '📌')} #{order.id} | {order.cleaning_type[:25]} | {order.date}\n"
        text += f"   Статус: {status_text.get(order.status, order.status)}\n\n"
    await message.answer(text)

@router.message(F.text == "📞 Контакты")
async def contacts(message: Message):
    from config import COMPANY_PHONE, COMPANY_EMAIL, COMPANY_WEBSITE, COMPANY_MANAGER
    await message.answer(
        f"📞 {COMPANY_PHONE}\n📧 {COMPANY_EMAIL}\n🌐 {COMPANY_WEBSITE}\n\n🕒 9:00-21:00"
    )

@router.message(Command("cancel"))
async def cancel_command(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Отменено", reply_markup=start_kb())