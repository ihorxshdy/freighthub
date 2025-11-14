#!/usr/bin/env python3
"""
Применение миграции: добавление функций админ-панели
"""
import sqlite3
import os

# Путь к БД в production (Docker volume)
DATABASE_PATH = '/app/data/delivery.db'

# Для локального запуска
if not os.path.exists(DATABASE_PATH):
    DATABASE_PATH = 'telegram-bot/database/delivery.db'
    if not os.path.exists(DATABASE_PATH):
        DATABASE_PATH = '../telegram-bot/database/delivery.db'

def apply_migration():
    """Применить миграцию"""
    print(f"Применение миграции к БД: {DATABASE_PATH}")
    
    conn = sqlite3.connect(DATABASE_PATH)
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA busy_timeout=30000')
    cursor = conn.cursor()
    
    try:
        # Проверяем, есть ли уже колонка is_banned
        cursor.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'is_banned' not in columns:
            print("Добавление колонки is_banned...")
            cursor.execute("ALTER TABLE users ADD COLUMN is_banned INTEGER DEFAULT 0")
        else:
            print("Колонка is_banned уже существует")
        
        if 'organization_id' not in columns:
            print("Добавление колонки organization_id...")
            cursor.execute("ALTER TABLE users ADD COLUMN organization_id INTEGER")
        else:
            print("Колонка organization_id уже существует")
        
        if 'invite_code_id' not in columns:
            print("Добавление колонки invite_code_id...")
            cursor.execute("ALTER TABLE users ADD COLUMN invite_code_id INTEGER")
        else:
            print("Колонка invite_code_id уже существует")
        
        # Создание таблицы организаций
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS organizations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("Таблица organizations создана/проверена")
        
        # Создание таблицы инвайт-кодов
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS invite_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL UNIQUE,
                organization_id INTEGER NOT NULL,
                uses_limit INTEGER,
                uses_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE,
                FOREIGN KEY (organization_id) REFERENCES organizations (id)
            )
        """)
        print("Таблица invite_codes создана/проверена")
        
        conn.commit()
        print("Миграция успешно применена!")
        
    except Exception as e:
        conn.rollback()
        print(f"Ошибка при применении миграции: {e}")
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    apply_migration()
