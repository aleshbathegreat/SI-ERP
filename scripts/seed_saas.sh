#!/bin/bash
set -euo pipefail
# Push updated seed_erp into running api container and reseed SaaS catalog/gateways.
SRC=/home/sidms/jmc/backend/core/management/commands/seed_erp.py
DST=/app/core/management/commands/seed_erp.py

if [ ! -f "$SRC" ]; then
  echo "missing $SRC — copy from workstation first"
  exit 1
fi

docker cp "$SRC" "jmc_api:$DST"
docker exec jmc_api python manage.py seed_erp

echo
echo "=== SaaS catalog / gateways ==="
docker exec jmc_api python manage.py shell -c "
from core.models import (
    SubscriptionPackage, PayFastSettings, PlatformSmtpSettings,
    TenantPayGateway, TenantSmtpSettings, SubscriptionPayment, Organization,
)
print('packages:')
for p in SubscriptionPackage.objects.order_by('sort'):
    print(f'  {p.code:12} {p.name:12} {p.price} {p.interval} active={p.active}')
pf = PayFastSettings.load()
print('platform_payfast', pf.environment, 'merchant=', pf.sandbox_merchant_id or '(empty)', 'ready=', pf.ready)
smtp = PlatformSmtpSettings.load()
print('platform_smtp', smtp.host, 'active=', smtp.is_active, 'from=', smtp.from_email)
o = Organization.objects.get(code='jmc')
print('org_package', o.package_id and o.package.code, 'plan', o.plan, 'trial_ends', o.trial_ends)
gw = TenantPayGateway.objects.filter(organization=o).first()
print('tenant_payfast', gw.environment if gw else None, getattr(gw, 'sandbox_merchant_id', None))
ts = TenantSmtpSettings.objects.filter(organization=o).first()
print('tenant_smtp', ts.host if ts else None, 'active=', getattr(ts, 'is_active', None))
print('payments', SubscriptionPayment.objects.filter(organization=o).count())
for pay in SubscriptionPayment.objects.filter(organization=o).order_by('-id')[:5]:
    print(f'  {pay.reference} {pay.plan} {pay.status} {pay.amount}')
"
echo DONE
