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
    НОВАЯ ЛОГИКА: После истечения времени заявка НЕ закрывается автоматически,
    а переходит в статус "auction_completed" для ручного выбора заказчиком
    """
    # Увеличиваем таймаут и включаем WAL режим для избежания блокировок
    conn = sqlite3.connect(DATABASE_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA busy_timeout=30000')
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
            # Есть ставки - переводим в статус "auction_completed" 
            # Заказчик сможет посмотреть предложения и выбрать исполнителя
            cursor.execute('''
                UPDATE orders
                SET status = 'auction_completed'
                WHERE id = ?
            ''', (order_id,))
            
            conn.commit()
            
            # Получаем данные заказчика для уведомления
            customer = cursor.execute('''
                SELECT telegram_id
                FROM users
                WHERE id = ?
            ''', (order['customer_id'],)).fetchone()
            
            # Отправляем webhook уведомление заказчику о завершении сбора предложений
            try:
                from webhook_client import notify_auction_bids_ready
                notify_auction_bids_ready(
                    order_id=order_id,
                    customer_user_id=customer['telegram_id'],
                    cargo_description=order['cargo_description'],
                    bids_count=len(bids),
                    min_price=bids[0]['price'] if bids else 0
                )
                logger.info(f"✅ Подбор завершен для ручного выбора: заказ {order_id}, предложений: {len(bids)}")
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
