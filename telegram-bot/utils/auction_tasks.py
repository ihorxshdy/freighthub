"""
Фоновые задачи для подборной системы
"""
import asyncio
from datetime import datetime, timedelta
from aiogram import Bot
import aiosqlite
from bot.config import DB_PATH
from utils.helpers import logger
from utils.notifications import (
    notify_drivers_new_order,
    notify_auction_winner,
    notify_auction_losers,
    notify_customer_no_bids,
    notify_customer_auction_complete
)
from database.models import get_user_by_id, get_order_by_id

# Длительность подбора в секундах (2 минуты)
AUCTION_DURATION = 120

# Хранилище для отслеживания заявок, по которым уже отправлены уведомления
notified_orders = set()


async def check_new_orders(bot: Bot):
    """Проверка новых заявок и отправка уведомлений водителям"""
    while True:
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                # Находим новые заявки в статусе active, которые ещё не истекли
                now = datetime.now()
                
                async with db.execute("""
                    SELECT id, truck_type, cargo_description, delivery_address, 
                           pickup_address, max_price, created_at
                    FROM orders
                    WHERE status = 'active'
                    AND datetime(expires_at) > datetime(?)
                """, (now.isoformat(),)) as cursor:
                    active_orders = await cursor.fetchall()
                
                for order_data in active_orders:
                    order_id = order_data[0]
                    
                    # Пропускаем, если уже отправляли уведомление
                    if order_id in notified_orders:
                        continue
                    
                    truck_type = order_data[1]
                    cargo_description = order_data[2]
                    delivery_address = order_data[3]
                    max_price = order_data[5] if order_data[5] else 0
                    
                    # Отправляем уведомление водителям
                    count = await notify_drivers_new_order(
                        bot=bot,
                        order_id=order_id,
                        truck_type=truck_type,
                        cargo_description=cargo_description,
                        delivery_address=delivery_address,
                        max_price=max_price
                    )
                    
                    # Помечаем заявку как обработанную
                    notified_orders.add(order_id)
                    
                    logger.info(f"Отправлены уведомления о заявке #{order_id} ({count} водителей)")
                
                # Очищаем старые записи из notified_orders (старше 24 часов)
                # чтобы не раздувать память
                if len(notified_orders) > 1000:
                    notified_orders.clear()
                    logger.info("Очищен кеш отправленных уведомлений")
            
        except Exception as e:
            logger.error(f"Ошибка проверки новых заявок: {e}")
        
        # Проверяем каждые 10 секунд
        await asyncio.sleep(10)


async def check_expired_auctions(bot: Bot):
    """Проверка завершенных подборов - просто помечаем что прием заявок завершен"""
    while True:
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                # Находим заказы в статусе active, у которых истекло время подбора
                now = datetime.now()
                
                async with db.execute("""
                    SELECT id, customer_id, cargo_description
                    FROM orders
                    WHERE status = 'active'
                    AND selection_ended = FALSE
                    AND datetime(expires_at) <= datetime(?)
                """, (now.isoformat(),)) as cursor:
                    expired_orders = await cursor.fetchall()
                
                for order_id, customer_id, cargo_description in expired_orders:
                    # Просто помечаем что прием заявок завершен
                    # Заказчик сам выберет исполнителя
                    await db.execute("""
                        UPDATE orders
                        SET selection_ended = TRUE
                        WHERE id = ?
                    """, (order_id,))
                    
                    await db.commit()
                    
                    # Проверяем есть ли предложения
                    async with db.execute("""
                        SELECT COUNT(*) FROM bids WHERE order_id = ?
                    """, (order_id,)) as cursor:
                        bids_count_row = await cursor.fetchone()
                        bids_count = bids_count_row[0] if bids_count_row else 0
                    
                    if bids_count == 0:
                        # Нет предложений - уведомляем заказчика
                        await notify_customer_no_bids(
                            bot=bot,
                            order_id=order_id,
                            customer_user_id=customer_id,
                            cargo_description=cargo_description
                        )
                        logger.info(f"Заказ {order_id} не получил ставок за время подбора")
                    else:
                        logger.info(f"Прием заявок для заказа {order_id} завершен. Получено предложений: {bids_count}")
            
        except Exception as e:
            logger.error(f"Ошибка проверки подборов: {e}")
        
        # Проверяем каждые 30 секунд
        await asyncio.sleep(30)


async def start_auction_checker(bot: Bot):
    """Запуск фоновых задач проверки подборов и новых заявок"""
    logger.info("Запуск фоновой задачи проверки подборов...")
    asyncio.create_task(check_expired_auctions(bot))
    
    logger.info("Запуск фоновой задачи проверки новых заявок...")
    asyncio.create_task(check_new_orders(bot))

