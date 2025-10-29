FROM python:3.9-slim

WORKDIR /app

# Копируем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код
COPY . .

# Создаём папку для БД
RUN mkdir -p /app/database

# Открываем порт
EXPOSE 5000

# Запускаем webapp
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
