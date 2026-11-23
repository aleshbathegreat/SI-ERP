#!/bin/bash
set -euo pipefail
JMC=/home/sidms/jmc

mkdir -p "$JMC/backend/core" "$JMC/backend/config"
cp /tmp/platform_views.py "$JMC/backend/core/platform_views.py"
cp /tmp/serializers.py "$JMC/backend/core/serializers.py"
cp /tmp/urls.py "$JMC/backend/config/urls.py"
cp /tmp/frontend-standalone.tgz "$JMC/"

docker cp "$JMC/backend/core/platform_views.py" jmc_api:/app/core/platform_views.py
docker cp "$JMC/backend/core/serializers.py" jmc_api:/app/core/serializers.py
docker cp "$JMC/backend/config/urls.py" jmc_api:/app/config/urls.py

docker restart jmc_api
for i in $(seq 1 40); do
  st=$(docker inspect jmc_api --format '{{.State.Health.Status}}' 2>/dev/null || echo starting)
  [ "$st" = "healthy" ] && break
  sleep 2
done
docker inspect jmc_api --format 'api={{.State.Health.Status}}'

PACCESS=$(curl -k -sS --max-time 20 --resolve si-erp-api.mushaz.com:443:127.0.0.1 \
  -H 'Content-Type: application/json' \
  -d '{"username":"platform","password":"Platform@123"}' \
  https://si-erp-api.mushaz.com/api/auth/login/ | python3 -c 'import sys,json;print(json.load(sys.stdin).get("access",""))')

curl -k -sS -o /tmp/pkgs.json -w "packages=%{http_code}\n" --max-time 15 \
  --resolve si-erp-api.mushaz.com:443:127.0.0.1 \
  -H "Authorization: Bearer $PACCESS" \
  https://si-erp-api.mushaz.com/api/platform/packages/
python3 -c 'import json;d=json.load(open("/tmp/pkgs.json"));print("pkg_count", len(d) if isinstance(d,list) else d.get("count", d.get("detail")))'

curl -k -sS -o /tmp/tnts.json -w "tenants=%{http_code}\n" --max-time 15 \
  --resolve si-erp-api.mushaz.com:443:127.0.0.1 \
  -H "Authorization: Bearer $PACCESS" \
  https://si-erp-api.mushaz.com/api/platform/tenants/
python3 -c 'import json;d=json.load(open("/tmp/tnts.json"));print("tenant_count", d.get("count", d.get("detail")))'

cd "$JMC/frontend"
rm -rf .next && mkdir -p .next
tar -xzf "$JMC/frontend-standalone.tgz" -C "$JMC/frontend"
cd "$JMC"
docker compose build web
docker compose up -d --force-recreate web
sleep 5
for path in /platform /platform/packages /platform/tenants /platform/domains; do
  curl -k -sS -o /dev/null -w "${path}=%{http_code}\n" --max-time 15 \
    --resolve si-erp.mushaz.com:443:127.0.0.1 "https://si-erp.mushaz.com${path}"
done
docker exec jmc_web sh -c "grep -Rao 'Subscription packages\|Platform · SaaS\|Collapse sidebar\|Control center' /app/.next/static 2>/dev/null | sort -u | head -15 || true"
echo DONE
