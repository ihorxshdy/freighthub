#!/bin/bash

# Скрипт настройки Nginx на сервере

echo "🔧 Установка и настройка Nginx..."

# Установка Nginx (если еще не установлен)
sudo apt update
sudo apt install -y nginx

# Останавливаем Nginx
sudo systemctl stop nginx

# Копируем конфигурацию
sudo tee /etc/nginx/sites-available/freight-hub.ru > /dev/null << 'EOF'
server {
    listen 80;
    server_name freight-hub.ru www.freight-hub.ru;

    # Web Application - точный путь
    location /tgbotfiles/freighthub/ {
        proxy_pass http://localhost:5000/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Telegram Bot webhook
    location /webhook {
        proxy_pass http://localhost:8080/webhook;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Root - показываем информацию
    location = / {
        return 200 'FreightHub Service\nWebApp: https://freight-hub.ru/tgbotfiles/freighthub/\nBot: @freighthub_bot';
        add_header Content-Type text/plain;
    }

    # Другие пути - редирект на webapp
    location / {
        return 301 https://freight-hub.ru/tgbotfiles/freighthub/;
    }
}
EOF

# Создаем символическую ссылку
sudo ln -sf /etc/nginx/sites-available/freight-hub.ru /etc/nginx/sites-enabled/

# Удаляем дефолтную конфигурацию если есть
sudo rm -f /etc/nginx/sites-enabled/default

# Проверяем конфигурацию
echo "Проверка конфигурации Nginx..."
sudo nginx -t

if [ $? -eq 0 ]; then
    # Перезапускаем Nginx
    sudo systemctl start nginx
    sudo systemctl enable nginx
    
    echo ""
    echo "✅ Nginx настроен и запущен!"
    echo ""
    echo "📍 WebApp доступно по адресу:"
    echo "   http://freight-hub.ru/tgbotfiles/freighthub/"
    echo ""
    echo "После включения SSL Proxy в Cloudflare будет:"
    echo "   https://freight-hub.ru/tgbotfiles/freighthub/"
else
    echo ""
    echo "❌ Ошибка в конфигурации Nginx!"
    echo "Проверьте вывод выше"
fi
