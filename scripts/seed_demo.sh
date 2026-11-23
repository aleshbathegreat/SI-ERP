#!/bin/bash
set -euo pipefail
cd /home/sidms/jmc

echo "=== containers ==="
docker compose ps

echo "=== migrate ==="
docker exec jmc_api python manage.py migrate --noinput

echo "=== seed_erp demo ==="
docker exec jmc_api python manage.py seed_erp

echo "=== demo counts ==="
docker exec jmc_api python manage.py shell -c "
from core.models import Organization
from finance.models import Account, Vendor, JournalEntry
from hr.models import Employee
from payroll.models import Payslip
from django.contrib.auth.models import User
o = Organization.objects.get(code='jmc')
print('org', o.name, o.code)
print('accounts', Account.objects.filter(organization=o).count())
print('vendors', Vendor.objects.filter(organization=o).count())
print('journals', JournalEntry.objects.filter(organization=o).count())
print('employees', Employee.objects.filter(organization=o).count())
print('payslips', Payslip.objects.filter(period__organization=o).count())
print('users', User.objects.filter(profile__organization=o).count())
"

echo "=== health ==="
docker exec jmc_api python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/api/health/', timeout=5).read().decode())"

echo "=== https ==="
curl -k -sS -o /dev/null -w "api:%{http_code}\n" --max-time 15 --resolve si-erp-api.mushaz.com:443:127.0.0.1 https://si-erp-api.mushaz.com/api/health/
curl -k -sS -o /dev/null -w "web:%{http_code}\n" --max-time 15 --resolve si-erp.mushaz.com:443:127.0.0.1 https://si-erp.mushaz.com/
curl -sS -o /dev/null -w "public_web:%{http_code}\n" --max-time 20 https://si-erp.mushaz.com/ || true

# keep RUN_SEED off
if grep -q '^RUN_SEED=' .env 2>/dev/null; then
  sed -i 's/^RUN_SEED=.*/RUN_SEED=0/' .env
else
  echo 'RUN_SEED=0' >> .env
fi
echo DONE
