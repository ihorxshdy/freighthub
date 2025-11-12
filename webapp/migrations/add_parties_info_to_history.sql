-- Добавление информации о сторонах заказа в таблицу order_history

-- Информация о заказчике
ALTER TABLE order_history ADD COLUMN customer_id INTEGER;
ALTER TABLE order_history ADD COLUMN customer_telegram_id INTEGER;
ALTER TABLE order_history ADD COLUMN customer_name TEXT;
ALTER TABLE order_history ADD COLUMN customer_phone TEXT;

-- Информация о водителе (если назначен)
ALTER TABLE order_history ADD COLUMN driver_id INTEGER;
ALTER TABLE order_history ADD COLUMN driver_telegram_id INTEGER;
ALTER TABLE order_history ADD COLUMN driver_name TEXT;
ALTER TABLE order_history ADD COLUMN driver_phone TEXT;

-- Пересоздаем представление с новыми полями
DROP VIEW IF EXISTS v_order_history;

CREATE VIEW v_order_history AS
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
    -- Информация о заказчике
    oh.customer_id,
    oh.customer_telegram_id,
    oh.customer_name,
    oh.customer_phone,
    -- Информация о водителе
    oh.driver_id,
    oh.driver_telegram_id,
    oh.driver_name,
    oh.driver_phone,
    -- Данные заказа
    o.status as order_status,
    o.truck_type,
    o.pickup_address,
    o.delivery_address
FROM order_history oh
JOIN orders o ON oh.order_id = o.id
ORDER BY oh.created_at DESC;
