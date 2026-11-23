#!/bin/bash
set -euo pipefail
JMC=/home/sidms/jmc

mkdir -p \
  "$JMC/backend/core/migrations" \
  "$JMC/backend/accounts" \
  "$JMC/backend/config" \
  "$JMC/frontend/.next"

cp /tmp/core_models.py "$JMC/backend/core/models.py"
cp /tmp/core_serializers.py "$JMC/backend/core/serializers.py"
cp /tmp/core_access.py "$JMC/backend/core/access.py"
cp /tmp/platform_views.py "$JMC/backend/core/platform_views.py"
cp /tmp/0010_package_core_modules.py "$JMC/backend/core/migrations/0010_package_core_modules.py"
cp /tmp/rbac.py "$JMC/backend/accounts/rbac.py"
cp /tmp/urls.py "$JMC/backend/config/urls.py"
cp /tmp/frontend-standalone.tgz "$JMC/"

docker cp "$JMC/backend/core/models.py" jmc_api:/app/core/models.py
docker cp "$JMC/backend/core/serializers.py" jmc_api:/app/core/serializers.py
docker cp "$JMC/backend/core/access.py" jmc_api:/app/core/access.py
docker cp "$JMC/backend/core/platform_views.py" jmc_api:/app/core/platform_views.py
docker cp "$JMC/backend/core/migrations/0010_package_core_modules.py" jmc_api:/app/core/migrations/0010_package_core_modules.py
docker cp "$JMC/backend/accounts/rbac.py" jmc_api:/app/accounts/rbac.py
docker cp "$JMC/backend/config/urls.py" jmc_api:/app/config/urls.py

docker exec -w /app jmc_api python manage.py migrate core 0010_package_core_modules --noinput || true
docker exec -w /app jmc_api python manage.py shell -c "
from core.access import ensure_default_packages
ensure_default_packages()
print('packages synced')
"
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
# keep public guide images if present
cd "$JMC"
docker compose build web
docker compose up -d --force-recreate web
sleep 5

PACCESS=$(curl -k -sS --max-time 20 --resolve si-erp-api.mushaz.com:443:127.0.0.1 \
  -H 'Content-Type: application/json' \
  -d '{"username":"platform","password":"Platform@123"}' \
  https://si-erp-api.mushaz.com/api/auth/login/ | python3 -c 'import sys,json;print(json.load(sys.stdin).get("access",""))')

curl -k -sS -o /tmp/ov.json -w "overview=%{http_code}\n" --max-time 20 \
  --resolve si-erp-api.mushaz.com:443:127.0.0.1 \
  -H "Authorization: Bearer $PACCESS" \
  https://si-erp-api.mushaz.com/api/platform/overview/
python3 -c 'import json;d=json.load(open("/tmp/ov.json"));print("health",d.get("health_score"),"pkgs",len(d.get("package_stats") or []),"sentiments",len(d.get("sentiments") or []))'

curl -k -sS -o /tmp/mc.json -w "catalog=%{http_code}\n" --max-time 20 \
  --resolve si-erp-api.mushaz.com:443:127.0.0.1 \
  -H "Authorization: Bearer $PACCESS" \
  https://si-erp-api.mushaz.com/api/platform/module-catalog/
python3 -c 'import json;d=json.load(open("/tmp/mc.json"));print("groups",len(d.get("groups") or []),"core",len(d.get("core_keys") or []),"assignable",len(d.get("assignable_keys") or []))'

curl -k -sS -o /dev/null -w "web=%{http_code}\n" --max-time 15 \
  --resolve si-erp.mushaz.com:443:127.0.0.1 https://si-erp.mushaz.com/login
echo DONE
