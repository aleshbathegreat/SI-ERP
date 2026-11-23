#!/bin/bash
set -euo pipefail
JMC=/home/sidms/jmc
SRC=/tmp/jmc_int_pack

echo "=== unpack integrations backend ==="
for app in integrations config accounts core; do
  if [ -d "$SRC/backend/$app" ]; then
    mkdir -p "$JMC/backend/$app"
    find "$SRC/backend/$app" -type d -name '__pycache__' -prune -exec rm -rf {} + 2>/dev/null || true
    cp -a "$SRC/backend/$app/." "$JMC/backend/$app/"
    docker cp "$JMC/backend/$app/." "jmc_api:/app/$app/"
  fi
done

echo "=== migrate + roles ==="
docker exec -w /app jmc_api python manage.py migrate integrations --noinput
docker exec -w /app jmc_api python -c "
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
django.setup()
from core.models import Organization
from accounts.rbac import ensure_default_roles
n=0
for org in Organization.objects.filter(is_active=True):
    ensure_default_roles(org); n+=1
print('roles', n)
from integrations.catalog import INTEGRATION_CATALOG
print('catalog', len(INTEGRATION_CATALOG))
"

docker restart jmc_api
for i in $(seq 1 40); do
  st=$(docker inspect jmc_api --format '{{.State.Health.Status}}' 2>/dev/null || echo starting)
  [ "$st" = "healthy" ] && break
  sleep 2
done
docker inspect jmc_api --format 'api={{.State.Health.Status}}'

echo "=== frontend ==="
cp /tmp/frontend-standalone.tgz "$JMC/"
cd "$JMC/frontend"
rm -rf .next/standalone .next/static standalone static
mkdir -p .next
tar -xzf "$JMC/frontend-standalone.tgz" -C "$JMC/frontend"
[ -d standalone ] && mv standalone .next/standalone
[ -d static ] && mv static .next/static
mkdir -p .next/standalone/.next
rm -rf .next/standalone/.next/static
cp -a .next/static .next/standalone/.next/static
cd "$JMC"
docker compose build web
docker compose up -d --force-recreate web
sleep 6
curl -k -sS -o /dev/null -w "integrations_page=%{http_code}\n" --max-time 20 \
  --resolve si-erp.mushaz.com:443:127.0.0.1 https://si-erp.mushaz.com/settings/integrations
echo DONE
