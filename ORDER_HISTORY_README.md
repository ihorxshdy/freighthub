# Система отслеживания истории заказов FreightHub

## Обзор

Система логирования обеспечивает полный аудит всех изменений заказов с информацией о пользователе, времени и деталях изменения.

## Структура данных

### Таблица `order_history`

Хранит все изменения заказов:

```sql
CREATE TABLE order_history (
    id INTEGER PRIMARY KEY,
    order_id INTEGER NOT NULL,           -- ID заказа
    user_id INTEGER,                     -- ID пользователя
    user_telegram_id INTEGER,            -- Telegram ID пользователя
    user_name TEXT,                      -- Имя пользователя
    user_role TEXT,                      -- Роль (customer/driver)
    action TEXT NOT NULL,                -- Тип действия
    field_name TEXT,                     -- Имя измененного поля
    old_value TEXT,                      -- Старое значение
    new_value TEXT,                      -- Новое значение
    description TEXT,                    -- Описание изменения
    ip_address TEXT,                     -- IP адрес
    user_agent TEXT,                     -- User-Agent браузера
    created_at TIMESTAMP                 -- Время изменения
);
```

### Представление `v_order_history`

Объединяет историю с данными заказа и пользователей:

```sql
CREATE VIEW v_order_history AS
SELECT 
    oh.*,
    o.customer_id,
    o.status as order_status,
    o.truck_type,
    o.pickup_address,
    o.delivery_address,
    customer.name as customer_name,
    customer.telegram_id as customer_telegram_id
FROM order_history oh
JOIN orders o ON oh.order_id = o.id
LEFT JOIN users customer ON o.customer_id = customer.id;
```

## Типы действий

```python
ACTION_CREATED = 'created'                    # Создание заказа
ACTION_UPDATED = 'updated'                    # Обновление заказа
ACTION_STATUS_CHANGED = 'status_changed'      # Изменение статуса
ACTION_BID_ADDED = 'bid_added'               # Добавлено предложение
ACTION_WINNER_SELECTED = 'winner_selected'    # Выбран исполнитель
ACTION_CONFIRMED_CUSTOMER = 'confirmed_customer'  # Подтверждение заказчиком
ACTION_CONFIRMED_DRIVER = 'confirmed_driver'      # Подтверждение водителем
ACTION_CANCELLED = 'cancelled'               # Отмена заказа
ACTION_COMPLETED = 'completed'               # Завершение заказа
ACTION_PRICE_CHANGED = 'price_changed'       # Изменение цены
```

## API Endpoints

### 1. История конкретного заказа

```http
GET /api/orders/{order_id}/history
```

**Пример запроса:**
```bash
curl http://your-domain.com/api/orders/123/history
```

**Ответ:**
```json
[
  {
    "id": 1,
    "order_id": 123,
    "user_id": 5,
    "user_telegram_id": 1955229007,
    "user_name": "Иван Иванов",
    "user_role": "customer",
    "action": "created",
    "field_name": null,
    "old_value": null,
    "new_value": "truck_type: gazel_closed_15m3, price: 5000",
    "description": "Заказ создан: Доставка мебели...",
    "ip_address": "192.168.1.1",
    "user_agent": "Mozilla/5.0...",
    "created_at": "2025-11-11 10:30:00",
    "customer_name": "Иван Иванов",
    "order_status": "active"
  }
]
```

### 2. Общая история с фильтрами

```http
GET /api/history?order_id={id}&user_id={id}&limit={number}
```

**Параметры:**
- `order_id` (опционально) - фильтр по заказу
- `user_id` (опционально) - фильтр по пользователю
- `limit` (по умолчанию 100) - количество записей

**Пример запроса:**
```bash
# Все изменения конкретного пользователя
curl "http://your-domain.com/api/history?user_id=5&limit=50"

# Последние 20 изменений
curl "http://your-domain.com/api/history?limit=20"
```

### 3. Все заказы с историей (Админ)

```http
GET /api/admin/orders/full
```

**Описание:** Возвращает все заказы с полной историей изменений каждого.

**Пример запроса:**
```bash
curl http://your-domain.com/api/admin/orders/full
```

**Ответ:**
```json
[
  {
    "id": 123,
    "customer_id": 5,
    "status": "completed",
    "truck_type": "gazel_closed_15m3",
    "pickup_address": "Москва, ул. Ленина, 1",
    "delivery_address": "Москва, ул. Пушкина, 10",
    "customer_name": "Иван Иванов",
    "driver_name": "Петр Петров",
    "history": [
      {
        "action": "created",
        "description": "Заказ создан",
        "created_at": "2025-11-11 10:30:00",
        "user_name": "Иван Иванов"
      },
      {
        "action": "bid_added",
        "description": "Добавлено предложение: 4500₽",
        "created_at": "2025-11-11 10:35:00",
        "user_name": "Петр Петров"
      },
      {
        "action": "winner_selected",
        "description": "Выбран исполнитель",
        "created_at": "2025-11-11 10:40:00",
        "user_name": "Иван Иванов"
      }
    ]
  }
]
```

## Использование в коде

### Логирование изменений

```python
from order_logger import log_order_change, ACTION_CREATED, ACTION_STATUS_CHANGED

# При создании заказа
log_order_change(
    conn, 
    order_id=123, 
    user_id=5, 
    action=ACTION_CREATED,
    description="Заказ создан: Доставка мебели",
    new_value="truck_type: gazel_closed_15m3, price: 5000"
)

# При изменении статуса
log_order_change(
    conn,
    order_id=123,
    user_id=5,
    action=ACTION_STATUS_CHANGED,
    field_name="status",
    old_value="active",
    new_value="in_progress",
    description="Статус изменен на 'В процессе'"
)

# При выборе исполнителя
log_order_change(
    conn,
    order_id=123,
    user_id=5,
    action=ACTION_WINNER_SELECTED,
    description=f"Выбран исполнитель: Петр Петров (цена: 4500₽)"
)
```

### Получение истории

```python
from order_logger import get_order_history

# История конкретного заказа
history = get_order_history(conn, order_id=123)

# История действий пользователя
history = get_order_history(conn, user_id=5)

# Последние 50 изменений
history = get_order_history(conn, limit=50)
```

## SQL запросы для анализа

### Все изменения заказа

```sql
SELECT * FROM v_order_history 
WHERE order_id = 123 
ORDER BY created_at;
```

### Действия конкретного пользователя

```sql
SELECT * FROM v_order_history 
WHERE user_telegram_id = 1955229007 
ORDER BY created_at DESC;
```

### Статистика по действиям

```sql
SELECT action, COUNT(*) as count 
FROM order_history 
GROUP BY action 
ORDER BY count DESC;
```

### Активность по дням

```sql
SELECT DATE(created_at) as date, 
       COUNT(*) as actions_count,
       COUNT(DISTINCT order_id) as orders_count,
       COUNT(DISTINCT user_id) as users_count
FROM order_history 
GROUP BY DATE(created_at) 
ORDER BY date DESC;
```

### Последние действия

```sql
SELECT * FROM v_order_history 
ORDER BY created_at DESC 
LIMIT 20;
```

### Изменения за период

```sql
SELECT * FROM v_order_history 
WHERE created_at >= '2025-11-01 00:00:00' 
  AND created_at <= '2025-11-30 23:59:59'
ORDER BY created_at;
```

## Безопасность

### Рекомендации:

1. **Ограничение доступа к админ endpoint:**
   ```python
   # Добавьте проверку ключа
   admin_key = request.headers.get('X-Admin-Key')
   if admin_key != os.environ.get('ADMIN_KEY'):
       return jsonify({'error': 'Unauthorized'}), 401
   ```

2. **Ротация данных:**
   ```sql
   -- Архивация старых записей (старше 6 месяцев)
   INSERT INTO order_history_archive 
   SELECT * FROM order_history 
   WHERE created_at < date('now', '-6 months');
   
   DELETE FROM order_history 
   WHERE created_at < date('now', '-6 months');
   ```

3. **Индексы для производительности:**
   ```sql
   -- Уже созданы при миграции
   CREATE INDEX idx_order_history_order_id ON order_history(order_id);
   CREATE INDEX idx_order_history_user_id ON order_history(user_id);
   CREATE INDEX idx_order_history_created_at ON order_history(created_at);
   ```

## Мониторинг

### Размер таблицы

```sql
SELECT COUNT(*) as total_records,
       COUNT(DISTINCT order_id) as unique_orders,
       COUNT(DISTINCT user_id) as unique_users
FROM order_history;
```

### Средние изменения на заказ

```sql
SELECT AVG(changes_count) as avg_changes_per_order
FROM (
    SELECT order_id, COUNT(*) as changes_count 
    FROM order_history 
    GROUP BY order_id
);
```

## Примеры использования

### Отследить путь заказа

```python
# Python
history = get_order_history(conn, order_id=123)
for entry in history:
    print(f"{entry['created_at']} | {entry['action']} | {entry['user_name']} | {entry['description']}")
```

```sql
-- SQL
SELECT created_at, action, user_name, description
FROM v_order_history
WHERE order_id = 123
ORDER BY created_at;
```

### Найти все отмененные заказы

```sql
SELECT DISTINCT order_id, customer_name, description, created_at
FROM v_order_history
WHERE action = 'cancelled'
ORDER BY created_at DESC;
```

### Активность водителя

```sql
SELECT 
    user_name,
    COUNT(*) as total_actions,
    COUNT(DISTINCT order_id) as orders_participated,
    MIN(created_at) as first_action,
    MAX(created_at) as last_action
FROM v_order_history
WHERE user_role = 'driver' AND user_id = 5
GROUP BY user_name;
```

## Миграция

Для применения на существующей БД:

```bash
# Локально
python migrations/apply_order_history.py

# На сервере
docker exec freighthub-webapp python /app/migrations/apply_order_history.py
```

## Поддержка

При возникновении вопросов или проблем обращайтесь к разработчику.
