#!/bin/bash
set -e
cd ~/jmc

echo "=== containers ==="
docker compose ps

echo "=== networks ==="
docker inspect jmc_api -f '{{range $k,$v := .NetworkSettings.Networks}}{{$k}} {{end}}'
docker inspect jmc_web -f '{{range $k,$v := .NetworkSettings.Networks}}{{$k}} {{end}}'
docker inspect scpms-frontend-1 -f '{{range $k,$v := .NetworkSettings.Networks}}{{$k}} {{end}}' 2>/dev/null || true

echo "=== jmc web traefik labels ==="
docker inspect jmc_web --format '{{json .Config.Labels}}' | python3 -c "import sys,json; d=json.load(sys.stdin); print('\n'.join(f'{k}={v}' for k,v in sorted(d.items()) if 'traefik' in k))"

echo "=== jmc api traefik labels ==="
docker inspect jmc_api --format '{{json .Config.Labels}}' | python3 -c "import sys,json; d=json.load(sys.stdin); print('\n'.join(f'{k}={v}' for k,v in sorted(d.items()) if 'traefik' in k))"

echo "=== scpms frontend traefik labels ==="
docker inspect scpms-frontend-1 --format '{{json .Config.Labels}}' | python3 -c "import sys,json; d=json.load(sys.stdin); print('\n'.join(f'{k}={v}' for k,v in sorted(d.items()) if 'traefik' in k))" 2>/dev/null || true

echo "=== sipulse frontend traefik labels ==="
docker inspect sipulse-frontend-1 --format '{{json .Config.Labels}}' | python3 -c "import sys,json; d=json.load(sys.stdin); print('\n'.join(f'{k}={v}' for k,v in sorted(d.items()) if 'traefik' in k))" 2>/dev/null || docker ps -a --format '{{.Names}}' | grep -i sipulse | head

echo "=== internal health ==="
docker exec jmc_api python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/api/health/').read().decode())"

echo "=== via traefik http host headers ==="
curl -sS -o /tmp/h.txt -w "api_http:%{http_code}\n" -H "Host: si-erp-api.sidms.online" http://127.0.0.1/api/health/ || true
head -c 200 /tmp/h.txt; echo
curl -sS -o /tmp/w.txt -w "web_http:%{http_code}\n" -H "Host: si-erp.sidms.online" http://127.0.0.1/login || true
head -c 200 /tmp/w.txt; echo

echo "=== demo seed counts ==="
docker exec jmc_api python manage.py shell -c "
from core.models import Organization
from finance.models import Account, Vendor, JournalEntry
from hr.models import Employee
from payroll.models import Payslip
from django.contrib.auth.models import User
o=Organization.objects.filter(code='jmc').first()
print('org', o)
if o:
  print('accounts', Account.objects.filter(organization=o).count())
  print('vendors', Vendor.objects.filter(organization=o).count())
  print('journals', JournalEntry.objects.filter(organization=o).count())
  print('employees', Employee.objects.filter(organization=o).count())
  print('payslips', Payslip.objects.filter(period__organization=o).count())
  print('users', User.objects.filter(profile__organization=o).count())
"

echo "=== compose env RUN_SEED ==="
grep RUN_SEED .env || true
