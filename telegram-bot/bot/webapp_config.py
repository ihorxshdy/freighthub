# Конфигурация для бота и веб-приложения
import os
from dotenv import load_dotenv

load_dotenv()

# URL веб-приложения
# Читаем из переменной окружения, если есть, иначе используем дефолтный
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://webapp-b7hr.onrender.com")

# ВАЖНО для Telegram Mini Apps:
# 1. URL ОБЯЗАТЕЛЬНО должен начинаться с https://
# 2. Нужен SSL сертификат (Let's Encrypt или другой)
# 3. Локальный http://localhost НЕ РАБОТАЕТ в Telegram!
