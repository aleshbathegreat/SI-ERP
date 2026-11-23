#!/bin/bash
set -euo pipefail
ROOT=/home/sidms/jmc
SRC=/tmp/jmc_hr_lc2
rm -rf "$SRC"
mkdir -p "$SRC"
tar -xzf /tmp/hr-lifecycle2.tgz -C "$SRC"

if [ -d "$SRC/backend/hr" ]; then
  mkdir -p "$ROOT/backend/hr"
  find "$SRC/backend/hr" -type d -name '__pycache__' -prune -exec rm -rf {} + 2>/dev/null || true
  cp -a "$SRC/backend/hr/." "$ROOT/backend/hr/"
  docker cp "$ROOT/backend/hr/." "jmc_api:/app/hr/"
fi
for f in payroll/views.py config/urls.py; do
  if [ -f "$SRC/backend/$f" ]; then
    mkdir -p "$ROOT/backend/$(dirname "$f")"
    cp -a "$SRC/backend/$f" "$ROOT/backend/$f"
    docker cp "$ROOT/backend/$f" "jmc_api:/app/$f"
  fi
done

docker exec jmc_api python manage.py migrate hr --noinput
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
for p in hr/job-history hr/document-types hr/training-courses hr/employees; do
  curl -k -sS -o /dev/null -w "$p=%{http_code}\n" --max-time 20 \
    --resolve si-erp.mushaz.com:443:127.0.0.1 "https://si-erp.mushaz.com/$p"
done
echo DONE
