#!/bin/bash

# Быстрая настройка сервера для FreightHub

echo "🔧 Installing Docker on server..."

# Обновляем пакеты
sudo apt update
sudo apt install -y apt-transport-https ca-certificates curl software-properties-common

# Добавляем Docker репозиторий
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Устанавливаем Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Устанавливаем Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Добавляем текущего пользователя в группу docker
sudo usermod -aG docker $USER

# Проверяем установку
docker --version
docker-compose --version

echo "✅ Docker installed successfully!"
echo ""
echo "⚠️  Please logout and login again for group changes to take effect"
echo "Then run: ./deploy.sh"
