import aiosqlite
import asyncio
from bot.config import DB_PATH
import os

async def init_database():
    """Инициализация базы данных и создание таблиц"""
    # Создаем папку для базы данных если не существует
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    async with aiosqlite.connect(DB_PATH) as db:
        # Таблица пользователей
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                phone_number TEXT NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('customer', 'driver')),
                truck_type TEXT,
                name TEXT,
                username TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Таблица заявок
        await db.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                truck_type TEXT NOT NULL,
                cargo_description TEXT NOT NULL,
                delivery_address TEXT NOT NULL,
                status TEXT DEFAULT 'active' CHECK (status IN ('active', 'auction_completed', 'in_progress', 'completed', 'cancelled', 'closed', 'no_offers')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                winner_driver_id INTEGER,
                winning_price REAL,
                pickup_address TEXT,
                pickup_time TEXT,
                delivery_time TEXT,
                max_price REAL,
                delivery_date TEXT,
                customer_confirmed BOOLEAN DEFAULT FALSE,
                driver_confirmed BOOLEAN DEFAULT FALSE,
                cancelled_by INTEGER,
                cancelled_at TIMESTAMP,
                cancellation_reason TEXT,
                selection_ended BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (customer_id) REFERENCES users (id),
                FOREIGN KEY (winner_driver_id) REFERENCES users (id),
                FOREIGN KEY (cancelled_by) REFERENCES users (id)
            )
        """)
        
        # Таблица предложений водителей
        await db.execute("""
            CREATE TABLE IF NOT EXISTS bids (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                driver_id INTEGER NOT NULL,
                price REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (order_id) REFERENCES orders (id),
                FOREIGN KEY (driver_id) REFERENCES users (id),
                UNIQUE(order_id, driver_id)
            )
        """)
        
        # Таблица машин водителей
        await db.execute("""
            CREATE TABLE IF NOT EXISTS driver_vehicles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                driver_id INTEGER NOT NULL,
                truck_type TEXT NOT NULL,
                is_primary BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (driver_id) REFERENCES users (id),
                UNIQUE(driver_id, truck_type)
            )
        """)
        
        # Таблица для отслеживания сообщений заявок
        await db.execute("""
            CREATE TABLE IF NOT EXISTS order_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                chat_id INTEGER NOT NULL,
                message_id INTEGER NOT NULL,
                message_type TEXT NOT NULL CHECK (message_type IN ('customer', 'driver_notification', 'admin')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (order_id) REFERENCES orders (id),
                FOREIGN KEY (user_id) REFERENCES users (id),
                UNIQUE(order_id, user_id, message_type)
            )
        """)
        
        # Таблица отзывов
        await db.execute("""
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                reviewer_id INTEGER NOT NULL,
                reviewee_id INTEGER NOT NULL,
                rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
                comment TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (order_id) REFERENCES orders (id),
                FOREIGN KEY (reviewer_id) REFERENCES users (id),
                FOREIGN KEY (reviewee_id) REFERENCES users (id),
                UNIQUE(order_id, reviewer_id, reviewee_id)
            )
        """)
        
        await db.commit()

async def get_user_by_telegram_id(telegram_id: int):
    """Получить пользователя по Telegram ID"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT * FROM users WHERE telegram_id = ?", 
            (telegram_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    'id': row[0],
                    'telegram_id': row[1],
                    'phone_number': row[2],
                    'role': row[3],
                    'truck_type': row[4],
                    'name': row[5],
                    'created_at': row[6]
                }
            return None

async def get_user_by_id(user_id: int):
    """Получить пользователя по ID"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT * FROM users WHERE id = ?", 
            (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    'id': row[0],
                    'telegram_id': row[1],
                    'phone_number': row[2],
                    'role': row[3],
                    'truck_type': row[4],
                    'name': row[5],
                    'created_at': row[6]
                }
            return None

async def get_all_drivers(truck_type: str = None):
    """
    Получить всех водителей
    
    Args:
        truck_type: Фильтр по типу машины (опционально). 
                   Если указан, вернёт водителей, у которых есть машина этого типа.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        if truck_type:
            # Ищем водителей через таблицу driver_vehicles
            query = """
                SELECT DISTINCT u.* 
                FROM users u
                INNER JOIN driver_vehicles dv ON u.id = dv.driver_id
                WHERE u.role = 'driver' AND dv.truck_type = ?
            """
            params = (truck_type,)
        else:
            query = "SELECT * FROM users WHERE role = 'driver'"
            params = ()
            
        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [{
                'id': row[0],
                'telegram_id': row[1],
                'phone_number': row[2],
                'role': row[3],
                'truck_type': row[4] if len(row) > 4 else None,
                'name': row[5] if len(row) > 5 else None,
                'created_at': row[6] if len(row) > 6 else None
            } for row in rows]

async def get_bid_participants(order_id: int):
    """Получить всех участников подбора (кто сделал предложения)"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            """SELECT DISTINCT u.* 
               FROM users u 
               JOIN bids b ON u.id = b.driver_id 
               WHERE b.order_id = ?""",
            (order_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [{
                'user_id': row[0],
                'telegram_id': row[1],
                'phone_number': row[2],
                'role': row[3],
                'truck_type': row[4],
                'name': row[5],
                'created_at': row[6]
            } for row in rows]

async def create_user(telegram_id: int, phone_number: str, role: str, truck_type: str = None, name: str = None):
    """Создать нового пользователя"""
    from datetime import datetime
    async with aiosqlite.connect(DB_PATH) as db:
        # Создаём пользователя
        cursor = await db.execute(
            """INSERT INTO users (telegram_id, phone_number, role, truck_type, name) 
               VALUES (?, ?, ?, ?, ?)""",
            (telegram_id, phone_number, role, truck_type, name)
        )
        user_id = cursor.lastrowid
        
        # Если это водитель и указан тип машины, добавляем в driver_vehicles
        if role == 'driver' and truck_type:
            await db.execute(
                """INSERT INTO driver_vehicles (driver_id, truck_type, created_at) 
                   VALUES (?, ?, ?)""",
                (user_id, truck_type, datetime.now().isoformat())
            )
        
        await db.commit()
        return user_id

async def create_order(customer_id: int, truck_type: str, cargo_description: str, 
                      delivery_address: str, expires_at: str, pickup_address: str = None,
                      pickup_time: str = None, delivery_time: str = None):
    """Создать новую заявку"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """INSERT INTO orders (customer_id, truck_type, cargo_description, 
               delivery_address, expires_at, pickup_address, pickup_time, delivery_time) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (customer_id, truck_type, cargo_description, delivery_address, expires_at,
             pickup_address, pickup_time, delivery_time)
        )
        await db.commit()
        return cursor.lastrowid

async def get_drivers_by_truck_type(truck_type: str):
    """Получить всех водителей с указанным типом машины"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            """SELECT DISTINCT u.* 
               FROM users u
               INNER JOIN driver_vehicles dv ON u.id = dv.driver_id
               WHERE u.role = 'driver' AND dv.truck_type = ?""",
            (truck_type,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [{
                'id': row[0],
                'telegram_id': row[1],
                'phone_number': row[2],
                'role': row[3],
                'truck_type': row[4],
                'name': row[5],
                'created_at': row[6]
            } for row in rows]

async def create_bid(order_id: int, driver_id: int, price: float):
    """Создать предложение водителя"""
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute(
                "INSERT INTO bids (order_id, driver_id, price) VALUES (?, ?, ?)",
                (order_id, driver_id, price)
            )
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            # Водитель уже сделал предложение для этого заказа
            await db.execute(
                "UPDATE bids SET price = ? WHERE order_id = ? AND driver_id = ?",
                (price, order_id, driver_id)
            )
            await db.commit()
            return True

async def get_order_by_id(order_id: int):
    """Получить заявку по ID"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT * FROM orders WHERE id = ?",
            (order_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    'id': row[0],
                    'customer_id': row[1],
                    'truck_type': row[2],
                    'cargo_description': row[3],
                    'delivery_address': row[4],
                    'status': row[5],
                    'created_at': row[6],
                    'expires_at': row[7],
                    'winner_driver_id': row[8],
                    'winning_price': row[9],
                    'pickup_address': row[10],
                    'pickup_time': row[11],
                    'delivery_time': row[12]
                }
            return None

async def get_bids_for_order(order_id: int):
    """Получить все предложения для заявки"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            """SELECT b.*, u.telegram_id, u.phone_number, u.name 
               FROM bids b 
               JOIN users u ON b.driver_id = u.id 
               WHERE b.order_id = ? 
               ORDER BY b.price ASC""",
            (order_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [{
                'id': row[0],
                'order_id': row[1],
                'driver_id': row[2],
                'price': row[3],
                'created_at': row[4],
                'driver_telegram_id': row[5],
                'driver_phone': row[6],
                'driver_name': row[7]
            } for row in rows]

async def complete_order(order_id: int, winner_driver_id = None, winning_price = None, status: str = 'completed'):
    """Завершить заявку с выбором победителя"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """UPDATE orders 
               SET status = ?, winner_driver_id = ?, winning_price = ? 
               WHERE id = ?""",
            (status, winner_driver_id, winning_price, order_id)
        )
        await db.commit()

async def get_active_orders():
    """Получить все активные заявки"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT * FROM orders WHERE status = 'active'",
        ) as cursor:
            rows = await cursor.fetchall()
            return [{
                'id': row[0],
                'customer_id': row[1],
                'truck_type': row[2],
                'cargo_description': row[3],
                'delivery_address': row[4],
                'status': row[5],
                'created_at': row[6],
                'expires_at': row[7],
                'winner_driver_id': row[8],
                'winning_price': row[9],
                'pickup_address': row[10],
                'pickup_time': row[11],
                'delivery_time': row[12]
            } for row in rows]

async def get_all_users():
    """Получить всех пользователей"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT * FROM users ORDER BY created_at DESC") as cursor:
            rows = await cursor.fetchall()
            return [{
                'id': row[0],
                'telegram_id': row[1],
                'phone_number': row[2],
                'role': row[3],
                'truck_type': row[4],
                'name': row[5],
                'created_at': row[6]
            } for row in rows]

async def delete_user_by_telegram_id(telegram_id: int):
    """Удалить пользователя по Telegram ID"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM users WHERE telegram_id = ?", (telegram_id,))
        await db.commit()
        return True

async def delete_all_users():
    """Удалить всех пользователей (для тестирования)"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM users")
        await db.commit()
        return True

async def get_user_stats():
    """Получить статистику пользователей"""
    async with aiosqlite.connect(DB_PATH) as db:
        # Общее количество пользователей
        async with db.execute("SELECT COUNT(*) FROM users") as cursor:
            total_users = (await cursor.fetchone())[0]
        
        # Количество водителей
        async with db.execute("SELECT COUNT(*) FROM users WHERE role = 'driver'") as cursor:
            drivers_count = (await cursor.fetchone())[0]
        
        # Количество заказчиков
        async with db.execute("SELECT COUNT(*) FROM users WHERE role = 'customer'") as cursor:
            customers_count = (await cursor.fetchone())[0]
        
        # Количество активных заявок
        async with db.execute("SELECT COUNT(*) FROM orders WHERE status = 'active'") as cursor:
            active_orders = (await cursor.fetchone())[0]
        
        return {
            'total_users': total_users,
            'drivers_count': drivers_count,
            'customers_count': customers_count,
            'active_orders': active_orders
        }

async def get_orders_by_customer(customer_id: int):
    """Получить все заявки заказчика"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            """SELECT * FROM orders WHERE customer_id = ? 
               ORDER BY created_at DESC""",
            (customer_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [{
                'id': row[0],
                'customer_id': row[1],
                'truck_type': row[2],
                'cargo_description': row[3],
                'delivery_address': row[4],
                'status': row[5],
                'created_at': row[6],
                'expires_at': row[7],
                'winner_driver_id': row[8],
                'winning_price': row[9],
                    'pickup_address': row[10],
                    'pickup_time': row[11],
                    'delivery_time': row[12]
                } for row in rows]

async def get_bids_by_driver(driver_id: int):
    """Получить все предложения водителя"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            """SELECT b.*, o.cargo_description, o.delivery_address, 
               o.status, o.expires_at, o.winning_price, o.winner_driver_id
               FROM bids b 
               JOIN orders o ON b.order_id = o.id 
               WHERE b.driver_id = ? 
               ORDER BY b.created_at DESC""",
            (driver_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [{
                'id': row[0],
                'order_id': row[1],
                'driver_id': row[2],
                'price': row[3],
                'created_at': row[4],
                'cargo_description': row[5],
                'delivery_address': row[6],
                'order_status': row[7],
                'expires_at': row[8],
                'winning_price': row[9],
                'winner_driver_id': row[10]
            } for row in rows]

async def get_won_orders_by_driver(driver_id: int):
    """Получить заявки, выигранные водителем"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            """SELECT * FROM orders WHERE winner_driver_id = ? 
               ORDER BY created_at DESC""",
            (driver_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [{
                'id': row[0],
                'customer_id': row[1],
                'truck_type': row[2],
                'cargo_description': row[3],
                'delivery_address': row[4],
                'status': row[5],
                'created_at': row[6],
                'expires_at': row[7],
                'winner_driver_id': row[8],
                'winning_price': row[9],
                    'pickup_address': row[10],
                    'pickup_time': row[11],
                    'delivery_time': row[12]
                } for row in rows]

# Функции для работы с множественными машинами водителей

async def add_driver_vehicle(driver_id: int, truck_type: str, is_primary: bool = False):
    """Добавить машину водителю"""
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            # Если это первичная машина, убираем флаг у всех остальных
            if is_primary:
                await db.execute(
                    "UPDATE driver_vehicles SET is_primary = FALSE WHERE driver_id = ?",
                    (driver_id,)
                )
            
            await db.execute(
                """INSERT INTO driver_vehicles (driver_id, truck_type, is_primary) 
                   VALUES (?, ?, ?)""",
                (driver_id, truck_type, is_primary)
            )
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            # Такой тип машины уже есть у водителя
            return False

async def get_driver_vehicles(driver_id: int):
    """Получить все машины водителя"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            """SELECT * FROM driver_vehicles WHERE driver_id = ? 
               ORDER BY is_primary DESC, created_at ASC""",
            (driver_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [{
                'id': row[0],
                'driver_id': row[1],
                'truck_type': row[2],
                'is_primary': bool(row[3]),
                'created_at': row[4]
            } for row in rows]

async def delete_driver_vehicle(driver_id: int, truck_type: str):
    """Удалить машину у водителя"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM driver_vehicles WHERE driver_id = ? AND truck_type = ?",
            (driver_id, truck_type)
        )
        await db.commit()
        return True

async def set_primary_vehicle(driver_id: int, truck_type: str):
    """Установить машину как основную"""
    async with aiosqlite.connect(DB_PATH) as db:
        # Убираем флаг у всех машин водителя
        await db.execute(
            "UPDATE driver_vehicles SET is_primary = FALSE WHERE driver_id = ?",
            (driver_id,)
        )
        # Устанавливаем флаг для выбранной машины
        await db.execute(
            "UPDATE driver_vehicles SET is_primary = TRUE WHERE driver_id = ? AND truck_type = ?",
            (driver_id, truck_type)
        )
        await db.commit()
        return True

async def get_drivers_by_truck_type_multiple(truck_type: str):
    """Получить всех водителей с указанным типом машины (из множественных машин)"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            """SELECT DISTINCT u.* FROM users u
               JOIN driver_vehicles dv ON u.id = dv.driver_id
               WHERE u.role = 'driver' AND dv.truck_type = ?""",
            (truck_type,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [{
                'id': row[0],
                'telegram_id': row[1],
                'phone_number': row[2],
                'role': row[3],
                'truck_type': row[4],
                'name': row[5],
                'created_at': row[6]
            } for row in rows]

async def migrate_existing_trucks():
    """Перенести существующие truck_type из users в driver_vehicles"""
    async with aiosqlite.connect(DB_PATH) as db:
        # Получаем всех водителей с truck_type
        async with db.execute(
            "SELECT id, truck_type FROM users WHERE role = 'driver' AND truck_type IS NOT NULL"
        ) as cursor:
            drivers = await cursor.fetchall()
        
        # Переносим их в новую таблицу как основные машины
        for driver_id, truck_type in drivers:
            await add_driver_vehicle(driver_id, truck_type, is_primary=True)
        
        return len(drivers)

# Функции для работы с сообщениями заявок

async def save_order_message(order_id: int, user_id: int, chat_id: int, message_id: int, message_type: str):
    """Сохранить ID сообщения для заявки"""
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute(
                """INSERT OR REPLACE INTO order_messages 
                   (order_id, user_id, chat_id, message_id, message_type) 
                   VALUES (?, ?, ?, ?, ?)""",
                (order_id, user_id, chat_id, message_id, message_type)
            )
            await db.commit()
            return True
        except Exception as e:
            print(f"Error saving order message: {e}")
            return False

async def get_order_message(order_id: int, message_type: str = 'order_status'):
    """Получить сообщение заявки"""
    async with aiosqlite.connect(DB_PATH) as db:
        query = "SELECT chat_id, message_id FROM order_messages WHERE order_id = ? AND message_type = ? ORDER BY created_at DESC LIMIT 1"
        async with db.execute(query, (order_id, message_type)) as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    'chat_id': row[0],
                    'message_id': row[1]
                }
            return None

async def get_driver_messages_for_order(order_id: int):
    """Получить все сообщения водителей для заявки"""
    async with aiosqlite.connect(DB_PATH) as db:
        query = """
        SELECT om.chat_id, om.message_id, om.user_id, u.telegram_id 
        FROM order_messages om
        JOIN users u ON om.user_id = u.id
        WHERE om.order_id = ? AND om.message_type = 'driver_notification'
        """
        async with db.execute(query, (order_id,)) as cursor:
            rows = await cursor.fetchall()
            return [{
                'chat_id': row[0],
                'message_id': row[1],
                'user_id': row[2],
                'telegram_id': row[3]
            } for row in rows]

async def get_order_messages(order_id: int, message_type: str = None):
    """Получить все сообщения для заявки"""
    async with aiosqlite.connect(DB_PATH) as db:
        if message_type:
            query = "SELECT * FROM order_messages WHERE order_id = ? AND message_type = ?"
            params = (order_id, message_type)
        else:
            query = "SELECT * FROM order_messages WHERE order_id = ?"
            params = (order_id,)
        
        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [{
                'id': row[0],
                'order_id': row[1],
                'user_id': row[2],
                'chat_id': row[3],
                'message_id': row[4],
                'message_type': row[5],
                'created_at': row[6]
            } for row in rows]

async def delete_order_messages(order_id: int):
    """Удалить все сообщения заявки"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM order_messages WHERE order_id = ?", (order_id,))
        await db.commit()
        return True

async def get_orders_by_driver(driver_id: int):
    """Получить все заказы, доступные водителю или в которых он участвовал"""
    async with aiosqlite.connect(DB_PATH) as db:
        # Получаем типы машин водителя
        async with db.execute("SELECT truck_type FROM driver_vehicles WHERE driver_id = ?", (driver_id,)) as cursor:
            vehicle_rows = await cursor.fetchall()
            if vehicle_rows:
                truck_types = [row[0] for row in vehicle_rows]
            else:
                # Fallback на старое поле
                async with db.execute("SELECT truck_type FROM users WHERE id = ?", (driver_id,)) as cursor:
                    user_row = await cursor.fetchone()
                    if user_row and user_row[0]:
                        truck_types = [user_row[0]]
                    else:
                        return []
        
        if not truck_types:
            return []
        
        # Формируем запрос для поиска подходящих заказов
        placeholders = ','.join(['?' for _ in truck_types])
        query = f"""
        SELECT DISTINCT o.* FROM orders o
        WHERE o.truck_type IN ({placeholders})
        OR o.id IN (
            SELECT DISTINCT b.order_id FROM bids b WHERE b.driver_id = ?
        )
        ORDER BY o.created_at DESC
        """
        
        params = truck_types + [driver_id]
        
        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [{
                'id': row[0],
                'customer_id': row[1], 
                'truck_type': row[2],
                'cargo_description': row[3],
                'pickup_address': row[4],
                'delivery_address': row[5],
                'pickup_time': row[6],
                'delivery_time': row[7],
                'status': row[8],
                'created_at': row[9],
                'expires_at': row[10],
                'winner_driver_id': row[11],
                'winning_price': row[12]
            } for row in rows]