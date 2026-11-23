#!/bin/sh
set -e

mkdir -p /app/logs /app/media /app/staticfiles /app/backups

echo "Waiting for database..."
python <<'PY'
import os, time
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()
from django.db import connection
from django.db.utils import OperationalError

for i in range(60):
    try:
        connection.ensure_connection()
        print("Database ready")
        break
    except OperationalError:
        time.sleep(1)
else:
    raise SystemExit("Database not available")
PY

python manage.py migrate --noinput
python manage.py collectstatic --noinput

if [ "${RUN_SEED:-0}" = "1" ]; then
  python manage.py seed_erp || true
fi

exec "$@"
