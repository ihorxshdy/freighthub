"""
Утилиты для отправки уведомлений пользователям
"""
from aiogram import Bot
from database.models import get_user_by_telegram_id, get_all_drivers, get_bid_participants
from bot.config import get_truck_display_name
from bot.webapp_config import WEBAPP_URL


from typing import Optional

async def notify_drivers_new_order(bot: Bot, order_id: int, truck_type: str, cargo_description: str, delivery_address: str, max_price: Optional[float] = None, pickup_address: Optional[str] = None, pickup_time: Optional[str] = None, delivery_time: Optional[str] = None, delivery_date: Optional[str] = None):
    """
    Уведомляет всех водителей о новой заявке
    
    Args:
        bot: Экземпляр бота
        order_id: ID заявки
        truck_type: Тип машины
        cargo_description: Описание груза
        delivery_address: Адрес доставки
        max_price: Максимальная цена (может быть None)
        pickup_address: Адрес подачи (может быть None)
        pickup_time: Время подачи (может быть None)
        delivery_time: Время доставки (может быть None)
        delivery_date: Дата доставки (может быть None)
    """
    drivers = await get_all_drivers()
    truck_name = get_truck_display_name(truck_type)
    
    # Формируем текст сообщения
    price_text = f"Желаемая цена: {max_price} руб.\n" if max_price else ""
    pickup_text = f"Адрес подачи: {pickup_address}\n" if pickup_address else ""
    pickup_time_text = f"Время подачи: {pickup_time}\n" if pickup_time else ""
    delivery_time_text = f"Время доставки: {delivery_time}\n" if delivery_time else ""
    delivery_date_text = f"Дата доставки: {delivery_date}\n" if delivery_date else ""
    
    message_text = (
        f"Новая заявка #{order_id}\n\n"
        f"Тип машины: {truck_name}\n"
        f"Груз: {cargo_description}\n"
        f"{pickup_text}"
        f"{pickup_time_text}"
        f"Адрес доставки: {delivery_address}\n"
        f"{delivery_time_text}"
        f"{delivery_date_text}"
        f"{price_text}\n"
        f"Подбор длится 2 минуты!\n"
        f"Откройте приложение для участия"
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


async def notify_auction_winner(bot: Bot, order_id: int, winner_telegram_id: int, winning_price: float, cargo_description: str, delivery_address: str, customer_phone: str, customer_username: Optional[str] = None):
    """
    Уведомляет победителя подбора
    
    Args:
        bot: Экземпляр бота
        order_id: ID заявки
        winner_telegram_id: telegram_id победителя
        winning_price: Выигрышная цена
        cargo_description: Описание груза
        delivery_address: Адрес доставки
        customer_phone: Телефон заказчика
        customer_username: Username заказчика (опционально)
    """
    winner = await get_user_by_telegram_id(winner_telegram_id)
    
    if not winner:
        print(f"Не найден победитель с telegram_id {winner_telegram_id}")
        return False
    
    # Формируем контактную информацию
    if customer_username:
        contact_info = f"Telegram: @{customer_username}\nТелефон: {customer_phone}"
    else:
        contact_info = f"Телефон: {customer_phone}"
    
    message_text = (
        f"Поздравляем! Вы выиграли подбор!\n\n"
        f"Заявка #{order_id}\n"
        f"Груз: {cargo_description}\n"
        f"Адрес доставки: {delivery_address}\n"
        f"Ваша цена: {winning_price} руб.\n\n"
        f"{contact_info}\n\n"
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
    Уведомляет проигравших участников подбора
    
    Args:
        bot: Экземпляр бота
        order_id: ID заявки
        winner_user_id: ID победителя в БД (не telegram_id!) для исключения из уведомлений
        cargo_description: Описание груза
    """
    participants = await get_bid_participants(order_id)
    
    if not participants:
        print(f"Нет участников для заявки #{order_id}")
        return 0
    
    # Фильтруем победителя (сравниваем user_id из БД, не telegram_id!)
    losers = [p for p in participants if p['user_id'] != winner_user_id]
    
    print(f"Подбор #{order_id}: всего участников {len(participants)}, проигравших {len(losers)}, winner_user_id={winner_user_id}")
    
    message_text = (
        f"Подбор завершен\n\n"
        f"Заявка #{order_id}\n"
        f"Груз: {cargo_description}\n\n"
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
            print(f"Уведомление проигравшему: user_id={loser['user_id']}, telegram_id={loser['telegram_id']}")
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
        customer_user_id: telegram_id заказчика
        cargo_description: Описание груза
    """
    customer = await get_user_by_telegram_id(customer_user_id)
    
    if not customer:
        print(f"Не найден заказчик с telegram_id {customer_user_id}")
        return False
    
    message_text = (
        f"Подбор завершен\n\n"
        f"Заявка #{order_id}\n"
        f"Груз: {cargo_description}\n\n"
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


async def notify_customer_auction_complete(bot: Bot, order_id: int, customer_user_id: int, cargo_description: str, winning_price: float, driver_phone: str, driver_username: Optional[str] = None):
    """
    Уведомляет заказчика о завершении подбора и победителе
    
    Args:
        bot: Экземпляр бота
        order_id: ID заявки
        customer_user_id: telegram_id заказчика
        cargo_description: Описание груза
        winning_price: Выигрышная цена
        driver_phone: Телефон водителя-победителя
        driver_username: Username водителя (опционально)
    """
    customer = await get_user_by_telegram_id(customer_user_id)
    
    if not customer:
        print(f"Не найден заказчик с telegram_id {customer_user_id}")
        return False
    
    # Формируем контактную информацию
    if driver_username:
        contact_info = f"Telegram: @{driver_username}\nТелефон: {driver_phone}"
    else:
        contact_info = f"Телефон: {driver_phone}"
    
    message_text = (
        f"Подбор завершен!\n\n"
        f"Заявка #{order_id}\n"
        f"Груз: {cargo_description}\n"
        f"Выигрышная цена: {winning_price} руб.\n\n"
        f"{contact_info}\n\n"
        f"Свяжитесь с водителем для уточнения деталей перевозки!"
    )
    
    try:
        await bot.send_message(
            chat_id=customer['telegram_id'],
            text=message_text
        )
        print(f"Отправлено уведомление заказчику о завершении подбора #{order_id}")
        return True
    except Exception as e:
        print(f"Не удалось отправить уведомление заказчику: {str(e)}")
        return False


async def notify_order_confirmed(bot: Bot, telegram_id: int, order_id: int, confirmed_by: str, cargo_description: str):
    """
    Уведомляет сторону о подтверждении выполнения заказа другой стороной
    
    Args:
        bot: Экземпляр бота
        telegram_id: telegram_id пользователя для уведомления
        order_id: ID заявки
        confirmed_by: Кто подтвердил ('customer' или 'driver')
        cargo_description: Описание груза
    """
    user = await get_user_by_telegram_id(telegram_id)
    
    if not user:
        print(f"Не найден пользователь с telegram_id {telegram_id}")
        return False
    
    if confirmed_by == 'customer':
        confirmer = "Заказчик"
        action_text = "Подтвердите выполнение заказа в приложении, чтобы закрыть заявку."
    else:
        confirmer = "Водитель"
        action_text = "Подтвердите выполнение заказа в приложении, чтобы закрыть заявку."
    
    message_text = (
        f"Заявка #{order_id}\n\n"
        f"{confirmer} подтвердил выполнение заказа!\n"
        f"Груз: {cargo_description}\n\n"
        f"{action_text}"
    )
    
    try:
        await bot.send_message(
            chat_id=telegram_id,
            text=message_text
        )
        print(f"Отправлено уведомление о подтверждении заказа #{order_id} пользователю {telegram_id}")
        return True
    except Exception as e:
        print(f"Не удалось отправить уведомление о подтверждении: {str(e)}")
        return False


async def notify_order_cancelled(bot: Bot, telegram_id: int, order_id: int, cancelled_by: str, cargo_description: str):
    """
    Уведомляет пользователя об отмене заказа
    
    Args:
        bot: Экземпляр бота
        telegram_id: telegram_id пользователя для уведомления
        order_id: ID заявки
        cancelled_by: Кто отменил ('customer' или 'driver')
        cargo_description: Описание груза
    """
    user = await get_user_by_telegram_id(telegram_id)
    
    if not user:
        print(f"Не найден пользователь с telegram_id {telegram_id}")
        return False
    
    if cancelled_by == 'customer':
        canceller = "Заказчик"
    else:
        canceller = "Водитель"
    
    message_text = (
        f"Заявка #{order_id} отменена!\n\n"
        f"{canceller} отменил заказ.\n"
        f"Груз: {cargo_description}\n\n"
        f"Заявка закрыта."
    )
    
    try:
        await bot.send_message(
            chat_id=telegram_id,
            text=message_text
        )
        print(f"Отправлено уведомление об отмене заказа #{order_id} пользователю {telegram_id}")
        return True
    except Exception as e:
        print(f"Не удалось отправить уведомление об отмене: {str(e)}")
        return False


async def notify_customer_bids_ready(bot: Bot, order_id: int, customer_user_id: int, cargo_description: str, bids_count: int, min_price: float):
    """
    Уведомляет заказчика о готовности предложений для выбора исполнителя
    
    Args:
        bot: Экземпляр бота
        order_id: ID заявки
        customer_user_id: telegram_id заказчика
        cargo_description: Описание груза
        bids_count: Количество предложений
        min_price: Минимальная цена среди предложений
    """
    customer = await get_user_by_telegram_id(customer_user_id)
    
    if not customer:
        print(f"Не найден заказчик с telegram_id {customer_user_id}")
        return False
    
    message_text = (
        f"🎉 Прием заявок завершен!\n\n"
        f"Заявка #{order_id}\n"
        f"Груз: {cargo_description}\n\n"
        f"📊 Получено предложений: {bids_count}\n"
        f"💰 Минимальная цена: {min_price} руб.\n\n"
        f"📱 Откройте приложение для выбора исполнителя!\n"
        f"Вы можете посмотреть все предложения с контактами водителей."
    )
    
    try:
        await bot.send_message(
            chat_id=customer['telegram_id'],
            text=message_text
        )
        print(f"Отправлено уведомление заказчику о готовности предложений для заявки #{order_id}")
        return True
    except Exception as e:
        print(f"Не удалось отправить уведомление заказчику о предложениях: {str(e)}")
        return False
