#!/bin/bash
set -euo pipefail
ROOT=/home/sidms/jmc
SRC=/tmp/wave12

echo "=== extract payload ==="
rm -rf "$SRC"
mkdir -p "$SRC"
tar -xzf /tmp/wave12-backend.tgz -C "$SRC"

echo "=== sync backend apps ==="
cp -a "$SRC"/backend/. "$ROOT/backend/"

echo "=== frontend standalone ==="
if [ -f /tmp/frontend-standalone.tgz ]; then
  cp /tmp/frontend-standalone.tgz "$ROOT/"
  cd "$ROOT/frontend"
  rm -rf .next/standalone .next/static standalone static
  mkdir -p .next
  tar -xzf "$ROOT/frontend-standalone.tgz" -C "$ROOT/frontend"
  [ -d standalone ] && mv standalone .next/standalone
  [ -d static ] && mv static .next/static
  mkdir -p .next/standalone/.next
  rm -rf .next/standalone/.next/static
  cp -a .next/static .next/standalone/.next/static
fi

echo "=== rebuild api + web ==="
cd "$ROOT"
docker compose build api web
docker compose up -d --force-recreate api web
sleep 8

echo "=== migrate ==="
docker exec -w /app -e PYTHONPATH=/app jmc_api python manage.py migrate --noinput

echo "=== sync RBAC roles ==="
if [ -f "$ROOT/backend/../scripts/sync_rbac_roles.py" ] || [ -f /tmp/sync_rbac_roles.py ]; then
  docker cp /tmp/sync_rbac_roles.py jmc_api:/tmp/sync_rbac_roles.py 2>/dev/null || \
    docker cp "$ROOT/scripts/sync_rbac_roles.py" jmc_api:/tmp/sync_rbac_roles.py
  docker exec -w /app -e PYTHONPATH=/app jmc_api sh -c 'python manage.py shell < /tmp/sync_rbac_roles.py' || true
fi

echo "=== smoke ==="
for p in dashboard crm/leads projects projects/timesheets mfg/boms finance/tax-returns finance/e-invoices \
  service/cases finance/maintenance-orders qms/inspections inventory/bins inventory/pick-lists \
  dms/documents finance/reports; do
  curl -k -sS -o /dev/null -w "$p=%{http_code}\n" --max-time 15 \
    --resolve si-erp.mushaz.com:443:127.0.0.1 "https://si-erp.mushaz.com/$p" || true
done
docker inspect jmc_api --format 'api={{.State.Health.Status}}'
docker inspect jmc_web --format 'web={{.State.Status}}'
echo DONE
