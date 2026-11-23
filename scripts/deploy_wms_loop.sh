#!/bin/bash
set -euo pipefail
ROOT=/home/sidms/jmc
SRC=/tmp/wms_loop

echo "=== extract backend ==="
rm -rf "$SRC"
mkdir -p "$SRC"
tar -xzf /tmp/wms-loop-backend.tgz -C "$SRC"
cp -a "$SRC"/backend/. "$ROOT/backend/"

echo "=== frontend standalone ==="
if [ -f /tmp/frontend-standalone.tgz ]; then
  cp /tmp/frontend-standalone.tgz "$ROOT/"
  cd "$ROOT/frontend"
  rm -rf .next/standalone .next/static standalone static
  mkdir -p .next
  tar -xzf "$ROOT/frontend-standalone.tgz" -C "$ROOT/frontend"
  [ -d standalone ] && mv standalone .next/standalone
  [ -d static ] && mv static .next/static
  mkdir -p .next/standalone/.next
  rm -rf .next/standalone/.next/static
  cp -a .next/static .next/standalone/.next/static
  date -u +%Y-%m-%dT%H:%M:%SZ > .next/standalone/.deploy-stamp
fi

echo "=== rebuild api + web ==="
cd "$ROOT"
docker compose build api web
docker compose up -d --force-recreate api web
sleep 8
docker exec -w /app -e PYTHONPATH=/app jmc_api python manage.py migrate --noinput

echo "=== smoke ==="
for p in chat ess/chat ess ess/attendance ess/profile ess/performance ess/activity ess/tasks ess/notifications approvals legal/privacy legal/terms legal/cookies legal/acceptable-use legal/data-processing pricing guide crm/leads crm/opportunities crm/calendar crm/mailbox inventory/pick-lists procurement/receipts qms/inspections service/cases finance/maintenance-orders projects projects/timesheets finance/accounts finance/accounts/new finance/periods finance/periods/new finance/journals ess/leave sales/orders sales/contracts/new finance/e-invoices/new dms/documents dms/folders dms/types dms/tags dms/metadata-types dms/workflows inbox comments tasks; do
  curl -k -sS -o /dev/null -w "$p=%{http_code}\n" --max-time 20 \
    --resolve si-erp.mushaz.com:443:127.0.0.1 "https://si-erp.mushaz.com/$p" || true
done
docker inspect jmc_api --format 'api={{.State.Health.Status}}'
docker inspect jmc_web --format 'web={{.State.Status}}'
echo DONE
