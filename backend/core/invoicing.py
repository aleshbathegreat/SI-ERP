"""SaaS invoice helpers — platform AR for tenant subscriptions."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from core.models import Organization, SaaSInvoice, SubscriptionPackage, SubscriptionPayment


def next_invoice_no() -> str:
    year = date.today().year
    prefix = f"SI-{year}-"
    last = (
        SaaSInvoice.objects.filter(invoice_no__startswith=prefix)
        .order_by("-invoice_no")
        .values_list("invoice_no", flat=True)
        .first()
    )
    seq = 1
    if last:
        try:
            seq = int(last.split("-")[-1]) + 1
        except ValueError:
            seq = SaaSInvoice.objects.count() + 1
    return f"{prefix}{seq:05d}"


@transaction.atomic
def create_invoice(
    org: Organization,
    *,
    amount: Decimal | str | float,
    plan_code: str = "",
    package: SubscriptionPackage | None = None,
    period_start: date | None = None,
    period_end: date | None = None,
    description: str = "",
    tax_amount: Decimal | str | float = 0,
    due_days: int = 14,
    status: str = SaaSInvoice.Status.SENT,
    payment: SubscriptionPayment | None = None,
    user=None,
    notes: str = "",
) -> SaaSInvoice:
    amount = Decimal(str(amount))
    tax_amount = Decimal(str(tax_amount))
    if package is None and plan_code:
        package = SubscriptionPackage.objects.filter(code=plan_code).first()
    inv = SaaSInvoice(
        organization=org,
        invoice_no=next_invoice_no(),
        package=package,
        plan_code=plan_code or (package.code if package else ""),
        description=description
        or f"SI-ERP subscription · {plan_code or (package.name if package else 'plan')}",
        period_start=period_start,
        period_end=period_end,
        amount=amount,
        tax_amount=tax_amount,
        total=amount + tax_amount,
        status=status,
        issue_date=date.today(),
        due_date=date.today() + timedelta(days=due_days),
        payment=payment,
        created_by=user,
        notes=notes,
    )
    if status == SaaSInvoice.Status.PAID:
        inv.paid_at = timezone.now()
    inv.save()
    return inv


def mark_invoice_paid(inv: SaaSInvoice, payment: SubscriptionPayment | None = None):
    inv.status = SaaSInvoice.Status.PAID
    inv.paid_at = timezone.now()
    if payment:
        inv.payment = payment
    inv.save(update_fields=["status", "paid_at", "payment", "updated_at"])
    return inv


def invoice_from_payment(payment: SubscriptionPayment, user=None) -> SaaSInvoice:
    existing = SaaSInvoice.objects.filter(payment=payment).first()
    if existing:
        if payment.status == SubscriptionPayment.Status.PAID:
            mark_invoice_paid(existing, payment)
        return existing
    status = (
        SaaSInvoice.Status.PAID
        if payment.status == SubscriptionPayment.Status.PAID
        else SaaSInvoice.Status.SENT
    )
    return create_invoice(
        payment.organization,
        amount=payment.amount,
        plan_code=payment.plan,
        period_start=payment.period_start,
        period_end=payment.period_end,
        description=f"Payment {payment.reference}",
        status=status,
        payment=payment,
        user=user or payment.user,
        due_days=0 if status == SaaSInvoice.Status.PAID else 7,
    )


def mark_overdue_invoices() -> int:
    today = date.today()
    qs = SaaSInvoice.objects.filter(
        status=SaaSInvoice.Status.SENT,
        due_date__lt=today,
    )
    return qs.update(status=SaaSInvoice.Status.OVERDUE)
