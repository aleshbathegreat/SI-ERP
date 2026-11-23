#!/bin/bash
set -euo pipefail
JMC=/home/sidms/jmc

echo "=== sync backend payroll + rbac + urls ==="
docker cp "$JMC/backend/payroll/models.py" jmc_api:/app/payroll/models.py
docker cp "$JMC/backend/payroll/serializers.py" jmc_api:/app/payroll/serializers.py
docker cp "$JMC/backend/payroll/views.py" jmc_api:/app/payroll/views.py
docker cp "$JMC/backend/payroll/migrations/0003_intl_payroll_and_loans.py" jmc_api:/app/payroll/migrations/0003_intl_payroll_and_loans.py
docker cp "$JMC/backend/accounts/rbac.py" jmc_api:/app/accounts/rbac.py
docker cp "$JMC/backend/config/urls.py" jmc_api:/app/config/urls.py

echo "=== migrate ==="
docker exec jmc_api python manage.py migrate payroll --noinput
docker exec jmc_api python manage.py shell -c "
from accounts.rbac import ensure_default_roles, full_permissions
from accounts.models import Role
from core.models import Organization
for org in Organization.objects.all():
    ensure_default_roles(org)
    for code in ('owner','admin','platform'):
        r = Role.objects.filter(organization=org, code=code).first()
        if r:
            r.permissions = full_permissions()
            r.save(update_fields=['permissions'])
print('roles_synced', Organization.objects.count())
"

docker restart jmc_api
for i in $(seq 1 30); do
  st=$(docker inspect jmc_api --format '{{.State.Health.Status}}' 2>/dev/null || echo starting)
  [ "$st" = "healthy" ] && break
  sleep 2
done
docker inspect jmc_api --format 'api={{.State.Health.Status}}'

echo "=== frontend extract & rebuild ==="
cd "$JMC/frontend"
rm -rf .next
mkdir -p .next
tar -xzf "$JMC/frontend-standalone.tgz" -C "$JMC/frontend"
cd "$JMC"
docker compose build web
docker compose up -d --force-recreate web
sleep 5

echo "=== verify ==="
TOKEN=$(curl -k -sS --max-time 20 --resolve si-erp-api.mushaz.com:443:127.0.0.1 \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"Admin@123"}' \
  https://si-erp-api.mushaz.com/api/auth/login/ | python3 -c 'import sys,json; print(json.load(sys.stdin).get("access",""))')
echo "token_len=${#TOKEN}"
curl -k -sS -o /tmp/loans.json -w "loans=%{http_code}\n" --max-time 15 \
  --resolve si-erp-api.mushaz.com:443:127.0.0.1 \
  -H "Authorization: Bearer $TOKEN" \
  https://si-erp-api.mushaz.com/api/payroll/loans/
curl -k -sS -o /tmp/slips.json -w "payslips=%{http_code}\n" --max-time 15 \
  --resolve si-erp-api.mushaz.com:443:127.0.0.1 \
  -H "Authorization: Bearer $TOKEN" \
  https://si-erp-api.mushaz.com/api/payroll/payslips/?page_size=1
python3 - <<'PY'
import json
d=json.load(open('/tmp/slips.json'))
row=(d.get('results') or d or [None])[0] if isinstance(d,dict) else None
if isinstance(d,list): row=d[0] if d else None
print('sample_keys', sorted(row.keys())[:25] if isinstance(row,dict) else type(d))
PY
curl -k -sS -o /dev/null -w "payroll_page=%{http_code}\n" --max-time 15 \
  --resolve si-erp.mushaz.com:443:127.0.0.1 https://si-erp.mushaz.com/payroll
curl -k -sS -o /dev/null -w "loans_page=%{http_code}\n" --max-time 15 \
  --resolve si-erp.mushaz.com:443:127.0.0.1 https://si-erp.mushaz.com/payroll/loans
docker exec jmc_web sh -c "grep -Rao 'Loan repayment\|Employee loans\|housing_allowance\|Generate / refresh' /app/.next/static 2>/dev/null | sort -u | head -20 || true"
echo DONE
