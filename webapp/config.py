# Конфигурация веб-приложения

# URL веб-приложения
# Для локальной разработки:
WEBAPP_URL = "http://localhost:5001"

# Для продакшена замените на ваш домен с HTTPS:
# WEBAPP_URL = "https://ваш-домен.ru"
# WEBAPP_URL = "https://app.freighthub.ru"

# Настройки Flask
FLASK_HOST = "0.0.0.0"
FLASK_PORT = 5001
FLASK_DEBUG = True

# Настройки базы данных
DATABASE_PATH = "../bot_database.db"
