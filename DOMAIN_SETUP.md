# 🌐 Настройка домена freight-hub.ru

## Текущее состояние
- ✅ Домен: `freight-hub.ru`
- ✅ Сервер: `81.200.147.68`
- ✅ Docker контейнеры запущены
- 🔧 Нужно: Настроить Nginx для правильного пути

## Шаг 1: Включите SSL Proxy в Cloudflare

1. Откройте: https://dash.cloudflare.com
2. Выберите домен `freight-hub.ru`
3. Перейдите в **SSL/TLS** → **Overview**
4. Установите режим: **Flexible** (или **Full** если у вас есть SSL на сервере)
5. В разделе **Edge Certificates** включите:
   - ✅ Always Use HTTPS
   - ✅ Automatic HTTPS Rewrites

## Шаг 2: Настройте Nginx на сервере

```bash
# Подключитесь к серверу
ssh -i ~/.ssh/freighthub_deploy root@81.200.147.68

# Скопируйте и запустите скрипт установки
cd /opt/freighthub
./setup-nginx.sh
```

Или вручную:

```bash
# Установите Nginx
sudo apt update && sudo apt install -y nginx

# Создайте конфигурацию
sudo nano /etc/nginx/sites-available/freight-hub.ru
```

Вставьте содержимое из `nginx.conf`

```bash
# Активируйте конфигурацию
sudo ln -sf /etc/nginx/sites-available/freight-hub.ru /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Проверьте и перезапустите
sudo nginx -t
sudo systemctl restart nginx
sudo systemctl enable nginx
```

## Шаг 3: Обновите проект

```bash
# На вашем компьютере
cd /Users/igordvoretskii/Documents/deliveryapp
git add .
git commit -m "Update: configure domain freight-hub.ru with Nginx"
git push

# Деплой
./deploy.sh
```

## Шаг 4: Проверьте работу

После настройки откройте:
- 🌐 **WebApp:** https://freight-hub.ru/tgbotfiles/freighthub/
- 🤖 **Telegram Bot:** https://t.me/freighthub_bot

В боте нажмите кнопку "Приложение" - должно открыться WebApp.

## Проблемы и решения

### Nginx не запускается
```bash
# Проверьте логи
sudo nginx -t
sudo journalctl -u nginx -n 50
```

### WebApp не открывается
```bash
# Проверьте, что контейнеры работают
cd /opt/freighthub
docker-compose ps

# Проверьте логи
docker-compose logs webapp --tail=50
```

### Telegram показывает ошибку "Invalid URL"
- Убедитесь, что в Cloudflare включен SSL (Flexible режим)
- URL в `.env` должен быть: `https://freight-hub.ru/tgbotfiles/freighthub/`
- Перезапустите бота: `cd /opt/freighthub && docker-compose restart telegram-bot`

## Структура URL

```
https://freight-hub.ru/
├── /tgbotfiles/freighthub/     → WebApp (порт 80)
├── /webhook                     → Telegram Bot webhook (порт 8080)
└── /                           → Информационная страница
```

## Cloudflare настройки

**DNS:**
- Type: `A`
- Name: `@`
- Content: `81.200.147.68`
- Proxy: ✅ **Proxied** (оранжевое облако)

**SSL/TLS:**
- Mode: **Flexible**
- Always Use HTTPS: ✅ **On**
- Automatic HTTPS Rewrites: ✅ **On**

**Speed:**
- Auto Minify: ✅ CSS, JavaScript, HTML
- Brotli: ✅ On

---

После всех настроек WebApp будет доступно по адресу:
**https://freight-hub.ru/tgbotfiles/freighthub/**
