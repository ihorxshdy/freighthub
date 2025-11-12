#!/usr/bin/env python3
"""
Применение миграции для добавления системы фотофиксации
"""
import sqlite3
import sys

def apply_migration(db_path='/app/data/delivery.db'):
    """Применить миграцию"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("🔄 Начинаем миграцию для добавления order_photos...")
        
        # Проверяем существование таблицы order_photos
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='order_photos'
        """)
        
        if cursor.fetchone():
            print("ℹ️  Таблица order_photos уже существует")
        else:
            # Создаем таблицу order_photos
            cursor.execute("""
                CREATE TABLE order_photos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id INTEGER NOT NULL,
                    photo_type TEXT NOT NULL CHECK(photo_type IN ('loading', 'unloading')),
                    file_path TEXT NOT NULL,
                    telegram_file_id TEXT,
                    uploaded_by INTEGER NOT NULL,
                    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
                    FOREIGN KEY (uploaded_by) REFERENCES users(id)
                )
            """)
            print("✅ Таблица order_photos создана")
            
            # Создаем индексы
            cursor.execute("""
                CREATE INDEX idx_order_photos_order_id ON order_photos(order_id)
            """)
            cursor.execute("""
                CREATE INDEX idx_order_photos_type ON order_photos(photo_type)
            """)
            print("✅ Индексы созданы")
        
        # Проверяем и добавляем колонки в orders
        cursor.execute("PRAGMA table_info(orders)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'loading_confirmed_at' not in columns:
            cursor.execute("ALTER TABLE orders ADD COLUMN loading_confirmed_at TIMESTAMP")
            print("✅ Добавлена колонка loading_confirmed_at")
        else:
            print("ℹ️  Колонка loading_confirmed_at уже существует")
            
        if 'unloading_confirmed_at' not in columns:
            cursor.execute("ALTER TABLE orders ADD COLUMN unloading_confirmed_at TIMESTAMP")
            print("✅ Добавлена колонка unloading_confirmed_at")
        else:
            print("ℹ️  Колонка unloading_confirmed_at уже существует")
            
        if 'driver_completed_at' not in columns:
            cursor.execute("ALTER TABLE orders ADD COLUMN driver_completed_at TIMESTAMP")
            print("✅ Добавлена колонка driver_completed_at")
        else:
            print("ℹ️  Колонка driver_completed_at уже существует")
        
        conn.commit()
        print("✅ Миграция успешно применена!")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Ошибка при применении миграции: {e}")
        sys.exit(1)
    finally:
        conn.close()

if __name__ == '__main__':
    db_path = sys.argv[1] if len(sys.argv) > 1 else '/app/data/delivery.db'
    apply_migration(db_path)
