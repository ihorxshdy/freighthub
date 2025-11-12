#!/usr/bin/env python3
"""
Миграция: добавление информации о сторонах заказа в таблицу order_history
"""
import sqlite3
import sys

def apply_migration(db_path='/app/data/delivery.db'):
    """Применить миграцию к базе данных"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🔄 Добавление колонок информации о заказчике...")
        
        # Проверяем существование колонок перед добавлением
        columns_to_add = [
            ('customer_id', 'INTEGER'),
            ('customer_telegram_id', 'INTEGER'),
            ('customer_name', 'TEXT'),
            ('customer_phone', 'TEXT'),
            ('driver_id', 'INTEGER'),
            ('driver_telegram_id', 'INTEGER'),
            ('driver_name', 'TEXT'),
            ('driver_phone', 'TEXT')
        ]
        
        # Получаем существующие колонки
        cursor.execute("PRAGMA table_info(order_history)")
        existing_columns = {row[1] for row in cursor.fetchall()}
        
        for col_name, col_type in columns_to_add:
            if col_name not in existing_columns:
                print(f"  ✅ Добавление колонки {col_name}...")
                cursor.execute(f"ALTER TABLE order_history ADD COLUMN {col_name} {col_type}")
            else:
                print(f"  ⏭️  Колонка {col_name} уже существует")
        
        conn.commit()
        
        print("🔄 Пересоздание представления v_order_history...")
        
        # Удаляем старое представление
        cursor.execute("DROP VIEW IF EXISTS v_order_history")
        
        # Создаем новое представление с дополнительными полями
        cursor.execute('''
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
                -- Информация о заказчике
                oh.customer_id,
                oh.customer_telegram_id,
                oh.customer_name,
                oh.customer_phone,
                -- Информация о водителе
                oh.driver_id,
                oh.driver_telegram_id,
                oh.driver_name,
                oh.driver_phone,
                -- Данные заказа
                o.status as order_status,
                o.truck_type,
                o.pickup_address,
                o.delivery_address
            FROM order_history oh
            JOIN orders o ON oh.order_id = o.id
            ORDER BY oh.created_at DESC
        ''')
        
        conn.commit()
        
        print("✅ Миграция успешно применена!")
        print(f"📊 Колонки добавлены: {len([c for c in columns_to_add if c[0] not in existing_columns])}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при применении миграции: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    db_path = sys.argv[1] if len(sys.argv) > 1 else '/app/data/delivery.db'
    success = apply_migration(db_path)
    sys.exit(0 if success else 1)
