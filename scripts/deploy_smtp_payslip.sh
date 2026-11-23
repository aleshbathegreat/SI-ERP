#!/bin/bash
set -euo pipefail
JMC=/home/sidms/jmc

cp /tmp/frontend-standalone.tgz "$JMC/"
cp /tmp/mailer.py "$JMC/backend/core/mailer.py"
mkdir -p "$JMC/backend/payroll"
cp /tmp/emails.py "$JMC/backend/payroll/emails.py"
cp /tmp/views.py "$JMC/backend/payroll/views.py"
cp /tmp/configure_tenant_smtp.sh "$JMC/configure_tenant_smtp.sh"
sed -i 's/\r$//' "$JMC/configure_tenant_smtp.sh"

docker cp "$JMC/backend/core/mailer.py" jmc_api:/app/core/mailer.py
docker cp "$JMC/backend/payroll/emails.py" jmc_api:/app/payroll/emails.py
docker cp "$JMC/backend/payroll/views.py" jmc_api:/app/payroll/views.py
docker restart jmc_api
for i in $(seq 1 40); do
  st=$(docker inspect jmc_api --format '{{.State.Health.Status}}' 2>/dev/null || echo starting)
  [ "$st" = "healthy" ] && break
  sleep 2
done
docker inspect jmc_api --format 'api={{.State.Health.Status}}'

export SMTP_HOST="${SMTP_HOST:-smtp.gmail.com}"
export SMTP_PORT="${SMTP_PORT:-587}"
export SMTP_USER="${SMTP_USER:?}"
export SMTP_PASSWORD="${SMTP_PASSWORD:?}"
export SMTP_FROM_NAME="${SMTP_FROM_NAME:-JMC ERP Payroll}"
export ORG_CODE="${ORG_CODE:-jmc}"
bash "$JMC/configure_tenant_smtp.sh"

cd "$JMC/frontend"
rm -rf .next
mkdir -p .next
tar -xzf "$JMC/frontend-standalone.tgz" -C "$JMC/frontend"
cd "$JMC"
docker compose build web
docker compose up -d --force-recreate web
sleep 4
docker exec jmc_web sh -c "grep -Rao 'Email payslips' /app/.next/static 2>/dev/null | head -3 || true"
echo ALL_DONE
