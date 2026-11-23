#!/bin/bash
set -euo pipefail
ROOT=/home/sidms/jmc

# Backend: RBAC companions for quotes/AR/GRN
mkdir -p "$ROOT/backend/accounts"
cp -a /tmp/qa_rbac.py "$ROOT/backend/accounts/rbac.py"
docker cp "$ROOT/backend/accounts/rbac.py" jmc_api:/app/accounts/rbac.py
docker restart jmc_api
for i in $(seq 1 40); do
  st=$(docker inspect jmc_api --format '{{.State.Health.Status}}' 2>/dev/null || echo starting)
  [ "$st" = "healthy" ] && break
  sleep 2
done
docker inspect jmc_api --format 'api={{.State.Health.Status}}'

# Frontend standalone
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
for p in procurement/receipts procurement/orders sales/quotes sales/invoices; do
  curl -k -sS -o /dev/null -w "$p=%{http_code}\n" --max-time 20 \
    --resolve si-erp.mushaz.com:443:127.0.0.1 "https://si-erp.mushaz.com/$p"
done
echo DONE
