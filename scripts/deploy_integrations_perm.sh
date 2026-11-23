#!/bin/bash
set -euo pipefail
JMC=/home/sidms/jmc
SRC=/tmp/jmc_int_perm
rm -rf "$SRC"
mkdir -p "$SRC"
tar -xzf /tmp/integrations-perm-fix.tgz -C "$SRC"
cp -a "$SRC/backend/accounts/rbac.py" "$JMC/backend/accounts/rbac.py"
cp -a "$SRC/backend/accounts/mfa.py" "$JMC/backend/accounts/mfa.py"
cp -a "$SRC/backend/accounts/views.py" "$JMC/backend/accounts/views.py"
docker cp "$JMC/backend/accounts/rbac.py" jmc_api:/app/accounts/rbac.py
docker cp "$JMC/backend/accounts/mfa.py" jmc_api:/app/accounts/mfa.py
docker cp "$JMC/backend/accounts/views.py" jmc_api:/app/accounts/views.py
docker exec -w /app jmc_api python -c "
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
django.setup()
from core.access import ensure_default_packages
from core.models import Organization, SubscriptionPackage
from accounts.rbac import ensure_default_roles, CORE_MODULE_KEYS, effective_package_modules
ensure_default_packages()
n=0
for org in Organization.objects.filter(is_active=True):
    ensure_default_roles(org); n+=1
print('roles', n)
print('core_has_integrations', 'settings.integrations' in CORE_MODULE_KEYS)
for p in SubscriptionPackage.objects.all():
    eff=effective_package_modules(p)
    print(p.code, 'settings.integrations' in eff)
"
docker restart jmc_api
for i in $(seq 1 40); do
  st=$(docker inspect jmc_api --format '{{.State.Health.Status}}' 2>/dev/null || echo starting)
  [ "$st" = "healthy" ] && break
  sleep 2
done
docker inspect jmc_api --format 'api={{.State.Health.Status}}'
echo DONE
