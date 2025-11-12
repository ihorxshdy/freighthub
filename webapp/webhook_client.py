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


def notify_new_order(order_id, truck_type, cargo_description, delivery_address, max_price, 
                     pickup_address=None, pickup_time=None, delivery_time=None, delivery_date=None):
    """Уведомить водителей о новой заявке"""
    return send_webhook('/webhook/new-order', {
        'order_id': order_id,
        'truck_type': truck_type,
        'cargo_description': cargo_description,
        'delivery_address': delivery_address,
        'max_price': max_price,
        'pickup_address': pickup_address,
        'pickup_time': pickup_time,
        'delivery_time': delivery_time,
        'delivery_date': delivery_date
    })


def notify_auction_complete(order_id, winner_telegram_id, winner_user_id, winner_username, winning_price, cargo_description, 
                           delivery_address, customer_user_id, customer_username, customer_phone, driver_phone):
    """Уведомить о завершении подбора с победителем"""
    return send_webhook('/webhook/auction-complete', {
        'order_id': order_id,
        'winner_telegram_id': winner_telegram_id,
        'winner_user_id': winner_user_id,
        'winner_username': winner_username,
        'winning_price': winning_price,
        'cargo_description': cargo_description,
        'delivery_address': delivery_address,
        'customer_user_id': customer_user_id,
        'customer_username': customer_username,
        'customer_phone': customer_phone,
        'driver_phone': driver_phone
    })


def notify_auction_no_bids(order_id, customer_user_id, cargo_description):
    """Уведомить об подборе без ставок"""
    return send_webhook('/webhook/auction-no-bids', {
        'order_id': order_id,
        'customer_user_id': customer_user_id,
        'cargo_description': cargo_description
    })


def notify_order_confirmed(order_id, confirmed_by_telegram_id, confirmed_by_role, customer_telegram_id, driver_telegram_id):
    """Уведомить о подтверждении выполнения заказа одной из сторон"""
    return send_webhook('/webhook/order-confirmed', {
        'order_id': order_id,
        'confirmed_by_telegram_id': confirmed_by_telegram_id,
        'confirmed_by_role': confirmed_by_role,
        'customer_telegram_id': customer_telegram_id,
        'driver_telegram_id': driver_telegram_id
    })


def notify_order_cancelled(order_id, cancelled_by_telegram_id, cancelled_by_role, customer_telegram_id, driver_telegram_id, cargo_description):
    """Уведомить об отмене заказа"""
    return send_webhook('/webhook/order-cancelled', {
        'order_id': order_id,
        'cancelled_by_telegram_id': cancelled_by_telegram_id,
        'cancelled_by_role': cancelled_by_role,
        'customer_telegram_id': customer_telegram_id,
        'driver_telegram_id': driver_telegram_id,
        'cargo_description': cargo_description
    })


def notify_auction_bids_ready(order_id, customer_user_id, cargo_description, bids_count, min_price):
    """Уведомить заказчика о готовности предложений для выбора"""
    return send_webhook('/webhook/auction-bids-ready', {
        'order_id': order_id,
        'customer_user_id': customer_user_id,
        'cargo_description': cargo_description,
        'bids_count': bids_count,
        'min_price': min_price
    })


def notify_photo_uploaded(order_id, photo_type, uploader_role, customer_telegram_id, driver_telegram_id):
    """Уведомить о загрузке фото погрузки/выгрузки"""
    return send_webhook('/webhook/photo-uploaded', {
        'order_id': order_id,
        'photo_type': photo_type,  # 'loading' или 'unloading'
        'uploader_role': uploader_role,  # 'driver' или 'customer'
        'customer_telegram_id': customer_telegram_id,
        'driver_telegram_id': driver_telegram_id
    })


def notify_status_changed(order_id, old_status, new_status, customer_telegram_id, driver_telegram_id, cargo_description):
    """Уведомить об изменении статуса заказа"""
    return send_webhook('/webhook/status-changed', {
        'order_id': order_id,
        'old_status': old_status,
        'new_status': new_status,
        'customer_telegram_id': customer_telegram_id,
        'driver_telegram_id': driver_telegram_id,
        'cargo_description': cargo_description
    })


def send_webhook_notification(notification_data):
    """
    Универсальная функция для отправки уведомлений
    Используется для отправки уведомлений о сообщениях в чате
    
    notification_data должен содержать:
    {
        'type': 'new_chat_message',
        'order_id': 123,
        'sender_name': 'Иван',
        'sender_role': 'customer',
        'message_text': 'Текст сообщения',
        'recipient_telegram_id': 123456789
    }
    """
    notification_type = notification_data.get('type')
    
    if notification_type == 'new_chat_message':
        return send_webhook('/webhook/new-chat-message', notification_data)
    
    print(f"⚠️  Unknown notification type: {notification_type}")
    return None

