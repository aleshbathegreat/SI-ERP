#!/bin/bash
set -euo pipefail
JMC=/home/sidms/jmc

mkdir -p "$JMC/backend/core" "$JMC/backend/config" "$JMC/backend/core/management/commands" "$JMC/backend/accounts"
cp /tmp/models.py "$JMC/backend/core/models.py"
cp /tmp/access.py "$JMC/backend/core/access.py"
cp /tmp/serializers.py "$JMC/backend/core/serializers.py"
cp /tmp/platform_views.py "$JMC/backend/core/platform_views.py"
cp /tmp/platform_rbac.py "$JMC/backend/core/platform_rbac.py"
cp /tmp/invoicing.py "$JMC/backend/core/invoicing.py"
cp /tmp/subscription_lifecycle.py "$JMC/backend/core/subscription_lifecycle.py"
cp /tmp/saas_ops_views.py "$JMC/backend/core/saas_ops_views.py"
cp /tmp/middleware.py "$JMC/backend/core/middleware.py"
cp /tmp/billing_payfast.py "$JMC/backend/core/billing_payfast.py"
cp /tmp/email_views.py "$JMC/backend/core/email_views.py"
cp /tmp/domain_views.py "$JMC/backend/core/domain_views.py"
cp /tmp/views_core.py "$JMC/backend/core/views.py"
cp /tmp/urls.py "$JMC/backend/config/urls.py"
cp /tmp/mfa.py "$JMC/backend/accounts/mfa.py"
cp /tmp/accounts_views.py "$JMC/backend/accounts/views.py"
cp /tmp/0008_saas_ops_enterprise.py "$JMC/backend/core/migrations/0008_saas_ops_enterprise.py"
cp /tmp/expire_subscriptions.py "$JMC/backend/core/management/commands/expire_subscriptions.py"
cp /tmp/frontend-standalone.tgz "$JMC/"

for f in \
  models.py access.py serializers.py platform_views.py platform_rbac.py invoicing.py \
  subscription_lifecycle.py saas_ops_views.py middleware.py billing_payfast.py \
  email_views.py domain_views.py views.py; do
  src="$JMC/backend/core/$f"
  [ -f "$src" ] && docker cp "$src" "jmc_api:/app/core/$f"
done
docker cp "$JMC/backend/config/urls.py" jmc_api:/app/config/urls.py
docker cp "$JMC/backend/accounts/mfa.py" jmc_api:/app/accounts/mfa.py
docker cp "$JMC/backend/accounts/views.py" jmc_api:/app/accounts/views.py
docker cp "$JMC/backend/core/migrations/0008_saas_ops_enterprise.py" jmc_api:/app/core/migrations/0008_saas_ops_enterprise.py
docker cp "$JMC/backend/core/management/commands/expire_subscriptions.py" jmc_api:/app/core/management/commands/expire_subscriptions.py

docker exec -w /app jmc_api python manage.py migrate core --noinput
docker restart jmc_api
for i in $(seq 1 40); do
  st=$(docker inspect jmc_api --format '{{.State.Health.Status}}' 2>/dev/null || echo starting)
  [ "$st" = "healthy" ] && break
  sleep 2
done
docker inspect jmc_api --format 'api={{.State.Health.Status}}'

docker exec -w /app jmc_api python manage.py expire_subscriptions --no-mail || true

PACCESS=$(curl -k -sS --max-time 20 --resolve si-erp-api.mushaz.com:443:127.0.0.1 \
  -H 'Content-Type: application/json' \
  -d '{"username":"platform","password":"Platform@123"}' \
  https://si-erp-api.mushaz.com/api/auth/login/ | python3 -c 'import sys,json;d=json.load(sys.stdin);print(d.get("access",""))')

echo "platform_role=$(curl -k -sS --max-time 15 --resolve si-erp-api.mushaz.com:443:127.0.0.1 \
  -H "Authorization: Bearer $PACCESS" \
  https://si-erp-api.mushaz.com/api/platform/me/ | python3 -c 'import sys,json;d=json.load(sys.stdin);print(d.get("platform_role"), len(d.get("platform_capabilities",[])))')"

for path in platform/invoices/ platform/tickets/ platform/staff/ platform/packages/ support/tickets/ saas/invoices/; do
  code=$(curl -k -sS -o /tmp/p.json -w "%{http_code}" --max-time 15 \
    --resolve si-erp-api.mushaz.com:443:127.0.0.1 \
    -H "Authorization: Bearer $PACCESS" \
    "https://si-erp-api.mushaz.com/api/${path}")
  echo "GET /api/${path} -> ${code}"
done

cd "$JMC/frontend"
rm -rf .next && mkdir -p .next
tar -xzf "$JMC/frontend-standalone.tgz" -C "$JMC/frontend"
# normalize layout: tarball may contain standalone/ + static/
if [ -d "$JMC/frontend/standalone" ]; then
  mkdir -p "$JMC/frontend/.next"
  mv "$JMC/frontend/standalone" "$JMC/frontend/.next/standalone"
fi
if [ -d "$JMC/frontend/static" ]; then
  mkdir -p "$JMC/frontend/.next"
  mv "$JMC/frontend/static" "$JMC/frontend/.next/static"
fi
cd "$JMC"
docker compose build web
docker compose up -d --force-recreate web
sleep 5
for path in /platform /platform/invoices /platform/tickets /platform/staff /support /billing; do
  curl -k -sS -o /dev/null -w "${path}=%{http_code}\n" --max-time 15 \
    --resolve si-erp.mushaz.com:443:127.0.0.1 "https://si-erp.mushaz.com${path}"
done
echo DONE
