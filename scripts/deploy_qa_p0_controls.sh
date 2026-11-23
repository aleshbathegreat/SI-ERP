#!/bin/bash
set -euo pipefail
ROOT=/home/sidms/jmc
SRC=/tmp/qa_p0_controls
rm -rf "$SRC"
mkdir -p "$SRC"
tar -xzf /tmp/qa-p0-controls.tgz -C "$SRC"

for f in \
  accounts/permissions.py \
  accounts/rbac.py \
  accounts/rbac_views.py \
  ops/views.py \
  finance/views.py \
  hr/serializers.py \
  core/management/commands/seed_erp.py
do
  mkdir -p "$ROOT/backend/$(dirname "$f")"
  cp -a "$SRC/backend/$f" "$ROOT/backend/$f"
  docker cp "$ROOT/backend/$f" "jmc_api:/app/$f"
done

docker restart jmc_api
for i in $(seq 1 40); do
  st=$(docker inspect jmc_api --format '{{.State.Health.Status}}' 2>/dev/null || echo starting)
  [ "$st" = "healthy" ] && break
  sleep 2
done
docker inspect jmc_api --format 'api={{.State.Health.Status}}'

# Frontend
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
curl -k -sS -o /dev/null -w "login=%{http_code}\n" --max-time 20 \
  --resolve si-erp.mushaz.com:443:127.0.0.1 https://si-erp.mushaz.com/login
echo DONE
