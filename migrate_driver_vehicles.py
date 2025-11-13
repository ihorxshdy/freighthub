#!/usr/bin/env python3
"""
Миграция: Перенос типов машин из users.truck_type в driver_vehicles
Для всех водителей, у которых есть truck_type, но нет записей в driver_vehicles
"""
import sqlite3
import sys
from datetime import datetime

def migrate_driver_vehicles(db_path):
    """Мигрировать типы машин водителей"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Находим водителей с truck_type, но без записей в driver_vehicles
    cursor.execute("""
        SELECT u.id, u.truck_type
        FROM users u
        WHERE u.role = 'driver' 
          AND u.truck_type IS NOT NULL
          AND NOT EXISTS (
              SELECT 1 FROM driver_vehicles dv 
              WHERE dv.driver_id = u.id AND dv.truck_type = u.truck_type
          )
    """)
    
    drivers_to_migrate = cursor.fetchall()
    
    if not drivers_to_migrate:
        print("✅ Нет водителей для миграции")
        conn.close()
        return
    
    print(f"Найдено водителей для миграции: {len(drivers_to_migrate)}")
    
    # Добавляем записи в driver_vehicles
    migrated = 0
    for driver_id, truck_type in drivers_to_migrate:
        try:
            cursor.execute("""
                INSERT INTO driver_vehicles (driver_id, truck_type, is_primary, created_at)
                VALUES (?, ?, TRUE, ?)
            """, (driver_id, truck_type, datetime.now().isoformat()))
            migrated += 1
            print(f"  ✅ Водитель ID={driver_id}, truck_type={truck_type}")
        except sqlite3.IntegrityError:
            print(f"  ⚠️  Пропущен водитель ID={driver_id} (запись уже существует)")
    
    conn.commit()
    conn.close()
    
    print(f"\n✅ Миграция завершена: {migrated} из {len(drivers_to_migrate)} водителей")

if __name__ == '__main__':
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        db_path = '/app/data/delivery.db'  # Путь по умолчанию для Docker
    
    print(f"База данных: {db_path}")
    migrate_driver_vehicles(db_path)
