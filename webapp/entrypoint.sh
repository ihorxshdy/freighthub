#!/bin/sh
set -e

echo "Применение миграций..."
python3 migrations/apply_admin_features.py || echo "Миграция уже применена или произошла ошибка"

echo "Запуск webapp..."
exec gunicorn -w 4 -b 0.0.0.0:5000 app:app
