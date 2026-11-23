#!/bin/bash
set -euo pipefail
JMC=/home/sidms/jmc

# ensure PUBLIC_MEDIA_BASE in compose env if .env exists
if [ -f "$JMC/.env" ] && ! grep -q PUBLIC_MEDIA_BASE "$JMC/.env"; then
  echo 'PUBLIC_MEDIA_BASE=https://si-erp-api.mushaz.com' >> "$JMC/.env"
fi

echo "=== sync backend branding ==="
docker cp "$JMC/backend/core/models.py" jmc_api:/app/core/models.py
docker cp "$JMC/backend/core/tenancy.py" jmc_api:/app/core/tenancy.py
docker cp "$JMC/backend/core/domain_views.py" jmc_api:/app/core/domain_views.py
docker cp "$JMC/backend/core/serializers.py" jmc_api:/app/core/serializers.py
docker cp "$JMC/backend/core/migrations/0007_tenant_branding_assets.py" jmc_api:/app/core/migrations/0007_tenant_branding_assets.py
docker cp "$JMC/backend/config/urls.py" jmc_api:/app/config/urls.py
docker cp "$JMC/backend/config/settings.py" jmc_api:/app/config/settings.py
docker cp "$JMC/backend/accounts/views.py" jmc_api:/app/accounts/views.py
docker cp "$JMC/backend/accounts/mfa.py" jmc_api:/app/accounts/mfa.py

docker exec -e PUBLIC_MEDIA_BASE=https://si-erp-api.mushaz.com jmc_api \
  python manage.py migrate core --noinput

# seed brand tagline if empty
docker exec jmc_api python manage.py shell -c "
from core.models import Organization
for o in Organization.objects.all():
    changed=[]
    if not o.brand_name:
        o.brand_name=o.name; changed.append('brand_name')
    if not o.brand_tagline:
        o.brand_tagline='Accounts · HR · Payroll'; changed.append('brand_tagline')
    if changed:
        o.save(update_fields=changed+['updated_at'])
        print('updated', o.code, changed)
print('orgs', Organization.objects.count())
"

# restart only — force-recreate would wipe docker-cp'd Python modules
docker restart jmc_api
for i in $(seq 1 40); do
  st=$(docker inspect jmc_api --format '{{.State.Health.Status}}' 2>/dev/null || echo starting)
  [ "$st" = "healthy" ] && break
  sleep 2
done
docker inspect jmc_api --format 'api={{.State.Health.Status}}'

echo "=== frontend ==="
cd "$JMC/frontend"
rm -rf .next
mkdir -p .next
tar -xzf "$JMC/frontend-standalone.tgz" -C "$JMC/frontend"
cd "$JMC"
docker compose build web
docker compose up -d --force-recreate web
sleep 4

echo "=== verify ==="
curl -k -sS -o /tmp/brand.json -w "resolve=%{http_code}\n" --max-time 15 \
  --resolve si-erp-api.mushaz.com:443:127.0.0.1 \
  https://si-erp-api.mushaz.com/api/public/resolve-host/
python3 -c "import json;d=json.load(open('/tmp/brand.json'));print({k:d.get(k) for k in ['brand_name','brand_tagline','brand_primary_color','brand_logo_url']})"
curl -k -sS -o /dev/null -w "domain_page=%{http_code}\n" --max-time 15 \
  --resolve si-erp.mushaz.com:443:127.0.0.1 https://si-erp.mushaz.com/settings/domain
docker exec jmc_web sh -c "grep -Rao 'Brand identity\|Live preview\|brand_logo' /app/.next/static 2>/dev/null | sort -u | head -10 || true"
echo DONE
