#!/bin/bash
set -euo pipefail
JMC=/home/sidms/jmc
SRC=/tmp/jmc_inv_pack

echo "=== unpack backend ==="
for app in ops accounts config core; do
  if [ -d "$SRC/backend/$app" ]; then
    mkdir -p "$JMC/backend/$app"
    find "$SRC/backend/$app" -type d -name '__pycache__' -prune -exec rm -rf {} + 2>/dev/null || true
    cp -a "$SRC/backend/$app/." "$JMC/backend/$app/"
    docker cp "$JMC/backend/$app/." "jmc_api:/app/$app/"
  fi
done

echo "=== migrate ==="
docker exec -w /app jmc_api python manage.py migrate ops --noinput

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
curl -k -sS -o /dev/null -w "web=%{http_code}\n" --max-time 20 \
  --resolve si-erp.mushaz.com:443:127.0.0.1 https://si-erp.mushaz.com/login
echo DONE
