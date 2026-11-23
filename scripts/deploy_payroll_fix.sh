#!/bin/bash
set -euo pipefail
JMC=/home/sidms/jmc

echo "=== push backend payroll modules ==="
docker cp "$JMC/backend/payroll/views.py" jmc_api:/app/payroll/views.py
docker cp "$JMC/backend/payroll/serializers.py" jmc_api:/app/payroll/serializers.py
docker cp "$JMC/backend/payroll/models.py" jmc_api:/app/payroll/models.py
docker restart jmc_api
echo "waiting api..."
for i in $(seq 1 30); do
  st=$(docker inspect jmc_api --format '{{.State.Health.Status}}' 2>/dev/null || echo starting)
  [ "$st" = "healthy" ] && break
  sleep 2
done
docker inspect jmc_api --format 'api={{.State.Health.Status}}'

echo "=== extract frontend & rebuild web ==="
cd "$JMC/frontend"
rm -rf .next
mkdir -p .next
tar -xzf "$JMC/frontend-standalone.tgz" -C "$JMC/frontend"
cd "$JMC"
docker compose build web
docker compose up -d --force-recreate web
sleep 5

echo "=== verify ==="
TOKEN=$(curl -k -sS --max-time 15 --resolve si-erp-api.mushaz.com:443:127.0.0.1 \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"Admin@123"}' \
  https://si-erp-api.mushaz.com/api/auth/login/ | python3 -c 'import sys,json; print(json.load(sys.stdin).get("access",""))')
PID=$(curl -k -sS --max-time 15 --resolve si-erp-api.mushaz.com:443:127.0.0.1 \
  -H "Authorization: Bearer $TOKEN" https://si-erp-api.mushaz.com/api/payroll/periods/ \
  | python3 -c 'import sys,json; d=json.load(sys.stdin); print((d.get("results") or d)[0]["id"])')
echo "period=$PID"
curl -k -sS -o /tmp/sum.json -w "summary=%{http_code}\n" --max-time 15 \
  --resolve si-erp-api.mushaz.com:443:127.0.0.1 \
  -H "Authorization: Bearer $TOKEN" \
  "https://si-erp-api.mushaz.com/api/payroll/periods/$PID/summary/"
head -c 200 /tmp/sum.json; echo
curl -k -sS -o /dev/null -w "payroll_page=%{http_code}\n" --max-time 15 \
  --resolve si-erp.mushaz.com:443:127.0.0.1 https://si-erp.mushaz.com/payroll
docker exec jmc_web sh -c "grep -Rao 'Active period\|Generate payslips\|Box is not defined' /app/.next/static 2>/dev/null | head -10 || true"
echo DONE
