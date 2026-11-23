"""Recurring AR contract helpers (LotBatch/Serial serializers live in ops.serializers)."""

from __future__ import annotations

from calendar import monthrange
from datetime import date, timedelta

from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from ops.models import CustomerContract

RO = (
    "organization",
    "created_at",
    "updated_at",
    "created_by",
    "updated_by",
    "is_deleted",
    "deleted_at",
    "deleted_by",
)


def _add_months(d: date, months: int) -> date:
    y = d.year + (d.month - 1 + months) // 12
    m = (d.month - 1 + months) % 12 + 1
    day = min(d.day, monthrange(y, m)[1])
    return date(y, m, day)


class CustomerContractSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.name", read_only=True)
    customer_code = serializers.CharField(source="customer.code", read_only=True)

    class Meta:
        model = CustomerContract
        fields = "__all__"
        read_only_fields = RO

    def create(self, validated_data):
        if not validated_data.get("next_bill_date"):
            validated_data["next_bill_date"] = validated_data.get("start_date")
        return super().create(validated_data)


def generate_contract_invoice(contract: CustomerContract, *, user=None):
    from core.doc_numbers import ensure_doc_no
    from finance.models import CustomerInvoice

    if contract.status != CustomerContract.Status.ACTIVE:
        raise ValidationError("Only active contracts can generate invoices.")

    bill_date = contract.next_bill_date or timezone.localdate()
    due = bill_date + timedelta(days=int(contract.customer.payment_terms_days or 30))
    data = {
        "invoice_no": "",
        "invoice_date": bill_date,
        "due_date": due,
        "amount": contract.amount,
        "tax_amount": 0,
        "description": f"Contract billing · {contract.name}",
        "status": CustomerInvoice.Status.DRAFT,
        "customer": contract.customer,
        "organization": contract.organization,
        "created_by": user,
        "updated_by": user,
    }
    ensure_doc_no(
        data, "invoice_no", contract.organization, kind="ar_invoice", model=CustomerInvoice
    )
    inv = CustomerInvoice.objects.create(**data)

    freq = contract.billing_frequency
    if freq == CustomerContract.BillingFrequency.MONTHLY:
        nxt = _add_months(bill_date, 1)
    elif freq == CustomerContract.BillingFrequency.QUARTERLY:
        nxt = _add_months(bill_date, 3)
    else:
        nxt = _add_months(bill_date, 12)
    contract.next_bill_date = nxt
    if contract.end_date and nxt > contract.end_date:
        contract.status = CustomerContract.Status.ENDED
    if user:
        contract.updated_by = user
    contract.save(update_fields=["next_bill_date", "status", "updated_by", "updated_at"])
    return inv
