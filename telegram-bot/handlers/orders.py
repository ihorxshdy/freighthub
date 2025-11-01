from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timedelta
import asyncio
import aiosqlite
import logging

from database.models import (
    get_user_by_telegram_id, create_order, get_drivers_by_truck_type_multiple, 
    get_order_by_id, create_bid, get_bids_for_order, complete_order,
    save_order_message, get_order_message, get_driver_messages_for_order
)
from bot.config import TRUCK_TYPES, TRUCK_CATEGORIES, AUCTION_DURATION, DB_PATH, get_truck_display_name
from utils.message_formatter import format_order_message, format_driver_notification

router = Router()

class OrderStates(StatesGroup):
    choosing_truck_category = State()
    choosing_truck_subtype = State() 
    choosing_truck_final = State()
    entering_order_details = State()

class BidStates(StatesGroup):
    entering_bid = State()

# Хранилище активных аукционов
active_auctions = {}

@router.message(F.text == "📦 Создать заявку")
async def start_order_creation(message: Message, state: FSMContext):
    """Начало создания заявки"""
    if not message.from_user:
        return
        
    user = await get_user_by_telegram_id(message.from_user.id)
    
    if not user or user['role'] != 'customer':
        await message.answer("❌ Эта функция доступна только заказчикам!")
        return
    
    # Создаем временную заявку для форматирования
    temp_order = {
        'id': '...',
        'truck_type': 'Не выбран',
        'cargo_description': 'Ожидание описания...',
        'pickup_address': None,
        'pickup_time': None,
        'delivery_address': None,
        'delivery_time': None,
        'created_at': datetime.now().isoformat()
    }
    
    # Показываем категории машин
    category_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=category_info['name'], callback_data=f"order_category_{category_id}")]
        for category_id, category_info in TRUCK_CATEGORIES.items()
    ])
    
    # Форматируем сообщение для этапа создания
    message_text, _ = format_order_message(temp_order, stage="creating")
    message_text += f"\n\n� **Шаг 1/2: Выберите тип машины**"
    
    # Отправляем сообщение и сохраняем его ID в состоянии
    sent_message = await message.answer(message_text, reply_markup=category_keyboard)
    
    # Сохраняем ID сообщения в состоянии для дальнейшего редактирования
    await state.update_data(
        order_message_id=sent_message.message_id,
        order_chat_id=sent_message.chat.id
    )
    
    await state.set_state(OrderStates.choosing_truck_category)

@router.callback_query(StateFilter(OrderStates.choosing_truck_category), F.data.startswith("order_category_"))
async def order_category_chosen(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора категории машины для заявки"""
    if not callback.data:
        return
        
    category_id = callback.data.split("_")[2]
    category_info = TRUCK_CATEGORIES[category_id]
    
    await state.update_data(order_truck_category=category_id)
    
    # Создаем клавиатуру с подтипами
    subtype_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=subtype_name, callback_data=f"order_subtype_{category_id}_{subtype_id}")]
        for subtype_id, subtype_name in category_info['subtypes'].items()
    ] + [[InlineKeyboardButton(text="◀️ Назад", callback_data="order_back_to_categories")]])
    
    await callback.message.edit_text(
        f"📝 **Создание заявки - шаг 1/2**\n\n"
        f"🚚 Категория: {category_info['name']}\n\n"
        "Выберите подтип:",
        reply_markup=subtype_keyboard
    )
    
    await state.set_state(OrderStates.choosing_truck_subtype)

@router.callback_query(StateFilter(OrderStates.choosing_truck_subtype), F.data.startswith("order_subtype_"))
async def order_subtype_chosen(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора подтипа машины для заявки"""
    parts = callback.data.split("_")
    # Формат: order_subtype_category_subtype_id
    # где subtype_id может содержать _ и category prefix
    category_id = parts[2]  # всегда третий элемент
    # subtype_id - все остальные части, объединенные обратно
    subtype_id = "_".join(parts[3:])
    
    print(f"DEBUG: order_subtype_chosen - callback_data: {callback.data}")
    print(f"DEBUG: parts: {parts}")
    print(f"DEBUG: category_id: {category_id}, subtype_id: {subtype_id}")
    
    category_info = TRUCK_CATEGORIES[category_id]
    print(f"DEBUG: category_info: {category_info}")
    
    # Проверяем, есть ли дополнительные подуровни
    print(f"DEBUG: Проверка sub_subtypes:")
    print(f"DEBUG: category_id in TRUCK_CATEGORIES: {category_id in TRUCK_CATEGORIES}")
    print(f"DEBUG: 'sub_subtypes' in category_info: {'sub_subtypes' in category_info}")
    print(f"DEBUG: subtype_id in category_info['sub_subtypes']: {subtype_id in category_info.get('sub_subtypes', {})}")
    
    if category_id in TRUCK_CATEGORIES and 'sub_subtypes' in category_info and subtype_id in category_info['sub_subtypes']:
        # Есть дополнительные подуровни (для Газели)
        print(f"DEBUG: Переходим к финальному выбору для {subtype_id}")
        await state.update_data(order_truck_subtype=subtype_id)
        
        sub_subtypes = category_info['sub_subtypes'][subtype_id]
        final_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=sub_subtype_name, callback_data=f"order_final_{category_id}_{subtype_id}_{sub_subtype_id}")]
            for sub_subtype_id, sub_subtype_name in sub_subtypes.items()
        ] + [[InlineKeyboardButton(text="◀️ Назад", callback_data=f"order_back_to_subtypes_{category_id}")]])
        
        subtype_name = category_info['subtypes'][subtype_id]
        await callback.message.edit_text(
            f"📝 **Создание заявки - шаг 1/2**\n\n"
            f"🚚 Категория: {category_info['name']}\n"
            f"Тип: {subtype_name}\n\n"
            "Выберите характеристики:",
            reply_markup=final_keyboard
        )
        
        await state.set_state(OrderStates.choosing_truck_final)
    else:
        # Это финальный выбор (для Манипулятора и Длинномера)
        print(f"DEBUG: Выбран финальный тип машины: {subtype_id}")
        await state.update_data(truck_type=subtype_id)
        
        truck_name = get_truck_display_name(subtype_id)
        print(f"DEBUG: Отображаемое имя: {truck_name}")
        await callback.message.edit_text(
            f"📝 **Создание заявки - шаг 2/2**\n\n"
            f"✅ Выбран тип машины: {truck_name}\n\n"
            f"📝 Опишите ваш заказ:\n\n"
            f"Укажите всю необходимую информацию:\n"
            f"• Что перевозить (груз, вес, размеры)\n"
            f"• Откуда забрать (адрес погрузки)\n"
            f"• Куда доставить (адрес доставки)\n"
            f"• Время погрузки и доставки\n"
            f"• Дополнительные требования\n\n"
            f"Пример:\n"
            f"Перевезти мебель (диван + шкаф) примерно 500кг.\n"
            f"Забрать: ул. Ленина 15, Москва, завтра в 10:00\n"
            f"Доставить: ул. Мира 22, Подольск, до 15:00\n"
            f"Нужна помощь с погрузкой."
        )
        
        await state.set_state(OrderStates.entering_order_details)

@router.callback_query(StateFilter(OrderStates.choosing_truck_final), F.data.startswith("order_final_"))
async def order_final_chosen(callback: CallbackQuery, state: FSMContext):
    """Обработка финального выбора характеристик машины для заявки"""
    parts = callback.data.split("_")
    # Формат: order_final_category_subtype_id_final_type_id
    # Последний элемент - это финальный тип (например gazel_closed_10m3)
    final_id = parts[-1]  # последний элемент
    # Но если это составной ID, нужно взять правильную часть
    # Ищем в TRUCK_TYPES по ключу который заканчивается на final_id
    for truck_key in TRUCK_TYPES.keys():
        if truck_key.endswith(final_id):
            final_id = truck_key
            break
    
    print(f"DEBUG: order_final_chosen - callback_data: {callback.data}")
    print(f"DEBUG: parts: {parts}")
    print(f"DEBUG: Выбран финальный тип машины: {final_id}")
    await state.update_data(truck_type=final_id)
    
    truck_name = get_truck_display_name(final_id)
    print(f"DEBUG: Отображаемое имя (Газель): {truck_name}")
    await callback.message.edit_text(
        f"📝 **Создание заявки - шаг 2/2**\n\n"
        f"✅ Выбран тип машины: {truck_name}\n\n"
        f"📝 Опишите ваш заказ:\n\n"
        f"Укажите всю необходимую информацию:\n"
        f"• Что перевозить (груз, вес, размеры)\n"
        f"• Откуда забрать (адрес погрузки)\n"
        f"• Куда доставить (адрес доставки)\n"
        f"• Время погрузки и доставки\n"
        f"• Дополнительные требования\n\n"
        f"Пример:\n"
        f"Перевезти мебель (диван + шкаф) примерно 500кг.\n"
        f"Забрать: ул. Ленина 15, Москва, завтра в 10:00\n"
        f"Доставить: ул. Мира 22, Подольск, до 15:00\n"
        f"Нужна помощь с погрузкой."
    )
    
    await state.set_state(OrderStates.entering_order_details)

# Обработчики кнопок "Назад" для заявок
@router.callback_query(F.data == "order_back_to_categories")
async def order_back_to_categories(callback: CallbackQuery, state: FSMContext):
    """Возврат к выбору категорий для заявки"""
    category_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=category_info['name'], callback_data=f"order_category_{category_id}")]
        for category_id, category_info in TRUCK_CATEGORIES.items()
    ])
    
    await callback.message.edit_text(
        "📝 **Создание заявки - шаг 1/2**\n\n"
        "🚚 Выберите тип машины для перевозки:",
        reply_markup=category_keyboard
    )
    
    await state.set_state(OrderStates.choosing_truck_category)

@router.callback_query(F.data.startswith("order_back_to_subtypes_"))
async def order_back_to_subtypes(callback: CallbackQuery, state: FSMContext):
    """Возврат к выбору подтипов для заявки"""
    category_id = callback.data.split("_")[4]
    category_info = TRUCK_CATEGORIES[category_id]
    
    subtype_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=subtype_name, callback_data=f"order_subtype_{category_id}_{subtype_id}")]
        for subtype_id, subtype_name in category_info['subtypes'].items()
    ] + [[InlineKeyboardButton(text="◀️ Назад", callback_data="order_back_to_categories")]])
    
    await callback.message.edit_text(
        f"📝 **Создание заявки - шаг 1/2**\n\n"
        f"🚚 Категория: {category_info['name']}\n\n"
        "Выберите подтип:",
        reply_markup=subtype_keyboard
    )
    
    await state.set_state(OrderStates.choosing_truck_subtype)

@router.message(StateFilter(OrderStates.entering_order_details), F.text)
async def order_details_received(message: Message, state: FSMContext, bot: Bot):
    """Обработка деталей заказа"""
    if not message.text or not message.from_user:
        return
        
    order_description = message.text.strip()
    
    # Проверяем минимальную длину описания
    if len(order_description) < 10:
        await message.answer(
            "❌ Слишком короткое описание заказа. Пожалуйста, укажите более подробную информацию о:\n\n"
            "• Что нужно перевозить\n"
            "• Откуда и куда\n"
            "• Когда нужно выполнить\n"
        )
        return
    
    data = await state.get_data()
    
    # Проверяем, что выбран конкретный тип машины, а не категория
    if 'truck_type' not in data:
        await message.answer("❌ Ошибка: тип машины не выбран. Попробуйте создать заявку заново.")
        await state.clear()
        return
    
    # Проверяем, что truck_type является конечным типом из TRUCK_TYPES
    truck_type = data['truck_type']
    if truck_type not in TRUCK_TYPES:
        print(f"DEBUG: truck_type '{truck_type}' не найден в TRUCK_TYPES. Пытаемся исправить...")
        
        # Возможно, сохранена категория вместо конкретного типа
        # Попробуем найти первый доступный тип из этой категории
        if truck_type in TRUCK_CATEGORIES:
            category_info = TRUCK_CATEGORIES[truck_type]
            subtypes = category_info.get('subtypes', {})
            if subtypes:
                # Берем первый доступный подтип
                first_subtype = list(subtypes.keys())[0]
                print(f"DEBUG: Исправляем {truck_type} -> {first_subtype}")
                data['truck_type'] = first_subtype
                truck_type = first_subtype
        
        # Если все еще не найден, выводим ошибку
        if truck_type not in TRUCK_TYPES:
            print(f"DEBUG: Не удалось исправить truck_type '{truck_type}'")
            print(f"DEBUG: Доступные типы: {list(TRUCK_TYPES.keys())}")
            await message.answer(f"❌ Ошибка: неизвестный тип машины '{truck_type}'. Попробуйте создать заявку заново.")
            await state.clear()
            return
    
    user = await get_user_by_telegram_id(message.from_user.id)
    
    # Создание времени истечения заявки (10 минут)
    from datetime import datetime, timedelta
    expires_at = datetime.now() + timedelta(seconds=AUCTION_DURATION)
    
    # Получаем ID сообщения из состояния для обновления
    print(f"DEBUG: Создание заявки с типом машины: {data['truck_type']}")
    truck_name = get_truck_display_name(data['truck_type'])
    print(f"DEBUG: Финальное отображаемое имя при создании: {truck_name}")
    
    # Обновляем существующее сообщение вместо создания нового
    order_message_id = data.get('order_message_id')
    order_chat_id = data.get('order_chat_id')
    
    initial_text = (
        f"📝 Создание заявки...\n\n"
        f"🚚 Тип машины: {truck_name}\n"
        f"📦 Описание заказа:\n{order_description}\n\n"
        f"⏳ Обработка..."
    )
    
    if order_message_id and order_chat_id:
        # Обновляем существующее сообщение
        try:
            await bot.edit_message_text(
                chat_id=order_chat_id,
                message_id=order_message_id,
                text=initial_text
            )
            print(f"DEBUG: Обновлено существующее сообщение {order_message_id}")
        except Exception as e:
            print(f"DEBUG: Ошибка при обновлении сообщения: {e}")
            # Fallback: создаем новое сообщение
            status_message = await message.answer(initial_text)
            order_message_id = status_message.message_id
            order_chat_id = status_message.chat.id
    else:
        # Создаем новое сообщение если не найдено существующее
        status_message = await message.answer(initial_text)
        order_message_id = status_message.message_id
        order_chat_id = status_message.chat.id
    
    try:
        order_id = await create_order(
            customer_id=user['id'],
            truck_type=data['truck_type'],
            cargo_description=order_description,
            delivery_address="Указан в описании",
            expires_at=expires_at.isoformat(),
            pickup_address="Указан в описании",
            pickup_time="Указано в описании",
            delivery_time="Указано в описании"
        )
        
        # Обновляем сообщение - заявка создана
        await bot.edit_message_text(
            chat_id=order_chat_id,
            message_id=order_message_id,
            text=f"✅ Заявка создана и отправлена водителям!\n\n"
                 f"📋 Заявка #{order_id}\n"
                 f"🚚 Тип машины: {truck_name}\n"
                 f"📦 Описание:\n{order_description}\n\n"
                 f"⏰ Время на подачу предложений: {AUCTION_DURATION // 60} минут\n"
                 f"🔄 Статус: Ожидание предложений от водителей..."
        )
        
        # Отправляем заявку всем подходящим водителям
        drivers_count = await notify_drivers_about_order(bot, order_id, data['truck_type'])
        
        # Обновляем сообщение с количеством уведомленных водителей
        await bot.edit_message_text(
            chat_id=order_chat_id,
            message_id=order_message_id,
            text=f"✅ Заявка создана и отправлена водителям!\n\n"
                 f"📋 Заявка #{order_id}\n"
                 f"🚚 Тип машины: {truck_name}\n"
                 f"📦 Описание:\n{order_description}\n\n"
                 f"👥 Уведомлено водителей: {drivers_count}\n"
                 f"⏰ Время на подачу предложений: {AUCTION_DURATION // 60} минут\n"
                 f"🔄 Статус: Ожидание предложений от водителей..."
        )
        
        # Сохраняем информацию о сообщении заказчика
        await save_order_message(
            order_id=order_id,
            user_id=user['id'],
            chat_id=order_chat_id,
            message_id=order_message_id,
            message_type='customer'
        )
        
        # Запускаем таймер аукциона
        import asyncio
        asyncio.create_task(auction_timer(bot, order_id))
        
    except Exception as e:
        await status_message.edit_text(f"❌ Ошибка при создании заявки: {str(e)}")
    
    await state.clear()



async def notify_drivers_about_order(bot: Bot, order_id: int, truck_type: str):
    """Уведомление водителей о новой заявке"""
    order = await get_order_by_id(order_id)
    drivers = await get_drivers_by_truck_type_multiple(truck_type)
    
    if not drivers:
        return 0
    
    truck_name = get_truck_display_name(truck_type)
    
    bid_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Сделать предложение", callback_data=f"bid_{order_id}")]
    ])
    
    message_text = (
        f"🆕 Новая заявка #{order_id}\n\n"
        f"🚚 Тип машины: {truck_name}\n"
        f"📋 Описание заказа:\n{order['cargo_description']}\n\n"
        f"⏰ Время на предложения: {AUCTION_DURATION // 60} минут"
    )
    
    sent_count = 0
    for driver in drivers:
        try:
            sent_message = await bot.send_message(
                chat_id=driver['telegram_id'],
                text=message_text,
                reply_markup=bid_keyboard
            )
            # Сохраняем информацию о сообщении для каждого водителя
            await save_order_message(
                order_id=order_id,
                user_id=driver['id'],
                chat_id=driver['telegram_id'],
                message_id=sent_message.message_id,
                message_type='driver_notification'
            )
            sent_count += 1
        except Exception as e:
            print(f"Не удалось отправить сообщение водителю {driver['telegram_id']}: {e}")
    
    return sent_count

@router.callback_query(F.data.startswith("bid_"))
async def make_bid_start(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Начало процесса подачи предложения"""
    order_id = int(callback.data.split("_")[1])
    
    user = await get_user_by_telegram_id(callback.from_user.id)
    
    if not user or user['role'] != 'driver':
        await callback.answer("❌ Только водители могут делать предложения!")
        return
    
    order = await get_order_by_id(order_id)
    if not order or order['status'] != 'active':
        await callback.answer("❌ Заявка больше не активна!")
        return
    
    truck_name = get_truck_display_name(order['truck_type'])
    
    # Обновляем существующее сообщение с формой для ввода цены
    try:
        await bot.edit_message_text(
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id,
            text=f"🚚 Заявка #{order_id}\n\n"
                 f"🚚 Тип машины: {truck_name}\n"
                 f"📋 Описание заказа:\n{order['cargo_description']}\n\n"
                 "💰 Введите вашу цену за перевозку (в рублях):"
        )
    except Exception as e:
        logging.error(f"Ошибка при обновлении сообщения водителя: {e}")
    
    # Сохраняем информацию для обновления этого сообщения
    await state.update_data(
        order_id=order_id, 
        message_id=callback.message.message_id,
        chat_id=callback.message.chat.id
    )
    
    await state.set_state(BidStates.entering_bid)

@router.message(StateFilter(BidStates.entering_bid), F.text)
async def bid_price_received(message: Message, state: FSMContext, bot: Bot):
    """Обработка цены предложения"""
    try:
        price = float(message.text.strip())
        if price <= 0:
            raise ValueError("Цена должна быть положительной")
            
        data = await state.get_data()
        order_id = data['order_id']
        message_id = data.get('message_id')
        chat_id = data.get('chat_id')
        
        user = await get_user_by_telegram_id(message.from_user.id)
        order = await get_order_by_id(order_id)
        
        await create_bid(order_id, user['id'], price)
        
        # Обновляем существующее сообщение с подтверждением предложения
        if message_id and chat_id:
            truck_name = get_truck_display_name(order['truck_type'])
            try:
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=f"✅ Ваше предложение принято!\n\n"
                         f"🚚 Заявка #{order_id}\n"
                         f"🚚 Тип машины: {truck_name}\n"
                         f"📋 Описание заказа:\n{order['cargo_description']}\n\n"
                         f"💰 Цена: {price} руб.\n"
                         f"⏰ Результаты будут объявлены в конце аукциона."
                )
            except Exception as e:
                logging.error(f"Ошибка при обновлении сообщения с предложением: {e}")
                # Fallback - отправляем новое сообщение если не удалось обновить
                await message.answer(
                    f"✅ Ваше предложение принято!\n\n"
                    f"💰 Цена: {price} руб.\n"
                    f"⏰ Результаты будут объявлены в конце аукциона."
                )
        else:
            # Fallback - если нет данных о сообщении
            await message.answer(
                f"✅ Ваше предложение принято!\n\n"
                f"💰 Цена: {price} руб.\n"
                f"⏰ Результаты будут объявлены в конце аукциона."
            )
        
    except ValueError:
        await message.answer(
            "❌ Неверный формат цены. Введите число (например: 5000):"
        )
        return
    except Exception as e:
        await message.answer(f"❌ Ошибка при подаче предложения: {str(e)}")
    
    await state.clear()

async def auction_timer(bot: Bot, order_id: int):
    """Таймер аукциона"""
    # Ждем окончания аукциона
    await asyncio.sleep(AUCTION_DURATION)
    
    # Получаем все предложения
    bids = await get_bids_for_order(order_id)
    order = await get_order_by_id(order_id)
    
    if not order or order['status'] != 'active':
        return
    
    if not bids:
        # Нет предложений
        await complete_order(order_id, None, None, 'no_offers')
        
        # Получаем информацию о сообщении заявки
        order_message_info = await get_order_message(order_id, 'customer')
        
        # Обновляем статусное сообщение заказчика
        if order_message_info:
            try:
                truck_name = get_truck_display_name(order['truck_type'])
                await bot.edit_message_text(
                    chat_id=order_message_info['chat_id'],
                    message_id=order_message_info['message_id'],
                    text=f"❌ Заявка #{order_id} закрыта\n\n"
                         f"🚚 Тип машины: {truck_name}\n"
                         f"📦 Описание: {order['cargo_description']}\n\n"
                         f"⏰ Аукцион завершен\n"
                         f"🔄 Статус: Нет предложений от водителей\n\n"
                         f"💡 Попробуйте создать новую заявку или изменить условия."
                )
            except Exception as e:
                logging.error(f"Ошибка при обновлении сообщения заявки: {e}")
                # Fallback: отправляем новое сообщение если не удалось обновить
                async with aiosqlite.connect(DB_PATH) as db:
                    async with db.execute("SELECT telegram_id FROM users WHERE id = ?", (order['customer_id'],)) as cursor:
                        customer_row = await cursor.fetchone()
                        if customer_row:
                            try:
                                await bot.send_message(
                                    chat_id=customer_row[0],
                                    text=f"❌ К сожалению, на заявку #{order_id} не поступило предложений от водителей.\n\n"
                                         f"Попробуйте создать новую заявку или изменить условия."
                                )
                            except:
                                pass
            
    else:
        # Есть предложения, выбираем минимальную цену
        winning_bid = bids[0]  # Уже отсортировано по цене
        
        await complete_order(
            order_id, 
            winning_bid['driver_id'], 
            winning_bid['price'], 
            'completed'
        )
        
        # Уведомляем заказчика о результатах (функция сама обновит сообщение)
        await notify_customer_about_winner(bot, order, winning_bid)
        
        # Уведомляем водителей
        await notify_drivers_about_results(bot, order_id, bids, winning_bid)

async def notify_customer_about_winner(bot: Bot, order: dict, winning_bid: dict):
    """Уведомление заказчика о результатах аукциона"""
    order_id = order['id']
    
    # Получаем информацию о сообщении заказчика
    order_message_info = await get_order_message(order_id, 'customer')
    
    truck_name = get_truck_display_name(order['truck_type'])
    
    # Получаем количество предложений для отображения
    bids = await get_bids_for_order(order_id)
    bids_count = len(bids) if bids else 0
    
    message_text = (
        f"🎉 Заявка #{order_id} завершена!\n\n"
        f"🚚 Тип машины: {truck_name}\n"
        f"📦 Описание: {order['cargo_description']}\n\n"
        f"🏆 Выбран водитель: {winning_bid['driver_name'] or 'Неизвестно'}\n"
        f"💰 Выигрышная цена: {winning_bid['price']} руб.\n"
        f"👥 Всего предложений: {bids_count}\n"
        f"📞 Телефон водителя: {winning_bid['driver_phone']}\n\n"
        f"✅ Свяжитесь с водителем для уточнения деталей заказа."
    )
    
    # Пытаемся обновить существующее сообщение заказчика
    if order_message_info:
        try:
            await bot.edit_message_text(
                chat_id=order_message_info['chat_id'],
                message_id=order_message_info['message_id'],
                text=message_text
            )
            return  # Успешно обновили, выходим
        except Exception as e:
            logging.error(f"Ошибка при обновлении сообщения заказчика: {e}")
    
    # Fallback: если не удалось обновить, отправляем новое сообщение
    try:
        # Получаем telegram_id заказчика
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT telegram_id FROM users WHERE id = ?", (order['customer_id'],)) as cursor:
                customer_row = await cursor.fetchone()
                if customer_row:
                    customer_telegram_id = customer_row[0]
                    await bot.send_message(
                        chat_id=customer_telegram_id,
                        text=message_text
                    )
    except Exception as e:
        logging.error(f"Ошибка отправки нового сообщения заказчику: {e}")

async def notify_drivers_about_results(bot: Bot, order_id: int, all_bids: list, winning_bid: dict):
    """Уведомление водителей о результатах аукциона"""
    # Получаем данные заявки и заказчика
    order = await get_order_by_id(order_id)
    customer_info = None
    
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT phone_number, name FROM users WHERE id = ?", (order['customer_id'],)) as cursor:
            customer_row = await cursor.fetchone()
            if customer_row:
                customer_info = {
                    'phone': customer_row[0],
                    'name': customer_row[1] or 'Заказчик'
                }
    
    # Получаем сообщения водителей для этой заявки
    driver_messages = await get_driver_messages_for_order(order_id)
    
    # Создаем словарь для быстрого поиска сообщений по telegram_id водителя
    messages_by_telegram_id = {msg['telegram_id']: msg for msg in driver_messages}
    
    for bid in all_bids:
        driver_telegram_id = bid['driver_telegram_id']
        
        if bid['driver_id'] == winning_bid['driver_id']:
            # Победитель - получает контакты заказчика
            truck_name = get_truck_display_name(order['truck_type'])
            message_text = (
                f"🎉 Поздравляем! Вы выиграли заявку #{order_id}\n\n"
                f"🚚 Тип машины: {truck_name}\n"
                f"� Описание: {order['cargo_description']}\n"
                f"� Ваша цена: {bid['price']} руб.\n\n"
                f"👤 Заказчик: {customer_info['name'] if customer_info else 'Неизвестно'}\n"
                f"📞 Телефон заказчика: {customer_info['phone'] if customer_info else 'Неизвестно'}\n\n"
                f"Свяжитесь с заказчиком для уточнения деталей доставки."
            )
        else:
            # Проигравший
            message_text = (
                f"❌ Заявка #{order_id} завершена\n\n"
                f"💰 Ваше предложение: {bid['price']} руб.\n"
                f"🏆 Выигрышная цена: {winning_bid['price']} руб.\n\n"
                f"К сожалению, выбран водитель с более низкой ценой."
            )
        
        # Пытаемся обновить существующее сообщение
        if driver_telegram_id in messages_by_telegram_id:
            msg_info = messages_by_telegram_id[driver_telegram_id]
            try:
                await bot.edit_message_text(
                    chat_id=msg_info['chat_id'],
                    message_id=msg_info['message_id'],
                    text=message_text
                )
            except Exception as e:
                logging.error(f"Ошибка при обновлении сообщения водителя {driver_telegram_id}: {e}")
                # Fallback - отправляем новое сообщение
                try:
                    await bot.send_message(
                        chat_id=driver_telegram_id,
                        text=message_text
                    )
                except Exception as e2:
                    logging.error(f"Ошибка отправки нового сообщения водителю {driver_telegram_id}: {e2}")
        else:
            # Если сообщение не найдено, отправляем новое
            try:
                await bot.send_message(
                    chat_id=driver_telegram_id,
                    text=message_text
                )
            except Exception as e:
                logging.error(f"Ошибка отправки уведомления водителю {driver_telegram_id}: {e}")