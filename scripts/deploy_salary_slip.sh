#!/bin/bash
set -euo pipefail
JMC=/home/sidms/jmc
mkdir -p "$JMC/backend/payroll" "$JMC/backend/ess"
cp /tmp/payslip_document.py "$JMC/backend/payroll/payslip_document.py"
cp /tmp/ess_views.py "$JMC/backend/ess/views.py"
docker cp /tmp/payslip_document.py jmc_api:/app/payroll/payslip_document.py
docker cp /tmp/ess_views.py jmc_api:/app/ess/views.py
docker restart jmc_api
for i in $(seq 1 30); do
  st=$(docker inspect jmc_api --format '{{.State.Health.Status}}' 2>/dev/null || echo starting)
  [ "$st" = "healthy" ] && break
  sleep 2
done
docker inspect jmc_api --format 'api={{.State.Health.Status}}'
docker exec -w /app jmc_api python - <<'PY'
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
django.setup()
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from payroll.models import Payslip
u = get_user_model().objects.get(username='ess.user')
slip = Payslip.objects.filter(employee=u.employee).order_by('-id').first()
c = APIClient(); c.force_authenticate(user=u)
r = c.get(f'/api/ess/payslips/{slip.id}/print/')
print('status', r.status_code)
print('has_title', b'SALARY SLIP' in r.content)
print('has_net', b'Net salary payable' in r.content)
print('len', len(r.content))
PY
echo DONE
