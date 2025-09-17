FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --upgrade pip

RUN pip install --no-cache-dir --root-user-action=ignore -r requirements.txt

COPY . .

RUN mkdir -p migrations

COPY entrypoint.sh .

RUN chmod +x entrypoint.sh

RUN python manage.py collectstatic --noinput