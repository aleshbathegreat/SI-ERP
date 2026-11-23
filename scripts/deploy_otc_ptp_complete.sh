#!/bin/bash
set -euo pipefail
ROOT=/home/sidms/jmc
SRC=/tmp/jmc_otc_ptp
rm -rf "$SRC"
mkdir -p "$SRC"
tar -xzf /tmp/otc-ptp-complete.tgz -C "$SRC"

for app in ops finance core accounts config; do
  if [ -d "$SRC/backend/$app" ]; then
    mkdir -p "$ROOT/backend/$app"
    find "$SRC/backend/$app" -type d -name '__pycache__' -prune -exec rm -rf {} + 2>/dev/null || true
    cp -a "$SRC/backend/$app/." "$ROOT/backend/$app/"
    docker cp "$ROOT/backend/$app/." "jmc_api:/app/$app/"
  fi
done
# config may be single files
if [ -f "$SRC/backend/config/urls.py" ]; then
  cp -a "$SRC/backend/config/urls.py" "$ROOT/backend/config/urls.py"
  docker cp "$ROOT/backend/config/urls.py" jmc_api:/app/config/urls.py
fi

docker exec -w /app jmc_api python manage.py migrate ops --noinput
docker exec -w /app jmc_api python manage.py migrate finance --noinput
docker exec -w /app jmc_api python -c "
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
django.setup()
from accounts.rbac import ASSIGNABLE_MODULE_KEYS, ensure_default_roles
from core.access import ensure_default_packages
from core.models import Organization, SubscriptionPackage
ensure_default_packages()
# Merge new module keys into existing packages that already have sales.orders / procurement.orders
new_sales = ['sales.quotes','sales.invoices']
new_proc = ['procurement.receipts']
for pkg in SubscriptionPackage.objects.all():
    mods = list(pkg.module_keys or [])
    changed = False
    if 'sales.orders' in mods or '*' in mods:
        for k in new_sales:
            if k not in mods and '*' not in mods:
                mods.append(k); changed = True
    if 'procurement.orders' in mods or '*' in mods:
        for k in new_proc:
            if k not in mods and '*' not in mods:
                mods.append(k); changed = True
    if changed:
        pkg.module_keys = mods
        pkg.save(update_fields=['module_keys'])
        print('package_updated', pkg.code)
for org in Organization.objects.filter(is_active=True):
    ensure_default_roles(org)
print('roles_ok')
"

docker restart jmc_api
for i in $(seq 1 40); do
  st=$(docker inspect jmc_api --format '{{.State.Health.Status}}' 2>/dev/null || echo starting)
  [ "$st" = "healthy" ] && break
  sleep 2
done
docker inspect jmc_api --format 'api={{.State.Health.Status}}'

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
cd "$ROOT"
docker compose build web
docker compose up -d --force-recreate web
sleep 6
for p in sales/quotes sales/invoices sales/orders procurement/receipts procurement/orders finance/invoices; do
  curl -k -sS -o /dev/null -w "$p=%{http_code}\n" --max-time 20 \
    --resolve si-erp.mushaz.com:443:127.0.0.1 "https://si-erp.mushaz.com/$p"
done
echo DONE
