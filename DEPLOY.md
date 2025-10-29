# 🚀 Деплой на свой сервер (81.200.147.68)

## Выбор метода деплоя

### 🤖 Автоматический деплой (через GitHub Actions)
**Рекомендуется!** Автоматическое обновление при каждом `git push`

→ См. подробную инструкцию: **[GITHUB_ACTIONS.md](GITHUB_ACTIONS.md)**

### 🔧 Ручной деплой (через deploy.sh)
Обновление вручную командой `./deploy.sh`

---

## Один раз: Настройка сервера

```bash
# Подключитесь к серверу
ssh root@81.200.147.68
# Пароль: tSmLE76Upf@_B.

# Скопируйте и запустите скрипт установки
curl -o setup-server.sh https://raw.githubusercontent.com/ihorxshdy/webapp/main/setup-server.sh
chmod +x setup-server.sh
./setup-server.sh

# Перелогиньтесь
exit
ssh root@81.200.147.68
```

## Деплой (каждый раз после изменений)

```bash
# На вашем компьютере
cd /Users/igordvoretskii/Documents/deliveryapp

# Создайте .env файл (первый раз)
cp .env.example .env
# Отредактируйте BOT_TOKEN если нужно

# Запустите деплой
./deploy.sh
```

Готово! Приложение работает на http://81.200.147.68

---

## Управление

### Просмотр логов
```bash
ssh root@81.200.147.68
cd /opt/freighthub
docker-compose logs -f
```

### Перезапуск сервисов
```bash
ssh root@81.200.147.68
cd /opt/freighthub
docker-compose restart
```

### Остановка
```bash
ssh root@81.200.147.68
cd /opt/freighthub
docker-compose down
```

### Обновление кода
```bash
# Вариант 1: Автоматически (если настроен GitHub Actions)
git add .
git commit -m "Update"
git push  # Деплой запустится автоматически!

# Вариант 2: Вручную
./deploy.sh
```

---

## Проверка работы

- Бот webhook: http://81.200.147.68:8080/webhook/health
- WebApp: http://81.200.147.68
- Debug DB: http://81.200.147.68/api/debug/db-info
