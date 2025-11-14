-- Добавление колонок для админ-панели
-- is_banned: блокировка пользователя
-- organization_id: привязка к организации
-- invite_code_id: привязка к инвайт-коду

ALTER TABLE users ADD COLUMN is_banned INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN organization_id INTEGER;
ALTER TABLE users ADD COLUMN invite_code_id INTEGER;

-- Создание таблицы организаций
CREATE TABLE IF NOT EXISTS organizations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Создание таблицы инвайт-кодов
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
);
