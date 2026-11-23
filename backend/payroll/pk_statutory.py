"""Pakistan salaried-tax slabs and EOBI shares used by the pay run.

Slabs follow the same Finance Act bands the SIGBL payroll app uses
(1% on the band above 600,000 up to 1,200,000). EOBI is 1% employee and
5% employer on the minimum wage, not a flat deduction.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

EOBI_MINIMUM_WAGE = Decimal("37000")
_Q = Decimal("0.01")


def _money(value: Decimal) -> Decimal:
    return value.quantize(_Q, rounding=ROUND_HALF_UP)


def monthly_income_tax(monthly_taxable: Decimal) -> Decimal:
    """Monthly withholding from annualized taxable pay. Zero at or below 600,000."""
    yearly = Decimal(monthly_taxable or 0) * Decimal("12")
    if yearly <= Decimal("600000"):
        yearly_tax = Decimal("0")
    elif yearly <= Decimal("1200000"):
        yearly_tax = (yearly - Decimal("600000")) * Decimal("0.01")
    elif yearly <= Decimal("2200000"):
        yearly_tax = Decimal("6000") + (yearly - Decimal("1200000")) * Decimal("0.15")
    elif yearly <= Decimal("3200000"):
        yearly_tax = Decimal("156000") + (yearly - Decimal("2200000")) * Decimal("0.25")
    elif yearly <= Decimal("4100000"):
        yearly_tax = Decimal("406000") + (yearly - Decimal("3200000")) * Decimal("0.30")
    else:
        yearly_tax = Decimal("676000") + (yearly - Decimal("4100000")) * Decimal("0.35")
    return _money(yearly_tax / Decimal("12"))


def eobi_shares(minimum_wage: Decimal = EOBI_MINIMUM_WAGE) -> tuple[Decimal, Decimal]:
    """Employee 1% and employer 5% of the EOBI minimum wage."""
    wage = Decimal(minimum_wage or 0)
    return _money(wage * Decimal("0.01")), _money(wage * Decimal("0.05"))


def current_fiscal_year(today) -> str:
    """Pakistan fiscal year label, July–June, e.g. 2026-2027."""
    if today.month >= 7:
        return f"{today.year}-{today.year + 1}"
    return f"{today.year - 1}-{today.year}"


def fiscal_year_bounds(label: str) -> tuple:
    from datetime import date

    start_s, end_s = str(label).split("-", 1)
    start, end = int(start_s), int(end_s)
    if end != start + 1:
        raise ValueError("Fiscal year must be a July–June span such as 2025-2026")
    return date(start, 7, 1), date(end, 6, 30)


def tax_certificate(employee, fiscal_year: str) -> dict:
    """Annual salary and tax withheld for one employee, July through June."""
    from django.db.models import Q

    from payroll.models import Payslip

    start, end = fiscal_year_bounds(fiscal_year)
    slips = (
        Payslip.objects.filter(employee=employee)
        .filter(
            Q(period__year=start.year, period__month__gte=7)
            | Q(period__year=end.year, period__month__lte=6)
        )
        .select_related("period")
        .order_by("period__year", "period__month")
    )
    basic = gross = tax = net = Decimal("0")
    months = []
    for slip in slips:
        basic += Decimal(slip.basic or 0)
        gross += Decimal(slip.gross_pay or 0)
        tax += Decimal(slip.income_tax or 0)
        net += Decimal(slip.net_pay or 0)
        months.append(
            {
                "period": slip.period.name,
                "gross_pay": f"{Decimal(slip.gross_pay or 0):.2f}",
                "income_tax": f"{Decimal(slip.income_tax or 0):.2f}",
                "net_pay": f"{Decimal(slip.net_pay or 0):.2f}",
            }
        )
    org = employee.organization
    joined = getattr(employee, "date_of_joining", None)
    effective_from = joined if joined and joined > start else start
    return {
        "fiscal_year": fiscal_year,
        "period_from": start.isoformat(),
        "period_to": end.isoformat(),
        "effective_from": effective_from.isoformat(),
        "employee_id": employee.id,
        "employee_code": employee.employee_code,
        "employee_name": employee.full_name,
        "ntn": getattr(employee, "ntn", "") or "",
        "organization": org.brand_name or org.name,
        "organization_ntn": org.ntn or "",
        "organization_address": org.address or "",
        "total_basic": f"{basic:.2f}",
        "total_gross": f"{gross:.2f}",
        "total_tax": f"{tax:.2f}",
        "total_net": f"{net:.2f}",
        "months": months,
    }
