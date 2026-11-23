"""Statutory-style finance reports from posted journals."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Count, Sum

from finance.models import (
    Account,
    AccountType,
    Budget,
    JournalLine,
    VendorInvoice,
    ensure_default_account_types,
)


def _d(v) -> Decimal:
    return Decimal(str(v or 0))


def _statement_map(org) -> dict[str, str]:
    """Map Account.account_type code → statement_class for reporting buckets."""
    ensure_default_account_types(org)
    m = {c: c for c in ("asset", "liability", "equity", "income", "expense")}
    for at in AccountType.objects.filter(organization=org):
        m[at.code] = at.statement_class
    return m


def _codes_for_classes(org, classes: set[str] | list[str]) -> list[str]:
    want = set(classes)
    return [code for code, sc in _statement_map(org).items() if sc in want]


def account_balances(org, *, as_of: date | None = None):
    """Net balance per account from posted journals (debit − credit)."""
    qs = JournalLine.objects.filter(
        journal__organization=org, journal__status="posted"
    ).select_related("account")
    if as_of:
        qs = qs.filter(journal__entry_date__lte=as_of)
    totals: dict[int, dict] = {}
    for row in qs.values(
        "account_id", "account__code", "account__name", "account__account_type"
    ).annotate(debit=Sum("debit"), credit=Sum("credit")):
        net = _d(row["debit"]) - _d(row["credit"])
        totals[row["account_id"]] = {
            "account_id": row["account_id"],
            "code": row["account__code"],
            "name": row["account__name"],
            "account_type": row["account__account_type"],
            "debit": _d(row["debit"]),
            "credit": _d(row["credit"]),
            "balance": net,
        }
    # Include zero-balance leaf accounts for full TB option
    return totals


def trial_balance(org, *, as_of: date | None = None) -> dict:
    bals = account_balances(org, as_of=as_of)
    lines = []
    total_dr = Decimal("0")
    total_cr = Decimal("0")
    for a in Account.objects.filter(organization=org, is_active=True).order_by("code"):
        row = bals.get(a.id)
        if row:
            bal = row["balance"]
            dr = bal if bal > 0 else Decimal("0")
            cr = -bal if bal < 0 else Decimal("0")
            # Present natural side for TB display from raw totals
            dr = row["debit"]
            cr = row["credit"]
        else:
            dr = cr = Decimal("0")
        if dr == 0 and cr == 0:
            continue
        total_dr += dr
        total_cr += cr
        lines.append(
            {
                "code": a.code,
                "name": a.name,
                "account_type": a.account_type,
                "debit": str(dr),
                "credit": str(cr),
            }
        )
    return {
        "as_of": (as_of or date.today()).isoformat(),
        "lines": lines,
        "total_debit": str(total_dr),
        "total_credit": str(total_cr),
        "balanced": total_dr == total_cr,
    }


def income_statement(org, *, year: int | None = None) -> dict:
    year = year or date.today().year
    sm = _statement_map(org)
    pl_codes = _codes_for_classes(org, {"income", "expense"})
    qs = JournalLine.objects.filter(
        journal__organization=org,
        journal__status="posted",
        journal__entry_date__year=year,
        account__account_type__in=pl_codes,
    ).values("account__code", "account__name", "account__account_type").annotate(
        debit=Sum("debit"), credit=Sum("credit")
    )
    income = Decimal("0")
    expense = Decimal("0")
    lines = []
    for row in qs:
        stmt = sm.get(row["account__account_type"], row["account__account_type"])
        net = _d(row["credit"]) - _d(row["debit"])  # income natural credit
        if stmt == "expense":
            net = _d(row["debit"]) - _d(row["credit"])
            expense += net
        else:
            income += net
        lines.append(
            {
                "code": row["account__code"],
                "name": row["account__name"],
                "account_type": row["account__account_type"],
                "statement_class": stmt,
                "amount": str(net),
            }
        )
    return {
        "year": year,
        "lines": lines,
        "total_income": str(income),
        "total_expense": str(expense),
        "surplus_deficit": str(income - expense),
    }


def balance_sheet(org, *, as_of: date | None = None) -> dict:
    as_of = as_of or date.today()
    bals = account_balances(org, as_of=as_of)
    sm = _statement_map(org)
    bs_codes = _codes_for_classes(org, {"asset", "liability", "equity"})
    buckets = {"asset": [], "liability": [], "equity": []}
    totals = {k: Decimal("0") for k in buckets}
    for a in Account.objects.filter(
        organization=org, account_type__in=bs_codes, is_active=True
    ).order_by("code"):
        row = bals.get(a.id)
        if not row:
            continue
        bal = row["balance"]
        stmt = sm.get(a.account_type, a.account_type)
        # Assets natural debit; liability/equity natural credit → present as positive liability
        if stmt == "asset":
            amt = bal
        else:
            amt = -bal
        if amt == 0:
            continue
        if stmt not in buckets:
            continue
        buckets[stmt].append(
            {"code": a.code, "name": a.name, "amount": str(amt)}
        )
        totals[stmt] += amt
    # Fold P&L into equity for the year
    pl = income_statement(org, year=as_of.year)
    surplus = _d(pl["surplus_deficit"])
    if surplus != 0:
        buckets["equity"].append(
            {
                "code": "RE",
                "name": f"Surplus/(Deficit) FY{as_of.year}",
                "amount": str(surplus),
            }
        )
        totals["equity"] += surplus
    return {
        "as_of": as_of.isoformat(),
        "assets": buckets["asset"],
        "liabilities": buckets["liability"],
        "equity": buckets["equity"],
        "total_assets": str(totals["asset"]),
        "total_liabilities": str(totals["liability"]),
        "total_equity": str(totals["equity"]),
        "balanced": totals["asset"] == (totals["liability"] + totals["equity"]),
    }


def cash_position(org) -> dict:
    from finance.models import BankAccount

    banks = []
    total = Decimal("0")
    for b in BankAccount.objects.filter(organization=org, is_active=True):
        bal = b.current_balance if b.current_balance is not None else b.opening_balance
        banks.append(
            {
                "id": b.id,
                "name": b.name,
                "bank_name": b.bank_name,
                "account_no": b.account_no,
                "opening_balance": str(b.opening_balance),
                "current_balance": str(bal),
                "last_reconciled": b.last_reconciled.isoformat()
                if b.last_reconciled
                else None,
                "currency": b.currency,
            }
        )
        total += _d(bal)
    return {"banks": banks, "total_opening": str(total), "total_balance": str(total)}


def cash_flow(org, *, year: int | None = None) -> dict:
    """
    Indirect-style cash flow approximation from posted journals for the year:
    operating ≈ P&L surplus + non-cash adjustments stub;
    investing / financing from asset & equity/liability movement labels.
    """
    year = year or date.today().year
    pl = income_statement(org, year=year)
    surplus = _d(pl["surplus_deficit"])

    sm = _statement_map(org)
    qs = JournalLine.objects.filter(
        journal__organization=org,
        journal__status="posted",
        journal__entry_date__year=year,
    ).values("account__account_type", "account__code", "account__name").annotate(
        debit=Sum("debit"), credit=Sum("credit")
    )

    investing = Decimal("0")
    financing = Decimal("0")
    lines = []
    for row in qs:
        atype = sm.get(row["account__account_type"], row["account__account_type"])
        net_dr = _d(row["debit"]) - _d(row["credit"])
        if atype == "asset" and not str(row["account__code"] or "").startswith("1"):
            # Capex-like asset increases (debit) as investing outflow
            if net_dr > 0:
                investing -= net_dr
                lines.append(
                    {
                        "section": "investing",
                        "code": row["account__code"],
                        "name": row["account__name"],
                        "amount": str(-net_dr),
                    }
                )
        elif atype in ("liability", "equity"):
            # Net credit increase → financing inflow
            net_cr = -net_dr
            if net_cr != 0:
                financing += net_cr
                lines.append(
                    {
                        "section": "financing",
                        "code": row["account__code"],
                        "name": row["account__name"],
                        "amount": str(net_cr),
                    }
                )

    operating = surplus
    net_change = operating + investing + financing
    cash = cash_position(org)
    return {
        "year": year,
        "operating": str(operating),
        "investing": str(investing),
        "financing": str(financing),
        "net_change": str(net_change),
        "closing_cash": cash.get("total_balance", "0"),
        "lines": lines,
        "note": "Indirect approximation from posted journals + bank cash position",
    }


def ap_ageing(org, *, as_of: date | None = None) -> dict:
    as_of = as_of or date.today()
    buckets = {
        "current": Decimal("0"),
        "days_1_30": Decimal("0"),
        "days_31_60": Decimal("0"),
        "days_61_90": Decimal("0"),
        "days_90_plus": Decimal("0"),
    }
    rows = []
    qs = VendorInvoice.objects.filter(
        organization=org, status__in=["approved", "submitted", "draft"]
    ).select_related("vendor")
    for inv in qs:
        due = inv.due_date or inv.invoice_date
        age = (as_of - due).days
        amt = _d(inv.amount) - _d(inv.wht_amount)
        if age <= 0:
            key = "current"
        elif age <= 30:
            key = "days_1_30"
        elif age <= 60:
            key = "days_31_60"
        elif age <= 90:
            key = "days_61_90"
        else:
            key = "days_90_plus"
        buckets[key] += amt
        rows.append(
            {
                "invoice_no": inv.invoice_no,
                "vendor": inv.vendor.name,
                "due_date": due.isoformat(),
                "age_days": age,
                "amount": str(amt),
                "bucket": key,
                "status": inv.status,
            }
        )
    return {
        "as_of": as_of.isoformat(),
        "buckets": {k: str(v) for k, v in buckets.items()},
        "invoices": rows,
        "total_open": str(sum(buckets.values(), Decimal("0"))),
    }


def budget_vs_actual(org, *, fiscal_year: int | None = None) -> dict:
    """Budget vs actual (utilized) by cost centre for a fiscal year."""
    year = fiscal_year or date.today().year
    refresh_budget_utilized(org, year)
    rows = []
    total_budget = Decimal("0")
    total_actual = Decimal("0")
    for b in Budget.objects.filter(organization=org, fiscal_year=year).select_related(
        "cost_center"
    ):
        budgeted = _d(b.amount)
        actual = _d(b.utilized)
        variance = budgeted - actual
        total_budget += budgeted
        total_actual += actual
        rows.append(
            {
                "id": b.id,
                "name": b.name,
                "status": b.status,
                "cost_center": b.cost_center.code if b.cost_center_id else "ORG",
                "cost_center_name": b.cost_center.name if b.cost_center_id else "Organization",
                "budget": str(budgeted),
                "actual": str(actual),
                "variance": str(variance),
                "utilization_pct": str(
                    ((actual / budgeted) * Decimal("100")).quantize(Decimal("0.01"))
                    if budgeted
                    else Decimal("0")
                ),
            }
        )
    return {
        "fiscal_year": year,
        "lines": rows,
        "total_budget": str(total_budget),
        "total_actual": str(total_actual),
        "total_variance": str(total_budget - total_actual),
    }


def refresh_budget_utilized(org, fiscal_year: int | None = None):
    """Rebuild Budget.utilized from posted expense lines on matching cost centres."""
    year = fiscal_year or date.today().year
    budgets = Budget.objects.filter(organization=org, fiscal_year=year)
    for b in budgets:
        expense_codes = _codes_for_classes(org, {"expense"})
        qs = JournalLine.objects.filter(
            journal__organization=org,
            journal__status="posted",
            journal__entry_date__year=year,
            account__account_type__in=expense_codes,
        )
        if b.cost_center_id:
            qs = qs.filter(cost_center_id=b.cost_center_id)
        agg = qs.aggregate(s=Sum("debit"), c=Sum("credit"))
        utilized = _d(agg["s"]) - _d(agg["c"])
        if utilized < 0:
            utilized = Decimal("0")
        b.utilized = utilized
        b.save(update_fields=["utilized", "updated_at"])
    return budgets.count()


def budget_availability_ok(org, lines, entry_date: date) -> tuple[bool, str]:
    """
    Before posting expense lines: ensure approved budget remaining covers debit.
    Returns (ok, detail).
    """
    year = entry_date.year
    by_cc: dict[int | None, Decimal] = defaultdict(lambda: Decimal("0"))
    for line in lines:
        acct = getattr(line, "account", None)
        if not acct or acct.statement_class != "expense":
            continue
        cc_id = getattr(line, "cost_center_id", None)
        by_cc[cc_id] += _d(line.debit) - _d(line.credit)

    for cc_id, need in by_cc.items():
        if need <= 0:
            continue
        qs = Budget.objects.filter(
            organization=org, fiscal_year=year, status__in=["approved", "locked"]
        )
        if cc_id:
            qs = qs.filter(cost_center_id=cc_id)
        else:
            qs = qs.filter(cost_center__isnull=True)
        budget = qs.order_by("-id").first()
        if not budget:
            # No budget row → allow (configuration may not use budgets yet)
            continue
        remaining = _d(budget.amount) - _d(budget.utilized)
        if need > remaining:
            label = budget.cost_center.code if budget.cost_center_id else "org"
            return (
                False,
                f"Budget exceeded for {label}: need {need}, remaining {remaining}",
            )
    return True, ""


def ar_ageing(org, *, as_of: date | None = None) -> dict:
    """Open AR (approved/submitted) by ageing bucket from due date."""
    from finance.models import CustomerInvoice

    as_of = as_of or date.today()
    buckets = {
        "current": Decimal("0"),
        "days_1_30": Decimal("0"),
        "days_31_60": Decimal("0"),
        "days_61_90": Decimal("0"),
        "days_90_plus": Decimal("0"),
    }
    rows = []
    qs = CustomerInvoice.objects.filter(
        organization=org, is_deleted=False, status__in=["approved", "submitted"]
    ).select_related("customer")
    for inv in qs:
        due = inv.due_date or inv.invoice_date
        age = (as_of - due).days
        open_amt = _d(inv.amount) + _d(inv.tax_amount) - _d(inv.paid_amount)
        if open_amt <= 0:
            continue
        if age <= 0:
            key = "current"
        elif age <= 30:
            key = "days_1_30"
        elif age <= 60:
            key = "days_31_60"
        elif age <= 90:
            key = "days_61_90"
        else:
            key = "days_90_plus"
        buckets[key] += open_amt
        rows.append(
            {
                "invoice_no": inv.invoice_no,
                "customer": inv.customer.name,
                "due_date": due.isoformat(),
                "age_days": age,
                "amount": str(open_amt),
                "bucket": key,
                "status": inv.status,
            }
        )
    return {
        "as_of": as_of.isoformat(),
        "buckets": {k: str(v) for k, v in buckets.items()},
        "invoices": rows,
        "total_open": str(sum(buckets.values(), Decimal("0"))),
    }


def stock_valuation(org) -> dict:
    """Stock valuation summary: per item (and warehouse) qty × unit cost."""
    from ops.models import Item, StockLevel

    items = {
        i.id: i
        for i in Item.objects.filter(organization=org, is_deleted=False).exclude(
            item_type="service"
        )
    }
    rows = []
    total = Decimal("0")
    seen_items = set()
    for lvl in StockLevel.objects.filter(organization=org, is_deleted=False).select_related(
        "warehouse", "item"
    ):
        item = items.get(lvl.item_id)
        if not item:
            continue
        seen_items.add(item.id)
        qty = _d(lvl.qty)
        if qty == 0:
            continue
        value = (qty * _d(item.unit_cost)).quantize(Decimal("0.01"))
        total += value
        rows.append(
            {
                "sku": item.sku,
                "name": item.name,
                "warehouse": lvl.warehouse.code,
                "qty": str(qty),
                "unit_cost": str(_d(item.unit_cost)),
                "valuation_method": item.valuation_method,
                "amount": str(value),
            }
        )
    for item in items.values():
        if item.id in seen_items or _d(item.qty_on_hand) == 0:
            continue
        value = (_d(item.qty_on_hand) * _d(item.unit_cost)).quantize(Decimal("0.01"))
        total += value
        rows.append(
            {
                "sku": item.sku,
                "name": item.name,
                "warehouse": "—",
                "qty": str(_d(item.qty_on_hand)),
                "unit_cost": str(_d(item.unit_cost)),
                "valuation_method": item.valuation_method,
                "amount": str(value),
            }
        )
    rows.sort(key=lambda r: (r["sku"], r["warehouse"]))
    return {"lines": rows, "total_value": str(total), "line_count": len(rows)}


def wht_register(
    org, *, date_from: date | None = None, date_to: date | None = None
) -> dict:
    """WHT register from AP invoices (+ challans issued)."""
    from finance.models import TaxChallan

    date_to = date_to or date.today()
    date_from = date_from or date(date_to.year, 1, 1)
    qs = VendorInvoice.objects.filter(
        organization=org,
        is_deleted=False,
        invoice_date__gte=date_from,
        invoice_date__lte=date_to,
        status__in=["approved", "paid", "submitted"],
        wht_amount__gt=0,
    ).select_related("vendor")
    rows = []
    total_wht = Decimal("0")
    total_gross = Decimal("0")
    for inv in qs.order_by("invoice_date", "id"):
        wht = _d(inv.wht_amount)
        total_wht += wht
        total_gross += _d(inv.amount)
        rows.append(
            {
                "invoice_date": inv.invoice_date.isoformat(),
                "invoice_no": inv.invoice_no,
                "vendor": inv.vendor.name,
                "ntn": inv.vendor.ntn,
                "gross": str(_d(inv.amount)),
                "wht_amount": str(wht),
                "status": inv.status,
            }
        )
    challans = [
        {
            "challan_no": c.challan_no,
            "period": c.period_label,
            "amount": str(_d(c.amount)),
            "status": c.status,
        }
        for c in TaxChallan.objects.filter(
            organization=org, is_deleted=False, tax_type="wht"
        ).order_by("-id")[:50]
    ]
    return {
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
        "lines": rows,
        "total_gross": str(total_gross),
        "total_wht": str(total_wht),
        "challans": challans,
    }


def payroll_register_summary(org, *, year: int | None = None) -> dict:
    """Payroll register summary per period (headcount, gross, deductions, net)."""
    try:
        from payroll.models import Payslip
    except Exception:
        return {"year": year, "lines": [], "total_net": "0"}
    year = year or date.today().year
    qs = (
        Payslip.objects.filter(
            period__organization=org, period__year=year, is_deleted=False
        )
        .values("period__id", "period__name", "period__month")
        .annotate(
            headcount=Count("id"),
            gross=Sum("gross_pay"),
            deductions=Sum("total_deductions"),
            tax=Sum("income_tax"),
            employer_cost=Sum("employer_cost"),
            net=Sum("net_pay"),
        )
        .order_by("period__month")
    )
    rows = []
    total_net = Decimal("0")
    total_gross = Decimal("0")
    for r in qs:
        total_net += _d(r["net"])
        total_gross += _d(r["gross"])
        rows.append(
            {
                "period": r["period__name"],
                "month": r["period__month"],
                "headcount": r["headcount"],
                "gross": str(_d(r["gross"])),
                "deductions": str(_d(r["deductions"])),
                "tax": str(_d(r["tax"])),
                "employer_cost": str(_d(r["employer_cost"])),
                "net": str(_d(r["net"])),
            }
        )
    return {
        "year": year,
        "lines": rows,
        "total_gross": str(total_gross),
        "total_net": str(total_net),
    }


def ar_ageing(org, *, as_of: date | None = None) -> dict:
    """Open AR (approved/submitted) by ageing bucket from due date."""
    from finance.models import CustomerInvoice

    as_of = as_of or date.today()
    buckets = {
        "current": Decimal("0"),
        "days_1_30": Decimal("0"),
        "days_31_60": Decimal("0"),
        "days_61_90": Decimal("0"),
        "days_90_plus": Decimal("0"),
    }
    rows = []
    qs = CustomerInvoice.objects.filter(
        organization=org, is_deleted=False, status__in=["approved", "submitted"]
    ).select_related("customer")
    for inv in qs:
        due = inv.due_date or inv.invoice_date
        age = (as_of - due).days
        open_amt = _d(inv.amount) + _d(inv.tax_amount) - _d(inv.paid_amount)
        if open_amt <= 0:
            continue
        if age <= 0:
            key = "current"
        elif age <= 30:
            key = "days_1_30"
        elif age <= 60:
            key = "days_31_60"
        elif age <= 90:
            key = "days_61_90"
        else:
            key = "days_90_plus"
        buckets[key] += open_amt
        rows.append(
            {
                "invoice_no": inv.invoice_no,
                "customer": inv.customer.name,
                "due_date": due.isoformat(),
                "age_days": age,
                "amount": str(open_amt),
                "bucket": key,
                "status": inv.status,
            }
        )
    return {
        "as_of": as_of.isoformat(),
        "buckets": {k: str(v) for k, v in buckets.items()},
        "invoices": rows,
        "total_open": str(sum(buckets.values(), Decimal("0"))),
    }


def stock_valuation(org) -> dict:
    """Stock valuation summary: per item (and warehouse) qty × unit cost."""
    from ops.models import Item, StockLevel

    items = {
        i.id: i
        for i in Item.objects.filter(organization=org, is_deleted=False).exclude(
            item_type="service"
        )
    }
    rows = []
    total = Decimal("0")
    seen_items = set()
    for lvl in StockLevel.objects.filter(organization=org, is_deleted=False).select_related(
        "warehouse", "item"
    ):
        item = items.get(lvl.item_id)
        if not item:
            continue
        seen_items.add(item.id)
        qty = _d(lvl.qty)
        if qty == 0:
            continue
        value = (qty * _d(item.unit_cost)).quantize(Decimal("0.01"))
        total += value
        rows.append(
            {
                "sku": item.sku,
                "name": item.name,
                "warehouse": lvl.warehouse.code,
                "qty": str(qty),
                "unit_cost": str(_d(item.unit_cost)),
                "valuation_method": item.valuation_method,
                "amount": str(value),
            }
        )
    for item in items.values():
        if item.id in seen_items or _d(item.qty_on_hand) == 0:
            continue
        value = (_d(item.qty_on_hand) * _d(item.unit_cost)).quantize(Decimal("0.01"))
        total += value
        rows.append(
            {
                "sku": item.sku,
                "name": item.name,
                "warehouse": "—",
                "qty": str(_d(item.qty_on_hand)),
                "unit_cost": str(_d(item.unit_cost)),
                "valuation_method": item.valuation_method,
                "amount": str(value),
            }
        )
    rows.sort(key=lambda r: (r["sku"], r["warehouse"]))
    return {"lines": rows, "total_value": str(total), "line_count": len(rows)}


def wht_register(
    org, *, date_from: date | None = None, date_to: date | None = None
) -> dict:
    """WHT register from AP invoices (+ challans issued)."""
    from finance.models import TaxChallan

    date_to = date_to or date.today()
    date_from = date_from or date(date_to.year, 1, 1)
    qs = VendorInvoice.objects.filter(
        organization=org,
        is_deleted=False,
        invoice_date__gte=date_from,
        invoice_date__lte=date_to,
        status__in=["approved", "paid", "submitted"],
        wht_amount__gt=0,
    ).select_related("vendor")
    rows = []
    total_wht = Decimal("0")
    total_gross = Decimal("0")
    for inv in qs.order_by("invoice_date", "id"):
        wht = _d(inv.wht_amount)
        total_wht += wht
        total_gross += _d(inv.amount)
        rows.append(
            {
                "invoice_date": inv.invoice_date.isoformat(),
                "invoice_no": inv.invoice_no,
                "vendor": inv.vendor.name,
                "ntn": inv.vendor.ntn,
                "gross": str(_d(inv.amount)),
                "wht_amount": str(wht),
                "status": inv.status,
            }
        )
    challans = [
        {
            "challan_no": c.challan_no,
            "period": c.period_label,
            "amount": str(_d(c.amount)),
            "status": c.status,
        }
        for c in TaxChallan.objects.filter(
            organization=org, is_deleted=False, tax_type="wht"
        ).order_by("-id")[:50]
    ]
    return {
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
        "lines": rows,
        "total_gross": str(total_gross),
        "total_wht": str(total_wht),
        "challans": challans,
    }


def payroll_register_summary(org, *, year: int | None = None) -> dict:
    """Payroll register summary per period (headcount, gross, deductions, net)."""
    try:
        from payroll.models import Payslip
    except Exception:
        return {"year": year, "lines": [], "total_net": "0"}
    year = year or date.today().year
    qs = (
        Payslip.objects.filter(
            period__organization=org, period__year=year, is_deleted=False
        )
        .values("period__id", "period__name", "period__month")
        .annotate(
            headcount=Count("id"),
            gross=Sum("gross_pay"),
            deductions=Sum("total_deductions"),
            tax=Sum("income_tax"),
            employer_cost=Sum("employer_cost"),
            net=Sum("net_pay"),
        )
        .order_by("period__month")
    )
    rows = []
    total_net = Decimal("0")
    total_gross = Decimal("0")
    for r in qs:
        total_net += _d(r["net"])
        total_gross += _d(r["gross"])
        rows.append(
            {
                "period": r["period__name"],
                "month": r["period__month"],
                "headcount": r["headcount"],
                "gross": str(_d(r["gross"])),
                "deductions": str(_d(r["deductions"])),
                "tax": str(_d(r["tax"])),
                "employer_cost": str(_d(r["employer_cost"])),
                "net": str(_d(r["net"])),
            }
        )
    return {
        "year": year,
        "lines": rows,
        "total_gross": str(total_gross),
        "total_net": str(total_net),
    }
