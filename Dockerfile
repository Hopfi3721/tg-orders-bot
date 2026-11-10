# lang=python
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DB_PATH=/data/orders.db

WORKDIR /app

RUN pip install --no-cache-dir "aiogram>=3.13,<4"

COPY main.py ./
COPY app ./app

RUN adduser --disabled-password --uid 10001 bot \
    && mkdir -p /data \
    && chown bot:bot /data

USER bot

CMD ["python", "main.py"]
