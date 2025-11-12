"""
Обработчики webhook запросов от webapp
"""
from aiogram import Router, Bot
from aiogram.types import Update
from aiohttp import web
import os
import json
from utils.notifications import (
    notify_drivers_new_order,
    notify_auction_winner,
    notify_auction_losers,
    notify_customer_no_bids,
    notify_customer_auction_complete,
    notify_customer_bids_ready,
    notify_order_confirmed,
    notify_order_cancelled
)
from utils.helpers import logger

router = Router()

# Секретный ключ для валидации webhook запросов
WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET', 'change-this-secret-key')


async def verify_webhook_token(request):
    """Проверка токена авторизации"""
    auth_header = request.headers.get('Authorization', '')
    expected = f'Bearer {WEBHOOK_SECRET}'
    return auth_header == expected


async def webhook_new_order(request):
    """
    Webhook: новая заявка создана
    
    Ожидаемые данные:
    {
        "order_id": 123,
        "truck_type": "gazel_tent_3m",
        "cargo_description": "Мебель для переезда",
        "delivery_address": "ул. Ленина, д. 10",
        "max_price": 5000.0
    }
    """
    if not await verify_webhook_token(request):
        return web.json_response({'error': 'Unauthorized'}, status=401)
    
    try:
        data = await request.json()
        bot = request.app['bot']
        
        # Валидация обязательных данных
        required = ['order_id', 'truck_type', 'cargo_description', 'delivery_address']
        if not all(field in data for field in required):
            return web.json_response({'error': 'Missing required fields'}, status=400)
        
        # max_price может отсутствовать или быть None
        max_price = data.get('max_price')
        if max_price is not None:
            max_price = float(max_price) if max_price else None
        
        # Отправляем уведомление всем водителям
        count = await notify_drivers_new_order(
            bot=bot,
            order_id=data['order_id'],
            truck_type=data['truck_type'],
            cargo_description=data['cargo_description'],
            delivery_address=data['delivery_address'],
            max_price=max_price,
            pickup_address=data.get('pickup_address'),
            pickup_time=data.get('pickup_time'),
            delivery_time=data.get('delivery_time'),
            delivery_date=data.get('delivery_date')
        )
        
        logger.info(f"Webhook: Отправлены уведомления о заявке #{data['order_id']} ({count} водителей)")
        
        return web.json_response({
            'success': True,
            'notified_drivers': count
        })
        
    except Exception as e:
        logger.error(f"Ошибка обработки webhook new_order: {e}")
        return web.json_response({'error': str(e)}, status=500)


async def webhook_auction_complete(request):
    """
    Webhook: подбор завершён с победителем
    
    Ожидаемые данные:
    {
        "order_id": 123,
        "winner_telegram_id": 45,
        "winner_user_id": 2,
        "winning_price": 4500.0,
        "cargo_description": "Мебель для переезда",
        "delivery_address": "ул. Ленина, д. 10",
        "customer_user_id": 12,
        "customer_phone": "+79991234567",
        "driver_phone": "+79997654321"
    }
    """
    if not await verify_webhook_token(request):
        return web.json_response({'error': 'Unauthorized'}, status=401)
    
    try:
        data = await request.json()
        bot = request.app['bot']
        
        # Уведомляем победителя
        await notify_auction_winner(
            bot=bot,
            order_id=data['order_id'],
            winner_telegram_id=data['winner_telegram_id'],
            winning_price=float(data['winning_price']),
            cargo_description=data['cargo_description'],
            delivery_address=data['delivery_address'],
            customer_phone=data['customer_phone'],
            customer_username=data.get('customer_username')
        )
        
        # Уведомляем проигравших (передаем winner_user_id для фильтрации)
        await notify_auction_losers(
            bot=bot,
            order_id=data['order_id'],
            winner_user_id=data['winner_user_id'],
            cargo_description=data['cargo_description']
        )
        
        # Уведомляем заказчика
        await notify_customer_auction_complete(
            bot=bot,
            order_id=data['order_id'],
            customer_user_id=data['customer_user_id'],
            cargo_description=data['cargo_description'],
            winning_price=float(data['winning_price']),
            driver_phone=data['driver_phone'],
            driver_username=data.get('winner_username')
        )
        
        logger.info(f"Webhook: Подбор #{data['order_id']} завершён, победитель telegram_id={data['winner_telegram_id']}")
        
        return web.json_response({'success': True})
        
    except Exception as e:
        logger.error(f"Ошибка обработки webhook auction_complete: {e}")
        return web.json_response({'error': str(e)}, status=500)


async def webhook_auction_no_bids(request):
    """
    Webhook: подбор завершён без ставок
    
    Ожидаемые данные:
    {
        "order_id": 123,
        "customer_user_id": 12,
        "cargo_description": "Мебель для переезда"
    }
    """
    if not await verify_webhook_token(request):
        return web.json_response({'error': 'Unauthorized'}, status=401)
    
    try:
        data = await request.json()
        bot = request.app['bot']
        
        # Уведомляем заказчика
        await notify_customer_no_bids(
            bot=bot,
            order_id=data['order_id'],
            customer_user_id=data['customer_user_id'],
            cargo_description=data['cargo_description']
        )
        
        logger.info(f"Webhook: Подбор #{data['order_id']} завершён без ставок")
        
        return web.json_response({'success': True})
        
    except Exception as e:
        logger.error(f"Ошибка обработки webhook auction_no_bids: {e}")
        return web.json_response({'error': str(e)}, status=500)


async def webhook_auction_bids_ready(request):
    """
    Webhook: предложения готовы для выбора заказчиком
    
    Ожидаемые данные:
    {
        "order_id": 123,
        "customer_user_id": 12,
        "cargo_description": "Мебель для переезда",
        "bids_count": 5,
        "min_price": 4000.0
    }
    """
    if not await verify_webhook_token(request):
        return web.json_response({'error': 'Unauthorized'}, status=401)
    
    try:
        data = await request.json()
        bot = request.app['bot']
        
        # Уведомляем заказчика о готовности предложений для выбора
        await notify_customer_bids_ready(
            bot=bot,
            order_id=data['order_id'],
            customer_user_id=data['customer_user_id'],
            cargo_description=data['cargo_description'],
            bids_count=data['bids_count'],
            min_price=float(data['min_price'])
        )
        
        logger.info(f"Webhook: Заказчику уведомление о готовности {data['bids_count']} предложений для заказа #{data['order_id']}")
        
        return web.json_response({'success': True})
        
    except Exception as e:
        logger.error(f"Ошибка обработки webhook auction_bids_ready: {e}")
        return web.json_response({'error': str(e)}, status=500)


async def webhook_order_confirmed(request):
    """
    Webhook: одна из сторон подтвердила выполнение заказа
    
    Ожидаемые данные:
    {
        "order_id": 123,
        "confirmed_by_telegram_id": 12345,
        "confirmed_by_role": "customer",  # или "driver"
        "customer_telegram_id": 12345,
        "driver_telegram_id": 67890
    }
    """
    if not await verify_webhook_token(request):
        return web.json_response({'error': 'Unauthorized'}, status=401)
    
    try:
        data = await request.json()
        bot = request.app['bot']
        
        # Валидация обязательных данных
        required = ['order_id', 'confirmed_by_role', 'customer_telegram_id', 'driver_telegram_id']
        if not all(field in data for field in required):
            return web.json_response({'error': 'Missing required fields'}, status=400)
        
        # Получаем информацию о заказе для описания груза
        import aiosqlite
        from bot.config import DB_PATH
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute('SELECT cargo_description FROM orders WHERE id = ?', (data['order_id'],)) as cursor:
                order = await cursor.fetchone()
                cargo_description = order['cargo_description'] if order else "Заказ"
        
        # Определяем кому отправить уведомление
        if data['confirmed_by_role'] == 'customer':
            notify_telegram_id = data['driver_telegram_id']
        else:
            notify_telegram_id = data['customer_telegram_id']
        
        # Отправляем уведомление другой стороне
        await notify_order_confirmed(
            bot=bot,
            telegram_id=notify_telegram_id,
            order_id=data['order_id'],
            confirmed_by=data['confirmed_by_role'],
            cargo_description=cargo_description
        )
        
        logger.info(f"Webhook: Отправлено уведомление о подтверждении заказа #{data['order_id']}")
        
        return web.json_response({'success': True})
        
    except Exception as e:
        logger.error(f"Ошибка обработки webhook order_confirmed: {e}")
        return web.json_response({'error': str(e)}, status=500)


async def webhook_order_cancelled(request):
    """
    Webhook: заказ отменён одной из сторон
    
    Ожидаемые данные:
    {
        "order_id": 123,
        "cancelled_by_telegram_id": 12345,
        "cancelled_by_role": "customer",  # или "driver"
        "customer_telegram_id": 12345,
        "driver_telegram_id": 67890,
        "cargo_description": "Мебель для переезда"
    }
    """
    if not await verify_webhook_token(request):
        return web.json_response({'error': 'Unauthorized'}, status=401)
    
    try:
        data = await request.json()
        bot = request.app['bot']
        
        # Валидация обязательных данных
        required = ['order_id', 'cancelled_by_role', 'customer_telegram_id', 'driver_telegram_id', 'cargo_description']
        if not all(field in data for field in required):
            return web.json_response({'error': 'Missing required fields'}, status=400)
        
        # Отправляем уведомления обеим сторонам
        await notify_order_cancelled(
            bot=bot,
            telegram_id=data['customer_telegram_id'],
            order_id=data['order_id'],
            cancelled_by=data['cancelled_by_role'],
            cargo_description=data['cargo_description']
        )
        
        await notify_order_cancelled(
            bot=bot,
            telegram_id=data['driver_telegram_id'],
            order_id=data['order_id'],
            cancelled_by=data['cancelled_by_role'],
            cargo_description=data['cargo_description']
        )
        
        logger.info(f"Webhook: Отправлены уведомления об отмене заказа #{data['order_id']}")
        
        return web.json_response({'success': True})
        
    except Exception as e:
        logger.error(f"Ошибка обработки webhook order_cancelled: {e}")
        return web.json_response({'error': str(e)}, status=500)


async def webhook_health(request):
    """Проверка здоровья webhook сервера"""
    return web.json_response({
        'status': 'ok',
        'service': 'telegram-bot-webhooks'
    })


async def webhook_new_chat_message(request):
    """
    Webhook: новое сообщение в чат заказа
    
    Ожидаемые данные:
    {
        "type": "new_chat_message",
        "order_id": 123,
        "sender_name": "Иван",
        "sender_role": "customer",
        "message_text": "Когда приедете?",
        "recipient_telegram_id": 123456789
    }
    """
    if not await verify_webhook_token(request):
        return web.json_response({'error': 'Unauthorized'}, status=401)
    
    try:
        data = await request.json()
        bot = request.app['bot']
        
        order_id = data.get('order_id')
        sender_name = data.get('sender_name')
        sender_role = data.get('sender_role')
        message_text = data.get('message_text')
        recipient_telegram_id = data.get('recipient_telegram_id')
        
        if not all([order_id, sender_name, sender_role, message_text, recipient_telegram_id]):
            return web.json_response({'error': 'Missing required fields'}, status=400)
        
        # Определяем роль отправителя
        sender_role_text = "водителя" if sender_role == "driver" else "заказчика"
        
        # Формируем сообщение
        notification_text = (
            f"💬 <b>Новое сообщение от {sender_role_text}</b>\n\n"
            f"📦 Заказ #{order_id}\n"
            f"👤 {sender_name}: {message_text}\n\n"
            f"<i>Откройте приложение для ответа</i>"
        )
        
        # Отправляем уведомление получателю
        try:
            await bot.send_message(
                chat_id=recipient_telegram_id,
                text=notification_text,
                parse_mode='HTML'
            )
            logger.info(f"Chat message notification sent to {recipient_telegram_id} for order {order_id}")
        except Exception as e:
            logger.error(f"Failed to send chat notification: {e}")
            return web.json_response({'error': f'Failed to send notification: {str(e)}'}, status=500)
        
        return web.json_response({'status': 'ok'})
        
    except Exception as e:
        logger.error(f"Webhook new_chat_message error: {e}")
        return web.json_response({'error': str(e)}, status=500)


def setup_webhook_handlers(app, bot: Bot):
    """Настройка обработчиков webhook"""
    app['bot'] = bot
    app.router.add_post('/webhook/new-order', webhook_new_order)
    app.router.add_post('/webhook/auction-complete', webhook_auction_complete)
    app.router.add_post('/webhook/auction-no-bids', webhook_auction_no_bids)
    app.router.add_post('/webhook/auction-bids-ready', webhook_auction_bids_ready)
    app.router.add_post('/webhook/order-confirmed', webhook_order_confirmed)
    app.router.add_post('/webhook/order-cancelled', webhook_order_cancelled)
    app.router.add_post('/webhook/new-chat-message', webhook_new_chat_message)
    app.router.add_get('/webhook/health', webhook_health)
    logger.info("Webhook handlers настроены")
