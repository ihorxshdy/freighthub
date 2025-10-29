"""
Модуль для проверки завершения аукционов
Запускается как отдельный процесс или cron задача
"""
import sqlite3
from webhook_client import notify_auction_complete, notify_auction_no_bids
from truck_config import DATABASE_PATH


def check_expired_auctions():
    """
    Проверяет и завершает истекшие аукционы
    Должна запускаться периодически (каждую минуту)
    """
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Находим заказы, у которых истек срок аукциона
    expired_orders = cursor.execute('''
        SELECT id, customer_id, truck_type_id, description, delivery_location, price
        FROM orders
        WHERE status = 'active'
        AND datetime(created_at, '+30 minutes') <= datetime('now')
    ''').fetchall()
    
    for order in expired_orders:
        order_id = order['id']
        
        # Получаем ставки по этому заказу
        bids = cursor.execute('''
            SELECT id, driver_id, bid_amount
            FROM bids
            WHERE order_id = ? AND status = 'pending'
            ORDER BY bid_amount ASC
        ''', (order_id,)).fetchall()
        
        if bids:
            # Есть ставки - выбираем победителя (минимальная ставка)
            winning_bid = bids[0]
            
            # Получаем данные победителя
            winner = cursor.execute('''
                SELECT id, telegram_id, first_name, phone
                FROM users
                WHERE id = ?
            ''', (winning_bid['driver_id'],)).fetchone()
            
            # Получаем данные заказчика
            customer = cursor.execute('''
                SELECT id, telegram_id, phone
                FROM users
                WHERE id = ?
            ''', (order['customer_id'],)).fetchone()
            
            # Обновляем статус заказа
            cursor.execute('''
                UPDATE orders
                SET status = 'assigned', assigned_driver_id = ?
                WHERE id = ?
            ''', (winning_bid['driver_id'], order_id))
            
            # Обновляем статус выигравшей ставки
            cursor.execute('''
                UPDATE bids
                SET status = 'accepted'
                WHERE id = ?
            ''', (winning_bid['id'],))
            
            # Обновляем статус проигравших ставок
            for bid in bids[1:]:
                cursor.execute('''
                    UPDATE bids
                    SET status = 'rejected'
                    WHERE id = ?
                ''', (bid['id'],))
            
            conn.commit()
            
            # Отправляем webhook уведомление
            try:
                notify_auction_complete(
                    order_id=order_id,
                    winner_user_id=winner['telegram_id'],
                    winning_price=winning_bid['bid_amount'],
                    cargo_description=order['description'],
                    delivery_address=order['delivery_location'],
                    customer_user_id=customer['telegram_id'],
                    customer_phone=customer['phone'],
                    driver_phone=winner['phone']
                )
                print(f"✅ Аукцион завершен: заказ {order_id}, победитель {winner['first_name']}")
            except Exception as e:
                print(f"❌ Ошибка отправки webhook для заказа {order_id}: {e}")
        
        else:
            # Нет ставок - закрываем заказ
            cursor.execute('''
                UPDATE orders
                SET status = 'cancelled'
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
                    cargo_description=order['description']
                )
                print(f"⚠️ Аукцион без ставок: заказ {order_id}")
            except Exception as e:
                print(f"❌ Ошибка отправки webhook для заказа {order_id}: {e}")
    
    conn.close()
    return len(expired_orders)


if __name__ == '__main__':
    """
    Запуск проверки аукционов
    Можно запускать через cron каждую минуту:
    
    * * * * * cd /path/to/webapp && python auction_checker.py
    
    Или через systemd timer, или как отдельный процесс на Render
    """
    import time
    
    print("🚀 Запуск проверки аукционов...")
    
    while True:
        try:
            count = check_expired_auctions()
            if count > 0:
                print(f"⏰ Обработано аукционов: {count}")
            else:
                print(".", end="", flush=True)
        except Exception as e:
            print(f"\n❌ Ошибка: {e}")
        
        # Проверяем каждые 30 секунд
        time.sleep(30)
