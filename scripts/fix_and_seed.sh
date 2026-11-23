#!/bin/bash
set -e
cd /home/sidms/jmc

# Ensure .env exists
if [ ! -f .env ]; then
  echo "Missing .env"
  exit 1
fi

# Keep demo seed on recreate of empty DB only; force reseed now
grep -q '^RUN_SEED=' .env && sed -i 's/^RUN_SEED=.*/RUN_SEED=1/' .env || echo 'RUN_SEED=1' >> .env

docker compose up -d --force-recreate
echo "Waiting for api healthy..."
for i in $(seq 1 40); do
  st=$(docker inspect jmc_api --format '{{.State.Health.Status}}' 2>/dev/null || echo starting)
  echo "  api=$st"
  [ "$st" = "healthy" ] && break
  sleep 3
done

docker compose ps
echo "=== health ==="
docker exec jmc_api python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/api/health/').read().decode())"

echo "=== ensure demo seed ==="
docker exec -e RUN_SEED=1 jmc_api python manage.py seed_erp

echo "=== counts ==="
docker exec jmc_api python manage.py shell -c "from core.models import Organization; from finance.models import Account,Vendor,JournalEntry; from hr.models import Employee; from payroll.models import Payslip; from django.contrib.auth.models import User; o=Organization.objects.get(code='jmc'); print(o.name); print('accounts',Account.objects.filter(organization=o).count()); print('vendors',Vendor.objects.filter(organization=o).count()); print('journals',JournalEntry.objects.filter(organization=o).count()); print('employees',Employee.objects.filter(organization=o).count()); print('payslips',Payslip.objects.filter(period__organization=o).count()); print('users',User.objects.filter(profile__organization=o).count())"

echo "=== traefik https probe ==="
curl -k -sS -o /dev/null -w "api_https:%{http_code}\n" --resolve si-erp-api.sidms.online:443:127.0.0.1 https://si-erp-api.sidms.online/api/health/ || true
curl -k -sS -o /dev/null -w "web_https:%{http_code}\n" --resolve si-erp.sidms.online:443:127.0.0.1 https://si-erp.sidms.online/login || true

# Turn seed off for future restarts
sed -i 's/^RUN_SEED=.*/RUN_SEED=0/' .env
echo DONE
