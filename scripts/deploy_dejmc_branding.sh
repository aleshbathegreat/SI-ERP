#!/bin/bash
set -euo pipefail
JMC=/home/sidms/jmc
SRC=/tmp/jmc_dejmc
rm -rf "$SRC"
mkdir -p "$SRC"
tar -xzf /tmp/dejmc-branding.tgz -C "$SRC"

for app in integrations accounts config finance hr payroll core; do
  if [ -d "$SRC/backend/$app" ]; then
    mkdir -p "$JMC/backend/$app"
    find "$SRC/backend/$app" -type d -name '__pycache__' -prune -exec rm -rf {} + 2>/dev/null || true
    cp -a "$SRC/backend/$app/." "$JMC/backend/$app/"
    docker cp "$JMC/backend/$app/." "jmc_api:/app/$app/"
  fi
done

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
print('catalog', len(INTEGRATION_CATALOG), 'recommended', sum(1 for i in INTEGRATION_CATALOG if i.get('recommended')))
"

docker restart jmc_api
for i in $(seq 1 40); do
  st=$(docker inspect jmc_api --format '{{.State.Health.Status}}' 2>/dev/null || echo starting)
  [ "$st" = "healthy" ] && break
  sleep 2
done
docker inspect jmc_api --format 'api={{.State.Health.Status}}'

if [ -f /tmp/frontend-standalone.tgz ]; then
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
fi
echo DONE
