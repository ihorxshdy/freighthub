-- Миграция для добавления системы фотофиксации этапов доставки
-- Создана: 2025-11-12

-- Таблица для хранения фотографий заказов
CREATE TABLE IF NOT EXISTS order_photos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    photo_type TEXT NOT NULL CHECK(photo_type IN ('loading', 'unloading')),
    file_path TEXT NOT NULL,
    telegram_file_id TEXT,
    uploaded_by INTEGER NOT NULL,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (uploaded_by) REFERENCES users(id)
);

-- Индексы для быстрого поиска
CREATE INDEX IF NOT EXISTS idx_order_photos_order_id ON order_photos(order_id);
CREATE INDEX IF NOT EXISTS idx_order_photos_type ON order_photos(photo_type);

-- Добавление новых колонок в таблицу orders для отслеживания этапов
-- loading_confirmed_at - время подтверждения загрузки водителем
-- unloading_confirmed_at - время подтверждения выгрузки водителем  
-- driver_completed_at - время подтверждения выполнения водителем
ALTER TABLE orders ADD COLUMN loading_confirmed_at TIMESTAMP;
ALTER TABLE orders ADD COLUMN unloading_confirmed_at TIMESTAMP;
ALTER TABLE orders ADD COLUMN driver_completed_at TIMESTAMP;
