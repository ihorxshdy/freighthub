"""
Утилиты для форматирования сообщений заявок
"""
from datetime import datetime
from bot.config import get_truck_display_name, ORDER_STATUS

def format_order_message(order: dict, stage: str = "created", bids_count: int = 0, winner_info: dict = None) -> tuple[str, dict]:
    """
    Форматировать сообщение заявки в зависимости от этапа
    
    Args:
        order: Данные заявки
        stage: Этап ('creating', 'created', 'auction', 'completed', 'cancelled')
        bids_count: Количество предложений
        winner_info: Информация о победителе
    
    Returns:
        tuple: (текст сообщения, reply_markup или None)
    """
    truck_name = get_truck_display_name(order['truck_type'])
    status_emoji = get_status_emoji(stage)
    
    # Базовая информация о заявке
    base_info = (
        f"{status_emoji} **Заявка #{order['id']}**\n\n"
        f"🚚 **Тип машины:** {truck_name}\n"
        f"📦 **Груз:** {order['cargo_description']}\n"
    )
    
    # Адреса и время
    addresses_info = ""
    if order.get('pickup_address'):
        addresses_info += f"📍 **Откуда:** {order['pickup_address']}\n"
    if order.get('pickup_time'):
        addresses_info += f"⏰ **Время погрузки:** {order['pickup_time']}\n"
    if order.get('delivery_address'):
        addresses_info += f"🏁 **Куда:** {order['delivery_address']}\n"
    if order.get('delivery_time'):
        addresses_info += f"⏱️ **Время доставки:** {order['delivery_time']}\n"
    
    # Статус в зависимости от этапа
    if stage == "creating":
        status_info = "\n🔄 **Создание заявки...**\nВыберите тип машины и заполните описание."
        reply_markup = None
        
    elif stage == "created":
        # Заявка создана, идет подбор
        expires_time = datetime.fromisoformat(order['expires_at'].replace('Z', '+00:00'))
        time_left = expires_time - datetime.now()
        
        if time_left.total_seconds() > 0:
            minutes_left = int(time_left.total_seconds() / 60)
            status_info = (
                f"\n🔥 **Активный подбор**\n"
                f"⏱️ Осталось времени: {minutes_left} мин.\n"
                f"💰 Предложений: {bids_count}\n"
                f"🎯 Ждем предложения от водителей..."
            )
        else:
            status_info = f"\n⏱️ **Подбор завершен**\n💰 Получено предложений: {bids_count}"
        
        reply_markup = None
        
    elif stage == "completed":
        if winner_info:
            status_info = (
                f"\n✅ **Заявка выполнена**\n"
                f"🏆 **Победитель:** {winner_info.get('name', 'Неизвестен')}\n"
                f"💰 **Цена:** {order.get('winning_price', 'Не указана')} руб.\n"
                f"📱 **Контакт:** {winner_info.get('phone_number', 'Не указан')}"
            )
        else:
            status_info = "\n✅ **Заявка выполнена**"
        reply_markup = None
        
    elif stage == "cancelled":
        status_info = "\n❌ **Заявка отменена**"
        reply_markup = None
        
    elif stage == "no_offers":
        status_info = (
            f"\n🔴 **Подбор завершен**\n"
            f"К сожалению, не поступило ни одного предложения.\n"
            f"Попробуйте создать заявку позже или измените условия."
        )
        reply_markup = None
        
    else:
        status_info = f"\n📋 Статус: {ORDER_STATUS.get(order.get('status', 'unknown'), 'Неизвестен')}"
        reply_markup = None
    
    # Время создания
    created_time = order.get('created_at', '')[:16] if order.get('created_at') else ''
    time_info = f"\n📅 Создана: {created_time}"
    
    # Собираем полное сообщение
    message_text = base_info + addresses_info + status_info + time_info
    
    return message_text, reply_markup

def format_driver_notification(order: dict, stage: str = "new_order") -> tuple[str, dict]:
    """
    Форматировать уведомление для водителей
    
    Args:
        order: Данные заявки
        stage: Этап ('new_order', 'auction_end', 'won', 'lost')
    
    Returns:
        tuple: (текст сообщения, reply_markup)
    """
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    truck_name = get_truck_display_name(order['truck_type'])
    
    if stage == "new_order":
        # Новая заявка для водителя
        message_text = (
            f"🆕 **Новая заявка #{order['id']}**\n\n"
            f"🚚 **Тип машины:** {truck_name}\n"
            f"📦 **Груз:** {order['cargo_description']}\n"
        )
        
        # Добавляем адреса если есть
        if order.get('pickup_address'):
            message_text += f"📍 **Откуда:** {order['pickup_address']}\n"
        if order.get('delivery_address'):
            message_text += f"🏁 **Куда:** {order['delivery_address']}\n"
        
        expires_time = datetime.fromisoformat(order['expires_at'].replace('Z', '+00:00'))
        time_left = expires_time - datetime.now()
        minutes_left = int(time_left.total_seconds() / 60)
        
        message_text += (
            f"\n⏱️ **Время на предложение:** {minutes_left} мин.\n"
            f"💡 Предложите свою цену!"
        )
        
        reply_markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💰 Сделать предложение", callback_data=f"bid_{order['id']}")]
        ])
        
    elif stage == "auction_end":
        message_text = (
            f"⏱️ **Подбор завершен**\n\n"
            f"🚚 Заявка #{order['id']} ({truck_name})\n"
            f"📦 {order['cargo_description'][:50]}...\n\n"
            f"Результаты будут объявлены в ближайшее время."
        )
        reply_markup = None
        
    elif stage == "won":
        message_text = (
            f"🎉 **Поздравляем! Вы выиграли заявку!**\n\n"
            f"🚚 **Заявка #{order['id']}**\n"
            f"📦 **Груз:** {order['cargo_description']}\n"
            f"💰 **Ваша цена:** {order.get('winning_price', 'Не указана')} руб.\n\n"
            f"📱 **Свяжитесь с заказчиком для уточнения деталей.**"
        )
        reply_markup = None
        
    elif stage == "lost":
        message_text = (
            f"😔 **К сожалению, вы не выиграли заявку**\n\n"
            f"🚚 **Заявка #{order['id']}**\n"
            f"📦 {order['cargo_description'][:50]}...\n"
            f"💰 **Выигрышная цена:** {order.get('winning_price', 'Не указана')} руб.\n\n"
            f"🚀 Удачи в следующих подборах!"
        )
        reply_markup = None
        
    else:
        message_text = f"📋 Обновление по заявке #{order['id']}"
        reply_markup = None
    
    return message_text, reply_markup

def get_status_emoji(stage: str) -> str:
    """Получить эмодзи для статуса"""
    status_emojis = {
        "creating": "🔄",
        "created": "🔥",
        "auction": "🔥", 
        "completed": "✅",
        "cancelled": "❌",
        "no_offers": "🔴"
    }
    return status_emojis.get(stage, "📋")