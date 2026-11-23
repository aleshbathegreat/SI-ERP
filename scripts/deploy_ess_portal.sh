#!/bin/bash
set -euo pipefail
JMC=/home/sidms/jmc
SRC=/tmp/jmc_ess_pack

echo "=== unpack ESS backend ==="
for app in ess config accounts; do
  if [ -d "$SRC/backend/$app" ]; then
    mkdir -p "$JMC/backend/$app"
    find "$SRC/backend/$app" -type d -name '__pycache__' -prune -exec rm -rf {} + 2>/dev/null || true
    cp -a "$SRC/backend/$app/." "$JMC/backend/$app/"
    docker cp "$JMC/backend/$app/." "jmc_api:/app/$app/"
  fi
done

echo "=== ensure roles (ess perms) ==="
docker exec -w /app jmc_api python -c "
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from core.models import Organization
from accounts.rbac import ensure_default_roles
n = 0
for org in Organization.objects.filter(is_active=True):
    ensure_default_roles(org)
    n += 1
print('roles_refreshed', n)
"

echo "=== restart api ==="
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
CHUNK_COUNT=$(find .next/static/chunks -type f | wc -l)
echo "static_chunks=${CHUNK_COUNT}"
mkdir -p .next/standalone/.next
rm -rf .next/standalone/.next/static
cp -a .next/static .next/standalone/.next/static
cd "$JMC"
docker compose build web
docker compose up -d --force-recreate web
sleep 6
docker exec jmc_web sh -c 'echo -n container_chunks=; find /app/.next/static/chunks -type f 2>/dev/null | wc -l'
curl -k -sS -o /dev/null -w "ess_page=%{http_code}\n" --max-time 20 \
  --resolve si-erp.mushaz.com:443:127.0.0.1 https://si-erp.mushaz.com/ess
curl -k -sS -o /dev/null -w "ess_api=%{http_code}\n" --max-time 20 \
  --resolve si-erp-api.mushaz.com:443:127.0.0.1 https://si-erp-api.mushaz.com/api/ess/dashboard/ || true
echo DONE
