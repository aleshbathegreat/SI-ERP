#!/bin/bash
set -euo pipefail
JMC=/home/sidms/jmc
cp /tmp/accounts_views.py "$JMC/backend/accounts/views.py"
cp /tmp/hr_views.py "$JMC/backend/hr/views.py"
cp /tmp/hr_serializers.py "$JMC/backend/hr/serializers.py"
docker cp "$JMC/backend/accounts/views.py" jmc_api:/app/accounts/views.py
docker cp "$JMC/backend/hr/views.py" jmc_api:/app/hr/views.py
docker cp "$JMC/backend/hr/serializers.py" jmc_api:/app/hr/serializers.py
docker restart jmc_api
for i in $(seq 1 30); do
  st=$(docker inspect jmc_api --format '{{.State.Health.Status}}' 2>/dev/null || echo starting)
  [ "$st" = "healthy" ] && break
  sleep 2
done
docker inspect jmc_api --format 'api={{.State.Health.Status}}'
grep -n employee_id "$JMC/backend/accounts/views.py" | head -2
echo DONE
