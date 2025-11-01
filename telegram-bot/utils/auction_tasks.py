"""
Фоновые задачи для аукционной системы
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

# Длительность аукциона в секундах (10 минут)
AUCTION_DURATION = 600

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
    """Проверка завершенных аукционов и выбор победителя"""
    while True:
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                # Находим заказы в статусе active, у которых истекло время аукциона
                now = datetime.now()
                
                async with db.execute("""
                    SELECT id, customer_id, cargo_description, delivery_address
                    FROM orders
                    WHERE status = 'active'
                    AND datetime(expires_at) <= datetime(?)
                """, (now.isoformat(),)) as cursor:
                    expired_orders = await cursor.fetchall()
                
                for order_id, customer_id, cargo_description, delivery_address in expired_orders:
                    # Получаем лучшее предложение (с наименьшей ценой)
                    async with db.execute("""
                        SELECT driver_id, price
                        FROM bids
                        WHERE order_id = ?
                        ORDER BY price ASC
                        LIMIT 1
                    """, (order_id,)) as cursor:
                        best_bid = await cursor.fetchone()
                    
                    if best_bid:
                        winner_user_id, winning_price = best_bid
                        
                        # Обновляем заказ - устанавливаем победителя
                        await db.execute("""
                            UPDATE orders
                            SET winner_driver_id = ?, winning_price = ?, status = 'completed'
                            WHERE id = ?
                        """, (winner_user_id, winning_price, order_id))
                        
                        await db.commit()
                        
                        # Получаем информацию о заказчике и водителе
                        customer = await get_user_by_id(customer_id)
                        winner = await get_user_by_id(winner_user_id)
                        
                        if customer and winner:
                            # Уведомляем победителя
                            await notify_auction_winner(
                                bot=bot,
                                order_id=order_id,
                                winner_user_id=winner_user_id,
                                winning_price=winning_price,
                                cargo_description=cargo_description,
                                delivery_address=delivery_address,
                                customer_phone=customer['phone_number']
                            )
                            
                            # Уведомляем проигравших
                            await notify_auction_losers(
                                bot=bot,
                                order_id=order_id,
                                winner_user_id=winner_user_id,
                                cargo_description=cargo_description
                            )
                            
                            # Уведомляем заказчика
                            await notify_customer_auction_complete(
                                bot=bot,
                                order_id=order_id,
                                customer_user_id=customer_id,
                                cargo_description=cargo_description,
                                winning_price=winning_price,
                                driver_phone=winner['phone_number']
                            )
                        
                        logger.info(f"Аукцион для заказа {order_id} завершен. Победитель: водитель {winner_user_id}, цена: {winning_price}")
                    else:
                        # Нет ставок - меняем статус на no_offers
                        await db.execute("""
                            UPDATE orders
                            SET status = 'no_offers'
                            WHERE id = ?
                        """, (order_id,))
                        
                        await db.commit()
                        
                        logger.info(f"Заказ {order_id} не получил ставок за время аукциона")
                        
                        # Уведомляем заказчика об отсутствии предложений
                        await notify_customer_no_bids(
                            bot=bot,
                            order_id=order_id,
                            customer_user_id=customer_id,
                            cargo_description=cargo_description
                        )
            
        except Exception as e:
            logger.error(f"Ошибка проверки аукционов: {e}")
        
        # Проверяем каждые 30 секунд
        await asyncio.sleep(30)


async def start_auction_checker(bot: Bot):
    """Запуск фоновых задач проверки аукционов и новых заявок"""
    logger.info("Запуск фоновой задачи проверки аукционов...")
    asyncio.create_task(check_expired_auctions(bot))
    
    logger.info("Запуск фоновой задачи проверки новых заявок...")
    asyncio.create_task(check_new_orders(bot))

