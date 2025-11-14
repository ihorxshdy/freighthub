-- Миграция: Добавление поля is_banned для блокировки пользователей

ALTER TABLE users ADD COLUMN is_banned INTEGER DEFAULT 0;

CREATE INDEX IF NOT EXISTS idx_users_banned ON users(is_banned);
