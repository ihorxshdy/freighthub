# FreightHub - Telegram Mini App для грузоперевозок

Платформа для поиска водителей грузовых автомобилей через Telegram.

## 🚀 Быстрый старт

### Деплой на продакшн (Рекомендуется)

**Автоматический деплой через GitHub Actions:**
```bash
# Настройте один раз (см. GITHUB_ACTIONS.md)
# Затем просто:
git add .
git commit -m "Update"
git push  # Автоматически обновится на сервере!
```

**Ручной деплой:**
```bash
./deploy.sh  # Обновит сервер 81.200.147.68
```

Подробнее: [DEPLOY.md](DEPLOY.md) и [GITHUB_ACTIONS.md](GITHUB_ACTIONS.md)

### Локальная разработка
```bash
# Установите зависимости
cd telegram-bot && pip install -r requirements.txt
cd ../webapp && pip install -r requirements.txt

# Запустите бота
cd telegram-bot && python3 main.py

# Запустите webapp
cd webapp && python3 app.py
```

### Деплой на свой сервер (Docker)
```bash
# Скопируйте .env.example → .env и заполните
cp .env.example .env

# Запустите всё одной командой
docker-compose up -d
```

## 📦 Структура

- `telegram-bot/` - Telegram бот (регистрация + уведомления)
- `webapp/` - Web приложение (создание заявок + аукцион)
- `docker-compose.yml` - Docker конфигурация
- `.env` - Переменные окружения (не в Git)

## 🔧 Технологии

- Python 3.9+
- aiogram 3.22 (Telegram Bot)
- Flask 3.1 (Web App)
- SQLite (БД)
- Docker & Docker Compose
