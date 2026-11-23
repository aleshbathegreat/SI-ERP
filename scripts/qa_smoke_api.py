"""QA smoke: URL routes, model imports, package module keys."""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.urls import get_resolver, URLPattern, URLResolver
from accounts.rbac import MODULES, ASSIGNABLE_MODULE_KEYS, effective_package_modules
from core.models import SubscriptionPackage

print("=== DJANGO CHECK PATHS ===")
patterns = []


def walk(patterns_list, prefix=""):
    for p in patterns_list:
        if isinstance(p, URLResolver):
            walk(p.url_patterns, prefix + str(p.pattern))
        elif isinstance(p, URLPattern):
            patterns.append(prefix + str(p.pattern))


walk(get_resolver().url_patterns)
need = [
    "api/sales/quotes/",
    "api/sales/invoices/",
    "api/sales/orders/",
    "api/procurement/orders/",
    "api/procurement/receipts/",
    "api/finance/invoices/",
    "api/hr/employees/",
    "api/approvals/inbox/",
]
for n in need:
    ok = any(n.rstrip("/") in u.replace("^", "") for u in patterns)
    print(("OK " if ok else "MISS"), n)

print("\n=== MODULE KEYS ===")
for k in ["sales.quotes", "sales.invoices", "procurement.receipts"]:
    print(k, "in MODULES" if k in MODULES else "MISSING MODULES")
    print(k, "assignable" if k in ASSIGNABLE_MODULE_KEYS else "not assignable")

print("\n=== PACKAGE COVERAGE ===")
for pkg in SubscriptionPackage.objects.all():
    mods = effective_package_modules(pkg)
    missing = []
    if any(m.startswith("sales.") for m in mods):
        for k in ["sales.quotes", "sales.invoices"]:
            if k not in mods:
                missing.append(k)
    if any(m.startswith("procurement.") for m in mods):
        if "procurement.receipts" not in mods:
            missing.append("procurement.receipts")
    print(pkg.code, "missing=" + ",".join(missing) if missing else "ok", "n=" + str(len(mods)))

print("\n=== IMPORTS ===")
import ops.views as ov
import finance.views as fv

for name, obj in [
    ("SalesQuotationViewSet", getattr(ov, "SalesQuotationViewSet", None)),
    ("GoodsReceiptViewSet", getattr(ov, "GoodsReceiptViewSet", None)),
    ("CustomerInvoiceViewSet", getattr(fv, "CustomerInvoiceViewSet", None)),
]:
    print(name, "OK" if obj else "MISSING")

print("\n=== MODEL COUNTS ===")
from ops.models import SalesQuotation, GoodsReceipt, SalesOrder, PurchaseOrder
from finance.models import CustomerInvoice, VendorInvoice

for label, model in [
    ("quotes", SalesQuotation),
    ("grn", GoodsReceipt),
    ("ar", CustomerInvoice),
    ("ap", VendorInvoice),
    ("so", SalesOrder),
    ("po", PurchaseOrder),
]:
    print(label, model.objects.count())

print("DONE")
