#!/bin/bash
set -euo pipefail
JMC=/home/sidms/jmc
mkdir -p "$JMC/backend/accounts" "$JMC/frontend"
cp /tmp/accounts_views.py "$JMC/backend/accounts/views.py"
cp /tmp/frontend-standalone.tgz "$JMC/"
docker cp "$JMC/backend/accounts/views.py" jmc_api:/app/accounts/views.py
docker restart jmc_api
for i in $(seq 1 40); do
  st=$(docker inspect jmc_api --format '{{.State.Health.Status}}' 2>/dev/null || echo starting)
  [ "$st" = "healthy" ] && break
  sleep 2
done
docker inspect jmc_api --format 'api={{.State.Health.Status}}'

cd "$JMC/frontend"
rm -rf .next && mkdir -p .next
tar -xzf "$JMC/frontend-standalone.tgz" -C "$JMC/frontend"
[ -d "$JMC/frontend/standalone" ] && mv "$JMC/frontend/standalone" "$JMC/frontend/.next/standalone"
[ -d "$JMC/frontend/static" ] && mv "$JMC/frontend/static" "$JMC/frontend/.next/static"
# keep existing public/guide if present
cd "$JMC"
docker compose build web
docker compose up -d --force-recreate web
sleep 4

JACCESS=$(curl -k -sS --max-time 20 --resolve si-erp-api.mushaz.com:443:127.0.0.1 \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"Admin@123"}' \
  https://si-erp-api.mushaz.com/api/auth/login/ | python3 -c 'import sys,json;print(json.load(sys.stdin).get("access",""))' 2>/dev/null || true)

if [ -n "${JACCESS:-}" ]; then
  curl -k -sS -o /tmp/dash.json -w "dash=%{http_code}\n" --max-time 20 \
    --resolve si-erp-api.mushaz.com:443:127.0.0.1 \
    -H "Authorization: Bearer $JACCESS" \
    https://si-erp-api.mushaz.com/api/dashboard/
  python3 -c 'import json;d=json.load(open("/tmp/dash.json"));print("health",d.get("health_score"),"sentiments",len(d.get("sentiments") or []), "trend",len(d.get("trend_6m") or []))'
fi
curl -k -sS -o /dev/null -w "web=%{http_code}\n" --max-time 15 \
  --resolve si-erp.mushaz.com:443:127.0.0.1 https://si-erp.mushaz.com/login
echo DONE
