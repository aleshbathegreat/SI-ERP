"""Professional payslip emails via tenant SMTP."""

from __future__ import annotations

from decimal import Decimal
from html import escape

from core.mailer import send_tenant_email


def _money(v) -> str:
    try:
        n = Decimal(str(v or 0))
    except Exception:
        n = Decimal("0")
    return f"{n:,.2f}"


def _row(label: str, value, *, bold: bool = False) -> str:
    weight = "700" if bold else "400"
    return (
        f'<tr><td style="padding:8px 0;border-bottom:1px solid #E8EEF4;color:#5B6B7C">'
        f"{escape(label)}</td>"
        f'<td style="padding:8px 0;border-bottom:1px solid #E8EEF4;text-align:right;'
        f'font-weight:{weight};color:#102033">{escape(_money(value))}</td></tr>'
    )


def render_payslip_email(slip, organization) -> tuple[str, str, str]:
    """Return subject, plain text, html for one payslip."""
    emp = slip.employee
    period = slip.period
    brand = organization.brand_name or organization.name
    currency = slip.currency or period.currency or "PKR"
    name = emp.full_name
    subject = f"Payslip · {period.name} · {emp.employee_code}"

    plain = (
        f"Dear {name},\n\n"
        f"Please find your payslip for {period.name}.\n\n"
        f"Employee: {emp.employee_code} — {name}\n"
        f"Gross pay: {currency} {_money(slip.gross_pay or slip.basic)}\n"
        f"Total deductions: {currency} {_money(slip.total_deductions or slip.deductions)}\n"
        f"Net pay: {currency} {_money(slip.net_pay)}\n\n"
        f"This is a system-generated payslip from {brand}. "
        f"For queries contact your HR / Payroll team.\n"
    )

    accent = organization.brand_primary_color or "#0B3D5C"
    earn_rows = "".join(
        [
            _row("Basic salary", slip.basic),
            _row("Housing allowance", slip.housing_allowance),
            _row("Transport allowance", slip.transport_allowance),
            _row("Medical allowance", slip.medical_allowance),
            _row("Meal allowance", slip.meal_allowance),
            _row("Overtime", slip.overtime),
            _row("Bonus", slip.bonus),
            _row("Commission", slip.commission),
            _row("Other earnings", slip.other_earnings),
            _row("Gross pay", slip.gross_pay or slip.basic, bold=True),
        ]
    )
    ded_rows = "".join(
        [
            _row("Income tax / PAYE", slip.income_tax or slip.tax),
            _row("Social security / EOBI", slip.eobi or slip.social_security),
            _row("Provident fund", slip.provident_fund),
            _row("Pension", slip.pension),
            _row("Loan repayment", slip.loan_repayment),
            _row("Advance recovery", slip.advance_recovery),
            _row("Other deductions", slip.other_deductions),
            _row(
                "Total deductions",
                slip.total_deductions or slip.deductions,
                bold=True,
            ),
        ]
    )

    html = f"""<!DOCTYPE html>
<html><body style="margin:0;padding:0;background:#F4F7FA;font-family:Segoe UI,Roboto,Helvetica,Arial,sans-serif">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#F4F7FA;padding:24px 12px">
    <tr><td align="center">
      <table role="presentation" width="600" cellspacing="0" cellpadding="0" style="background:#ffffff;border-radius:12px;overflow:hidden;border:1px solid #E4EAF0">
        <tr><td style="background:{escape(accent)};padding:20px 28px;color:#fff">
          <div style="font-size:20px;font-weight:700">{escape(brand)}</div>
          <div style="opacity:.9;font-size:13px;margin-top:4px">Official payslip notification</div>
        </td></tr>
        <tr><td style="padding:28px">
          <p style="margin:0 0 12px;color:#102033;font-size:16px">Dear {escape(name)},</p>
          <p style="margin:0 0 20px;color:#5B6B7C;font-size:14px;line-height:1.5">
            Your payslip for <strong>{escape(period.name)}</strong> is ready.
            Please review the summary below. Retain this email for your records.
          </p>
          <table width="100%" style="font-size:13px;margin-bottom:20px">
            <tr><td style="color:#5B6B7C;padding:4px 0">Employee</td>
                <td style="text-align:right;color:#102033;font-weight:600">{escape(emp.employee_code)} — {escape(name)}</td></tr>
            <tr><td style="color:#5B6B7C;padding:4px 0">Period</td>
                <td style="text-align:right;color:#102033">{escape(period.name)}</td></tr>
            <tr><td style="color:#5B6B7C;padding:4px 0">Currency</td>
                <td style="text-align:right;color:#102033">{escape(currency)}</td></tr>
            <tr><td style="color:#5B6B7C;padding:4px 0">Days worked</td>
                <td style="text-align:right;color:#102033">{escape(str(slip.days_worked or "—"))}</td></tr>
            <tr><td style="color:#5B6B7C;padding:4px 0">Payment method</td>
                <td style="text-align:right;color:#102033">{escape((slip.payment_method or "bank_transfer").replace("_"," "))}</td></tr>
          </table>

          <div style="font-size:12px;font-weight:700;letter-spacing:.06em;color:{escape(accent)};margin:8px 0">EARNINGS</div>
          <table width="100%" style="font-size:13px;margin-bottom:16px">{earn_rows}</table>

          <div style="font-size:12px;font-weight:700;letter-spacing:.06em;color:{escape(accent)};margin:8px 0">DEDUCTIONS</div>
          <table width="100%" style="font-size:13px;margin-bottom:16px">{ded_rows}</table>

          <table width="100%" style="background:#F4F7FA;border-radius:8px;margin-top:8px">
            <tr>
              <td style="padding:14px 16px;font-size:14px;color:#5B6B7C">Net pay</td>
              <td style="padding:14px 16px;text-align:right;font-size:20px;font-weight:700;color:{escape(accent)}">
                {escape(currency)} {_money(slip.net_pay)}
              </td>
            </tr>
          </table>

          <p style="margin:24px 0 0;color:#9AA8B6;font-size:12px;line-height:1.5">
            This message was sent automatically by {escape(brand)}.
            If you believe there is an error, contact HR / Payroll.
            Do not reply to this email unless a reply-to address is configured.
          </p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body></html>"""
    return subject, plain, html


def send_payslip_email(slip) -> tuple[bool, str]:
    emp = slip.employee
    org = slip.period.organization
    to = (emp.email or "").strip()
    if not to:
        return False, f"{emp.employee_code}: no email"
    subject, plain, html = render_payslip_email(slip, org)
    ok = send_tenant_email(
        org,
        subject,
        plain,
        [to],
        purpose="payroll",
        html_message=html,
    )
    return ok, f"{emp.employee_code} → {to}" + ("" if ok else " (failed)")


def send_period_payslips(period, *, only_ids: list[int] | None = None) -> dict:
    qs = period.payslips.select_related("employee", "period", "period__organization")
    if only_ids:
        qs = qs.filter(id__in=only_ids)
    sent = 0
    failed = 0
    skipped = 0
    details = []
    for slip in qs:
        if not (slip.employee.email or "").strip():
            skipped += 1
            details.append(f"{slip.employee.employee_code}: skipped (no email)")
            continue
        ok, detail = send_payslip_email(slip)
        details.append(detail)
        if ok:
            sent += 1
        else:
            failed += 1
    return {
        "sent": sent,
        "failed": failed,
        "skipped": skipped,
        "details": details[:50],
    }
