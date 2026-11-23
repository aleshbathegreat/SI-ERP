#!/bin/bash
set -euo pipefail
JMC=/home/sidms/jmc
mkdir -p "$JMC/backend/payroll" "$JMC/backend/ess"
cp /tmp/payslip_document.py "$JMC/backend/payroll/payslip_document.py"
cp /tmp/ess_views.py "$JMC/backend/ess/views.py"
docker cp /tmp/payslip_document.py jmc_api:/app/payroll/payslip_document.py
docker cp /tmp/ess_views.py jmc_api:/app/ess/views.py
# clear pycache so python picks up new module
docker exec jmc_api sh -c 'rm -rf /app/payroll/__pycache__ /app/ess/__pycache__'
docker restart jmc_api
for i in $(seq 1 40); do
  st=$(docker inspect jmc_api --format '{{.State.Health.Status}}' 2>/dev/null || echo starting)
  [ "$st" = "healthy" ] && break
  sleep 2
done
docker inspect jmc_api --format 'api={{.State.Health.Status}}'
echo "--- file check ---"
docker exec jmc_api sh -c 'ls -la /app/payroll/payslip_document.py /app/ess/views.py; grep -n "render_salary_slip_html\|SALARY SLIP\|payslip_document" /app/ess/views.py /app/payroll/payslip_document.py | head -20'
echo "--- api smoke ---"
docker exec -w /app jmc_api python /tmp/verify_slip.py 2>/dev/null || docker exec -w /app jmc_api python verify_slip.py
echo DONE
