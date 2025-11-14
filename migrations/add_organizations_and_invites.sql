-- Таблица организаций
CREATE TABLE IF NOT EXISTS organizations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица инвайт-кодов
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
);

-- Добавляем поле organization_id в таблицу users
ALTER TABLE users ADD COLUMN organization_id INTEGER DEFAULT NULL;
ALTER TABLE users ADD COLUMN invite_code_id INTEGER DEFAULT NULL;

-- Создаём индексы для быстрого поиска
CREATE INDEX IF NOT EXISTS idx_invite_codes_code ON invite_codes(code);
CREATE INDEX IF NOT EXISTS idx_invite_codes_organization ON invite_codes(organization_id);
CREATE INDEX IF NOT EXISTS idx_invite_codes_telegram_id ON invite_codes(used_by_telegram_id);
CREATE INDEX IF NOT EXISTS idx_users_organization ON users(organization_id);

-- Создаём организацию по умолчанию для существующих пользователей
INSERT INTO organizations (name, description, is_active) 
VALUES ('Default Organization', 'Автоматически созданная организация для существующих пользователей', 1);

-- Привязываем всех существующих пользователей к дефолтной организации
UPDATE users SET organization_id = 1 WHERE organization_id IS NULL;
