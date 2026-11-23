#!/bin/bash
set -euo pipefail
JMC=/home/sidms/jmc
mkdir -p "$JMC/frontend/src/components/dashboard"
mkdir -p "$JMC/frontend/src/app/(app)/platform/packages"
mkdir -p "$JMC/frontend/src/components/crud"
cp -f /tmp/Charts.tsx "$JMC/frontend/src/components/dashboard/Charts.tsx"
cp -f /tmp/platform_page.tsx "$JMC/frontend/src/app/(app)/platform/page.tsx"
cp -f /tmp/packages_page.tsx "$JMC/frontend/src/app/(app)/platform/packages/page.tsx"
cp -f /tmp/FormDialog.tsx "$JMC/frontend/src/components/crud/FormDialog.tsx"

docker run --rm --network host \
  -v "$JMC/frontend:/app" \
  -w /app \
  node:22-alpine \
  sh -c "npx next build --webpack"

cd "$JMC"
docker compose build web
docker compose up -d --force-recreate web
sleep 5
curl -k -sS -o /dev/null -w "web=%{http_code}\n" --max-time 15 \
  --resolve si-erp.mushaz.com:443:127.0.0.1 https://si-erp.mushaz.com/login

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
echo DONE
