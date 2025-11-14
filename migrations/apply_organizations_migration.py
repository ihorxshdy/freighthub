#!/usr/bin/env python3
"""
Миграция: Добавление системы организаций и инвайт-кодов
"""
import sqlite3
import sys
import os

# Добавляем путь к корню проекта
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def apply_migration(db_path):
    """Применяет миграцию к базе данных"""
    print(f"Применение миграции к {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Проверяем, была ли миграция уже применена
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='organizations'")
        if cursor.fetchone():
            print("Миграция уже применена. Пропускаем...")
            conn.close()
            return
        
        print("Создание таблицы organizations...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS organizations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        print("Создание таблицы invite_codes...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS invite_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL UNIQUE,
                organization_id INTEGER NOT NULL,
                used_by_telegram_id INTEGER DEFAULT NULL,
                used_at TIMESTAMP DEFAULT NULL,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP DEFAULT NULL,
                FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE
            )
        """)
        
        print("Проверка существования столбцов в users...")
        cursor.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'organization_id' not in columns:
            print("Добавление organization_id в users...")
            cursor.execute("ALTER TABLE users ADD COLUMN organization_id INTEGER DEFAULT NULL")
        
        if 'invite_code_id' not in columns:
            print("Добавление invite_code_id в users...")
            cursor.execute("ALTER TABLE users ADD COLUMN invite_code_id INTEGER DEFAULT NULL")
        
        print("Создание индексов...")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_invite_codes_code ON invite_codes(code)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_invite_codes_organization ON invite_codes(organization_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_invite_codes_telegram_id ON invite_codes(used_by_telegram_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_organization ON users(organization_id)")
        
        print("Создание организации по умолчанию...")
        cursor.execute("""
            INSERT INTO organizations (name, description, is_active) 
            VALUES ('Default Organization', 'Автоматически созданная организация для существующих пользователей', 1)
        """)
        
        print("Привязка существующих пользователей к дефолтной организации...")
        cursor.execute("UPDATE users SET organization_id = 1 WHERE organization_id IS NULL")
        
        conn.commit()
        print("✅ Миграция успешно применена!")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Ошибка при применении миграции: {e}")
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    # Применяем к БД webapp
    webapp_db = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'webapp', 'delivery.db')
    if os.path.exists(webapp_db):
        apply_migration(webapp_db)
    
    # Применяем к БД telegram-bot
    bot_db = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'telegram-bot', 'database', 'delivery.db')
    if os.path.exists(bot_db):
        apply_migration(bot_db)
    
    # Применяем к shared БД (если используется)
    shared_db = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'telegram-bot', 'database', 'data', 'delivery.db')
    if os.path.exists(shared_db):
        apply_migration(shared_db)
    
    print("\n✅ Все миграции применены!")
