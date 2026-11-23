#!/bin/bash
set -euo pipefail
JMC=/home/sidms/jmc

cp /tmp/frontend-standalone.tgz "$JMC/"
mkdir -p "$JMC/backend/core" "$JMC/backend/config" "$JMC/backend/core/management/commands"
cp /tmp/platform_views.py "$JMC/backend/core/platform_views.py"
cp /tmp/tenancy.py "$JMC/backend/core/tenancy.py"
cp /tmp/mailer.py "$JMC/backend/core/mailer.py"
cp /tmp/urls.py "$JMC/backend/config/urls.py"
cp /tmp/seed_erp.py "$JMC/backend/core/management/commands/seed_erp.py"
cp /tmp/ensure_platform_owner.py "$JMC/ensure_platform_owner.py"

docker cp "$JMC/backend/core/platform_views.py" jmc_api:/app/core/platform_views.py
docker cp "$JMC/backend/core/tenancy.py" jmc_api:/app/core/tenancy.py
docker cp "$JMC/backend/core/mailer.py" jmc_api:/app/core/mailer.py
docker cp "$JMC/backend/config/urls.py" jmc_api:/app/config/urls.py
docker cp "$JMC/backend/core/management/commands/seed_erp.py" jmc_api:/app/core/management/commands/seed_erp.py
docker cp "$JMC/ensure_platform_owner.py" jmc_api:/app/ensure_platform_owner.py
# also ensure payroll views/emails/mailer still present after any prior recreate
if [ -f /tmp/payroll_views.py ]; then
  docker cp /tmp/payroll_views.py jmc_api:/app/payroll/views.py
fi
if [ -f /tmp/payroll_emails.py ]; then
  docker cp /tmp/payroll_emails.py jmc_api:/app/payroll/emails.py
fi

docker restart jmc_api
for i in $(seq 1 40); do
  st=$(docker inspect jmc_api --format '{{.State.Health.Status}}' 2>/dev/null || echo starting)
  [ "$st" = "healthy" ] && break
  sleep 2
done
docker inspect jmc_api --format 'api={{.State.Health.Status}}'

docker exec -w /app jmc_api python ensure_platform_owner.py

TOKEN_P=$(curl -k -sS --max-time 20 --resolve si-erp-api.mushaz.com:443:127.0.0.1 \
  -H 'Content-Type: application/json' \
  -d '{"username":"platform","password":"Platform@123"}' \
  https://si-erp-api.mushaz.com/api/auth/login/ | python3 -c 'import sys,json;d=json.load(sys.stdin);print(d.get("access",""), d.get("user",{}).get("is_superuser"), bool(d.get("organization")))')
echo "platform_login $TOKEN_P"

TOKEN_A=$(curl -k -sS --max-time 20 --resolve si-erp-api.mushaz.com:443:127.0.0.1 \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"Admin@123"}' \
  https://si-erp-api.mushaz.com/api/auth/login/ | python3 -c 'import sys,json;d=json.load(sys.stdin);print(d.get("access","")[:20], "super=", d.get("user",{}).get("is_superuser"), "owner=", d.get("user",{}).get("is_owner"))')
echo "admin_login $TOKEN_A"

PACCESS=$(curl -k -sS --max-time 20 --resolve si-erp-api.mushaz.com:443:127.0.0.1 \
  -H 'Content-Type: application/json' \
  -d '{"username":"platform","password":"Platform@123"}' \
  https://si-erp-api.mushaz.com/api/auth/login/ | python3 -c 'import sys,json;print(json.load(sys.stdin).get("access",""))')
curl -k -sS -o /tmp/ov.json -w "overview=%{http_code}\n" --max-time 15 \
  --resolve si-erp-api.mushaz.com:443:127.0.0.1 \
  -H "Authorization: Bearer $PACCESS" \
  https://si-erp-api.mushaz.com/api/platform/overview/
python3 -c 'import json;d=json.load(open("/tmp/ov.json"));print({k:d.get(k) for k in ["tenants","tenants_active","platform_smtp_active"]})'

AACCESS=$(curl -k -sS --max-time 20 --resolve si-erp-api.mushaz.com:443:127.0.0.1 \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"Admin@123"}' \
  https://si-erp-api.mushaz.com/api/auth/login/ | python3 -c 'import sys,json;print(json.load(sys.stdin).get("access",""))')
curl -k -sS -o /tmp/ov_a.json -w "admin_overview=%{http_code}\n" --max-time 15 \
  --resolve si-erp-api.mushaz.com:443:127.0.0.1 \
  -H "Authorization: Bearer $AACCESS" \
  https://si-erp-api.mushaz.com/api/platform/overview/

cd "$JMC/frontend"
rm -rf .next && mkdir -p .next
tar -xzf "$JMC/frontend-standalone.tgz" -C "$JMC/frontend"
cd "$JMC"
docker compose build web
docker compose up -d --force-recreate web
sleep 4
curl -k -sS -o /dev/null -w "platform_page=%{http_code}\n" --max-time 15 \
  --resolve si-erp.mushaz.com:443:127.0.0.1 https://si-erp.mushaz.com/platform
docker exec jmc_web sh -c "grep -Rao 'Control center\|Platform access only\|platform owner' /app/.next/static 2>/dev/null | sort -u | head -10 || true"
echo DONE
