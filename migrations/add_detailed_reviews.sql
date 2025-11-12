-- Миграция: Расширенная система отзывов с детальными критериями и комплиментами
-- Дата: 2025-11-12

-- Добавляем новые поля к существующей таблице reviews
ALTER TABLE reviews ADD COLUMN punctuality_rating INTEGER CHECK (punctuality_rating >= 1 AND punctuality_rating <= 5);
ALTER TABLE reviews ADD COLUMN quality_rating INTEGER CHECK (quality_rating >= 1 AND quality_rating <= 5);
ALTER TABLE reviews ADD COLUMN professionalism_rating INTEGER CHECK (professionalism_rating >= 1 AND professionalism_rating <= 5);
ALTER TABLE reviews ADD COLUMN communication_rating INTEGER CHECK (communication_rating >= 1 AND communication_rating <= 5);
ALTER TABLE reviews ADD COLUMN vehicle_condition_rating INTEGER CHECK (vehicle_condition_rating >= 1 AND vehicle_condition_rating <= 5);

-- Комплименты (JSON array со значками)
ALTER TABLE reviews ADD COLUMN badges TEXT; -- JSON: ["super_driver", "fast_delivery", "careful_handling"]

-- Публичный комментарий и ответ на него
ALTER TABLE reviews ADD COLUMN is_public BOOLEAN DEFAULT TRUE;
ALTER TABLE reviews ADD COLUMN response_text TEXT; -- Ответ на отзыв
ALTER TABLE reviews ADD COLUMN response_at TIMESTAMP; -- Когда был дан ответ

-- Полезность отзыва (для других пользователей)
ALTER TABLE reviews ADD COLUMN helpful_count INTEGER DEFAULT 0;
ALTER TABLE reviews ADD COLUMN not_helpful_count INTEGER DEFAULT 0;

-- Таблица для отслеживания кто отметил отзыв как полезный
CREATE TABLE IF NOT EXISTS review_helpfulness (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    review_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    is_helpful BOOLEAN NOT NULL, -- TRUE = helpful, FALSE = not helpful
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (review_id) REFERENCES reviews (id),
    FOREIGN KEY (user_id) REFERENCES users (id),
    UNIQUE(review_id, user_id)
);

-- Индексы для производительности
CREATE INDEX IF NOT EXISTS idx_reviews_reviewee ON reviews(reviewee_id);
CREATE INDEX IF NOT EXISTS idx_reviews_rating ON reviews(rating);
CREATE INDEX IF NOT EXISTS idx_reviews_public ON reviews(is_public);
CREATE INDEX IF NOT EXISTS idx_review_helpfulness_review ON review_helpfulness(review_id);
