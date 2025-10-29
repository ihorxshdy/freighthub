# 📚 Документация проекта - Навигация

## 🎯 С чего начать?

### Вы впервые настраиваете проект?
→ Читайте: **[QUICKSTART_AUTO_DEPLOY.md](QUICKSTART_AUTO_DEPLOY.md)** ⚡ (5 минут)

### Хотите понять структуру проекта?
→ Читайте: **[README.md](README.md)** 📖

---

## 📄 Список документов

### Основные файлы

| Файл | Назначение | Когда читать |
|------|------------|--------------|
| **README.md** | Обзор проекта, структура, технологии | Первый раз |
| **QUICKSTART_AUTO_DEPLOY.md** | ⚡ Быстрая настройка автодеплоя (5 мин) | Для начала работы |
| **GITHUB_ACTIONS.md** | Подробная инструкция по GitHub Actions | Если нужны детали |
| **DEPLOY.md** | Ручной деплой и управление сервером | Если не используете автодеплой |

### Скрипты

| Файл | Назначение | Как запустить |
|------|------------|---------------|
| **setup-server.sh** | Установка Docker на сервере (один раз) | `ssh root@81.200.147.68 < setup-server.sh` |
| **deploy.sh** | Ручной деплой на сервер | `./deploy.sh` |

### Конфигурация

| Файл | Назначение |
|------|------------|
| **docker-compose.yml** | Описание всех контейнеров |
| **.env** | Переменные окружения (НЕ в Git) |
| **.env.example** | Шаблон для .env |
| **.github/workflows/deploy.yml** | GitHub Actions автодеплой |

---

## 🚀 Типичные сценарии

### Первый деплой

1. Прочитайте: [QUICKSTART_AUTO_DEPLOY.md](QUICKSTART_AUTO_DEPLOY.md)
2. Настройте SSH и GitHub Secrets (5 минут)
3. Сделайте `git push` - всё обновится автоматически!

### Обновление кода

```bash
git add .
git commit -m "Описание изменений"
git push  # 🚀 Автоматически обновится!
```

### Просмотр логов

```bash
ssh root@81.200.147.68 'cd /opt/freighthub && docker-compose logs -f'
```

Или на GitHub: https://github.com/ihorxshdy/webapp/actions

### Перезапуск сервисов

```bash
ssh root@81.200.147.68 'cd /opt/freighthub && docker-compose restart'
```

### Отключить автодеплой

Удалите файл `.github/workflows/deploy.yml` и сделайте push.

---

## 🔧 Полезные команды

### Проверка статуса на сервере
```bash
ssh root@81.200.147.68 'cd /opt/freighthub && docker-compose ps'
```

### Ручной деплой (если не настроен GitHub Actions)
```bash
./deploy.sh
```

### Остановка всех сервисов
```bash
ssh root@81.200.147.68 'cd /opt/freighthub && docker-compose down'
```

### Полная пересборка
```bash
ssh root@81.200.147.68 'cd /opt/freighthub && docker-compose down && docker-compose build --no-cache && docker-compose up -d'
```

---

## 📍 Важные URL

- **Бот webhook health:** http://81.200.147.68:8080/webhook/health
- **WebApp:** http://81.200.147.68
- **Debug DB info:** http://81.200.147.68/api/debug/db-info
- **GitHub Actions:** https://github.com/ihorxshdy/webapp/actions
- **GitHub Secrets:** https://github.com/ihorxshdy/webapp/settings/secrets/actions

---

## 🆘 Помощь

### Ошибка при деплое через GitHub Actions?
→ Проверьте: [GITHUB_ACTIONS.md](GITHUB_ACTIONS.md) → раздел "Troubleshooting"

### Контейнеры не запускаются?
→ Смотрите логи: `ssh root@81.200.147.68 'cd /opt/freighthub && docker-compose logs'`

### База данных не синхронизируется?
→ Все контейнеры используют общий volume `./database:/app/database`

### Хотите откатить изменения?
```bash
git revert HEAD
git push  # Автоматически откатит на сервере
```

---

## 📂 Структура файлов проекта

```
deliveryapp/
├── .github/
│   └── workflows/
│       └── deploy.yml          # GitHub Actions автодеплой
├── telegram-bot/
│   ├── bot/                    # Код бота
│   ├── Dockerfile              # Docker образ бота
│   └── requirements.txt
├── webapp/
│   ├── app.py                  # Flask приложение
│   ├── auction_checker.py      # Background worker
│   ├── Dockerfile              # Docker образ webapp
│   └── requirements.txt
├── database/                   # Общая БД (в .gitignore)
├── .env                        # Переменные окружения (НЕ в Git)
├── .env.example                # Шаблон
├── .gitignore                  # Игнорируемые файлы
├── docker-compose.yml          # Описание всех сервисов
├── deploy.sh                   # Скрипт ручного деплоя
├── setup-server.sh             # Скрипт настройки сервера
├── README.md                   # Обзор проекта
├── QUICKSTART_AUTO_DEPLOY.md   # ⚡ Быстрый старт
├── GITHUB_ACTIONS.md           # Детали GitHub Actions
└── DEPLOY.md                   # Ручной деплой
```

---

**Рекомендуемый порядок чтения:**

1. **README.md** - понять что за проект
2. **QUICKSTART_AUTO_DEPLOY.md** - настроить автодеплой за 5 минут
3. **GITHUB_ACTIONS.md** - узнать детали (опционально)

После настройки просто делайте `git push` - всё остальное произойдет автоматически! 🚀
