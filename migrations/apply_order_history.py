#!/usr/bin/env python3
"""
Миграция: Добавление таблицы истории изменений заказов
"""
import sqlite3
import sys
import os

# Путь к базе данных
DB_PATH = os.environ.get('DATABASE_PATH', '/app/data/delivery.db')

def apply_migration():
    """Применить миграцию"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Создаем таблицу истории
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS order_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                user_id INTEGER,
                user_telegram_id INTEGER,
                user_name TEXT,
                user_role TEXT,
                action TEXT NOT NULL,
                field_name TEXT,
                old_value TEXT,
                new_value TEXT,
                description TEXT,
                ip_address TEXT,
                user_agent TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (order_id) REFERENCES orders (id),
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        
        # Создаем индексы
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_order_history_order_id ON order_history(order_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_order_history_user_id ON order_history(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_order_history_action ON order_history(action)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_order_history_created_at ON order_history(created_at)")
        
        # Создаем представление
        cursor.execute("DROP VIEW IF EXISTS v_order_history")
        cursor.execute("""
            CREATE VIEW v_order_history AS
            SELECT 
                oh.id,
                oh.order_id,
                oh.user_id,
                oh.user_telegram_id,
                oh.user_name,
                oh.user_role,
                oh.action,
                oh.field_name,
                oh.old_value,
                oh.new_value,
                oh.description,
                oh.ip_address,
                oh.user_agent,
                oh.created_at,
                o.customer_id,
                o.status as order_status,
                o.truck_type,
                o.pickup_address,
                o.delivery_address,
                customer.name as customer_name,
                customer.telegram_id as customer_telegram_id
            FROM order_history oh
            JOIN orders o ON oh.order_id = o.id
            LEFT JOIN users customer ON o.customer_id = customer.id
            ORDER BY oh.created_at DESC
        """)
        
        conn.commit()
        print("✅ Миграция успешно применена!")
        print("   - Создана таблица order_history")
        print("   - Созданы индексы для быстрого поиска")
        print("   - Создано представление v_order_history")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Ошибка применения миграции: {e}")
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    apply_migration()
