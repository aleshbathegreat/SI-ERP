"""Printable / PDF-ready salary slip HTML (ESS + payroll)."""

from __future__ import annotations

from decimal import Decimal
from html import escape


def _money(v) -> str:
    try:
        n = Decimal(str(v or 0))
    except Exception:
        n = Decimal("0")
    return f"{n:,.2f}"


def _nz(v) -> bool:
    try:
        return Decimal(str(v or 0)) != 0
    except Exception:
        return False


def _line(label: str, amount, *, deduct: bool = False, bold: bool = False, currency: str = "") -> str:
    cls = "line bold" if bold else "line"
    prefix = "- " if deduct else ""
    cur = f"{escape(currency)} " if currency and bold else ""
    return (
        f'<div class="{cls}"><span>{escape(label)}</span>'
        f"<span>{prefix}{cur}{_money(amount)}</span></div>"
    )


def _meta(label: str, value: str) -> str:
    return (
        f'<div class="meta-cell"><div class="meta-label">{escape(label)}</div>'
        f'<div class="meta-value">{escape(value or "—")}</div></div>'
    )


def render_salary_slip_html(slip) -> str:
    """Enterprise salary slip layout aligned to standard paystub PDFs."""
    emp = slip.employee
    period = slip.period
    org = getattr(period, "organization", None) or getattr(emp, "organization", None)
    org_name = getattr(org, "brand_name", None) or getattr(org, "name", None) or "Organization"
    accent = getattr(org, "brand_primary_color", None) or "#0B3D5C"
    currency = slip.currency or getattr(period, "currency", None) or "PKR"
    curr_label = "RS." if currency.upper() in ("PKR", "RS", "RS.") else currency.upper()

    dept = ""
    if getattr(emp, "department", None):
        dept = getattr(emp.department, "name", "") or ""
    desig = ""
    if getattr(emp, "designation", None):
        desig = getattr(emp.designation, "title", None) or getattr(emp.designation, "name", "") or ""

    branch = ""
    if org and getattr(org, "address", None):
        branch = (org.address or "").strip().split("\n")[0][:80]
    if not branch and org:
        branch = getattr(org, "name", "") or ""

    pay_method = (slip.payment_method or "bank_transfer").replace("_", " ").upper()
    if pay_method == "BANK TRANSFER":
        pay_method = "BANK"
    bank_account = (slip.bank_account or "").strip() or "—"
    # Prefer remarks hint for bank name if stored as "Bank: UBL"
    bank_name = "—"
    remarks = (slip.remarks or "").strip()
    if remarks.lower().startswith("bank:"):
        bank_name = remarks.split(":", 1)[1].strip() or "—"

    status = (getattr(period, "status", None) or "open").upper()
    if status == "PAID":
        status_label = "PAID"
    elif status == "APPROVED":
        status_label = "APPROVED"
    else:
        status_label = status

    earn_parts: list[tuple[str, object]] = [
        ("Basic Salary", slip.basic),
        ("Housing Allowance", slip.housing_allowance),
        ("Transport Allowance", slip.transport_allowance),
        ("Medical Allowance", slip.medical_allowance),
        ("Meal Allowance", slip.meal_allowance),
        ("Overtime", slip.overtime),
        ("Bonus", slip.bonus),
        ("Commission", slip.commission),
        ("Other Earnings", slip.other_earnings),
    ]
    earn_html = "".join(
        _line(lbl, amt) for lbl, amt in earn_parts if _nz(amt) or lbl == "Basic Salary"
    )
    gross = slip.gross_pay or slip.basic
    earn_html += _line("Total Gross Earnings", gross, bold=True, currency=f"Rs.")

    ded_parts: list[tuple[str, object]] = [
        ("EOBI Contribution", slip.eobi or slip.social_security),
        ("Income Tax", slip.income_tax or slip.tax),
        ("Provident Fund", slip.provident_fund),
        ("Pension", slip.pension),
        ("Loan Repayment", slip.loan_repayment),
        ("Advance Recovery", slip.advance_recovery),
        ("Other Deductions", slip.other_deductions),
    ]
    ded_html = "".join(_line(lbl, amt, deduct=True) for lbl, amt in ded_parts if _nz(amt))
    if not ded_html:
        ded_html = _line("No deductions", 0, deduct=True)
    total_ded = slip.total_deductions or slip.deductions
    ded_html += _line("Total Deductions", total_ded, deduct=True, bold=True, currency="Rs.")

    period_name = getattr(period, "name", None) or f"Period #{slip.period_id}"
    days = str(slip.days_worked or "—")
    unpaid = slip.unpaid_leave_days

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>Salary Slip · {escape(emp.employee_code)} · {escape(period_name)}</title>
<style>
  :root {{ --accent: {escape(accent)}; --ink: #102033; --muted: #5B6B7C; --line: #D8E0E8; --soft: #F4F7FA; }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; padding: 28px 20px; color: var(--ink);
    font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
    background: #E8EEF3;
  }}
  .sheet {{
    max-width: 820px; margin: 0 auto; background: #fff;
    border: 1px solid var(--line); box-shadow: 0 8px 28px rgba(16,32,51,.08);
  }}
  .bar {{ height: 6px; background: var(--accent); }}
  .pad {{ padding: 28px 32px 24px; }}
  .head {{
    display: flex; justify-content: space-between; align-items: flex-start;
    gap: 16px; border-bottom: 2px solid var(--accent); padding-bottom: 16px; margin-bottom: 18px;
  }}
  .title {{ font-size: 26px; font-weight: 800; letter-spacing: .04em; margin: 0; color: var(--accent); }}
  .org {{ font-size: 13px; color: var(--muted); margin-top: 4px; }}
  .badge {{
    text-align: right; font-size: 11px; letter-spacing: .08em; text-transform: uppercase;
    color: var(--muted); line-height: 1.5;
  }}
  .period {{
    font-size: 12px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase;
    color: var(--ink); margin-bottom: 16px;
  }}
  .period span {{ color: var(--muted); font-weight: 500; margin-left: 8px; }}
  .meta {{
    display: grid; grid-template-columns: 1fr 1fr; gap: 10px 24px;
    background: var(--soft); border: 1px solid var(--line); padding: 14px 16px; margin-bottom: 22px;
  }}
  .meta-label {{ font-size: 10px; letter-spacing: .08em; text-transform: uppercase; color: var(--muted); }}
  .meta-value {{ font-size: 14px; font-weight: 600; margin-top: 2px; }}
  .section-h {{
    display: flex; justify-content: space-between; align-items: baseline;
    font-size: 11px; font-weight: 800; letter-spacing: .1em; text-transform: uppercase;
    color: var(--accent); border-bottom: 1px solid var(--line); padding-bottom: 6px; margin: 18px 0 8px;
  }}
  .section-h .amt {{ color: var(--muted); font-weight: 700; }}
  .line {{
    display: flex; justify-content: space-between; gap: 12px;
    padding: 8px 0; border-bottom: 1px solid #EEF2F6; font-size: 14px;
  }}
  .line.bold {{ font-weight: 700; border-bottom: none; padding-top: 10px; }}
  .net-box {{
    margin-top: 22px; padding: 16px 18px; background: var(--accent); color: #fff;
    display: flex; justify-content: space-between; align-items: center; gap: 12px;
  }}
  .net-box .lbl {{ font-size: 11px; letter-spacing: .1em; text-transform: uppercase; opacity: .9; }}
  .net-box .val {{ font-size: 24px; font-weight: 800; margin-top: 4px; }}
  .status {{
    background: rgba(255,255,255,.16); border: 1px solid rgba(255,255,255,.35);
    padding: 8px 12px; font-size: 12px; font-weight: 700; letter-spacing: .08em;
  }}
  .foot {{
    margin-top: 20px; font-size: 11px; color: var(--muted); line-height: 1.5;
    border-top: 1px solid var(--line); padding-top: 12px;
  }}
  .actions {{ max-width: 820px; margin: 0 auto 12px; display: flex; gap: 8px; }}
  .actions button {{
    border: 0; background: var(--accent); color: #fff; padding: 10px 16px;
    font-weight: 600; cursor: pointer; border-radius: 6px;
  }}
  .actions button.secondary {{ background: #fff; color: var(--accent); border: 1px solid var(--accent); }}
  @media print {{
    body {{ background: #fff; padding: 0; }}
    .sheet {{ box-shadow: none; border: 0; max-width: none; }}
    .noprint {{ display: none !important; }}
  }}
  @media (max-width: 640px) {{
    .meta {{ grid-template-columns: 1fr; }}
    .head {{ flex-direction: column; }}
    .badge {{ text-align: left; }}
  }}
</style>
</head>
<body>
  <div class="actions noprint">
    <button onclick="window.print()">Print / Save PDF</button>
    <button class="secondary" onclick="window.close()">Close</button>
  </div>
  <div class="sheet">
    <div class="bar"></div>
    <div class="pad">
      <div class="head">
        <div>
          <h1 class="title">SALARY SLIP</h1>
          <div class="org">{escape(org_name)}</div>
        </div>
        <div class="badge">
          Confidential paystub statement<br/>
          Days worked: {escape(days)}
          {f"<br/>Unpaid leave: {escape(_money(unpaid))}" if _nz(unpaid) else ""}
        </div>
      </div>

      <div class="period">
        Payroll period: {escape(period_name)}
        <span>System-generated</span>
      </div>

      <div class="meta">
        {_meta("Employee code", emp.employee_code)}
        {_meta("Employee name", emp.full_name)}
        {_meta("Department", dept or "—")}
        {_meta("Designation", desig or "—")}
        {_meta("Branch", branch or "—")}
        {_meta("Payment method", pay_method)}
        {_meta("Bank name", bank_name)}
        {_meta("Account number", bank_account)}
      </div>

      <div class="section-h">
        <span>Earnings &amp; allowances</span>
        <span class="amt">Amount ({escape(curr_label)})</span>
      </div>
      {earn_html}

      <div class="section-h">
        <span>Deductions &amp; statutory</span>
        <span class="amt">Amount ({escape(curr_label)})</span>
      </div>
      {ded_html}

      <div class="net-box">
        <div>
          <div class="lbl">Net salary payable</div>
          <div class="val">Rs. {_money(slip.net_pay)}</div>
        </div>
        <div class="status">STATUS: {escape(status_label)}</div>
      </div>

      <div class="foot">
        This is a system-generated computerized payslip statement and does not require any physical signature.
        For queries contact your HR / Payroll team. Currency: {escape(currency)}.
        {f" Payment date: {escape(str(slip.payment_date))}." if slip.payment_date else ""}
        {f" Ref: {escape(slip.payment_reference)}." if slip.payment_reference else ""}
      </div>
    </div>
  </div>
</body>
</html>"""
    return html
