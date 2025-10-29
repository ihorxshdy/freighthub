"""
Отправка webhook уведомлений в Telegram бот
"""
import requests
import os

# URL telegram бота (на Render будет из env)
TELEGRAM_BOT_URL = os.getenv('TELEGRAM_BOT_WEBHOOK_URL', 'http://localhost:8080')
WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET', 'change-this-secret-key')


def send_webhook(endpoint, data):
    """Отправка webhook запроса в бот"""
    url = f"{TELEGRAM_BOT_URL}{endpoint}"
    headers = {
        'Authorization': f'Bearer {WEBHOOK_SECRET}',
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.post(url, json=data, headers=headers, timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Webhook error: {e}")
        return None


def notify_new_order(order_id, truck_type, cargo_description, delivery_address, max_price):
    """Уведомить водителей о новой заявке"""
    return send_webhook('/webhook/new-order', {
        'order_id': order_id,
        'truck_type': truck_type,
        'cargo_description': cargo_description,
        'delivery_address': delivery_address,
        'max_price': max_price
    })


def notify_auction_complete(order_id, winner_user_id, winning_price, cargo_description, 
                           delivery_address, customer_user_id, customer_phone, driver_phone):
    """Уведомить о завершении аукциона с победителем"""
    return send_webhook('/webhook/auction-complete', {
        'order_id': order_id,
        'winner_user_id': winner_user_id,
        'winning_price': winning_price,
        'cargo_description': cargo_description,
        'delivery_address': delivery_address,
        'customer_user_id': customer_user_id,
        'customer_phone': customer_phone,
        'driver_phone': driver_phone
    })


def notify_auction_no_bids(order_id, customer_user_id, cargo_description):
    """Уведомить об аукционе без ставок"""
    return send_webhook('/webhook/auction-no-bids', {
        'order_id': order_id,
        'customer_user_id': customer_user_id,
        'cargo_description': cargo_description
    })
