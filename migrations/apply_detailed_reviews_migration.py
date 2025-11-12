#!/usr/bin/env python3
"""
Миграция: Расширенная система отзывов
Добавляет детальные критерии оценки, комплименты и публичные комментарии
"""
import sqlite3
import sys
import os

# Добавляем путь к конфигурации
sys.path.insert(0, '/app')
from truck_config import DATABASE_PATH

def apply_migration():
    """Применить миграцию для расширенной системы отзывов"""
    print("🔄 Начинаем миграцию расширенной системы отзывов...")
    
    conn = sqlite3.connect(DATABASE_PATH, timeout=30.0)
    cursor = conn.cursor()
    
    try:
        # Проверяем существующие колонки
        cursor.execute("PRAGMA table_info(reviews)")
        existing_columns = {row[1] for row in cursor.fetchall()}
        print(f"✅ Существующие колонки: {existing_columns}")
        
        # Добавляем новые колонки если их нет
        new_columns = [
            ('punctuality_rating', 'INTEGER'),
            ('quality_rating', 'INTEGER'),
            ('professionalism_rating', 'INTEGER'),
            ('communication_rating', 'INTEGER'),
            ('vehicle_condition_rating', 'INTEGER'),
            ('badges', 'TEXT'),
            ('is_public', 'BOOLEAN DEFAULT TRUE'),
            ('response_text', 'TEXT'),
            ('response_at', 'TIMESTAMP'),
            ('helpful_count', 'INTEGER DEFAULT 0'),
            ('not_helpful_count', 'INTEGER DEFAULT 0')
        ]
        
        for column_name, column_type in new_columns:
            if column_name not in existing_columns:
                print(f"➕ Добавляем колонку: {column_name}")
                cursor.execute(f"ALTER TABLE reviews ADD COLUMN {column_name} {column_type}")
            else:
                print(f"⏭️  Колонка {column_name} уже существует")
        
        # Создаём таблицу для полезности отзывов
        print("📊 Создаём таблицу review_helpfulness...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS review_helpfulness (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                review_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                is_helpful BOOLEAN NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (review_id) REFERENCES reviews (id),
                FOREIGN KEY (user_id) REFERENCES users (id),
                UNIQUE(review_id, user_id)
            )
        """)
        
        # Создаём индексы
        print("🔍 Создаём индексы...")
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_reviews_reviewee ON reviews(reviewee_id)",
            "CREATE INDEX IF NOT EXISTS idx_reviews_rating ON reviews(rating)",
            "CREATE INDEX IF NOT EXISTS idx_reviews_public ON reviews(is_public)",
            "CREATE INDEX IF NOT EXISTS idx_review_helpfulness_review ON review_helpfulness(review_id)"
        ]
        
        for index_sql in indexes:
            cursor.execute(index_sql)
            print(f"✅ Индекс создан")
        
        conn.commit()
        print("✅ Миграция успешно применена!")
        
        # Показываем итоговую структуру
        cursor.execute("PRAGMA table_info(reviews)")
        all_columns = cursor.fetchall()
        print("\n📋 Итоговая структура таблицы reviews:")
        for col in all_columns:
            print(f"  - {col[1]}: {col[2]}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при миграции: {e}")
        conn.rollback()
        return False
        
    finally:
        conn.close()

if __name__ == '__main__':
    success = apply_migration()
    sys.exit(0 if success else 1)
