#!/bin/bash
set -euo pipefail
JMC=/home/sidms/jmc

mkdir -p "$JMC/frontend"
cp /tmp/frontend-standalone.tgz "$JMC/"

cd "$JMC/frontend"
# Wipe prior extract targets so `mv` cannot nest into existing dirs
rm -rf .next/standalone .next/static standalone static
mkdir -p .next
tar -xzf "$JMC/frontend-standalone.tgz" -C "$JMC/frontend"

# Accept either layout: top-level standalone/static OR already under .next/
if [ -d standalone ]; then
  mv standalone .next/standalone
fi
if [ -d static ]; then
  mv static .next/static
fi

# Ensure static chunks sit where the Dockerfile expects
if [ ! -d .next/static/chunks ]; then
  echo "ERROR: .next/static/chunks missing after extract" >&2
  find .next -maxdepth 3 -type d | head -40 >&2
  exit 1
fi
CHUNK_COUNT=$(find .next/static/chunks -type f | wc -l)
echo "static_chunks=${CHUNK_COUNT}"
if [ "$CHUNK_COUNT" -lt 10 ]; then
  echo "ERROR: too few static chunks (${CHUNK_COUNT})" >&2
  exit 1
fi

# Also mirror into standalone so server.js can serve even if COPY order differs
mkdir -p .next/standalone/.next
rm -rf .next/standalone/.next/static
cp -a .next/static .next/standalone/.next/static

cd "$JMC"
docker compose build web
docker compose up -d --force-recreate web
sleep 6

# Verify chunks inside the running container
docker exec jmc_web sh -c 'echo -n container_chunks=; find /app/.next/static/chunks -type f 2>/dev/null | wc -l'
SAMPLE=$(docker exec jmc_web sh -c 'ls /app/.next/static/chunks/*.js 2>/dev/null | head -1')
if [ -n "$SAMPLE" ]; then
  NAME=$(basename "$SAMPLE")
  curl -k -sS -o /dev/null -w "sample_chunk=%{http_code} name=${NAME}\n" --max-time 20 \
    --resolve si-erp.mushaz.com:443:127.0.0.1 "https://si-erp.mushaz.com/_next/static/chunks/${NAME}"
fi

curl -k -sS -o /dev/null -w "web=%{http_code}\n" --max-time 20 \
  --resolve si-erp.mushaz.com:443:127.0.0.1 https://si-erp.mushaz.com/login
echo DONE
