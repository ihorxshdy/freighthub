"""
Инициализация базы данных для webapp
ВНИМАНИЕ: Webapp использует ОБЩУЮ БД с ботом!
Этот файл НЕ НУЖЕН локально, т.к. бот создает БД.
Используется только на проде если нужно создать БД вручную.
"""
import sqlite3
import os
from truck_config import DATABASE_PATH

def init_database():
    """
    Создание таблиц базы данных по схеме БОТА
    Используется только на проде для инициализации общей БД
    """
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Таблица пользователей (схема как в боте)
    cursor.execute("""
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
    
    # Таблица заявок (схема как в боте)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            truck_type TEXT NOT NULL,
            cargo_description TEXT NOT NULL,
            delivery_address TEXT NOT NULL,
            status TEXT DEFAULT 'active' CHECK (status IN ('active', 'in_progress', 'completed', 'cancelled', 'closed', 'no_offers')),
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
    
    # Таблица предложений водителей (схема как в боте)
    cursor.execute("""
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
    
    # Таблица машин водителей (схема как в боте)
    cursor.execute("""
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
    
    # Таблица для отслеживания сообщений заявок (схема как в боте)
    cursor.execute("""
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
    
    conn.commit()
    conn.close()
    print(f"База данных создана: {DATABASE_PATH}")

if __name__ == '__main__':
    init_database()
