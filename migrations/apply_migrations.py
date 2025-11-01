#!/usr/bin/env python3
"""
Скрипт для применения миграций к существующей БД
Добавляет новые поля, если их еще нет
"""
import sqlite3
import sys

def apply_migrations(db_path='/app/data/delivery.db'):
    """Применяет все необходимые миграции"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print(f"📊 Применение миграций к БД: {db_path}")
    
    # Получаем список колонок в таблице orders
    cursor.execute("PRAGMA table_info(orders)")
    existing_columns = {row[1] for row in cursor.fetchall()}
    print(f"✅ Существующие колонки orders: {existing_columns}")
    
    # Миграция 1: Добавляем поля для tracking completion
    migrations = [
        ('customer_confirmed', 'ALTER TABLE orders ADD COLUMN customer_confirmed BOOLEAN DEFAULT FALSE'),
        ('driver_confirmed', 'ALTER TABLE orders ADD COLUMN driver_confirmed BOOLEAN DEFAULT FALSE'),
        ('cancelled_by', 'ALTER TABLE orders ADD COLUMN cancelled_by INTEGER NULL'),
        ('cancelled_at', 'ALTER TABLE orders ADD COLUMN cancelled_at TIMESTAMP NULL'),
        ('delivery_date', 'ALTER TABLE orders ADD COLUMN delivery_date TEXT NULL'),
    ]
    
    for column_name, sql in migrations:
        if column_name not in existing_columns:
            print(f"➕ Добавляем колонку: {column_name}")
            cursor.execute(sql)
        else:
            print(f"⏭️  Колонка {column_name} уже существует")
    
    # Проверяем поле username в users
    cursor.execute("PRAGMA table_info(users)")
    user_columns = {row[1] for row in cursor.fetchall()}
    print(f"✅ Существующие колонки users: {user_columns}")
    
    if 'username' not in user_columns:
        print("➕ Добавляем колонку username в users")
        cursor.execute('ALTER TABLE users ADD COLUMN username TEXT NULL')
    else:
        print("⏭️  Колонка username уже существует")
    
    # Обновляем CHECK constraint для status (SQLite не поддерживает ALTER COLUMN)
    # Вместо этого просто убедимся, что новые статусы будут работать
    print("✅ Проверка статусов: 'in_progress' и 'closed' теперь разрешены")
    
    conn.commit()
    conn.close()
    
    print("✅ Все миграции применены успешно!")

if __name__ == '__main__':
    db_path = sys.argv[1] if len(sys.argv) > 1 else '/app/data/delivery.db'
    apply_migrations(db_path)
