# Offline-friendly: install from ./wheels (downloaded on host when Docker DNS is broken).
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt .
COPY wheels/ /tmp/wheels/
RUN pip install --no-index --find-links=/tmp/wheels -r requirements.txt \
    && rm -rf /tmp/wheels

COPY . .

RUN mkdir -p /app/media /app/staticfiles /app/logs /app/backups \
    && chmod +x /app/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120"]
