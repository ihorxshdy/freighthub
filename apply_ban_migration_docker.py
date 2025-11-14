#!/usr/bin/env python3
"""
Миграция для Docker контейнера - добавление поля is_banned
"""
import sqlite3

DB_PATH = '/app/data/delivery.db'

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Проверка существования поля
cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='users'")
users_schema = cursor.fetchone()[0]

if 'is_banned' not in users_schema:
    print('Добавление поля is_banned...')
    cursor.execute('ALTER TABLE users ADD COLUMN is_banned INTEGER DEFAULT 0')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_banned ON users(is_banned)')
    conn.commit()
    print('✅ Поле is_banned добавлено')
else:
    print('✅ Поле is_banned уже существует')

conn.close()
