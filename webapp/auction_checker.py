"""
Модуль для проверки завершения подборов
Запускается как отдельный процесс или cron задача
"""
import sqlite3
import logging
from datetime import datetime
from webhook_client import notify_auction_complete, notify_auction_no_bids
from config import DATABASE_PATH

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_expired_auctions():
    """
    Проверяет и завершает истекшие подборы
    Должна запускаться периодически (каждую минуту)
    """
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Находим заказы, у которых истек срок подбора (expires_at)
    expired_orders = cursor.execute('''
        SELECT id, customer_id, truck_type, cargo_description, delivery_address, pickup_address
        FROM orders
        WHERE status = 'active'
        AND datetime(expires_at) <= datetime('now')
    ''').fetchall()
    
    for order in expired_orders:
        order_id = order['id']
        
        # Получаем ставки по этому заказу (сортируем по цене - меньше лучше)
        bids = cursor.execute('''
            SELECT id, driver_id, price, created_at
            FROM bids
            WHERE order_id = ?
            ORDER BY price ASC
        ''', (order_id,)).fetchall()
        
        if bids:
            # Есть ставки - выбираем победителя (минимальная цена)
            winning_bid = bids[0]
            
            # Получаем данные победителя
            winner = cursor.execute('''
                SELECT id, telegram_id, name, phone_number, username
                FROM users
                WHERE id = ?
            ''', (winning_bid['driver_id'],)).fetchone()
            
            # Получаем данные заказчика
            customer = cursor.execute('''
                SELECT id, telegram_id, phone_number, username
                FROM users
                WHERE id = ?
            ''', (order['customer_id'],)).fetchone()
            
            # Обновляем статус заказа - устанавливаем победителя и статус "в процессе"
            cursor.execute('''
                UPDATE orders
                SET status = 'in_progress', 
                    winner_driver_id = ?,
                    winning_price = ?
                WHERE id = ?
            ''', (winning_bid['driver_id'], winning_bid['price'], order_id))
            
            conn.commit()
            
            # Отправляем webhook уведомление
            try:
                notify_auction_complete(
                    order_id=order_id,
                    winner_telegram_id=winner['telegram_id'],
                    winner_user_id=winner['id'],
                    winner_username=winner['username'],
                    winning_price=winning_bid['price'],
                    cargo_description=order['cargo_description'],
                    delivery_address=order['delivery_address'],
                    customer_user_id=customer['telegram_id'],
                    customer_username=customer['username'],
                    customer_phone=customer['phone_number'],
                    driver_phone=winner['phone_number']
                )
                logger.info(f"✅ Подбор завершен: заказ {order_id}, победитель {winner['name']}, цена {winning_bid['price']}")
            except Exception as e:
                logger.error(f"❌ Ошибка отправки webhook для заказа {order_id}: {e}")
        
        else:
            # Нет ставок - меняем статус на no_offers
            cursor.execute('''
                UPDATE orders
                SET status = 'no_offers'
                WHERE id = ?
            ''', (order_id,))
            
            conn.commit()
            
            # Получаем данные заказчика
            customer = cursor.execute('''
                SELECT telegram_id
                FROM users
                WHERE id = ?
            ''', (order['customer_id'],)).fetchone()
            
            # Отправляем webhook уведомление
            try:
                notify_auction_no_bids(
                    order_id=order_id,
                    customer_user_id=customer['telegram_id'],
                    cargo_description=order['cargo_description']
                )
                logger.info(f"⚠️ Подбор без ставок: заказ {order_id}")
            except Exception as e:
                logger.error(f"❌ Ошибка отправки webhook для заказа {order_id}: {e}")
    
    conn.close()
    return len(expired_orders)


if __name__ == '__main__':
    """
    Запуск проверки подборов в цикле
    """
    import time
    
    logger.info("🚀 Запуск проверки подборов...")
    
    while True:
        try:
            count = check_expired_auctions()
            if count > 0:
                logger.info(f"⏰ Обработано подборов: {count}")
            time.sleep(30)  # Проверка каждые 30 секунд
        except Exception as e:
            logger.error(f"❌ Ошибка проверки подборов: {e}", exc_info=True)
            time.sleep(60)  # При ошибке ждем дольше
