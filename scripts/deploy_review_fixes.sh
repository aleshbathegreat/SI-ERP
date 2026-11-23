#!/bin/bash
set -euo pipefail
JMC=/home/sidms/jmc

mkdir -p \
  "$JMC/backend/core" \
  "$JMC/backend/core/migrations" \
  "$JMC/backend/finance" \
  "$JMC/backend/finance/migrations" \
  "$JMC/backend/hr/migrations" \
  "$JMC/backend/payroll/migrations" \
  "$JMC/backend/config" \
  "$JMC/frontend/.next"

cp /tmp/softdelete.py "$JMC/backend/core/softdelete.py"
cp /tmp/exceptions.py "$JMC/backend/core/exceptions.py"
cp /tmp/bulk.py "$JMC/backend/core/bulk.py"
cp /tmp/core_models.py "$JMC/backend/core/models.py"
cp /tmp/settings.py "$JMC/backend/config/settings.py"
cp /tmp/finance_serializers.py "$JMC/backend/finance/serializers.py"
cp /tmp/0011_soft_delete.py "$JMC/backend/core/migrations/0011_soft_delete.py"
cp /tmp/0005_soft_delete_finance.py "$JMC/backend/finance/migrations/0005_soft_delete.py"
cp /tmp/0006_soft_delete_hr.py "$JMC/backend/hr/migrations/0006_soft_delete.py"
cp /tmp/0005_soft_delete_payroll.py "$JMC/backend/payroll/migrations/0005_soft_delete.py"
cp /tmp/frontend-standalone.tgz "$JMC/"

docker cp "$JMC/backend/core/softdelete.py" jmc_api:/app/core/softdelete.py
docker cp "$JMC/backend/core/exceptions.py" jmc_api:/app/core/exceptions.py
docker cp "$JMC/backend/core/bulk.py" jmc_api:/app/core/bulk.py
docker cp "$JMC/backend/core/models.py" jmc_api:/app/core/models.py
docker cp "$JMC/backend/config/settings.py" jmc_api:/app/config/settings.py
docker cp "$JMC/backend/finance/serializers.py" jmc_api:/app/finance/serializers.py
docker cp "$JMC/backend/core/migrations/0011_soft_delete.py" jmc_api:/app/core/migrations/0011_soft_delete.py
docker cp "$JMC/backend/finance/migrations/0005_soft_delete.py" jmc_api:/app/finance/migrations/0005_soft_delete.py
docker cp "$JMC/backend/hr/migrations/0006_soft_delete.py" jmc_api:/app/hr/migrations/0006_soft_delete.py
docker cp "$JMC/backend/payroll/migrations/0005_soft_delete.py" jmc_api:/app/payroll/migrations/0005_soft_delete.py

docker exec -w /app jmc_api python manage.py migrate --noinput
docker restart jmc_api

cd "$JMC/frontend"
rm -rf .next/standalone .next/static standalone static
mkdir -p .next
tar -xzf "$JMC/frontend-standalone.tgz" -C "$JMC/frontend"
[ -d standalone ] && mv standalone .next/standalone
[ -d static ] && mv static .next/static
if [ -d .next/static/static ]; then
  mv .next/static/static/* .next/static/ || true
  rm -rf .next/static/static
fi
mkdir -p .next/standalone/.next
rm -rf .next/standalone/.next/static
cp -a .next/static .next/standalone/.next/static

cd "$JMC"
docker compose build web
docker compose up -d --force-recreate web

for i in $(seq 1 40); do
  st=$(docker inspect jmc_api --format '{{.State.Health.Status}}' 2>/dev/null || echo starting)
  [ "$st" = "healthy" ] && break
  sleep 2
done
docker inspect jmc_api --format 'api={{.State.Health.Status}}'
sleep 4
curl -k -sS -o /dev/null -w "web=%{http_code}\n" --max-time 20 \
  --resolve si-erp.mushaz.com:443:127.0.0.1 https://si-erp.mushaz.com/login
echo DONE
