"""
Утилиты для отправки уведомлений пользователям
"""
from aiogram import Bot
from database.models import get_user_by_id, get_all_drivers, get_bid_participants
from bot.config import get_truck_display_name
from bot.webapp_config import WEBAPP_URL


from typing import Optional

async def notify_drivers_new_order(bot: Bot, order_id: int, truck_type: str, cargo_description: str, delivery_address: str, max_price: Optional[float] = None):
    """
    Уведомляет всех водителей о новой заявке
    
    Args:
        bot: Экземпляр бота
        order_id: ID заявки
        truck_type: Тип машины
        cargo_description: Описание груза
        delivery_address: Адрес доставки
        max_price: Максимальная цена (может быть None)
    """
    drivers = await get_all_drivers()
    truck_name = get_truck_display_name(truck_type)
    
    # Формируем текст сообщения
    price_text = f"**Максимальная цена:** {max_price} руб.\n" if max_price else ""
    
    message_text = (
        f"🚚 **Новая заявка #{order_id}**\n\n"
        f"**Тип машины:** {truck_name}\n"
        f"**Груз:** {cargo_description}\n"
        f"**Адрес доставки:** {delivery_address}\n"
        f"{price_text}"
        f"⏱ Аукцион длится 30 минут!\n"
        f"Откройте приложение для участия 👇"
    )
    
    # Отправляем уведомление всем водителям
    sent_count = 0
    for driver in drivers:
        try:
            await bot.send_message(
                chat_id=driver['telegram_id'],
                text=message_text
            )
            sent_count += 1
        except Exception as e:
            print(f"Не удалось отправить уведомление водителю {driver['id']}: {str(e)}")
    
    print(f"Отправлено уведомлений о заявке #{order_id}: {sent_count} из {len(drivers)}")
    return sent_count


async def notify_auction_winner(bot: Bot, order_id: int, winner_user_id: int, winning_price: float, cargo_description: str, delivery_address: str, customer_phone: str):
    """
    Уведомляет победителя аукциона
    
    Args:
        bot: Экземпляр бота
        order_id: ID заявки
        winner_user_id: ID победителя (user_id в БД)
        winning_price: Выигрышная цена
        cargo_description: Описание груза
        delivery_address: Адрес доставки
        customer_phone: Телефон заказчика
    """
    winner = await get_user_by_id(winner_user_id)
    
    if not winner:
        print(f"Не найден победитель с ID {winner_user_id}")
        return False
    
    message_text = (
        f"🎉 **Поздравляем! Вы выиграли аукцион!**\n\n"
        f"**Заявка #{order_id}**\n"
        f"**Груз:** {cargo_description}\n"
        f"**Адрес доставки:** {delivery_address}\n"
        f"**Ваша цена:** {winning_price} руб.\n\n"
        f"📞 **Телефон заказчика:** {customer_phone}\n\n"
        f"Свяжитесь с заказчиком для уточнения деталей!"
    )
    
    try:
        await bot.send_message(
            chat_id=winner['telegram_id'],
            text=message_text
        )
        print(f"Отправлено уведомление победителю заявки #{order_id}")
        return True
    except Exception as e:
        print(f"Не удалось отправить уведомление победителю: {str(e)}")
        return False


async def notify_auction_losers(bot: Bot, order_id: int, winner_user_id: int, cargo_description: str):
    """
    Уведомляет проигравших участников аукциона
    
    Args:
        bot: Экземпляр бота
        order_id: ID заявки
        winner_user_id: ID победителя (чтобы исключить из уведомлений)
        cargo_description: Описание груза
    """
    participants = await get_bid_participants(order_id)
    
    if not participants:
        print(f"Нет участников для заявки #{order_id}")
        return 0
    
    # Фильтруем победителя
    losers = [p for p in participants if p['user_id'] != winner_user_id]
    
    message_text = (
        f"❌ **Аукцион завершен**\n\n"
        f"**Заявка #{order_id}**\n"
        f"**Груз:** {cargo_description}\n\n"
        f"К сожалению, ваше предложение не было выбрано.\n"
        f"Следите за новыми заявками!"
    )
    
    sent_count = 0
    for loser in losers:
        try:
            await bot.send_message(
                chat_id=loser['telegram_id'],
                text=message_text
            )
            sent_count += 1
        except Exception as e:
            print(f"Не удалось отправить уведомление проигравшему {loser['user_id']}: {str(e)}")
    
    print(f"Отправлено уведомлений проигравшим для заявки #{order_id}: {sent_count} из {len(losers)}")
    return sent_count


async def notify_customer_no_bids(bot: Bot, order_id: int, customer_user_id: int, cargo_description: str):
    """
    Уведомляет заказчика об отсутствии предложений
    
    Args:
        bot: Экземпляр бота
        order_id: ID заявки
        customer_user_id: ID заказчика (user_id в БД)
        cargo_description: Описание груза
    """
    customer = await get_user_by_id(customer_user_id)
    
    if not customer:
        print(f"Не найден заказчик с ID {customer_user_id}")
        return False
    
    message_text = (
        f"⏰ **Аукцион завершен**\n\n"
        f"**Заявка #{order_id}**\n"
        f"**Груз:** {cargo_description}\n\n"
        f"К сожалению, не поступило ни одного предложения от водителей.\n"
        f"Вы можете создать новую заявку с другими условиями."
    )
    
    try:
        await bot.send_message(
            chat_id=customer['telegram_id'],
            text=message_text
        )
        print(f"Отправлено уведомление заказчику о заявке #{order_id} без предложений")
        return True
    except Exception as e:
        print(f"Не удалось отправить уведомление заказчику: {str(e)}")
        return False


async def notify_customer_auction_complete(bot: Bot, order_id: int, customer_user_id: int, cargo_description: str, winning_price: float, driver_phone: str):
    """
    Уведомляет заказчика о завершении аукциона и победителе
    
    Args:
        bot: Экземпляр бота
        order_id: ID заявки
        customer_user_id: ID заказчика (user_id в БД)
        cargo_description: Описание груза
        winning_price: Выигрышная цена
        driver_phone: Телефон водителя-победителя
    """
    customer = await get_user_by_id(customer_user_id)
    
    if not customer:
        print(f"Не найден заказчик с ID {customer_user_id}")
        return False
    
    message_text = (
        f"✅ **Аукцион завершен!**\n\n"
        f"**Заявка #{order_id}**\n"
        f"**Груз:** {cargo_description}\n"
        f"**Выигрышная цена:** {winning_price} руб.\n\n"
        f"📞 **Телефон водителя:** {driver_phone}\n\n"
        f"Свяжитесь с водителем для уточнения деталей перевозки!"
    )
    
    try:
        await bot.send_message(
            chat_id=customer['telegram_id'],
            text=message_text
        )
        print(f"Отправлено уведомление заказчику о завершении аукциона #{order_id}")
        return True
    except Exception as e:
        print(f"Не удалось отправить уведомление заказчику: {str(e)}")
        return False
