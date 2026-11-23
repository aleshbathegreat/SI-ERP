#!/bin/bash
set -euo pipefail
ROOT=/home/sidms/jmc
SRC=/tmp/jmc_conn_ent
rm -rf "$SRC"
mkdir -p "$SRC"
tar -xzf /tmp/connectors-enterprise.tgz -C "$SRC"

if [ -d "$SRC/backend/hr" ]; then
  mkdir -p "$ROOT/backend/hr"
  find "$SRC/backend/hr" -type d -name '__pycache__' -prune -exec rm -rf {} + 2>/dev/null || true
  cp -a "$SRC/backend/hr/." "$ROOT/backend/hr/"
  docker cp "$ROOT/backend/hr/." "jmc_api:/app/hr/"
fi

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
curl -k -sS -o /dev/null -w "attendance=%{http_code}\n" --max-time 20 \
  --resolve si-erp.mushaz.com:443:127.0.0.1 "https://si-erp.mushaz.com/hr/attendance?tab=connectors"
echo DONE
