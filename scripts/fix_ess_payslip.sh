#!/bin/bash
set -euo pipefail
cp /tmp/ess_views.py /home/sidms/jmc/backend/ess/views.py
docker cp /tmp/ess_views.py jmc_api:/app/ess/views.py
docker restart jmc_api
for i in $(seq 1 30); do
  st=$(docker inspect jmc_api --format '{{.State.Health.Status}}' 2>/dev/null || echo starting)
  [ "$st" = "healthy" ] && break
  sleep 2
done
docker inspect jmc_api --format 'api={{.State.Health.Status}}'
docker cp /tmp/test_payslip.py jmc_api:/app/test_payslip.py
docker exec -w /app jmc_api python test_payslip.py
docker exec jmc_api rm -f /app/test_payslip.py
echo DONE
