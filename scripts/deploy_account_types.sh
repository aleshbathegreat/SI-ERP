#!/bin/bash
set -euo pipefail
ROOT=/home/sidms/jmc
SRC=/tmp/jmc_acct_types
rm -rf "$SRC"
mkdir -p "$SRC"
tar -xzf /tmp/account-types.tgz -C "$SRC"

if [ -d "$SRC/backend/finance" ]; then
  mkdir -p "$ROOT/backend/finance"
  find "$SRC/backend/finance" -type d -name '__pycache__' -prune -exec rm -rf {} + 2>/dev/null || true
  cp -a "$SRC/backend/finance/." "$ROOT/backend/finance/"
  docker cp "$ROOT/backend/finance/." "jmc_api:/app/finance/"
fi
if [ -f "$SRC/backend/config/urls.py" ]; then
  mkdir -p "$ROOT/backend/config"
  cp -a "$SRC/backend/config/urls.py" "$ROOT/backend/config/urls.py"
  docker cp "$ROOT/backend/config/urls.py" "jmc_api:/app/config/urls.py"
fi

docker exec jmc_api python manage.py migrate finance --noinput
docker restart jmc_api
for i in $(seq 1 40); do
  st=$(docker inspect jmc_api --format '{{.State.Health.Status}}' 2>/dev/null || echo starting)
  [ "$st" = "healthy" ] && break
  sleep 2
done
docker inspect jmc_api --format 'api={{.State.Health.Status}}'

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
cd "$ROOT"
docker compose build web
docker compose up -d --force-recreate web
sleep 6
curl -k -sS -o /dev/null -w "accounts=%{http_code}\n" --max-time 20 \
  --resolve si-erp.mushaz.com:443:127.0.0.1 https://si-erp.mushaz.com/finance/accounts
curl -k -sS -o /dev/null -w "account-types=%{http_code}\n" --max-time 20 \
  --resolve si-erp.mushaz.com:443:127.0.0.1 https://si-erp.mushaz.com/finance/account-types
curl -k -sS -o /dev/null -w "accounts-new=%{http_code}\n" --max-time 20 \
  --resolve si-erp.mushaz.com:443:127.0.0.1 https://si-erp.mushaz.com/finance/accounts/new
echo DONE
