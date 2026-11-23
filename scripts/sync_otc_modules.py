import django
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from accounts.rbac import ensure_default_roles
from core.access import ensure_default_packages
from core.models import Organization, SubscriptionPackage

ensure_default_packages()
new_sales = ["sales.quotes", "sales.invoices"]
new_proc = ["procurement.receipts"]
for pkg in SubscriptionPackage.objects.all():
    mods = list(pkg.module_keys or [])
    changed = False
    if "sales.orders" in mods or "*" in mods:
        for k in new_sales:
            if k not in mods and "*" not in mods:
                mods.append(k)
                changed = True
    if "procurement.orders" in mods or "*" in mods:
        for k in new_proc:
            if k not in mods and "*" not in mods:
                mods.append(k)
                changed = True
    if changed:
        pkg.module_keys = mods
        pkg.save(update_fields=["module_keys"])
        print("package_updated", pkg.code)
for org in Organization.objects.filter(is_active=True):
    ensure_default_roles(org)
print("roles_ok", Organization.objects.filter(is_active=True).count())
