FROM python:3.9-slim

WORKDIR /app

# Создаём временную директорию для pip
RUN mkdir -p /tmp && chmod 1777 /tmp

# Копируем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код
COPY . .

# Создаём папку для БД (теперь монтируется в /app/data)
RUN mkdir -p /app/data

# Копируем и делаем исполняемым entrypoint скрипт
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Открываем порт
EXPOSE 5000

# Запускаем через entrypoint для применения миграций
CMD ["/app/entrypoint.sh"]
