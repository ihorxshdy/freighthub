import asyncio
import aiosqlite
import os

DATABASE_PATH = 'bot_database.db'

async def init_database():
    """Инициализация базы данных"""
    # Удаляем старую БД если есть
    if os.path.exists(DATABASE_PATH):
        os.remove(DATABASE_PATH)
        print(f"Удалена старая база данных: {DATABASE_PATH}")
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Таблица пользователей
        await db.execute('''
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                phone_number TEXT,
                role TEXT NOT NULL DEFAULT 'customer',
                created_at TEXT NOT NULL
            )
        ''')
        
        # Таблица заказов
        await db.execute('''
            CREATE TABLE orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                pickup_location TEXT NOT NULL,
                delivery_location TEXT NOT NULL,
                description TEXT NOT NULL,
                truck_type_id INTEGER NOT NULL,
                cargo_weight REAL,
                cargo_volume REAL,
                price REAL,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL,
                FOREIGN KEY (customer_id) REFERENCES users (id)
            )
        ''')
        
        # Таблица ставок/предложений
        await db.execute('''
            CREATE TABLE bids (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                driver_id INTEGER NOT NULL,
                bid_amount REAL NOT NULL,
                comment TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL,
                FOREIGN KEY (order_id) REFERENCES orders (id),
                FOREIGN KEY (driver_id) REFERENCES users (id)
            )
        ''')
        
        # Таблица транспорта водителей
        await db.execute('''
            CREATE TABLE driver_vehicles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                driver_id INTEGER NOT NULL,
                truck_type_id INTEGER NOT NULL,
                model TEXT,
                year INTEGER,
                license_plate TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (driver_id) REFERENCES users (id)
            )
        ''')
        
        # Таблица сообщений для live updates
        await db.execute('''
            CREATE TABLE order_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                message_id INTEGER NOT NULL,
                chat_id INTEGER NOT NULL,
                message_type TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (order_id) REFERENCES orders (id)
            )
        ''')
        
        await db.commit()
        print("База данных успешно инициализирована!")
        
        # Создадим тестовых пользователей
        from datetime import datetime
        
        # Тестовый заказчик
        await db.execute('''
            INSERT INTO users (telegram_id, username, first_name, last_name, phone_number, role, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (123456789, 'test_customer', 'Тестовый', 'Заказчик', '+7-900-123-45-67', 'customer', datetime.now().isoformat()))
        
        # Тестовый водитель
        await db.execute('''
            INSERT INTO users (telegram_id, username, first_name, last_name, phone_number, role, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (987654321, 'test_driver', 'Тестовый', 'Водитель', '+7-900-987-65-43', 'driver', datetime.now().isoformat()))
        
        # Тестовый заказ
        await db.execute('''
            INSERT INTO orders (customer_id, pickup_location, delivery_location, description, truck_type_id, cargo_weight, cargo_volume, price, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (1, 'Москва, ул. Тверская, 1', 'СПб, Невский пр., 100', 'Тестовая перевозка мебели', 8, 500.0, 2.5, 5000.0, 'active', datetime.now().isoformat()))
        
        await db.commit()
        print("Тестовые данные добавлены!")

if __name__ == '__main__':
    asyncio.run(init_database())