from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, WebAppInfo
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database.models import get_user_by_telegram_id, create_user
from bot.config import TRUCK_TYPES, USER_ROLES, TRUCK_CATEGORIES, get_truck_display_name
from bot.keyboards import get_webapp_menu
from bot.webapp_config import WEBAPP_URL

router = Router()


class RegistrationStates(StatesGroup):
    waiting_for_phone = State()
    choosing_role = State()
    choosing_truck_category = State()
    choosing_truck_subtype = State()
    choosing_truck_final = State()

@router.message(Command("start"))
async def start_handler(message: Message, state: FSMContext):
    """Обработка команды /start - запуск регистрации"""
    if not message.from_user:
        return
        
    user = await get_user_by_telegram_id(message.from_user.id)
    
    if user:
        # Пользователь уже зарегистрирован - показываем приветствие и кнопку приложения
        role_emoji = "👤" if user['role'] == 'customer' else "🚚"
        role_name = "Заказчик" if user['role'] == 'customer' else "Водитель"
        
        await message.answer(
            f"{role_emoji} **Добро пожаловать, {user['name'] or role_name}!**\n\n"
            f"Вы вошли как: {role_name}\n\n"
            "🌐 Используйте кнопку **Приложение** для работы с заказами\n"
            "💬 Уведомления о новых заказах и результатах аукционов будут приходить в этот чат\n\n"
            "ℹ️ Для справки используйте команду /help",
            reply_markup=get_webapp_menu()
        )
    else:
        # Новый пользователь - запрашиваем номер телефона
        phone_keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📞 Поделиться номером телефона", request_contact=True)]
            ],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        
        await message.answer(
            "👋 **Добро пожаловать в FreightHub!**\n\n"
            "🚚 *Сервис грузоперевозок нового поколения*\n\n"
            "Для начала работы необходимо зарегистрироваться.\n"
            "Пожалуйста, поделитесь вашим номером телефона:",
            reply_markup=phone_keyboard
        )
        await state.set_state(RegistrationStates.waiting_for_phone)

@router.message(StateFilter(RegistrationStates.waiting_for_phone), F.contact)
async def phone_received(message: Message, state: FSMContext):
    """Обработка получения номера телефона - переход к выбору роли"""
    phone_number = message.contact.phone_number
    await state.update_data(phone_number=phone_number)
    
    # Показываем выбор роли
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👤 Заказчик", callback_data="role_customer"),
            InlineKeyboardButton(text="🚚 Водитель", callback_data="role_driver")
        ]
    ])
    
    await message.answer(
        "✅ Номер телефона получен!\n\n"
        "Теперь выберите вашу роль:\n\n"
        "👤 **Заказчик** - создавайте заявки на грузоперевозку\n"
        "🚚 **Водитель** - выполняйте заявки и зарабатывайте",
        reply_markup=keyboard
    )
    await state.set_state(RegistrationStates.choosing_role)

@router.callback_query(StateFilter(RegistrationStates.choosing_role), F.data.startswith("role_"))
async def role_chosen(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора роли"""
    role = callback.data.split("_")[1]  # customer или driver
    await state.update_data(role=role)
    
    if role == 'driver':
        # Для водителя показываем категории машин
        category_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=category_info['name'], callback_data=f"category_{category_id}")]
            for category_id, category_info in TRUCK_CATEGORIES.items()
        ])
        
        await callback.message.edit_text(
            "🚚 Вы выбрали роль: **Водитель**\n\n"
            "Выберите тип вашей машины:",
            reply_markup=category_keyboard
        )
        await state.set_state(RegistrationStates.choosing_truck_category)
    else:
        # Для заказчика сразу завершаем регистрацию
        data = await state.get_data()
        
        try:
            await create_user(
                telegram_id=callback.from_user.id,
                phone_number=data['phone_number'],
                role=role,
                truck_type=None,
                name=callback.from_user.full_name or "Заказчик"
            )
            
            await callback.message.edit_text(
                "✅ **Регистрация завершена!**\n\n"
                f"Роль: Заказчик\n"
                f"Телефон: {data['phone_number']}\n\n"
                "Теперь вы можете создавать заявки на грузоперевозку через приложение!"
            )
            
            await callback.message.answer(
                "🌐 Нажмите кнопку **Приложение** для начала работы\n\n"
                "💬 Уведомления о новых предложениях будут приходить в этот чат",
                reply_markup=get_webapp_menu()
            )
            
        except Exception as e:
            await callback.message.edit_text(
                f"❌ Ошибка при регистрации: {str(e)}\n"
                "Попробуйте снова с командой /start"
            )
        
        await state.clear()

@router.callback_query(F.data == "start_registration")
async def start_registration(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Начать работу' (deprecated)"""

@router.message(Command("start"))
async def start_handler(message: Message, state: FSMContext):
    """Обработка команды /start"""
    if not message.from_user:
        return
        
    user = await get_user_by_telegram_id(message.from_user.id)
    
    if user:
        # Удалили веб-приложение
        
        if user['role'] == 'customer':
            await message.answer(
                f"🏠 **Главное меню**\n\n"
                f"Добро пожаловать, {user['name'] or 'заказчик'}!\n\n"
                "📦 Создавайте заявки на грузоперевозку\n"
                "📋 Отслеживайте статус своих заявок\n\n"
                "Выберите действие:",
                reply_markup=get_customer_menu()
            )
        else:  # driver
            # Получаем все машины водителя
            from database.models import get_driver_vehicles
            vehicles = await get_driver_vehicles(user['id'])
            
            if vehicles:
                # Формируем список машин
                vehicles_text = ""
                for vehicle in vehicles:
                    truck_name = get_truck_display_name(vehicle['truck_type'])
                    primary_mark = "⭐ " if vehicle['is_primary'] else "• "
                    vehicles_text += f"{primary_mark}{truck_name}\n"
            else:
                # Если нет машин в новой таблице, используем старое поле
                if user['truck_type']:
                    vehicles_text = f"• {get_truck_display_name(user['truck_type'])}\n"
                else:
                    vehicles_text = "Нет добавленных машин\n"
            
            await message.answer(
                f"🏠 **Главное меню**\n\n"
                f"Добро пожаловать, {user['name'] or 'водитель'}!\n\n"
                f"🚚 Ваши машины:\n{vehicles_text}\n"
                "🏆 Просматривайте выигранные заявки\n"
                "💰 Отслеживайте свои предложения\n"
                "🚗 Управляйте вашими машинами\n\n"
                "Выберите действие:",
                reply_markup=get_driver_menu()
            )
    else:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="👤 Заказчик", callback_data="role_customer"),
                InlineKeyboardButton(text="🚚 Водитель", callback_data="role_driver")
            ]
        ])
        
        await message.answer(
            "🎉 **Добро пожаловать в FreightHub!** 🎉\n"
            "*Ваш надежный сервис грузоперевозок*\n\n"
            "🔹 **Для заказчиков:**\n"
            "📦 Создавайте заявки на перевозку груза\n"
            "💰 Водители предложат свои цены за 5 минут\n"
            "🏆 Система автоматически выберет лучшее предложение\n"
            "📱 Получите контакты победителя\n\n"
            "🔹 **Для водителей:**\n" 
            "🔔 Получайте уведомления о новых заявках\n"
            "⚡ Участвуйте в быстрых аукционах\n"
            "💵 Выигрывайте заявки с конкурентной ценой\n"
            "� Управляйте несколькими машинами\n\n"
            "👋 **Выберите вашу роль для начала работы:**",
            reply_markup=keyboard
        )
        await state.set_state(RegistrationStates.choosing_role)

@router.callback_query(F.data == "start_registration")
async def start_registration(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Начать работу' (deprecated - не используется)"""
    # Редирект на новую регистрацию
    await callback.message.answer("Используйте команду /start для регистрации")

@router.callback_query(StateFilter(RegistrationStates.choosing_truck_category), F.data.startswith("category_"))
async def truck_category_chosen(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора категории машины"""
    category_id = callback.data.split("_")[1]
    category_info = TRUCK_CATEGORIES[category_id]
    
    await state.update_data(truck_category=category_id)
    
    # Создаем клавиатуру с подтипами
    subtype_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=subtype_name, callback_data=f"subtype_{category_id}_{subtype_id}")]
        for subtype_id, subtype_name in category_info['subtypes'].items()
    ] + [[InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_categories")]])
    
    await callback.message.edit_text(
        f"Категория: {category_info['name']}\n\n"
        "Выберите подтип:",
        reply_markup=subtype_keyboard
    )
    
    await state.set_state(RegistrationStates.choosing_truck_subtype)

@router.callback_query(StateFilter(RegistrationStates.choosing_truck_subtype), F.data.startswith("subtype_"))
async def truck_subtype_chosen(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора подтипа машины"""
    parts = callback.data.split("_")
    # Формат: subtype_category_subtype_id
    category_id = parts[1]  # второй элемент
    # subtype_id - все остальные части, объединенные обратно
    subtype_id = "_".join(parts[2:])
    
    print(f"DEBUG: truck_subtype_chosen - callback_data: {callback.data}")
    print(f"DEBUG: parts: {parts}")
    print(f"DEBUG: category_id: {category_id}, subtype_id: {subtype_id}")
    
    category_info = TRUCK_CATEGORIES[category_id]
    
    # Проверяем, есть ли дополнительные подуровни
    if category_id in TRUCK_CATEGORIES and 'sub_subtypes' in category_info and subtype_id in category_info['sub_subtypes']:
        # Есть дополнительные подуровни (для Газели)
        await state.update_data(truck_subtype=subtype_id)
        
        sub_subtypes = category_info['sub_subtypes'][subtype_id]
        final_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=sub_subtype_name, callback_data=f"final_{category_id}_{subtype_id}_{sub_subtype_id}")]
            for sub_subtype_id, sub_subtype_name in sub_subtypes.items()
        ] + [[InlineKeyboardButton(text="◀️ Назад", callback_data=f"back_to_subtypes_{category_id}")]])
        
        subtype_name = category_info['subtypes'][subtype_id]
        await callback.message.edit_text(
            f"Категория: {category_info['name']}\n"
            f"Тип: {subtype_name}\n\n"
            "Выберите характеристики:",
            reply_markup=final_keyboard
        )
        
        await state.set_state(RegistrationStates.choosing_truck_final)
    else:
        # Это финальный выбор (для Манипулятора и Длинномера)
        # Сохраняем truck_type
        truck_type = subtype_id
        if truck_type in TRUCK_CATEGORIES:
            # Если это категория, берем первый доступный подтип
            category_info = TRUCK_CATEGORIES[truck_type]
            subtypes = category_info.get('subtypes', {})
            if subtypes:
                truck_type = list(subtypes.keys())[0]
        
        await state.update_data(truck_type=truck_type)
        
        # Завершаем регистрацию водителя сразу
        data = await state.get_data()
        truck_name = get_truck_display_name(truck_type)
        
        try:
            await create_user(
                telegram_id=callback.from_user.id,
                phone_number=data['phone_number'],
                role='driver',
                truck_type=truck_type,
                name=callback.from_user.full_name or "Водитель"
            )
            
            await callback.message.edit_text(
                f"✅ **Регистрация завершена!**\n\n"
                f"Роль: Водитель\n"
                f"Телефон: {data['phone_number']}\n"
                f"Тип машины: {truck_name}\n\n"
                "Теперь вы будете получать уведомления о новых заявках!"
            )
            
            await callback.message.answer(
                "🌐 Нажмите кнопку **Приложение** для работы с заказами\n\n"
                "💬 Уведомления о новых заказах и результатах аукционов будут приходить в этот чат",
                reply_markup=get_webapp_menu()
            )
            
        except Exception as e:
            await callback.message.edit_text(
                f"❌ Ошибка при регистрации: {str(e)}\n"
                "Попробуйте снова с командой /start"
            )
        
        await state.clear()

@router.callback_query(StateFilter(RegistrationStates.choosing_truck_final), F.data.startswith("final_"))
async def truck_final_chosen(callback: CallbackQuery, state: FSMContext):
    """Обработка финального выбора характеристик машины (для Газели)"""
    parts = callback.data.split("_")
    # Формат: final_category_subtype_id_final_type_id
    # Последний элемент - это финальный тип (например gazel_closed_10m3)
    final_id = parts[-1]  # последний элемент
    # Ищем в TRUCK_TYPES по ключу который заканчивается на final_id
    for truck_key in TRUCK_TYPES.keys():
        if truck_key.endswith(final_id):
            final_id = truck_key
            break
    
    await state.update_data(truck_type=final_id)
    
    # Завершаем регистрацию водителя сразу
    data = await state.get_data()
    truck_name = TRUCK_TYPES.get(final_id, final_id)
    
    try:
        await create_user(
            telegram_id=callback.from_user.id,
            phone_number=data['phone_number'],
            role='driver',
            truck_type=final_id,
            name=callback.from_user.full_name or "Водитель"
        )
        
        await callback.message.edit_text(
            f"✅ **Регистрация завершена!**\n\n"
            f"Роль: Водитель\n"
            f"Телефон: {data['phone_number']}\n"
            f"Тип машины: {truck_name}\n\n"
            "Теперь вы будете получать уведомления о новых заявках!"
        )
        
        await callback.message.answer(
            "🌐 Нажмите кнопку **Приложение** для работы с заказами\n\n"
            "💬 Уведомления о новых заказах и результатах аукционов будут приходить в этот чат",
            reply_markup=get_webapp_menu()
        )
        
    except Exception as e:
        await callback.message.edit_text(
            f"❌ Ошибка при регистрации: {str(e)}\n"
            "Попробуйте снова с командой /start"
        )
    
    await state.clear()

# Обработчики кнопок "Назад"
@router.callback_query(F.data == "back_to_categories")
async def back_to_categories(callback: CallbackQuery, state: FSMContext):
    """Возврат к выбору категорий"""
    category_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=category_info['name'], callback_data=f"category_{category_id}")]
        for category_id, category_info in TRUCK_CATEGORIES.items()
    ])
    
    await callback.message.edit_text(
        "Выберите категорию вашей машины:",
        reply_markup=category_keyboard
    )
    
    await state.set_state(RegistrationStates.choosing_truck_category)

@router.callback_query(F.data.startswith("back_to_subtypes_"))
async def back_to_subtypes(callback: CallbackQuery, state: FSMContext):
    """Возврат к выбору подтипов"""
    category_id = callback.data.split("_")[3]
    category_info = TRUCK_CATEGORIES[category_id]
    
    subtype_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=subtype_name, callback_data=f"subtype_{category_id}_{subtype_id}")]
        for subtype_id, subtype_name in category_info['subtypes'].items()
    ] + [[InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_categories")]])
    
    await callback.message.edit_text(
        f"Категория: {category_info['name']}\n\n"
        "Выберите подтип:",
        reply_markup=subtype_keyboard
    )
    
    await state.set_state(RegistrationStates.choosing_truck_subtype)