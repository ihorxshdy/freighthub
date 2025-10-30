#!/bin/bash

# Скрипт автоматического деплоя на сервер

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

SERVER_HOST="81.200.147.68"
SERVER_USER="root"
SERVER_PATH="/opt/freighthub"
SSH_KEY="$HOME/.ssh/freighthub_deploy"

echo -e "${GREEN}🚀 FreightHub Auto Deploy${NC}"
echo "================================"

# Проверяем наличие SSH ключа
if [ ! -f "${SSH_KEY}" ]; then
    echo -e "${RED}❌ SSH key not found: ${SSH_KEY}${NC}"
    echo ""
    echo "Please create SSH key first:"
    echo -e "${YELLOW}  ssh-keygen -t rsa -b 4096 -f ~/.ssh/freighthub_deploy${NC}"
    echo -e "${YELLOW}  ssh-copy-id -i ~/.ssh/freighthub_deploy.pub ${SERVER_USER}@${SERVER_HOST}${NC}"
    echo ""
    echo "See QUICKSTART_AUTO_DEPLOY.md for details"
    exit 1
fi

# Проверяем наличие .env файла
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  .env file not found!${NC}"
    echo "Creating from .env.example..."
    cp .env.example .env
    echo -e "${YELLOW}Please edit .env file and add your BOT_TOKEN${NC}"
    exit 1
fi

# Проверяем подключение к серверу
echo -e "${GREEN}📡 Checking server connection...${NC}"
if ! ssh -i ${SSH_KEY} -o ConnectTimeout=5 ${SERVER_USER}@${SERVER_HOST} "echo 'Connected'" &>/dev/null; then
    echo -e "${RED}❌ Cannot connect to server ${SERVER_HOST}${NC}"
    echo "Please check your SSH connection and key: ${SSH_KEY}"
    exit 1
fi

echo -e "${GREEN}✅ Server connection OK${NC}"

# Создаём директорию на сервере
echo -e "${GREEN}📁 Creating directory on server...${NC}"
ssh -i ${SSH_KEY} ${SERVER_USER}@${SERVER_HOST} "mkdir -p ${SERVER_PATH}"

# Копируем файлы на сервер
echo -e "${GREEN}📦 Copying files to server...${NC}"
rsync -avz --progress \
    -e "ssh -i ${SSH_KEY}" \
    --exclude 'database/*.db' \
    --exclude 'database/*.sqlite' \
    --exclude 'venv/' \
    --exclude '__pycache__/' \
    --exclude '*.pyc' \
    --exclude '.git/' \
    --exclude '.DS_Store' \
    ./ ${SERVER_USER}@${SERVER_HOST}:${SERVER_PATH}/

# Копируем .env файл
echo -e "${GREEN}🔐 Copying .env file...${NC}"
scp -i ${SSH_KEY} .env ${SERVER_USER}@${SERVER_HOST}:${SERVER_PATH}/.env

# Запускаем Docker Compose на сервере
echo -e "${GREEN}🐳 Starting Docker containers...${NC}"
ssh -i ${SSH_KEY} ${SERVER_USER}@${SERVER_HOST} << 'ENDSSH'
    cd /opt/freighthub
    
    # Останавливаем старые контейнеры
    docker-compose down
    
    # Собираем новые образы
    docker-compose build
    
    # Запускаем контейнеры
    docker-compose up -d
    
    # Показываем статус
    echo ""
    echo "================================"
    docker-compose ps
    echo "================================"
ENDSSH

echo ""
echo -e "${GREEN}✅ Deployment completed!${NC}"
echo ""
echo "Services are running on:"
echo -e "  🤖 Telegram Bot: http://${SERVER_HOST}:8080/webhook/health"
echo -e "  🌐 WebApp: http://${SERVER_HOST}"
echo ""
echo "To view logs:"
echo -e "  ${YELLOW}ssh ${SERVER_USER}@${SERVER_HOST} 'cd ${SERVER_PATH} && docker-compose logs -f'${NC}"
echo ""
echo "To stop services:"
echo -e "  ${YELLOW}ssh ${SERVER_USER}@${SERVER_HOST} 'cd ${SERVER_PATH} && docker-compose down'${NC}"
