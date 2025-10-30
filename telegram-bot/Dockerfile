FROM python:3.9-slim

WORKDIR /app

# Копируем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код
COPY . .

# Создаём папку для БД (теперь монтируется в /app/data)
RUN mkdir -p /app/data

# Запускаем бота
CMD ["python", "main.py"]
