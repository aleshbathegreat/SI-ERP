#!/bin/bash
set -euo pipefail
JMC=/home/sidms/jmc

mkdir -p "$JMC/backend/core" "$JMC/backend/config" "$JMC/frontend/.next"

cp /tmp/exceptions.py "$JMC/backend/core/exceptions.py"
cp /tmp/bulk.py "$JMC/backend/core/bulk.py"
cp /tmp/settings.py "$JMC/backend/config/settings.py"
cp /tmp/frontend-standalone.tgz "$JMC/"

docker cp "$JMC/backend/core/exceptions.py" jmc_api:/app/core/exceptions.py
docker cp "$JMC/backend/core/bulk.py" jmc_api:/app/core/bulk.py
docker cp "$JMC/backend/config/settings.py" jmc_api:/app/config/settings.py
docker restart jmc_api

cd "$JMC/frontend"
rm -rf .next/standalone .next/static standalone static
mkdir -p .next
tar -xzf "$JMC/frontend-standalone.tgz" -C "$JMC/frontend"
[ -d standalone ] && mv standalone .next/standalone
[ -d static ] && mv static .next/static
# Fix accidental nested static/static from bad packing
if [ -d .next/static/static ]; then
  mv .next/static/static/* .next/static/ 2>/dev/null || true
  rmdir .next/static/static 2>/dev/null || rm -rf .next/static/static
fi
if [ ! -d .next/static/chunks ]; then
  echo "ERROR: .next/static/chunks missing" >&2
  find .next -maxdepth 4 -type d | head -50 >&2
  exit 1
fi
mkdir -p .next/standalone/.next
rm -rf .next/standalone/.next/static
cp -a .next/static .next/standalone/.next/static

cd "$JMC"
docker compose build web
docker compose up -d --force-recreate web

for i in $(seq 1 40); do
  st=$(docker inspect jmc_api --format '{{.State.Health.Status}}' 2>/dev/null || echo starting)
  [ "$st" = "healthy" ] && break
  sleep 2
done
docker inspect jmc_api --format 'api={{.State.Health.Status}}'
sleep 4

curl -k -sS -o /dev/null -w "web=%{http_code}\n" --max-time 20 \
  --resolve si-erp.mushaz.com:443:127.0.0.1 https://si-erp.mushaz.com/login
SAMPLE=$(docker exec jmc_web sh -c 'ls /app/.next/static/chunks/*.js 2>/dev/null | head -1')
if [ -n "$SAMPLE" ]; then
  NAME=$(basename "$SAMPLE")
  curl -k -sS -o /dev/null -w "sample_chunk=%{http_code}\n" --max-time 15 \
    --resolve si-erp.mushaz.com:443:127.0.0.1 \
    "https://si-erp.mushaz.com/_next/static/chunks/${NAME}"
fi
echo DONE
