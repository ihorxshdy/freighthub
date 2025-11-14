# Система организаций и инвайт-кодов - Инструкция по внедрению

## 📋 Обзор

Реализована система контроля доступа через инвайт-коды с привязкой к организациям:
- Админ создает организации
- Генерирует пул инвайт-кодов для каждой организации
- Пользователь вводит код при регистрации
- Код привязывается к telegram_id пользователя перманентно
- Один код = один пользователь

## 🗃️ Новые таблицы БД

### organizations
- `id` - первичный ключ
- `name` - название организации (уникальное)
- `description` - описание
- `is_active` - активна ли организация
- `created_at`, `updated_at` - временные метки

### invite_codes
- `id` - первичный ключ  
- `code` - инвайт-код (уникальный, 8 символов A-Z0-9)
- `organization_id` - FK к organizations
- `used_by_telegram_id` - telegram_id пользователя (NULL пока не использован)
- `used_at` - дата использования
- `is_active` - активен ли код
- `expires_at` - дата истечения (опционально)
- `created_at` - дата создания

### users (новые поля)
- `organization_id` - FK к organizations
- `invite_code_id` - FK к invite_codes

## 📂 Созданные файлы

### 1. Миграция БД
- `migrations/add_organizations_and_invites.sql` - SQL схема
- `migrations/apply_organizations_migration.py` - Python скрипт применения

### 2. Backend API
- `webapp/admin_api.py` - API endpoints для админ панели
  * `/api/admin/organizations` - CRUD организаций
  * `/api/admin/invite-codes` - просмотр кодов
  * `/api/admin/invite-codes/generate` - генерация кодов
  * `/api/invite-codes/validate` - валидация кода
  * `/api/invite-codes/use` - использование кода

### 3. Frontend
- `webapp/templates/admin.html` - веб-интерфейс админ панели
- Добавлен роут `/admin` в `app.py`

### 4. Telegram Bot
- Обновлен `telegram-bot/handlers/registration.py`:
  * Новое состояние `waiting_for_invite_code`
  * Валидация кода через API
  * Привязка к организации

## 🚀 Применение миграции

### Шаг 1: Применить миграцию БД

```bash
cd /Users/igordvoretskii/Documents/deliveryapp
python migrations/apply_organizations_migration.py
```

Скрипт автоматически:
- Создаст таблицы organizations и invite_codes
- Добавит поля в users
- Создаст индексы
- Создаст организацию "Default Organization" (ID=1)
- Привяжет всех существующих пользователей к ней

### Шаг 2: Обновить функцию create_user

В `telegram-bot/database/models.py` нужно добавить параметры к create_user:

```python
async def create_user(telegram_id, phone_number, role, truck_type, name, 
                     organization_id=None, invite_code=None):
    # ... existing code ...
    
    # Получить invite_code_id если есть код
    invite_code_id = None
    if invite_code:
        code_row = await cursor.execute(
            'SELECT id FROM invite_codes WHERE code = ?',
            (invite_code,)
        ).fetchone()
        if code_row:
            invite_code_id = code_row[0]
    
    await cursor.execute(
        '''INSERT INTO users (telegram_id, phone_number, role, truck_type, name, 
                              organization_id, invite_code_id)
           VALUES (?, ?, ?, ?, ?, ?, ?)''',
        (telegram_id, phone_number, role, truck_type, name, 
         organization_id, invite_code_id)
    )
```

### Шаг 3: Обновить вызовы create_user в registration.py

Во всех местах где вызывается create_user, добавить:

```python
data = await state.get_data()

await create_user(
    telegram_id=callback.from_user.id,
    phone_number=data['phone_number'],
    role=role,
    truck_type=truck_type,
    name=callback.from_user.full_name,
    organization_id=data.get('organization_id'),  # НОВОЕ
    invite_code=data.get('invite_code')           # НОВОЕ
)
```

### Шаг 4: Использовать инвайт-код

После создания пользователя, пометить код как использованный:

```python
# В конце функции создания пользователя
if data.get('invite_code'):
    import aiohttp
    from bot.webapp_config import WEBAPP_URL
    async with aiohttp.ClientSession() as session:
        await session.post(
            f'{WEBAPP_URL}/api/invite-codes/use',
            json={
                'code': data['invite_code'],
                'telegram_id': callback.from_user.id
            }
        )
```

### Шаг 5: Настроить админа

В `webapp/admin_api.py` строка 12:

```python
ADMIN_IDS = [966377899]  # Замените на ваш telegram_id
```

Узнать свой telegram_id можно через бота @userinfobot

## 📱 Использование админ панели

### Доступ

1. Откройте Mini App в Telegram
2. Перейдите по URL: `https://ваш-домен/admin`
3. Если ваш telegram_id в списке ADMIN_IDS - откроется админка

### Возможности

**Вкладка "Организации":**
- ➕ Добавить организацию
- Просмотр статистики (пользователи, коды)
- Активация/деактивация
- Переход к кодам организации

**Вкладка "Инвайт-коды":**
- 🎫 Генерировать коды (1-100 штук)
- Фильтр по организации
- Просмотр использованных/неиспользованных кодов
- Опционально: срок действия кодов

### Процесс работы с организацией

1. Организация обращается с запросом
2. Админ создает организацию через панель
3. Генерирует N кодов для этой организации
4. Передает коды организации
5. Сотрудники организации вводят коды при регистрации
6. Коды привязываются к их telegram_id навсегда

## 🔒 Безопасность

- Каждый код используется только один раз
- Повторное использование того же кода тем же пользователем допустимо
- Использование чужого кода невозможно
- Деактивированные коды не работают
- Коды могут иметь срок действия

## 🧪 Тестирование

### 1. Создать тестовую организацию

```bash
curl -X POST "http://localhost:5000/api/admin/organizations?telegram_id=ВАШ_ID" \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Org", "description": "Тестовая организация"}'
```

### 2. Сгенерировать коды

```bash
curl -X POST "http://localhost:5000/api/admin/invite-codes/generate?telegram_id=ВАШ_ID" \
  -H "Content-Type: application/json" \
  -d '{"organization_id": 2, "count": 5}'
```

### 3. Проверить код

```bash
curl -X POST "http://localhost:5000/api/invite-codes/validate" \
  -H "Content-Type: application/json" \
  -d '{"code": "ABC12DEF", "telegram_id": 123456}'
```

### 4. Зарегистрироваться через бота

1. /start в боте
2. Подписаться на канал
3. Ввести инвайт-код
4. Поделиться номером
5. Выбрать роль
6. Завершить регистрацию

## 📊 Мониторинг

### SQL запросы для мониторинга

```sql
-- Статистика по организациям
SELECT 
    o.name,
    COUNT(DISTINCT u.id) as users,
    COUNT(DISTINCT ic.id) as total_codes,
    COUNT(DISTINCT CASE WHEN ic.used_by_telegram_id IS NOT NULL THEN ic.id END) as used_codes
FROM organizations o
LEFT JOIN users u ON o.id = u.organization_id
LEFT JOIN invite_codes ic ON o.id = ic.organization_id
GROUP BY o.id;

-- Неиспользованные коды
SELECT code, o.name as organization
FROM invite_codes ic
JOIN organizations o ON ic.organization_id = o.id
WHERE ic.used_by_telegram_id IS NULL
  AND ic.is_active = 1;

-- Истекшие коды
SELECT code, o.name, expires_at
FROM invite_codes ic
JOIN organizations o ON ic.organization_id = o.id
WHERE datetime(expires_at) < datetime('now')
  AND ic.used_by_telegram_id IS NULL;
```

## 🐛 Возможные проблемы

### Проблема: Бот не принимает код

**Решение:** 
- Проверить что WEBAPP_URL правильный
- Проверить что webapp запущен
- Проверить логи бота

### Проблема: Админ панель не открывается

**Решение:**
- Проверить telegram_id в ADMIN_IDS
- Открыть через /admin роут
- Проверить логи webapp

### Проблема: Код не валидируется

**Решение:**
- Проверить что организация активна (is_active=1)
- Проверить что код активен (is_active=1)
- Проверить срок действия (expires_at)

## 📝 TODO для завершения внедрения

- [ ] Применить миграцию БД
- [ ] Обновить database/models.py (create_user)
- [ ] Обновить все вызовы create_user в registration.py
- [ ] Добавить использование кода после регистрации
- [ ] Настроить ADMIN_IDS
- [ ] Протестировать полный флоу регистрации
- [ ] Создать первую реальную организацию
- [ ] Сгенерировать первые коды
- [ ] Задеплоить на сервер

## 🚢 Деплой

```bash
cd /Users/igordvoretskii/Documents/deliveryapp
git add .
git commit -m "Add organizations and invite codes system"
git push origin main
```

GitHub Actions автоматически задеплоит на сервер.

После деплоя на сервере:
```bash
ssh user@81.200.147.68
cd /opt/freighthub
docker exec freighthub-webapp python /app/migrations/apply_organizations_migration.py
```
