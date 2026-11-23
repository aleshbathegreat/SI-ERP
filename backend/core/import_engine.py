"""Tenant CSV import catalog: templates, validate (dry-run), commit (upsert)."""

from __future__ import annotations

import csv
import io
import re
import zipfile
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Callable

from django.db import transaction

from core.models import Organization

# Recommended load order for a greenfield / cutover (dependencies first).
IMPORT_ORDER: tuple[str, ...] = (
    "chart_of_accounts",
    "cost_centers",
    "tax_codes",
    "departments",
    "designations",
    "warehouses",
    "vendors",
    "customers",
    "items",
    "employees",
    "leave_balances",
    "fixed_assets",
    "opening_journals",
    "crm_leads",
    "projects",
)


def _norm(key: str | None) -> str:
    if not key:
        return ""
    return re.sub(r"[\s\-]+", "_", str(key).strip().lower())


def _row_get(row: dict[str, str], *aliases: str, default: str = "") -> str:
    for a in aliases:
        k = _norm(a)
        if k in row and row[k] not in (None, ""):
            return str(row[k]).strip()
    return default


def _parse_date(raw: str) -> date | None:
    s = (raw or "").strip()
    if not s:
        return None
    if "T" in s:
        s = s.split("T", 1)[0]
    s10 = s[:10]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y", "%d/%m/%y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s10 if len(fmt) <= 10 else s, fmt).date()
        except ValueError:
            continue
    try:
        return date.fromisoformat(s10)
    except ValueError:
        return None


def _dec(raw: str, default: str = "0") -> Decimal:
    s = (raw or default).strip().replace(",", "")
    if not s:
        s = default
    try:
        return Decimal(s)
    except (InvalidOperation, ValueError):
        raise ValueError(f"Invalid number: {raw!r}")


def _bool(raw: str, default: bool = True) -> bool:
    s = (raw or "").strip().lower()
    if not s:
        return default
    if s in ("1", "true", "yes", "y", "active"):
        return True
    if s in ("0", "false", "no", "n", "inactive"):
        return False
    return default


def _read_csv(text: str) -> tuple[list[str], list[dict[str, str]]]:
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return [], []
    headers = [str(h).strip() for h in reader.fieldnames if h and str(h).strip()]
    rows: list[dict[str, str]] = []
    for i, raw in enumerate(reader, start=2):
        if not raw or all(not (v or "").strip() for v in raw.values()):
            continue
        rows.append({_norm(k): (v or "").strip() for k, v in raw.items() if k})
    return headers, rows


@dataclass
class ColumnSpec:
    name: str
    required: bool = False
    help: str = ""
    example: str = ""


@dataclass
class ImportResult:
    created: int = 0
    updated: int = 0
    skipped: int = 0
    errors: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[dict[str, Any]] = field(default_factory=list)
    preview_rows: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "created": self.created,
            "updated": self.updated,
            "skipped": self.skipped,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "errors": self.errors[:100],
            "warnings": self.warnings[:50],
            "preview_rows": self.preview_rows[:25],
        }


ImporterFn = Callable[[Organization, list[dict[str, str]], bool, ImportResult], None]


@dataclass
class EntitySpec:
    key: str
    label: str
    description: str
    module: str
    columns: list[ColumnSpec]
    sample_rows: list[dict[str, str]]
    run: ImporterFn


def _require(row: dict[str, str], line: int, *names: str) -> str | None:
    for n in names:
        if _row_get(row, n):
            return None
    return f"Row {line}: missing required {names[0]}"


# ── importers ──────────────────────────────────────────────────────────────


def _imp_coa(org, rows, dry, result: ImportResult):
    from finance.models import Account

    for i, row in enumerate(rows, start=2):
        code = _row_get(row, "code", "account_code")
        name = _row_get(row, "name", "account_name")
        if not code or not name:
            result.errors.append({"row": i, "message": "code and name required"})
            continue
        atype = _row_get(row, "account_type", "type", default="expense") or "expense"
        parent_code = _row_get(row, "parent_code")
        preview = {"code": code, "name": name, "account_type": atype}
        result.preview_rows.append(preview)
        if dry:
            continue
        parent = None
        if parent_code:
            parent = Account.objects.filter(organization=org, code=parent_code).first()
            if not parent:
                result.warnings.append(
                    {"row": i, "message": f"parent_code {parent_code} not found"}
                )
        _, created = Account.objects.update_or_create(
            organization=org,
            code=code,
            defaults={
                "name": name,
                "account_type": atype,
                "parent": parent,
                "is_active": _bool(_row_get(row, "is_active"), True),
            },
        )
        if created:
            result.created += 1
        else:
            result.updated += 1


def _imp_cost_centers(org, rows, dry, result: ImportResult):
    from finance.models import CostCenter

    for i, row in enumerate(rows, start=2):
        code = _row_get(row, "code")
        name = _row_get(row, "name")
        if not code or not name:
            result.errors.append({"row": i, "message": "code and name required"})
            continue
        result.preview_rows.append({"code": code, "name": name})
        if dry:
            continue
        _, created = CostCenter.objects.update_or_create(
            organization=org,
            code=code,
            defaults={"name": name, "is_active": _bool(_row_get(row, "is_active"), True)},
        )
        result.created += int(created)
        result.updated += int(not created)


def _imp_vendors(org, rows, dry, result: ImportResult):
    from finance.models import Vendor

    for i, row in enumerate(rows, start=2):
        name = _row_get(row, "name", "vendor_name")
        if not name:
            result.errors.append({"row": i, "message": "name required"})
            continue
        code = _row_get(row, "code", "vendor_code") or name[:32].upper().replace(" ", "")
        result.preview_rows.append({"code": code, "name": name})
        if dry:
            continue
        defaults = {
            "name": name,
            "ntn": _row_get(row, "ntn", "tax_id"),
            "email": _row_get(row, "email"),
            "phone": _row_get(row, "phone"),
            "address": _row_get(row, "address"),
            "contact_person": _row_get(row, "contact_person", "contact"),
            "city": _row_get(row, "city"),
            "country": _row_get(row, "country", default="Pakistan") or "Pakistan",
            "currency": _row_get(row, "currency", default="PKR") or "PKR",
            "payment_terms_days": int(_row_get(row, "payment_terms_days", default="30") or 30),
            "is_active": _bool(_row_get(row, "is_active"), True),
        }
        try:
            defaults["credit_limit"] = _dec(_row_get(row, "credit_limit"))
        except ValueError as e:
            result.errors.append({"row": i, "message": str(e)})
            continue
        obj = Vendor.objects.filter(organization=org, code=code).first()
        if obj is None and not code:
            obj = Vendor.objects.filter(organization=org, name=name).first()
        if obj:
            for k, v in defaults.items():
                setattr(obj, k, v)
            if code:
                obj.code = code
            obj.save()
            result.updated += 1
        else:
            Vendor.objects.create(organization=org, code=code, **defaults)
            result.created += 1


def _imp_customers(org, rows, dry, result: ImportResult):
    from ops.models import Customer

    for i, row in enumerate(rows, start=2):
        code = _row_get(row, "code", "customer_code")
        name = _row_get(row, "name", "customer_name")
        if not code or not name:
            result.errors.append({"row": i, "message": "code and name required"})
            continue
        result.preview_rows.append({"code": code, "name": name})
        if dry:
            continue
        try:
            credit = _dec(_row_get(row, "credit_limit"))
            terms = int(_row_get(row, "payment_terms_days", default="30") or 30)
        except ValueError as e:
            result.errors.append({"row": i, "message": str(e)})
            continue
        _, created = Customer.objects.update_or_create(
            organization=org,
            code=code,
            defaults={
                "name": name,
                "email": _row_get(row, "email"),
                "phone": _row_get(row, "phone"),
                "ntn": _row_get(row, "ntn"),
                "address": _row_get(row, "address"),
                "contact_person": _row_get(row, "contact_person", "contact"),
                "city": _row_get(row, "city"),
                "country": _row_get(row, "country", default="Pakistan") or "Pakistan",
                "currency": _row_get(row, "currency", default="PKR") or "PKR",
                "payment_terms_days": terms,
                "credit_limit": credit,
                "notes": _row_get(row, "notes"),
                "is_active": _bool(_row_get(row, "is_active"), True),
            },
        )
        result.created += int(created)
        result.updated += int(not created)


def _imp_warehouses(org, rows, dry, result: ImportResult):
    from ops.models import Warehouse

    for i, row in enumerate(rows, start=2):
        code = _row_get(row, "code")
        name = _row_get(row, "name")
        if not code or not name:
            result.errors.append({"row": i, "message": "code and name required"})
            continue
        result.preview_rows.append({"code": code, "name": name})
        if dry:
            continue
        _, created = Warehouse.objects.update_or_create(
            organization=org,
            code=code,
            defaults={
                "name": name,
                "address": _row_get(row, "address"),
                "is_default": _bool(_row_get(row, "is_default"), False),
                "is_active": _bool(_row_get(row, "is_active"), True),
            },
        )
        result.created += int(created)
        result.updated += int(not created)


def _imp_items(org, rows, dry, result: ImportResult):
    from ops.models import Item, Warehouse

    for i, row in enumerate(rows, start=2):
        sku = _row_get(row, "sku", "item_code", "code")
        name = _row_get(row, "name", "item_name")
        if not sku or not name:
            result.errors.append({"row": i, "message": "sku and name required"})
            continue
        result.preview_rows.append({"sku": sku, "name": name})
        if dry:
            continue
        wh = None
        wh_code = _row_get(row, "warehouse_code", "default_warehouse")
        if wh_code:
            wh = Warehouse.objects.filter(organization=org, code=wh_code).first()
            if not wh:
                result.warnings.append(
                    {"row": i, "message": f"warehouse_code {wh_code} not found"}
                )
        try:
            defaults = {
                "name": name,
                "barcode": _row_get(row, "barcode"),
                "category": _row_get(row, "category"),
                "description": _row_get(row, "description"),
                "unit": _row_get(row, "unit", default="ea") or "ea",
                "item_type": _row_get(row, "item_type", default="stockable") or "stockable",
                "valuation_method": _row_get(row, "valuation_method", default="average")
                or "average",
                "default_warehouse": wh,
                "reorder_level": _dec(_row_get(row, "reorder_level")),
                "max_level": _dec(_row_get(row, "max_level")),
                "unit_cost": _dec(_row_get(row, "unit_cost", "cost")),
                "sales_price": _dec(_row_get(row, "sales_price", "price")),
                "is_active": _bool(_row_get(row, "is_active"), True),
                "track_serial": _bool(_row_get(row, "track_serial"), False),
                "track_batch": _bool(_row_get(row, "track_batch"), False),
            }
        except ValueError as e:
            result.errors.append({"row": i, "message": str(e)})
            continue
        _, created = Item.objects.update_or_create(
            organization=org, sku=sku, defaults=defaults
        )
        result.created += int(created)
        result.updated += int(not created)


def _imp_departments(org, rows, dry, result: ImportResult):
    from hr.models import Department

    for i, row in enumerate(rows, start=2):
        code = _row_get(row, "code", "dept_code")
        name = _row_get(row, "name", "dept_name")
        if not code or not name:
            result.errors.append({"row": i, "message": "code and name required"})
            continue
        result.preview_rows.append({"code": code, "name": name})
        if dry:
            continue
        parent = None
        pc = _row_get(row, "parent_code")
        if pc:
            parent = Department.objects.filter(organization=org, code=pc).first()
        _, created = Department.objects.update_or_create(
            organization=org, code=code, defaults={"name": name, "parent": parent}
        )
        result.created += int(created)
        result.updated += int(not created)


def _imp_designations(org, rows, dry, result: ImportResult):
    from hr.models import Designation

    for i, row in enumerate(rows, start=2):
        code = _row_get(row, "code", "desig_code")
        title = _row_get(row, "title", "name", "desig_name")
        if not code or not title:
            result.errors.append({"row": i, "message": "code and title required"})
            continue
        result.preview_rows.append({"code": code, "title": title})
        if dry:
            continue
        _, created = Designation.objects.update_or_create(
            organization=org,
            code=code,
            defaults={"title": title, "grade": _row_get(row, "grade")},
        )
        result.created += int(created)
        result.updated += int(not created)


def _imp_employees(org, rows, dry, result: ImportResult):
    from hr.models import Department, Designation, Employee

    for i, row in enumerate(rows, start=2):
        code = _row_get(row, "employee_code", "code", "emp_code")
        first = _row_get(row, "first_name", "firstname")
        last = _row_get(row, "last_name", "lastname")
        if not code or not first:
            result.errors.append(
                {"row": i, "message": "employee_code and first_name required"}
            )
            continue
        email = _row_get(row, "email") or f"{code.lower()}@imported.local"
        result.preview_rows.append(
            {"employee_code": code, "first_name": first, "last_name": last, "email": email}
        )
        if dry:
            continue
        dept = None
        desig = None
        dc = _row_get(row, "dept_code", "department_code")
        if dc:
            dept, _ = Department.objects.get_or_create(
                organization=org, code=dc, defaults={"name": dc}
            )
        dsc = _row_get(row, "desig_code", "designation_code")
        if dsc:
            desig, _ = Designation.objects.get_or_create(
                organization=org, code=dsc, defaults={"title": dsc}
            )
        try:
            salary = _dec(_row_get(row, "basic_salary", "salary"))
        except ValueError as e:
            result.errors.append({"row": i, "message": str(e)})
            continue
        joining = _parse_date(_row_get(row, "date_of_joining", "joining_date"))
        defaults = {
            "first_name": first,
            "last_name": last or "",
            "email": email,
            "phone": _row_get(row, "phone"),
            "department": dept,
            "designation": desig,
            "basic_salary": salary,
            "status": _row_get(row, "status", default="active") or "active",
        }
        if joining:
            defaults["date_of_joining"] = joining
        dob = _parse_date(_row_get(row, "date_of_birth", "dob"))
        if dob:
            defaults["date_of_birth"] = dob
        _, created = Employee.objects.update_or_create(
            organization=org, employee_code=code, defaults=defaults
        )
        result.created += int(created)
        result.updated += int(not created)


def _imp_leave_balances(org, rows, dry, result: ImportResult):
    from hr.models import Employee, LeaveBalance, LeaveType

    for i, row in enumerate(rows, start=2):
        emp_code = _row_get(row, "employee_code", "emp_code")
        lt_code = _row_get(row, "leave_type_code", "leave_type")
        if not emp_code or not lt_code:
            result.errors.append(
                {"row": i, "message": "employee_code and leave_type_code required"}
            )
            continue
        year = int(_row_get(row, "year", default=str(date.today().year)) or date.today().year)
        result.preview_rows.append(
            {"employee_code": emp_code, "leave_type_code": lt_code, "year": year}
        )
        if dry:
            continue
        emp = Employee.objects.filter(organization=org, employee_code=emp_code).first()
        if not emp:
            result.errors.append({"row": i, "message": f"unknown employee {emp_code}"})
            continue
        lt, _ = LeaveType.objects.get_or_create(
            organization=org, code=lt_code, defaults={"name": lt_code}
        )
        try:
            defaults = {
                "opening": _dec(_row_get(row, "opening")),
                "accrued": _dec(_row_get(row, "accrued")),
                "used": _dec(_row_get(row, "used")),
                "encashed": _dec(_row_get(row, "encashed")),
                "carried_forward": _dec(_row_get(row, "carried_forward", "cf")),
            }
        except ValueError as e:
            result.errors.append({"row": i, "message": str(e)})
            continue
        _, created = LeaveBalance.objects.update_or_create(
            organization=org,
            employee=emp,
            leave_type=lt,
            year=year,
            defaults=defaults,
        )
        result.created += int(created)
        result.updated += int(not created)


def _imp_assets(org, rows, dry, result: ImportResult):
    from finance.models import FixedAsset

    for i, row in enumerate(rows, start=2):
        code = _row_get(row, "asset_code", "code")
        name = _row_get(row, "name") or code
        if not code:
            result.errors.append({"row": i, "message": "asset_code required"})
            continue
        result.preview_rows.append({"asset_code": code, "name": name})
        if dry:
            continue
        try:
            cost = _dec(_row_get(row, "purchase_cost", "cost"))
            rate = _dec(_row_get(row, "depreciation_rate", "dep_rate"))
            book = _dec(_row_get(row, "book_value"), str(cost))
        except ValueError as e:
            result.errors.append({"row": i, "message": str(e)})
            continue
        _, created = FixedAsset.objects.update_or_create(
            organization=org,
            asset_code=code,
            defaults={
                "name": name,
                "category": _row_get(row, "category"),
                "location": _row_get(row, "location"),
                "custodian": _row_get(row, "custodian"),
                "purchase_date": _parse_date(_row_get(row, "purchase_date")),
                "purchase_cost": cost,
                "depreciation_rate": rate,
                "book_value": book,
                "status": _row_get(row, "status", default="active") or "active",
            },
        )
        result.created += int(created)
        result.updated += int(not created)


def _imp_opening_journals(org, rows, dry, result: ImportResult):
    from finance.models import Account, JournalEntry, JournalLine

    groups: dict[str, list[tuple[int, dict[str, str]]]] = {}
    for i, row in enumerate(rows, start=2):
        ref = _row_get(row, "reference", "ref", default="OPENING") or "OPENING"
        groups.setdefault(ref, []).append((i, row))

    for ref, items in groups.items():
        result.preview_rows.append({"reference": ref, "lines": len(items)})
        if dry:
            # validate accounts
            for i, row in items:
                ac = _row_get(row, "account_code", "code")
                if not ac:
                    result.errors.append({"row": i, "message": "account_code required"})
            continue
        if JournalEntry.objects.filter(organization=org, reference=ref).exists():
            result.skipped += 1
            result.warnings.append(
                {"row": items[0][0], "message": f"journal {ref} already exists — skipped"}
            )
            continue
        first = items[0][1]
        ed = _parse_date(_row_get(first, "entry_date", "date")) or date.today()
        with transaction.atomic():
            je = JournalEntry.objects.create(
                organization=org,
                entry_date=ed,
                reference=ref,
                narration=_row_get(first, "narration", "description")
                or f"Opening {ref}",
                status=JournalEntry.Status.POSTED,
            )
            line_ok = 0
            for i, row in items:
                ac = _row_get(row, "account_code", "code")
                acct = Account.objects.filter(organization=org, code=ac).first()
                if not acct:
                    result.errors.append(
                        {"row": i, "message": f"unknown account {ac}"}
                    )
                    continue
                try:
                    debit = _dec(_row_get(row, "debit", "dr"))
                    credit = _dec(_row_get(row, "credit", "cr"))
                except ValueError as e:
                    result.errors.append({"row": i, "message": str(e)})
                    continue
                JournalLine.objects.create(
                    journal=je,
                    account=acct,
                    debit=debit,
                    credit=credit,
                    description=_row_get(row, "description", "narration"),
                )
                line_ok += 1
            if line_ok:
                result.created += 1
            else:
                je.delete()
                result.skipped += 1


def _imp_leads(org, rows, dry, result: ImportResult):
    from crm.models import Lead

    for i, row in enumerate(rows, start=2):
        name = _row_get(row, "name", "lead_name")
        if not name:
            result.errors.append({"row": i, "message": "name required"})
            continue
        result.preview_rows.append({"name": name, "company": _row_get(row, "company")})
        if dry:
            continue
        status = _row_get(row, "status", default="new") or "new"
        if status == "converted":
            status = "new"
            result.warnings.append(
                {"row": i, "message": "converted status not allowed on import — set to new"}
            )
        Lead.objects.create(
            organization=org,
            name=name,
            company=_row_get(row, "company"),
            email=_row_get(row, "email"),
            phone=_row_get(row, "phone"),
            source=_row_get(row, "source"),
            status=status,
        )
        result.created += 1


def _imp_projects(org, rows, dry, result: ImportResult):
    from ops.models import Customer
    from projects.models import Project

    for i, row in enumerate(rows, start=2):
        code = _row_get(row, "code", "project_code")
        name = _row_get(row, "name", "project_name")
        if not code or not name:
            result.errors.append({"row": i, "message": "code and name required"})
            continue
        result.preview_rows.append({"code": code, "name": name})
        if dry:
            continue
        cust = None
        cc = _row_get(row, "customer_code")
        if cc:
            cust = Customer.objects.filter(organization=org, code=cc).first()
            if not cust:
                result.warnings.append(
                    {"row": i, "message": f"customer_code {cc} not found"}
                )
        try:
            budget = _dec(_row_get(row, "budget_amount", "budget"))
        except ValueError as e:
            result.errors.append({"row": i, "message": str(e)})
            continue
        _, created = Project.objects.update_or_create(
            organization=org,
            code=code,
            defaults={
                "name": name,
                "customer": cust,
                "start_date": _parse_date(_row_get(row, "start_date")),
                "end_date": _parse_date(_row_get(row, "end_date")),
                "status": _row_get(row, "status", default="draft") or "draft",
                "budget_amount": budget,
            },
        )
        result.created += int(created)
        result.updated += int(not created)


def _imp_tax_codes(org, rows, dry, result: ImportResult):
    from finance.models import TaxCode

    for i, row in enumerate(rows, start=2):
        code = _row_get(row, "code")
        name = _row_get(row, "name") or code
        if not code:
            result.errors.append({"row": i, "message": "code required"})
            continue
        result.preview_rows.append({"code": code, "name": name})
        if dry:
            continue
        try:
            rate = _dec(_row_get(row, "rate", "tax_rate"))
        except ValueError as e:
            result.errors.append({"row": i, "message": str(e)})
            continue
        kind = _row_get(row, "kind", "tax_type", default="sales_tax") or "sales_tax"
        _, created = TaxCode.objects.update_or_create(
            organization=org,
            code=code,
            defaults={
                "name": name,
                "rate_percent": rate,
                "tax_type": kind,
                "is_active": _bool(_row_get(row, "is_active"), True),
            },
        )
        result.created += int(created)
        result.updated += int(not created)


# ── catalog ────────────────────────────────────────────────────────────────


def _cols(*specs: tuple) -> list[ColumnSpec]:
    out = []
    for s in specs:
        name = s[0]
        required = s[1] if len(s) > 1 else False
        example = s[2] if len(s) > 2 else ""
        help_ = s[3] if len(s) > 3 else ""
        out.append(ColumnSpec(name=name, required=required, example=example, help=help_))
    return out


CATALOG: dict[str, EntitySpec] = {}


def _reg(spec: EntitySpec):
    CATALOG[spec.key] = spec


_reg(
    EntitySpec(
        key="chart_of_accounts",
        label="Chart of accounts",
        description="GL accounts (upsert by code)",
        module="finance.accounts",
        columns=_cols(
            ("code", True, "1000"),
            ("name", True, "Cash in hand"),
            ("account_type", False, "asset", "asset|liability|equity|income|expense"),
            ("parent_code", False, ""),
            ("is_active", False, "yes"),
        ),
        sample_rows=[
            {
                "code": "1000",
                "name": "Cash in hand",
                "account_type": "asset",
                "parent_code": "",
                "is_active": "yes",
            },
            {
                "code": "2000",
                "name": "Accounts payable",
                "account_type": "liability",
                "parent_code": "",
                "is_active": "yes",
            },
        ],
        run=_imp_coa,
    )
)
_reg(
    EntitySpec(
        key="cost_centers",
        label="Cost centers",
        description="Cost / profit centers",
        module="finance.cost_centers",
        columns=_cols(
            ("code", True, "HO"),
            ("name", True, "Head office"),
            ("is_active", False, "yes"),
        ),
        sample_rows=[{"code": "HO", "name": "Head office", "is_active": "yes"}],
        run=_imp_cost_centers,
    )
)
_reg(
    EntitySpec(
        key="vendors",
        label="Vendors",
        description="AP vendor masters",
        module="finance.vendors",
        columns=_cols(
            ("code", False, "V-001"),
            ("name", True, "ABC Supplies"),
            ("ntn", False, "1234567-8"),
            ("email", False, "ap@vendor.com"),
            ("phone", False, "03001234567"),
            ("address", False, ""),
            ("contact_person", False, "Ali"),
            ("city", False, "Karachi"),
            ("country", False, "Pakistan"),
            ("currency", False, "PKR"),
            ("payment_terms_days", False, "30"),
            ("credit_limit", False, "0"),
            ("is_active", False, "yes"),
        ),
        sample_rows=[
            {
                "code": "V-001",
                "name": "ABC Supplies",
                "ntn": "1234567-8",
                "email": "ap@vendor.com",
                "phone": "03001234567",
                "address": "Site 1",
                "contact_person": "Ali",
                "city": "Karachi",
                "country": "Pakistan",
                "currency": "PKR",
                "payment_terms_days": "30",
                "credit_limit": "500000",
                "is_active": "yes",
            }
        ],
        run=_imp_vendors,
    )
)
_reg(
    EntitySpec(
        key="customers",
        label="Customers",
        description="AR customer masters",
        module="sales.customers",
        columns=_cols(
            ("code", True, "C-001"),
            ("name", True, "Acme Trading"),
            ("email", False, "buyer@acme.com"),
            ("phone", False, "0211234567"),
            ("ntn", False, ""),
            ("address", False, ""),
            ("contact_person", False, ""),
            ("city", False, "Lahore"),
            ("country", False, "Pakistan"),
            ("currency", False, "PKR"),
            ("payment_terms_days", False, "30"),
            ("credit_limit", False, "0"),
            ("notes", False, ""),
            ("is_active", False, "yes"),
        ),
        sample_rows=[
            {
                "code": "C-001",
                "name": "Acme Trading",
                "email": "buyer@acme.com",
                "phone": "0211234567",
                "ntn": "",
                "address": "",
                "contact_person": "Sara",
                "city": "Lahore",
                "country": "Pakistan",
                "currency": "PKR",
                "payment_terms_days": "30",
                "credit_limit": "1000000",
                "notes": "",
                "is_active": "yes",
            }
        ],
        run=_imp_customers,
    )
)
_reg(
    EntitySpec(
        key="warehouses",
        label="Warehouses",
        description="Inventory locations",
        module="inventory.warehouses",
        columns=_cols(
            ("code", True, "MAIN"),
            ("name", True, "Main store"),
            ("address", False, ""),
            ("is_default", False, "yes"),
            ("is_active", False, "yes"),
        ),
        sample_rows=[
            {
                "code": "MAIN",
                "name": "Main store",
                "address": "Plant 1",
                "is_default": "yes",
                "is_active": "yes",
            }
        ],
        run=_imp_warehouses,
    )
)
_reg(
    EntitySpec(
        key="items",
        label="Items / SKUs",
        description="Inventory item masters",
        module="inventory.items",
        columns=_cols(
            ("sku", True, "SKU-001"),
            ("name", True, "Widget A"),
            ("barcode", False, ""),
            ("category", False, "Finished"),
            ("description", False, ""),
            ("unit", False, "ea"),
            ("item_type", False, "stockable", "stockable|consumable|service"),
            ("valuation_method", False, "average"),
            ("warehouse_code", False, "MAIN"),
            ("reorder_level", False, "10"),
            ("max_level", False, "100"),
            ("unit_cost", False, "100"),
            ("sales_price", False, "150"),
            ("track_batch", False, "no"),
            ("track_serial", False, "no"),
            ("is_active", False, "yes"),
        ),
        sample_rows=[
            {
                "sku": "SKU-001",
                "name": "Widget A",
                "barcode": "",
                "category": "Finished",
                "description": "",
                "unit": "ea",
                "item_type": "stockable",
                "valuation_method": "average",
                "warehouse_code": "MAIN",
                "reorder_level": "10",
                "max_level": "100",
                "unit_cost": "100",
                "sales_price": "150",
                "track_batch": "no",
                "track_serial": "no",
                "is_active": "yes",
            }
        ],
        run=_imp_items,
    )
)
_reg(
    EntitySpec(
        key="departments",
        label="Departments",
        description="HR departments",
        module="hr.employees",
        columns=_cols(
            ("code", True, "FIN"),
            ("name", True, "Finance"),
            ("parent_code", False, ""),
        ),
        sample_rows=[{"code": "FIN", "name": "Finance", "parent_code": ""}],
        run=_imp_departments,
    )
)
_reg(
    EntitySpec(
        key="designations",
        label="Designations",
        description="HR job titles",
        module="hr.employees",
        columns=_cols(
            ("code", True, "MGR"),
            ("title", True, "Manager"),
            ("grade", False, "M2"),
        ),
        sample_rows=[{"code": "MGR", "title": "Manager", "grade": "M2"}],
        run=_imp_designations,
    )
)
_reg(
    EntitySpec(
        key="employees",
        label="Employees",
        description="HR employee masters (upsert by employee_code)",
        module="hr.employees",
        columns=_cols(
            ("employee_code", True, "E001"),
            ("first_name", True, "Ahmed"),
            ("last_name", False, "Khan"),
            ("email", False, "ahmed@company.com"),
            ("phone", False, "03001112222"),
            ("dept_code", False, "FIN"),
            ("desig_code", False, "MGR"),
            ("basic_salary", False, "80000"),
            ("date_of_joining", False, "2024-01-15"),
            ("date_of_birth", False, ""),
            ("status", False, "active"),
        ),
        sample_rows=[
            {
                "employee_code": "E001",
                "first_name": "Ahmed",
                "last_name": "Khan",
                "email": "ahmed@company.com",
                "phone": "03001112222",
                "dept_code": "FIN",
                "desig_code": "MGR",
                "basic_salary": "80000",
                "date_of_joining": "2024-01-15",
                "date_of_birth": "1990-05-01",
                "status": "active",
            }
        ],
        run=_imp_employees,
    )
)
_reg(
    EntitySpec(
        key="leave_balances",
        label="Leave balances",
        description="Opening leave balances by employee / type / year",
        module="hr.leaves",
        columns=_cols(
            ("employee_code", True, "E001"),
            ("leave_type_code", True, "AL"),
            ("year", False, str(date.today().year)),
            ("opening", False, "14"),
            ("accrued", False, "0"),
            ("used", False, "0"),
            ("encashed", False, "0"),
            ("carried_forward", False, "0"),
        ),
        sample_rows=[
            {
                "employee_code": "E001",
                "leave_type_code": "AL",
                "year": str(date.today().year),
                "opening": "14",
                "accrued": "0",
                "used": "2",
                "encashed": "0",
                "carried_forward": "0",
            }
        ],
        run=_imp_leave_balances,
    )
)
_reg(
    EntitySpec(
        key="fixed_assets",
        label="Fixed assets",
        description="Asset register (upsert by asset_code)",
        module="finance.assets",
        columns=_cols(
            ("asset_code", True, "FA-001"),
            ("name", True, "Laptop"),
            ("category", False, "IT"),
            ("location", False, "HO"),
            ("custodian", False, ""),
            ("purchase_date", False, "2023-06-01"),
            ("purchase_cost", False, "150000"),
            ("depreciation_rate", False, "33.33"),
            ("book_value", False, "100000"),
            ("status", False, "active"),
        ),
        sample_rows=[
            {
                "asset_code": "FA-001",
                "name": "Laptop Dell",
                "category": "IT",
                "location": "HO",
                "custodian": "",
                "purchase_date": "2023-06-01",
                "purchase_cost": "150000",
                "depreciation_rate": "33.33",
                "book_value": "100000",
                "status": "active",
            }
        ],
        run=_imp_assets,
    )
)
_reg(
    EntitySpec(
        key="opening_journals",
        label="Opening journals",
        description="Posted opening JEs grouped by reference (skipped if reference exists)",
        module="finance.journals",
        columns=_cols(
            ("reference", True, "OB-2024"),
            ("entry_date", False, "2024-01-01"),
            ("account_code", True, "1000"),
            ("debit", False, "100000"),
            ("credit", False, "0"),
            ("description", False, "Opening cash"),
            ("narration", False, "Opening balances"),
        ),
        sample_rows=[
            {
                "reference": "OB-2024",
                "entry_date": "2024-01-01",
                "account_code": "1000",
                "debit": "100000",
                "credit": "0",
                "description": "Opening cash",
                "narration": "Opening balances",
            },
            {
                "reference": "OB-2024",
                "entry_date": "2024-01-01",
                "account_code": "3000",
                "debit": "0",
                "credit": "100000",
                "description": "Opening equity",
                "narration": "Opening balances",
            },
        ],
        run=_imp_opening_journals,
    )
)
_reg(
    EntitySpec(
        key="crm_leads",
        label="CRM leads",
        description="Create new leads (no upsert)",
        module="crm.leads",
        columns=_cols(
            ("name", True, "Ali Raza"),
            ("company", False, "Raza Traders"),
            ("email", False, "ali@raza.com"),
            ("phone", False, "03009998877"),
            ("source", False, "web"),
            ("status", False, "new"),
        ),
        sample_rows=[
            {
                "name": "Ali Raza",
                "company": "Raza Traders",
                "email": "ali@raza.com",
                "phone": "03009998877",
                "source": "web",
                "status": "new",
            }
        ],
        run=_imp_leads,
    )
)
_reg(
    EntitySpec(
        key="projects",
        label="Projects",
        description="Project masters (upsert by code)",
        module="projects.projects",
        columns=_cols(
            ("code", True, "PRJ-001"),
            ("name", True, "ERP rollout"),
            ("customer_code", False, "C-001"),
            ("start_date", False, date.today().isoformat()),
            ("end_date", False, ""),
            ("budget_amount", False, "500000"),
            ("status", False, "draft"),
        ),
        sample_rows=[
            {
                "code": "PRJ-001",
                "name": "ERP rollout",
                "customer_code": "C-001",
                "start_date": date.today().isoformat(),
                "end_date": "",
                "budget_amount": "500000",
                "status": "active",
            }
        ],
        run=_imp_projects,
    )
)


def try_tax_codes():
    try:
        from finance.models import TaxCode  # noqa: F401

        _reg(
            EntitySpec(
                key="tax_codes",
                label="Tax codes",
                description="Sales tax / WHT rate masters",
                module="finance.tax",
                columns=_cols(
                    ("code", True, "ST-17"),
                    ("name", True, "Sales tax 17%"),
                    ("rate", True, "17", "maps to rate_percent"),
                    ("tax_type", False, "sales_tax", "sales_tax|wht"),
                    ("is_active", False, "yes"),
                ),
                sample_rows=[
                    {
                        "code": "ST-17",
                        "name": "Sales tax 17%",
                        "rate": "17",
                        "tax_type": "sales_tax",
                        "is_active": "yes",
                    }
                ],
                run=_imp_tax_codes,
            )
        )
    except Exception:
        pass


try_tax_codes()


def list_catalog() -> list[dict[str, Any]]:
    return [
        {
            "key": e.key,
            "label": e.label,
            "description": e.description,
            "module": e.module,
            "columns": [
                {
                    "name": c.name,
                    "required": c.required,
                    "example": c.example,
                    "help": c.help,
                }
                for c in e.columns
            ],
        }
        for e in CATALOG.values()
    ]


def build_template_csv(entity_key: str) -> str:
    spec = CATALOG[entity_key]
    buf = io.StringIO()
    fieldnames = [c.name for c in spec.columns]
    writer = csv.DictWriter(buf, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    for sample in spec.sample_rows:
        writer.writerow({k: sample.get(k, "") for k in fieldnames})
    return buf.getvalue()


def ordered_entity_keys() -> list[str]:
    """Catalog keys in recommended import order, then any extras alphabetically."""
    seen: set[str] = set()
    ordered: list[str] = []
    for key in IMPORT_ORDER:
        if key in CATALOG and key not in seen:
            ordered.append(key)
            seen.add(key)
    for key in sorted(CATALOG.keys()):
        if key not in seen:
            ordered.append(key)
            seen.add(key)
    return ordered


def build_all_templates_zip() -> bytes:
    """ZIP pack: README + one CSV per entity (UTF-8 with BOM for Excel)."""
    buf = io.BytesIO()
    keys = ordered_entity_keys()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        readme_lines = [
            "SI-ERP Data Import Templates",
            "===========================",
            "",
            "How to use",
            "----------",
            "1. Open each CSV in Excel or Google Sheets (UTF-8).",
            "2. Keep the header row exactly as provided (column names matter).",
            "3. Replace sample rows with your data. Delete unused sample rows.",
            "4. In Import Hub: choose the matching entity → Validate → Commit.",
            "5. Import in the numbered order below so lookups resolve",
            "   (e.g. departments before employees, CoA before opening journals).",
            "",
            "Conventions",
            "-----------",
            "- Dates: YYYY-MM-DD (also accepts DD/MM/YYYY).",
            "- Booleans: yes/no, true/false, 1/0.",
            "- Numbers: no currency symbols; use plain decimals.",
            "- Upsert keys: code / sku / employee_code / asset_code (where noted).",
            "- Opening journals: grouped by reference; skipped if reference exists.",
            "",
            "Recommended import order",
            "------------------------",
        ]
        for i, key in enumerate(keys, start=1):
            spec = CATALOG[key]
            req = ", ".join(c.name for c in spec.columns if c.required) or "(none)"
            readme_lines.append(
                f"{i:02d}. {key}.csv  — {spec.label}"
                f"  [required: {req}]"
            )
            # Excel-friendly BOM
            csv_body = "\ufeff" + build_template_csv(key)
            zf.writestr(f"{i:02d}_{key}.csv", csv_body.encode("utf-8"))
        readme_lines.extend(
            [
                "",
                "Files in this pack",
                "------------------",
                "00_README.txt          this guide",
                "NN_<entity>.csv        template with header + sample row(s)",
                "manifest.csv           entity index (key, label, filename)",
                "",
            ]
        )
        zf.writestr("00_README.txt", "\n".join(readme_lines) + "\n")

        man = io.StringIO()
        writer = csv.DictWriter(
            man,
            fieldnames=["seq", "key", "label", "filename", "required_columns"],
            lineterminator="\n",
        )
        writer.writeheader()
        for i, key in enumerate(keys, start=1):
            spec = CATALOG[key]
            writer.writerow(
                {
                    "seq": i,
                    "key": key,
                    "label": spec.label,
                    "filename": f"{i:02d}_{key}.csv",
                    "required_columns": "|".join(
                        c.name for c in spec.columns if c.required
                    ),
                }
            )
        zf.writestr("manifest.csv", "\ufeff" + man.getvalue())
    return buf.getvalue()


def _entity_key_from_zip_name(name: str) -> str | None:
    """Map ZIP member name → catalog key.

    Accepts: customers.csv, 02_customers.csv, import_customers_template.csv,
    nested paths like templates/03_items.csv
    """
    base = name.replace("\\", "/").split("/")[-1].strip()
    if not base or base.startswith(".") or base.startswith("__"):
        return None
    lower = base.lower()
    if lower in ("00_readme.txt", "readme.txt", "manifest.csv", "manifest.json"):
        return None
    if not lower.endswith(".csv"):
        return None
    stem = lower[:-4]
    # strip leading NN_
    stem = re.sub(r"^\d{1,3}_", "", stem)
    stem = re.sub(r"^import_", "", stem)
    stem = re.sub(r"_template$", "", stem)
    if stem in CATALOG:
        return stem
    # fuzzy: key contained in stem
    for key in CATALOG:
        if key == stem or stem.endswith(key) or stem.startswith(key):
            return key
    return None


def run_import_zip(
    org: Organization,
    zip_bytes: bytes,
    *,
    dry_run: bool = True,
) -> dict[str, Any]:
    """Import every recognized CSV in a ZIP using recommended order."""
    try:
        zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    except zipfile.BadZipFile as exc:
        raise ValueError(f"Invalid ZIP file: {exc}") from exc

    # Map entity → (filename, text)
    found: dict[str, tuple[str, str]] = {}
    skipped_files: list[str] = []
    with zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            key = _entity_key_from_zip_name(info.filename)
            if not key:
                if info.filename.lower().endswith(".csv"):
                    skipped_files.append(info.filename)
                continue
            raw = zf.read(info.filename)
            text = raw.decode("utf-8-sig", errors="replace")
            # Prefer first match; numbered pack shouldn't duplicate
            found.setdefault(key, (info.filename, text))

    results: list[dict[str, Any]] = []
    totals = {
        "created": 0,
        "updated": 0,
        "skipped": 0,
        "error_count": 0,
        "warning_count": 0,
        "row_count": 0,
    }
    order = ordered_entity_keys()
    # Process known order first, then any extras found
    process_keys = [k for k in order if k in found] + [
        k for k in found if k not in order
    ]

    for key in process_keys:
        filename, text = found[key]
        one = run_import(org, key, text, dry_run=dry_run)
        one["source_file"] = filename
        results.append(one)
        for t in ("created", "updated", "skipped", "error_count", "warning_count", "row_count"):
            totals[t] += int(one.get(t) or 0)

    missing = [k for k in order if k not in found]
    return {
        "mode": "zip_pack",
        "dry_run": dry_run,
        "entities_found": list(found.keys()),
        "entities_processed": process_keys,
        "entities_missing": missing,
        "skipped_files": skipped_files[:50],
        "file_count": len(found),
        "results": results,
        **totals,
        "message": (
            f"{'Dry-run' if dry_run else 'Import'} pack: "
            f"{len(process_keys)} file(s), {totals['created']} created, "
            f"{totals['updated']} updated, {totals['error_count']} errors."
        ),
    }


def run_import(
    org: Organization,
    entity_key: str,
    text: str,
    *,
    dry_run: bool = True,
) -> dict[str, Any]:
    if entity_key not in CATALOG:
        raise ValueError(f"Unknown entity: {entity_key}")
    spec = CATALOG[entity_key]
    headers, rows = _read_csv(text)
    result = ImportResult()
    if not headers:
        result.errors.append({"row": 1, "message": "CSV has no header row"})
        return {
            "entity": entity_key,
            "dry_run": dry_run,
            "filename_headers": headers,
            "row_count": 0,
            **result.as_dict(),
        }

    # column coverage
    required = {c.name for c in spec.columns if c.required}
    present = {_norm(h) for h in headers}
    missing_req = [r for r in required if _norm(r) not in present]
    for m in missing_req:
        result.warnings.append(
            {
                "row": 1,
                "message": f"Required column '{m}' not found in header — rows may fail",
            }
        )

    if not rows:
        result.warnings.append({"row": 0, "message": "No data rows found"})
    else:
        if dry_run:
            spec.run(org, rows, True, result)
        else:
            with transaction.atomic():
                spec.run(org, rows, False, result)
                if result.errors and result.created == 0 and result.updated == 0:
                    # allow partial success; only hard-abort if nothing written and errors
                    pass

    return {
        "entity": entity_key,
        "label": spec.label,
        "dry_run": dry_run,
        "filename_headers": headers,
        "expected_columns": [c.name for c in spec.columns],
        "row_count": len(rows),
        **result.as_dict(),
    }
