#!/usr/bin/env python3
"""
Миграция для добавления системы чата между заказчиком и водителем
"""
import sqlite3
import sys

def apply_migration(db_path='/app/data/delivery.db'):
    """Применить миграцию для добавления таблицы сообщений чата"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("🔄 Начинаем миграцию для добавления системы чата...")
        
        # Проверяем существование таблицы order_messages
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='order_messages'
        """)
        
        if cursor.fetchone():
            print("ℹ️  Таблица order_messages уже существует")
        else:
            # Создаем таблицу сообщений чата
            cursor.execute("""
                CREATE TABLE order_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id INTEGER NOT NULL,
                    sender_id INTEGER NOT NULL,
                    message_text TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    read_by_customer BOOLEAN DEFAULT FALSE,
                    read_by_driver BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
                    FOREIGN KEY (sender_id) REFERENCES users(id)
                )
            """)
            print("✅ Таблица order_messages создана")
            
            # Создаем индексы для быстрого поиска
            cursor.execute("""
                CREATE INDEX idx_order_messages_order_id ON order_messages(order_id)
            """)
            cursor.execute("""
                CREATE INDEX idx_order_messages_created_at ON order_messages(created_at)
            """)
            cursor.execute("""
                CREATE INDEX idx_order_messages_unread ON order_messages(read_by_customer, read_by_driver)
            """)
            print("✅ Индексы созданы")
        
        conn.commit()
        print("✅ Миграция успешно применена!")
        
    except Exception as e:
        print(f"❌ Ошибка при применении миграции: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()

if __name__ == '__main__':
    db_path = sys.argv[1] if len(sys.argv) > 1 else '/app/data/delivery.db'
    apply_migration(db_path)
