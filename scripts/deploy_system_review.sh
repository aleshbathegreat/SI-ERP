#!/bin/bash
set -euo pipefail
JMC=/home/sidms/jmc
SRC=/tmp/jmc_review_pack

echo "=== unpack backend apps ==="
for app in finance hr payroll core accounts config ops; do
  if [ -d "$SRC/backend/$app" ]; then
    mkdir -p "$JMC/backend/$app"
    find "$SRC/backend/$app" -type d -name '__pycache__' -prune -exec rm -rf {} + 2>/dev/null || true
    find "$SRC/backend/$app" -type f -name '*.pyc' -delete 2>/dev/null || true
    cp -a "$SRC/backend/$app/." "$JMC/backend/$app/"
    docker cp "$JMC/backend/$app/." "jmc_api:/app/$app/"
  fi
done

echo "=== migrate ==="
docker exec -w /app jmc_api python manage.py migrate --noinput

echo "=== restart api ==="
docker restart jmc_api
for i in $(seq 1 40); do
  st=$(docker inspect jmc_api --format '{{.State.Health.Status}}' 2>/dev/null || echo starting)
  [ "$st" = "healthy" ] && break
  sleep 2
done
docker inspect jmc_api --format 'api={{.State.Health.Status}}'

echo "=== frontend ==="
if [ -f "$SRC/frontend-standalone.tgz" ]; then
  cp "$SRC/frontend-standalone.tgz" "$JMC/"
  cd "$JMC/frontend"
  rm -rf .next/standalone .next/static standalone static
  mkdir -p .next
  tar -xzf "$JMC/frontend-standalone.tgz" -C "$JMC/frontend"
  [ -d standalone ] && mv standalone .next/standalone
  [ -d static ] && mv static .next/static
  if [ -d .next/static/static ]; then
    mv .next/static/static/* .next/static/ || true
    rm -rf .next/static/static
  fi
  if [ ! -d .next/static/chunks ]; then
    echo "ERROR: .next/static/chunks missing" >&2
    find .next -maxdepth 3 -type d | head -40 >&2
    exit 1
  fi
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
  SAMPLE=$(docker exec jmc_web sh -c 'ls /app/.next/static/chunks/*.js 2>/dev/null | head -1')
  if [ -n "$SAMPLE" ]; then
    NAME=$(basename "$SAMPLE")
    curl -k -sS -o /dev/null -w "sample_chunk=%{http_code} name=${NAME}\n" --max-time 20 \
      --resolve si-erp.mushaz.com:443:127.0.0.1 "https://si-erp.mushaz.com/_next/static/chunks/${NAME}"
  fi
fi

curl -k -sS -o /dev/null -w "web=%{http_code}\n" --max-time 20 \
  --resolve si-erp.mushaz.com:443:127.0.0.1 https://si-erp.mushaz.com/login
echo DONE
