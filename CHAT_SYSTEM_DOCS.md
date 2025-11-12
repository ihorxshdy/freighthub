# Система внутреннего чата

## Описание

Система чата позволяет заказчику и водителю общаться внутри заказа в режиме реального времени. При получении нового сообщения второй участник получает уведомление в Telegram боте.

## Возможности

### Основные функции
- ✅ Обмен текстовыми сообщениями между заказчиком и водителем
- ✅ Уведомления в Telegram бот о новых сообщениях
- ✅ Отметка сообщений как прочитанных
- ✅ Автообновление чата каждые 3 секунды
- ✅ Счётчик непрочитанных сообщений (по заказам)
- ✅ Доступ только участникам заказа

### Ограничения
- Максимальная длина сообщения: 2000 символов
- Только текстовые сообщения (без файлов/изображений)
- Чат доступен только для заказов со статусом "in_progress"

## Архитектура

### База данных

**Таблица `order_messages`**:
```sql
CREATE TABLE order_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    sender_id INTEGER NOT NULL,
    message_text TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    read_by_customer BOOLEAN DEFAULT FALSE,
    read_by_driver BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (sender_id) REFERENCES users(id)
)
```

**Индексы**:
- `idx_order_messages_order_id` - поиск по заказу
- `idx_order_messages_created_at` - сортировка по времени
- `idx_order_messages_unread` - подсчёт непрочитанных

### API Endpoints

#### 1. Получение сообщений
```
GET /api/orders/{order_id}/messages?telegram_id={telegram_id}
```

**Ответ**:
```json
{
  "messages": [
    {
      "id": 1,
      "sender_id": 9,
      "sender_name": "Иван",
      "sender_role": "customer",
      "message_text": "Когда приедете?",
      "created_at": "2025-11-12 10:30:00",
      "read_by_customer": true,
      "read_by_driver": false,
      "is_mine": true
    }
  ],
  "unread_count": 2
}
```

#### 2. Отправка сообщения
```
POST /api/orders/{order_id}/messages
Content-Type: application/json

{
  "telegram_id": 123456789,
  "message_text": "Буду через 15 минут"
}
```

**Ответ**:
```json
{
  "success": true,
  "message": {
    "id": 2,
    "sender_id": 8,
    "sender_name": "Петр",
    "sender_role": "driver",
    "message_text": "Буду через 15 минут",
    "created_at": "2025-11-12 10:31:00",
    "read_by_customer": false,
    "read_by_driver": true,
    "is_mine": true
  }
}
```

#### 3. Отметить сообщения как прочитанные
```
POST /api/orders/{order_id}/messages/read
Content-Type: application/json

{
  "telegram_id": 123456789
}
```

#### 4. Получить счётчики непрочитанных
```
GET /api/orders/unread-messages-count?telegram_id={telegram_id}
```

**Ответ**:
```json
{
  "total_unread": 5,
  "unread_by_order": {
    "15": 2,
    "16": 3
  }
}
```

### Уведомления

При отправке сообщения автоматически отправляется webhook в Telegram бот:

```
POST http://telegram-bot:8080/webhook/new-chat-message
Authorization: Bearer {WEBHOOK_SECRET}
Content-Type: application/json

{
  "type": "new_chat_message",
  "order_id": 15,
  "sender_name": "Иван",
  "sender_role": "customer",
  "message_text": "Когда приедете?",
  "recipient_telegram_id": 987654321
}
```

Бот отправляет получателю уведомление:
```
💬 Новое сообщение от заказчика

📦 Заказ #15
👤 Иван: Когда приедете?

Откройте приложение для ответа
```

## UI Компоненты

### Кнопка открытия чата
В карточке заказа (для заказов in_progress):
- Заказчик видит: "💬 Чат с водителем"
- Водитель видит: "💬 Чат с заказчиком"

### Модальное окно чата

**Структура**:
```
┌─────────────────────────────────────┐
│ Чат с водителем              [×]    │
├─────────────────────────────────────┤
│                                     │
│  ┌───────────────────────────┐      │
│  │ Иван • Заказчик           │      │
│  │ ┌───────────────────────┐ │      │
│  │ │ Когда приедете?       │ │      │
│  │ └───────────────────────┘ │      │
│  │ 10:30                     │      │
│  └───────────────────────────┘      │
│                                     │
│      ┌───────────────────────────┐  │
│      │ Петр • Водитель           │  │
│      │ ┌───────────────────────┐ │  │
│      │ │ Буду через 15 минут   │ │  │
│      │ └───────────────────────┘ │  │
│      │                     10:31 │  │
│      └───────────────────────────┘  │
│                                     │
├─────────────────────────────────────┤
│ ┌────────────────────┬──────────┐   │
│ │ Введите сообщение..│ Отправить│   │
│ └────────────────────┴──────────┘   │
└─────────────────────────────────────┘
```

**Особенности**:
- Автопрокрутка вниз при новых сообщениях
- Автообновление каждые 3 секунды
- Различные цвета для своих/чужих сообщений
- Автоувеличение поля ввода (до 120px)
- Анимация появления новых сообщений

## Безопасность

### Контроль доступа
- Только участники заказа могут читать и писать сообщения
- Проверка по `telegram_id` в headers или query params
- Валидация принадлежности пользователя к заказу

### Валидация данных
- Максимальная длина сообщения: 2000 символов
- Обязательные поля при отправке
- Экранирование HTML в сообщениях

## Использование

### Для заказчика
1. Открыть заказ во вкладке "В процессе"
2. Нажать "💬 Чат с водителем"
3. Написать сообщение и отправить
4. Получить уведомление в боте при ответе водителя

### Для водителя
1. Открыть заказ во вкладке "В процессе"
2. Нажать "💬 Чат с заказчиком"
3. Написать сообщение и отправить
4. Получить уведомление в боте при ответе заказчика

## Примеры кода

### Открытие чата (JavaScript)
```javascript
openChat(orderId, recipientName, recipientRole);
```

### Отправка сообщения (JavaScript)
```javascript
const response = await fetch(`${API_BASE}api/orders/${orderId}/messages`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        telegram_id: telegram_id,
        message_text: messageText
    })
});
```

### Получение сообщений (Python)
```python
messages = conn.execute(
    '''SELECT m.id, m.message_text, m.created_at,
              u.name as sender_name
       FROM order_messages m
       JOIN users u ON m.sender_id = u.id
       WHERE m.order_id = ?
       ORDER BY m.created_at ASC''',
    (order_id,)
).fetchall()
```

## Развертывание

Миграция БД:
```bash
docker exec freighthub-webapp python /app/migrations/apply_chat_migration.py /app/data/delivery.db
```

## Будущие улучшения

- [ ] Отправка фотографий в чате
- [ ] Отправка геолокации
- [ ] История всех чатов пользователя
- [ ] Поиск по сообщениям
- [ ] Push-уведомления вместо polling
- [ ] WebSocket для мгновенного обновления
- [ ] Индикатор "печатает..."
- [ ] Прикрепление файлов/документов

## Troubleshooting

### Сообщения не отправляются
- Проверьте telegram_id в запросе
- Убедитесь что пользователь - участник заказа
- Проверьте логи: `docker logs freighthub-webapp`

### Уведомления не приходят
- Проверьте статус бота: `docker logs freighthub-bot`
- Убедитесь что WEBHOOK_SECRET совпадает
- Проверьте доступность webhook URL

### Чат не обновляется
- Проверьте консоль браузера на ошибки
- Убедитесь что интернет соединение стабильно
- Попробуйте обновить страницу

## Файлы

**Backend**:
- `webapp/chat_api.py` - API endpoints
- `webapp/migrations/apply_chat_migration.py` - миграция БД
- `webapp/webhook_client.py` - отправка уведомлений

**Frontend**:
- `webapp/static/js/app.js` - функции чата (openChat, sendChatMessage, loadChatMessages)
- `webapp/static/css/style.css` - стили чата
- `webapp/templates/index.html` - модальное окно чата

**Bot**:
- `telegram-bot/handlers/webhooks.py` - обработка уведомлений
