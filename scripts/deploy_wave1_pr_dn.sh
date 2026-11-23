#!/bin/bash
set -euo pipefail
ROOT=/home/sidms/jmc
SRC=/tmp/wave1_pr_dn
rm -rf "$SRC"
mkdir -p "$SRC"
tar -xzf /tmp/wave1-pr-dn.tgz -C "$SRC"

for app in ops accounts core config; do
  if [ -d "$SRC/backend/$app" ]; then
    mkdir -p "$ROOT/backend/$app"
    cp -a "$SRC/backend/$app/." "$ROOT/backend/$app/"
    docker cp "$ROOT/backend/$app/." "jmc_api:/app/$app/"
  fi
done

docker exec -w /app -e PYTHONPATH=/app jmc_api python manage.py migrate ops --noinput
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
for p in procurement/requisitions sales/deliveries sales/orders procurement/orders; do
  curl -k -sS -o /dev/null -w "$p=%{http_code}\n" --max-time 20 \
    --resolve si-erp.mushaz.com:443:127.0.0.1 "https://si-erp.mushaz.com/$p"
done
echo DONE
