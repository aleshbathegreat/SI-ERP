#!/bin/bash
set -euo pipefail
JMC=/home/sidms/jmc
mkdir -p "$JMC/backend/core" "$JMC/backend/config"
cp /tmp/notification_views.py "$JMC/backend/core/notification_views.py"
cp /tmp/urls.py "$JMC/backend/config/urls.py"
cp /tmp/middleware.py "$JMC/backend/core/middleware.py"
cp /tmp/frontend-standalone.tgz "$JMC/"

docker cp "$JMC/backend/core/notification_views.py" jmc_api:/app/core/notification_views.py
docker cp "$JMC/backend/config/urls.py" jmc_api:/app/config/urls.py
docker cp "$JMC/backend/core/middleware.py" jmc_api:/app/core/middleware.py
docker restart jmc_api
for i in $(seq 1 30); do
  st=$(docker inspect jmc_api --format '{{.State.Health.Status}}' 2>/dev/null || echo starting)
  [ "$st" = "healthy" ] && break
  sleep 2
done
docker inspect jmc_api --format 'api={{.State.Health.Status}}'

PACCESS=$(curl -k -sS --max-time 20 --resolve si-erp-api.mushaz.com:443:127.0.0.1 \
  -H 'Content-Type: application/json' \
  -d '{"username":"platform","password":"Platform@123"}' \
  https://si-erp-api.mushaz.com/api/auth/login/ | python3 -c 'import sys,json;print(json.load(sys.stdin).get("access",""))')

curl -k -sS -o /tmp/n.json -w "notifications=%{http_code}\n" --max-time 15 \
  --resolve si-erp-api.mushaz.com:443:127.0.0.1 \
  -H "Authorization: Bearer $PACCESS" \
  https://si-erp-api.mushaz.com/api/notifications/
python3 -c 'import json;d=json.load(open("/tmp/n.json"));print("count", d.get("count"), "items", len(d.get("items",[])))'

cd "$JMC/frontend"
rm -rf .next && mkdir -p .next
tar -xzf "$JMC/frontend-standalone.tgz" -C "$JMC/frontend"
[ -d "$JMC/frontend/standalone" ] && mv "$JMC/frontend/standalone" "$JMC/frontend/.next/standalone"
[ -d "$JMC/frontend/static" ] && mv "$JMC/frontend/static" "$JMC/frontend/.next/static"
cd "$JMC"
docker compose build web
docker compose up -d --force-recreate web
sleep 4
curl -k -sS -o /dev/null -w "web=%{http_code}\n" --max-time 15 \
  --resolve si-erp.mushaz.com:443:127.0.0.1 https://si-erp.mushaz.com/login
echo DONE
