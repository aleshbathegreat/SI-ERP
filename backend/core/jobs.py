"""Scheduled ERP jobs (callable from management commands / ops scripts / cron)."""

from __future__ import annotations

import logging
from datetime import date

log = logging.getLogger(__name__)

MAX_CATCHUP_PER_CONTRACT = 24


def bill_due_customer_contracts(today: date | None = None, *, organization=None) -> dict:
    """
    Generate draft AR invoices for active CustomerContracts with next_bill_date <= today.
    Catches up missed periods (bounded). Returns stats dict.
    """
    from django.db import transaction
    from django.utils import timezone

    from ops.enterprise_serializers import generate_contract_invoice
    from ops.models import CustomerContract

    today = today or timezone.localdate()
    qs = CustomerContract.objects.filter(
        status=CustomerContract.Status.ACTIVE,
        is_deleted=False,
        next_bill_date__isnull=False,
        next_bill_date__lte=today,
    ).select_related("customer", "organization")
    if organization is not None:
        qs = qs.filter(organization=organization)

    stats = {"contracts": 0, "invoices": 0, "errors": [], "invoice_ids": []}
    for contract in qs:
        stats["contracts"] += 1
        for _ in range(MAX_CATCHUP_PER_CONTRACT):
            if (
                contract.status != CustomerContract.Status.ACTIVE
                or not contract.next_bill_date
                or contract.next_bill_date > today
            ):
                break
            try:
                with transaction.atomic():
                    inv = generate_contract_invoice(contract)
                stats["invoices"] += 1
                stats["invoice_ids"].append(inv.id)
            except Exception as e:  # keep batch going
                log.exception("Contract %s billing failed", contract.pk)
                stats["errors"].append(f"contract {contract.pk}: {e}")
                break
    return stats
