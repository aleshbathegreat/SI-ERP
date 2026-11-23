#!/bin/bash
set -euo pipefail
ROOT=/home/sidms/jmc
SRC=/tmp/import_hub

echo "=== extract ==="
rm -rf "$SRC"
mkdir -p "$SRC"
tar -xzf /tmp/import-hub.tgz -C "$SRC"
cp -a "$SRC"/backend/. "$ROOT/backend/"

echo "=== frontend ==="
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

cd "$ROOT"
docker compose build api web
docker compose up -d --force-recreate api web
sleep 8

docker exec -w /app -e PYTHONPATH=/app jmc_api python manage.py migrate --noinput || true
if [ -f /tmp/sync_rbac_roles.py ]; then
  docker cp /tmp/sync_rbac_roles.py jmc_api:/tmp/sync_rbac_roles.py
  docker exec -w /app -e PYTHONPATH=/app jmc_api sh -c 'python manage.py shell < /tmp/sync_rbac_roles.py' || true
fi

curl -k -sS -o /dev/null -w "import-hub=%{http_code}\n" --max-time 15 \
  --resolve si-erp.mushaz.com:443:127.0.0.1 https://si-erp.mushaz.com/settings/import-hub
docker inspect jmc_api --format 'api={{.State.Health.Status}}'
echo DONE
