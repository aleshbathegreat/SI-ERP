"""CRM workflow helpers: lead conversion, forecast, and opportunity → quotation."""

from __future__ import annotations

import calendar
import re
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from core.doc_numbers import ensure_doc_no
from crm.models import STAGE_PROBABILITY, Lead, Opportunity
from ops.models import Customer, SalesQuotation


def _dec(value, default=Decimal("0")) -> Decimal:
    if value in (None, ""):
        return default
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        raise ValidationError({"amount": "Invalid amount."})


def _find_customer(lead: Lead) -> Customer | None:
    qs = Customer.objects.filter(organization_id=lead.organization_id)
    if lead.email:
        found = qs.filter(email__iexact=lead.email).first()
        if found:
            return found
    name = (lead.company or lead.name or "").strip()
    if name:
        return qs.filter(name__iexact=name).first()
    return None


@transaction.atomic
def convert_lead(lead: Lead, *, user=None, data: dict | None = None):
    """Create/link a Customer and an Opportunity from a lead.

    Returns (customer, opportunity, created) — idempotent for converted leads.
    """
    data = data or {}
    if lead.status == Lead.Status.CONVERTED and lead.converted_opportunity_id:
        return lead.converted_customer, lead.converted_opportunity, False
    if lead.status == Lead.Status.LOST:
        raise ValidationError("Cannot convert a lost lead. Reopen it first.")

    customer = None
    customer_id = data.get("customer")
    if customer_id:
        customer = Customer.objects.filter(
            organization_id=lead.organization_id, pk=customer_id
        ).first()
        if customer is None:
            raise ValidationError({"customer": "Customer not found."})
    if customer is None:
        customer = _find_customer(lead)
    if customer is None:
        display = (lead.company or lead.name).strip()
        cust_data = {"code": ""}
        ensure_doc_no(
            cust_data, "code", lead.organization, kind="customer", model=Customer
        )
        customer = Customer.objects.create(
            organization_id=lead.organization_id,
            code=cust_data["code"],
            name=display,
            email=lead.email or "",
            phone=lead.phone or "",
            contact_person=lead.name if lead.company else "",
            notes=f"Created from CRM lead #{lead.pk}",
            created_by=user,
            updated_by=user,
        )

    opp_name = (data.get("opportunity_name") or "").strip() or (
        f"{(lead.company or lead.name).strip()} - Opportunity"
    )
    opportunity = Opportunity.objects.create(
        organization_id=lead.organization_id,
        lead=lead,
        customer=customer,
        name=opp_name[:255],
        amount=_dec(data.get("amount")),
        stage=Opportunity.Stage.PROSPECTING,
        probability=10,
        owner=lead.owner or user,
        expected_close=data.get("expected_close") or None,
        created_by=user,
        updated_by=user,
    )

    lead.status = Lead.Status.CONVERTED
    lead.converted_customer = customer
    lead.converted_opportunity = opportunity
    if user:
        lead.updated_by = user
    lead.save(
        update_fields=[
            "status",
            "converted_customer",
            "converted_opportunity",
            "updated_by",
            "updated_at",
        ]
    )
    return customer, opportunity, True


@transaction.atomic
def create_quote_from_opportunity(opp: Opportunity, *, user=None):
    """Create a draft SalesQuotation for the opportunity's customer.

    Returns (quote, created). Re-uses an existing draft quote for the opportunity.
    """
    if opp.stage in (Opportunity.Stage.LOST,):
        raise ValidationError("Cannot create a quote for a lost opportunity.")

    existing = (
        SalesQuotation.objects.filter(
            organization_id=opp.organization_id,
            opportunity=opp,
            status=SalesQuotation.Status.DRAFT,
        )
        .order_by("-id")
        .first()
    )
    if existing:
        return existing, False

    customer = opp.customer
    if customer is None and opp.lead_id and opp.lead.converted_customer_id:
        customer = opp.lead.converted_customer
    if customer is None:
        raise ValidationError(
            "Link a customer to this opportunity (or convert the lead) before quoting."
        )
    if opp.customer_id != customer.id:
        opp.customer = customer
        opp.save(update_fields=["customer", "updated_at"])

    data = {"quote_no": ""}
    ensure_doc_no(
        data, "quote_no", opp.organization, kind="quote", model=SalesQuotation
    )
    quote = SalesQuotation.objects.create(
        organization_id=opp.organization_id,
        quote_no=data["quote_no"],
        customer=customer,
        opportunity=opp,
        quote_date=timezone.localdate(),
        valid_until=opp.expected_close,
        payment_terms_days=customer.payment_terms_days or 30,
        currency=customer.currency or "PKR",
        amount=opp.amount or Decimal("0"),
        status=SalesQuotation.Status.DRAFT,
        notes=f"From opportunity: {opp.name}",
        created_by=user,
        updated_by=user,
    )
    if opp.stage == Opportunity.Stage.PROSPECTING:
        opp.stage = Opportunity.Stage.PROPOSAL
        fields = ["stage", "updated_at"]
        if opp.probability in (None, STAGE_PROBABILITY[Opportunity.Stage.PROSPECTING]):
            opp.probability = STAGE_PROBABILITY[Opportunity.Stage.PROPOSAL]
            fields.append("probability")
        opp.save(update_fields=fields)
    return quote, True


def _digits(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def find_lead_duplicates(
    organization_id: int,
    *,
    email: str = "",
    phone: str = "",
    company: str = "",
    exclude_id: int | None = None,
    limit: int = 5,
):
    """Leads and customers that already match this email, phone, or company."""
    leads = Lead.objects.filter(organization_id=organization_id).select_related()
    customers = Customer.objects.filter(organization_id=organization_id)
    if exclude_id:
        leads = leads.exclude(pk=exclude_id)

    found_leads: dict[int, Lead] = {}
    found_customers: dict[int, Customer] = {}
    email = (email or "").strip()
    company = (company or "").strip()
    tail = _digits(phone)[-10:]

    if "@" in email:
        for row in leads.filter(email__iexact=email)[:limit]:
            found_leads[row.pk] = row
        for row in customers.filter(email__iexact=email)[:limit]:
            found_customers[row.pk] = row
    if len(tail) >= 7:
        for row in leads.exclude(phone="").filter(phone__icontains=tail[-7:])[:30]:
            if _digits(row.phone).endswith(tail[-7:]):
                found_leads[row.pk] = row
                if len(found_leads) >= limit:
                    break
        for row in customers.exclude(phone="").filter(phone__icontains=tail[-7:])[:30]:
            if _digits(row.phone).endswith(tail[-7:]):
                found_customers[row.pk] = row
                if len(found_customers) >= limit:
                    break
    if len(company) >= 3:
        for row in leads.filter(company__iexact=company)[:limit]:
            found_leads[row.pk] = row
        for row in customers.filter(name__iexact=company)[:limit]:
            found_customers[row.pk] = row

    return list(found_leads.values())[:limit], list(found_customers.values())[:limit]


def _blank_bucket():
    return {"count": 0, "amount": Decimal("0"), "weighted": Decimal("0")}


def _pack_bucket(key: str, label: str, bucket: dict) -> dict:
    return {
        "key": key,
        "label": label,
        "count": bucket["count"],
        "amount": str(bucket["amount"].quantize(Decimal("0.01"))),
        "weighted": str(bucket["weighted"].quantize(Decimal("0.01"))),
    }


def build_forecast(rows) -> list[dict]:
    """Open pipeline grouped into slipped, the next six months, later, and undated."""
    today = timezone.localdate()
    start = today.replace(day=1)
    keys: list[tuple[int, int]] = []
    year, month = start.year, start.month
    for _ in range(6):
        keys.append((year, month))
        month += 1
        if month == 13:
            year += 1
            month = 1
    buckets = {key: _blank_bucket() for key in keys}
    overdue = _blank_bucket()
    later = _blank_bucket()
    unscheduled = _blank_bucket()
    for row in rows:
        amount = Decimal(row.amount or 0)
        weighted = amount * Decimal(row.probability or 0) / Decimal(100)
        close = row.expected_close
        if close is None:
            target = unscheduled
        elif close < start:
            target = overdue
        else:
            target = buckets.get((close.year, close.month), later)
        target["count"] += 1
        target["amount"] += amount
        target["weighted"] += weighted
    months = [_pack_bucket("overdue", "Slipped", overdue)]
    for year, month in keys:
        months.append(
            _pack_bucket(
                f"{year:04d}-{month:02d}",
                f"{calendar.month_abbr[month]} {year}",
                buckets[(year, month)],
            )
        )
    months.append(_pack_bucket("later", "Later", later))
    months.append(_pack_bucket("unscheduled", "No close date", unscheduled))
    return months
