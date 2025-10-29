FROM python:3.9-slim

WORKDIR /app

# Копируем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код
COPY . .

# Создаём папку для БД
RUN mkdir -p /app/database

# Запускаем бота
CMD ["python", "main.py"]
