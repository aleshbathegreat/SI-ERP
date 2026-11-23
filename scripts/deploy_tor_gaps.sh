#!/bin/bash
set -euo pipefail
JMC=/home/sidms/jmc

mkdir -p \
  "$JMC/backend/finance" "$JMC/backend/finance/migrations" \
  "$JMC/backend/hr" "$JMC/backend/hr/migrations" \
  "$JMC/backend/payroll" "$JMC/backend/payroll/migrations" \
  "$JMC/backend/core/management/commands" \
  "$JMC/backend/accounts" "$JMC/backend/config"

# Copy uploaded payloads into repo tree
cp /tmp/fin_models.py "$JMC/backend/finance/models.py"
cp /tmp/fin_views.py "$JMC/backend/finance/views.py"
cp /tmp/fin_reporting.py "$JMC/backend/finance/reporting.py"
cp /tmp/fin_production_views.py "$JMC/backend/finance/production_views.py"
cp /tmp/fin_0004.py "$JMC/backend/finance/migrations/0004_tor_gap_ap_assets.py"
cp /tmp/hr_models.py "$JMC/backend/hr/models.py"
cp /tmp/hr_views.py "$JMC/backend/hr/views.py"
cp /tmp/hr_serializers.py "$JMC/backend/hr/serializers.py"
cp /tmp/hr_0005.py "$JMC/backend/hr/migrations/0005_leave_balances_docs.py"
cp /tmp/pay_models.py "$JMC/backend/payroll/models.py"
cp /tmp/pay_views.py "$JMC/backend/payroll/views.py"
cp /tmp/pay_0004.py "$JMC/backend/payroll/migrations/0004_payroll_gl_journal.py"
cp /tmp/workflow.py "$JMC/backend/core/workflow.py"
cp /tmp/import_masters.py "$JMC/backend/core/management/commands/import_masters.py"
cp /tmp/rbac_views.py "$JMC/backend/accounts/rbac_views.py"
cp /tmp/urls.py "$JMC/backend/config/urls.py"
cp /tmp/frontend-standalone.tgz "$JMC/"

# Sync into running API container
docker cp "$JMC/backend/finance/models.py" jmc_api:/app/finance/models.py
docker cp "$JMC/backend/finance/views.py" jmc_api:/app/finance/views.py
docker cp "$JMC/backend/finance/reporting.py" jmc_api:/app/finance/reporting.py
docker cp "$JMC/backend/finance/production_views.py" jmc_api:/app/finance/production_views.py
docker cp "$JMC/backend/finance/migrations/0004_tor_gap_ap_assets.py" jmc_api:/app/finance/migrations/0004_tor_gap_ap_assets.py
docker cp "$JMC/backend/hr/models.py" jmc_api:/app/hr/models.py
docker cp "$JMC/backend/hr/views.py" jmc_api:/app/hr/views.py
docker cp "$JMC/backend/hr/serializers.py" jmc_api:/app/hr/serializers.py
docker cp "$JMC/backend/hr/migrations/0005_leave_balances_docs.py" jmc_api:/app/hr/migrations/0005_leave_balances_docs.py
docker cp "$JMC/backend/payroll/models.py" jmc_api:/app/payroll/models.py
docker cp "$JMC/backend/payroll/views.py" jmc_api:/app/payroll/views.py
docker cp "$JMC/backend/payroll/migrations/0004_payroll_gl_journal.py" jmc_api:/app/payroll/migrations/0004_payroll_gl_journal.py
docker cp "$JMC/backend/core/workflow.py" jmc_api:/app/core/workflow.py
docker cp "$JMC/backend/core/management/commands/import_masters.py" jmc_api:/app/core/management/commands/import_masters.py
docker cp "$JMC/backend/accounts/rbac_views.py" jmc_api:/app/accounts/rbac_views.py
docker cp "$JMC/backend/config/urls.py" jmc_api:/app/config/urls.py

docker exec -w /app jmc_api python manage.py migrate finance 0004_tor_gap_ap_assets --noinput
docker exec -w /app jmc_api python manage.py migrate hr 0005_leave_balances_docs --noinput
docker exec -w /app jmc_api python manage.py migrate payroll 0004_payroll_gl_journal --noinput
docker restart jmc_api
for i in $(seq 1 40); do
  st=$(docker inspect jmc_api --format '{{.State.Health.Status}}' 2>/dev/null || echo starting)
  [ "$st" = "healthy" ] && break
  sleep 2
done
docker inspect jmc_api --format 'api={{.State.Health.Status}}'

JACCESS=$(curl -k -sS --max-time 20 --resolve jmc.mushaz.com:443:127.0.0.1 \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"Admin@123"}' \
  https://si-erp-api.mushaz.com/api/auth/login/ | python3 -c 'import sys,json;print(json.load(sys.stdin).get("access",""))' 2>/dev/null || true)

# Prefer tenant host login if admin lives on jmc tenant
if [ -z "${JACCESS:-}" ]; then
  JACCESS=$(curl -k -sS --max-time 20 --resolve jmc.mushaz.com:443:127.0.0.1 \
    -H 'Content-Type: application/json' -H 'Host: jmc.mushaz.com' \
    -d '{"username":"admin","password":"Admin@123"}' \
    https://jmc.mushaz.com/api/auth/login/ | python3 -c 'import sys,json;print(json.load(sys.stdin).get("access",""))' 2>/dev/null || true)
fi

if [ -n "${JACCESS:-}" ]; then
  for path in finance/reports/ hr/leave-balances/ finance/bank-statements/; do
    code=$(curl -k -sS -o /tmp/g.json -w "%{http_code}" --max-time 15 \
      --resolve si-erp-api.mushaz.com:443:127.0.0.1 \
      -H "Authorization: Bearer $JACCESS" \
      "https://si-erp-api.mushaz.com/api/${path}")
    echo "GET /api/${path} -> ${code}"
  done
else
  echo "WARN: tenant login failed; skipping API smoke checks"
fi

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
