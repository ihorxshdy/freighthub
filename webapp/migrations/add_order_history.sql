-- Таблица для истории изменений заказов
CREATE TABLE IF NOT EXISTS order_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    user_id INTEGER,
    user_telegram_id INTEGER,
    user_name TEXT,
    user_role TEXT,
    action TEXT NOT NULL,
    field_name TEXT,
    old_value TEXT,
    new_value TEXT,
    description TEXT,
    ip_address TEXT,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders (id),
    FOREIGN KEY (user_id) REFERENCES users (id)
);

-- Индексы для быстрого поиска
CREATE INDEX IF NOT EXISTS idx_order_history_order_id ON order_history(order_id);
CREATE INDEX IF NOT EXISTS idx_order_history_user_id ON order_history(user_id);
CREATE INDEX IF NOT EXISTS idx_order_history_action ON order_history(action);
CREATE INDEX IF NOT EXISTS idx_order_history_created_at ON order_history(created_at);

-- Представление для удобного просмотра истории с полными данными пользователя
CREATE VIEW IF NOT EXISTS v_order_history AS
SELECT 
    oh.id,
    oh.order_id,
    oh.user_id,
    oh.user_telegram_id,
    oh.user_name,
    oh.user_role,
    oh.action,
    oh.field_name,
    oh.old_value,
    oh.new_value,
    oh.description,
    oh.ip_address,
    oh.user_agent,
    oh.created_at,
    o.customer_id,
    o.status as order_status,
    o.truck_type,
    o.pickup_address,
    o.delivery_address,
    customer.name as customer_name,
    customer.telegram_id as customer_telegram_id
FROM order_history oh
JOIN orders o ON oh.order_id = o.id
LEFT JOIN users customer ON o.customer_id = customer.id
ORDER BY oh.created_at DESC;
