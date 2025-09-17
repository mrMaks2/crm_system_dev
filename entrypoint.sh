#!/bin/bash

# Ожидание доступности базы данных
echo "Waiting for database..."
while ! nc -z db 5432; do
  sleep 0.1
done
echo "Database started"

while ! python manage.py check --database default; do
  echo "Database not ready, waiting..."
  sleep 2
done

# Создание миграций (если нужно)
echo "Creating migrations..."
python manage.py makemigrations

# Применение миграций
echo "Applying migrations..."
python manage.py migrate

# Запуск основного процесса
exec "$@"