from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from aiogram.filters import Command
from database.models import (
    get_user_by_telegram_id, get_active_orders, get_orders_by_customer,
    get_bids_by_driver, get_won_orders_by_driver
)
from bot.config import TRUCK_TYPES, ORDER_STATUS, get_truck_display_name
from bot.keyboards import get_customer_menu, get_driver_menu, get_webapp_menu
from bot.webapp_config import WEBAPP_URL
from datetime import datetime

router = Router()

@router.message(Command("help"))
async def help_command(message: Message):
    """Команда /help - справочная информация"""
    await message.answer(
        "ℹ️ **Справка FreightHub**\n\n"
        "**Как пользоваться:**\n\n"
        "🌐 **Приложение** - кнопка для открытия веб-приложения\n"
        "   • Заказчики: создавайте и управляйте заявками\n"
        "   • Водители: просматривайте заявки и делайте предложения\n\n"
        "💬 **Уведомления** приходят в этот чат:\n"
        "   • Новые заявки (для водителей)\n"
        "   • Результаты аукционов (победа/проигрыш)\n"
        "   • Статус ваших заявок\n\n"
        "**Команды:**\n"
        "/start - Главное меню\n"
        "/webapp - Открыть приложение\n"
        "/help - Эта справка\n\n"
        "**Поддержка:** @freighthub_support",
        reply_markup=get_webapp_menu()
    )

@router.message(F.text == "📋 Мои заявки")
async def my_orders_customer(message: Message):
    """Просмотр заявок заказчика"""
    if not message.from_user:
        return
        
    user = await get_user_by_telegram_id(message.from_user.id)
    
    if not user or user['role'] != 'customer':
        await message.answer("❌ Эта функция доступна только заказчикам!")
        return
    
    orders = await get_orders_by_customer(user['id'])
    
    if not orders:
        await message.answer("📭 У вас пока нет заявок.")
        return
    
    response = "📋 **Ваши заявки:**\n\n"
    
    for order in orders:
        truck_name = get_truck_display_name(order['truck_type'])
        status_name = ORDER_STATUS.get(order['status'], order['status'])
        
        # Определяем emoji для статуса
        status_emoji = {
            'active': '🟡',
            'completed': '✅', 
            'cancelled': '❌',
            'no_offers': '🔴'
        }.get(order['status'], '⚪')
        
        response += f"{status_emoji} **Заявка #{order['id']}** ({status_name})\n"
        response += f"🚚 {truck_name}\n"
        response += f"📦 {order['cargo_description'][:50]}{'...' if len(order['cargo_description']) > 50 else ''}\n"
        response += f"📍 {order['delivery_address'][:50]}{'...' if len(order['delivery_address']) > 50 else ''}\n"
        
        if order['winning_price'] and order['status'] == 'completed':
            response += f"� Выигрышная цена: {order['winning_price']} руб.\n"
        
        response += f"📅 {order['created_at'][:16]}\n\n"
    
    # Разбиваем на части если слишком длинное
    if len(response) > 4000:
        parts = []
        current_part = "📋 **Ваши заявки:**\n\n"
        
        for order in orders:
            order_text = f"{status_emoji} **Заявка #{order['id']}** ({ORDER_STATUS.get(order['status'], order['status'])})\n"
            order_text += f"🚚 {get_truck_display_name(order['truck_type'])}\n"
            order_text += f"📦 {order['cargo_description'][:30]}...\n\n"
            
            if len(current_part + order_text) > 3500:
                parts.append(current_part)
                current_part = order_text
            else:
                current_part += order_text
        
        if current_part:
            parts.append(current_part)
        
        for part in parts:
            await message.answer(part)
    else:
        await message.answer(response)

@router.message(F.text == "🚛 Выигранные заявки")
async def won_orders_driver(message: Message):
    """Просмотр выигранных заявок водителя"""
    if not message.from_user:
        return
        
    user = await get_user_by_telegram_id(message.from_user.id)
    
    if not user or user['role'] != 'driver':
        await message.answer("❌ Эта функция доступна только водителям!")
        return
    
    won_orders = await get_won_orders_by_driver(user['id'])
    
    if not won_orders:
        await message.answer("📭 У вас пока нет выигранных заявок.")
        return
    
    response = "🏆 **Ваши выигранные заявки:**\n\n"
    
    for order in won_orders:
        truck_name = get_truck_display_name(order['truck_type'])
        status_name = ORDER_STATUS.get(order['status'], order['status'])
        
        response += f"✅ **Заявка #{order['id']}** ({status_name})\n"
        response += f"🚚 {truck_name}\n"
        response += f"� {order['cargo_description'][:50]}{'...' if len(order['cargo_description']) > 50 else ''}\n"
        response += f"📍 {order['delivery_address'][:50]}{'...' if len(order['delivery_address']) > 50 else ''}\n"
        response += f"💰 Цена: {order['winning_price']} руб.\n"
        response += f"📅 {order['created_at'][:16]}\n\n"
    
    if len(response) > 4000:
        parts = []
        current_part = "🏆 **Ваши выигранные заявки:**\n\n"
        
        for order in won_orders:
            order_text = f"✅ **Заявка #{order['id']}**\n"
            order_text += f"� {order['winning_price']} руб.\n\n"
            
            if len(current_part + order_text) > 3500:
                parts.append(current_part)
                current_part = order_text
            else:
                current_part += order_text
        
        if current_part:
            parts.append(current_part)
        
        for part in parts:
            await message.answer(part)
    else:
        await message.answer(response)

@router.message(F.text == "💰 Мои предложения")
async def my_bids_driver(message: Message):
    """Просмотр предложений водителя"""
    if not message.from_user:
        return
        
    user = await get_user_by_telegram_id(message.from_user.id)
    
    if not user or user['role'] != 'driver':
        await message.answer("❌ Эта функция доступна только водителям!")
        return
    
    bids = await get_bids_by_driver(user['id'])
    
    if not bids:
        await message.answer("📭 У вас пока нет предложений.")
        return
    
    response = "💰 **Ваши предложения:**\n\n"
    
    for bid in bids:
        # Определяем статус предложения
        if bid['order_status'] == 'completed':
            if bid['winner_driver_id'] == user['id']:
                status = "🏆 Выиграли!"
                status_emoji = "✅"
            else:
                status = "❌ Проиграли"
                status_emoji = "❌"
        elif bid['order_status'] == 'active':
            status = "⏳ В процессе"
            status_emoji = "🟡"
        else:
            status = "🔴 Завершено"
            status_emoji = "⚪"
        
        response += f"{status_emoji} **Заявка #{bid['order_id']}** - {status}\n"
        response += f"💵 Ваша цена: {bid['price']} руб.\n"
        
        if bid['order_status'] == 'completed' and bid['winning_price']:
            response += f"🏆 Выигрышная цена: {bid['winning_price']} руб.\n"
        
        response += f"📦 {bid['cargo_description'][:50]}{'...' if len(bid['cargo_description']) > 50 else ''}\n"
        response += f"📍 {bid['delivery_address'][:50]}{'...' if len(bid['delivery_address']) > 50 else ''}\n"
        response += f"� {bid['created_at'][:16]}\n\n"
    
    if len(response) > 4000:
        parts = []
        current_part = "💰 **Ваши предложения:**\n\n"
        
        for bid in bids:
            status = "🟡 В процессе" if bid['order_status'] == 'active' else "✅ Завершено"
            bid_text = f"**Заявка #{bid['order_id']}** - {status}\n"
            bid_text += f"💵 {bid['price']} руб.\n\n"
            
            if len(current_part + bid_text) > 3500:
                parts.append(current_part)
                current_part = bid_text
            else:
                current_part += bid_text
        
        if current_part:
            parts.append(current_part)
        
        for part in parts:
            await message.answer(part)
    else:
        await message.answer(response)

@router.message(F.text == "🏠 Главное меню")
async def main_menu(message: Message):
    """Обработчик кнопки главного меню"""
    if not message.from_user:
        return
        
    user = await get_user_by_telegram_id(message.from_user.id)
    
    if not user:
        await message.answer(
            "👋 Добро пожаловать в сервис грузоперевозок!\n\n"
            "Для начала работы нажмите /start для регистрации."
        )
        return
    
    if user['role'] == 'customer':
        await message.answer(
            f"🏠 Главное меню\n\n"
            f"Добро пожаловать, {user['name'] or 'заказчик'}!\n"
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
            f"🏠 Главное меню\n\n"
            f"Добро пожаловать, {user['name'] or 'водитель'}!\n"
            f"Ваши машины:\n{vehicles_text}\n"
            "Выберите действие:",
            reply_markup=get_driver_menu()
        )

@router.message(Command("help"))
async def help_command(message: Message):
    """Справка по командам"""
    user = await get_user_by_telegram_id(message.from_user.id)
    
    help_text = (
        "🆘 **Справка по командам**\n\n"
        "📋 **Основные команды:**\n"
        "/start - Начать работу / Регистрация\n"
        "/help - Показать эту справку\n\n"
    )
    
    if user:
        if user['role'] == 'customer':
            help_text += (
                "👤 **Команды для заказчика:**\n"
                "📦 Создать заявку - Создать новую заявку на перевозку\n"
                "📋 Мои заявки - Просмотр ваших заявок\n\n"
            )
        else:  # driver
            help_text += (
                "🚚 **Команды для водителя:**\n"
                "🚛 Выигранные заявки - Просмотр выигранных заявок\n"
                "💰 Мои предложения - Просмотр ваших предложений\n\n"
            )
    
    help_text += (
        "⏰ **Система аукциона:**\n"
        "• Время на подачу предложений: 5 минут\n"
        "• Автоматический выбор минимальной цены\n"
        "• Уведомления всех участников\n\n"
        "🚚 **Типы машин:**\n"
        "• 🏗️ Манипулятор (5т, 7т, 10т, 12т, 20т)\n"
        "• 🚐 Газель (открытая/закрытая)\n"
        "• 🚛 Длинномер (тент/площадка)\n\n"
        "❓ Если у вас есть вопросы, обратитесь к администратору."
    )
    
    await message.answer(help_text)

@router.message(Command("menu"))
async def menu_command(message: Message):
    """Главное меню"""
    if not message.from_user:
        return
        
    user = await get_user_by_telegram_id(message.from_user.id)
    
    if not user:
        # Пользователь не зарегистрирован
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
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
            "🚗 Управляйте несколькими машинами\n\n"
            "👋 **Выберите вашу роль для начала работы:**",
            reply_markup=keyboard
        )
        return
    
    # Пользователь зарегистрирован - показываем соответствующее меню
    if user['role'] == 'customer':
        from bot.keyboards import get_customer_menu
        await message.answer(
            f"🏠 **Главное меню**\n\n"
            f"Добро пожаловать, {user['name'] or 'заказчик'}!\n\n"
            "📦 Создавайте заявки на грузоперевозку\n"
            "📋 Отслеживайте статус своих заявок\n\n"
            "Выберите действие:",
            reply_markup=get_customer_menu()
        )
    else:  # driver
        from bot.keyboards import get_driver_menu
        from bot.config import get_truck_display_name
        from database.models import get_driver_vehicles
        
        # Получаем все машины водителя
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

@router.message(Command("webapp"))
async def webapp_command(message: Message):
    """Команда для открытия мини-приложения"""
    # Логируем URL для отладки
    print(f"[WEBAPP] Открываем URL: {WEBAPP_URL}")
    
    web_app_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🚛 Открыть FreightHub App",
            web_app=WebAppInfo(url=WEBAPP_URL)
        )]
    ])
    
    await message.answer(
        f"🚛 **FreightHub Mini App**\n\n"
        f"Удобный веб-интерфейс для управления заказами:\n\n"
        f"• 📦 Создавайте заявки\n"
        f"• 💰 Просматривайте предложения\n"
        f"• 🚛 Управляйте заказами\n\n"
        f"Нажмите кнопку ниже:",
        reply_markup=web_app_keyboard
    )

@router.message()
async def unknown_command(message: Message):
    """Обработчик неизвестных команд и сообщений"""
    if not message.from_user:
        return
        
    user_id = message.from_user.id
    text = message.text if message.text else ""
    
    # Игнорируем команды admin, reset и webapp - они обрабатываются в других хэндлерах
    if text.startswith(('/admin', '/reset', '/webapp')):
        print(f"[MISC] Пропускаем команду '{text}' от пользователя {user_id}")
        return
    
    # Проверяем, есть ли пользователь в базе данных
    user = await get_user_by_telegram_id(user_id)
    
    if not user:
        # Новый пользователь - показываем приветствие
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Начать работу", callback_data="start_registration")]
        ])
        
        await message.answer(
            "🚚 **Добро пожаловать в сервис грузоперевозок!** 🚚\n\n"
            "🔹 **Для заказчиков:**\n"
            "• Создавайте заявки на перевозку груза\n"
            "• Водители предложат свои цены за 5 минут\n"
            "• Система автоматически выберет лучшее предложение\n\n"
            "🔹 **Для водителей:**\n" 
            "• Получайте уведомления о новых заявках\n"
            "• Участвуйте в аукционах\n"
            "• Выигрывайте заказы с выгодной ценой\n\n"
            "👇 Нажмите кнопку ниже для начала работы:",
            reply_markup=keyboard
        )
        return
    
    print(f"[MISC] Неизвестная команда/сообщение от пользователя {user_id}: '{text}'")
        
    await message.answer(
        "🤔 Неизвестная команда!\n\n"
        "Используйте кнопку 🏠 Главное меню для навигации."
    )
