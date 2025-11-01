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
    Webhook: аукцион завершён с победителем
    
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
        
        logger.info(f"Webhook: Аукцион #{data['order_id']} завершён, победитель telegram_id={data['winner_telegram_id']}")
        
        return web.json_response({'success': True})
        
    except Exception as e:
        logger.error(f"Ошибка обработки webhook auction_complete: {e}")
        return web.json_response({'error': str(e)}, status=500)


async def webhook_auction_no_bids(request):
    """
    Webhook: аукцион завершён без ставок
    
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
        
        logger.info(f"Webhook: Аукцион #{data['order_id']} завершён без ставок")
        
        return web.json_response({'success': True})
        
    except Exception as e:
        logger.error(f"Ошибка обработки webhook auction_no_bids: {e}")
        return web.json_response({'error': str(e)}, status=500)


async def webhook_order_confirmed(request):
    """
    Webhook: одна из сторон подтвердила выполнение заказа
    
    Ожидаемые данные:
    {
        "order_id": 123,
        "confirmed_by": "customer",  # или "driver"
        "notify_telegram_id": 12345,  # telegram_id стороны, которую нужно уведомить
        "cargo_description": "Мебель для переезда"
    }
    """
    if not await verify_webhook_token(request):
        return web.json_response({'error': 'Unauthorized'}, status=401)
    
    try:
        data = await request.json()
        bot = request.app['bot']
        
        # Валидация обязательных данных
        required = ['order_id', 'confirmed_by', 'notify_telegram_id', 'cargo_description']
        if not all(field in data for field in required):
            return web.json_response({'error': 'Missing required fields'}, status=400)
        
        # Отправляем уведомление другой стороне
        await notify_order_confirmed(
            bot=bot,
            telegram_id=data['notify_telegram_id'],
            order_id=data['order_id'],
            confirmed_by=data['confirmed_by'],
            cargo_description=data['cargo_description']
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
        "cancelled_by": "customer",  # или "driver"
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
        required = ['order_id', 'cancelled_by', 'customer_telegram_id', 'driver_telegram_id', 'cargo_description']
        if not all(field in data for field in required):
            return web.json_response({'error': 'Missing required fields'}, status=400)
        
        # Отправляем уведомления обеим сторонам
        await notify_order_cancelled(
            bot=bot,
            telegram_id=data['customer_telegram_id'],
            order_id=data['order_id'],
            cancelled_by=data['cancelled_by'],
            cargo_description=data['cargo_description']
        )
        
        await notify_order_cancelled(
            bot=bot,
            telegram_id=data['driver_telegram_id'],
            order_id=data['order_id'],
            cancelled_by=data['cancelled_by'],
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


def setup_webhook_handlers(app, bot: Bot):
    """Настройка обработчиков webhook"""
    app['bot'] = bot
    app.router.add_post('/webhook/new-order', webhook_new_order)
    app.router.add_post('/webhook/auction-complete', webhook_auction_complete)
    app.router.add_post('/webhook/auction-no-bids', webhook_auction_no_bids)
    app.router.add_post('/webhook/order-confirmed', webhook_order_confirmed)
    app.router.add_post('/webhook/order-cancelled', webhook_order_cancelled)
    app.router.add_get('/webhook/health', webhook_health)
    logger.info("Webhook handlers настроены")
