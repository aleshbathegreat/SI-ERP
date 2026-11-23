"""Auto-post journals for AP payment, depreciation, and reversals."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from core.doc_numbers import ensure_doc_no
from finance.models import Account, BankAccount, JournalEntry, JournalLine


def _d(v) -> Decimal:
    return Decimal(str(v or 0)).quantize(Decimal("0.01"))


def ensure_system_account(
    org,
    *,
    code: str,
    name: str,
    account_type: str,
) -> Account:
    acc = Account.objects.filter(organization=org, code=code).first()
    if acc:
        return acc
    return Account.objects.create(
        organization=org,
        code=code,
        name=name,
        account_type=account_type,
        is_active=True,
    )


def system_accounts(org) -> dict[str, Account]:
    """Ensure standard control accounts exist (idempotent)."""
    return {
        "ap": ensure_system_account(
            org, code="2100", name="Trade payables (AP)", account_type="liability"
        ),
        "ar": ensure_system_account(
            org, code="1200", name="Trade receivables (AR)", account_type="asset"
        ),
        "revenue": ensure_system_account(
            org, code="4100", name="Sales revenue", account_type="income"
        ),
        "wht": ensure_system_account(
            org, code="2150", name="WHT payable", account_type="liability"
        ),
        "cash": ensure_system_account(
            org, code="1100", name="Cash at bank", account_type="asset"
        ),
        "dep_exp": ensure_system_account(
            org,
            code="5700",
            name="Depreciation expense",
            account_type="expense",
        ),
        "accum_dep": ensure_system_account(
            org,
            code="1590",
            name="Accumulated depreciation",
            account_type="asset",
        ),
        "purchases": ensure_system_account(
            org,
            code="5100",
            name="Purchases / inventory accrual",
            account_type="expense",
        ),
    }


@transaction.atomic
def post_ap_invoice_accrual(*, invoice, user=None) -> JournalEntry:
    """
    On AP invoice approve:
    Dr Purchases / inventory accrual
       Cr Trade payables (AP)
    """
    from finance.fx import invoice_base_rate

    org = invoice.organization
    accts = system_accounts(org)
    rate = invoice_base_rate(invoice, org, refresh=True)
    gross = _d(_d(invoice.amount) * rate)
    if gross <= 0:
        raise ValueError("Invoice amount must be positive to post accrual")
    return post_balanced_journal(
        org,
        entry_date=getattr(invoice, "invoice_date", None) or timezone.localdate(),
        reference="",
        narration=(
            f"Being accrual of vendor invoice {invoice.invoice_no} "
            f"({getattr(invoice.vendor, 'name', 'vendor')}) {_d(gross)}"
        ),
        lines=[
            {
                "account": accts["purchases"],
                "debit": gross,
                "credit": 0,
                "description": f"AP accrual {invoice.invoice_no}",
            },
            {
                "account": accts["ap"],
                "debit": 0,
                "credit": gross,
                "description": f"AP accrual {invoice.invoice_no}",
            },
        ],
        user=user,
    )


@transaction.atomic
def post_ar_invoice_accrual(*, invoice, user=None) -> JournalEntry:
    """
    On AR invoice approve:
    Dr Trade receivables (AR)
       Cr Sales revenue (+ tax portion stays in revenue for simplicity)
    """
    from finance.fx import invoice_base_rate

    org = invoice.organization
    accts = system_accounts(org)
    rate = invoice_base_rate(invoice, org, refresh=True)
    gross = _d(
        (_d(invoice.amount) + _d(getattr(invoice, "tax_amount", 0))) * rate
    )
    if gross <= 0:
        raise ValueError("Invoice amount must be positive to post accrual")
    return post_balanced_journal(
        org,
        entry_date=getattr(invoice, "invoice_date", None) or timezone.localdate(),
        reference="",
        narration=(
            f"Being accrual of AR invoice {invoice.invoice_no} "
            f"({getattr(invoice.customer, 'name', 'customer')}) {_d(gross)}"
        ),
        lines=[
            {
                "account": accts["ar"],
                "debit": gross,
                "credit": 0,
                "description": f"AR accrual {invoice.invoice_no}",
            },
            {
                "account": accts["revenue"],
                "debit": 0,
                "credit": gross,
                "description": f"AR accrual {invoice.invoice_no}",
            },
        ],
        user=user,
    )


@transaction.atomic
def post_balanced_journal(
    org,
    *,
    entry_date: date,
    reference: str,
    narration: str,
    lines: list[dict],
    user=None,
) -> JournalEntry:
    """
    Create a posted balanced journal.
    Each line: {account, debit=0, credit=0, description="", cost_center=None}
    """
    if len(lines) < 2:
        raise ValueError("Journal needs at least two lines")
    debit = sum(_d(l.get("debit")) for l in lines)
    credit = sum(_d(l.get("credit")) for l in lines)
    if abs(debit - credit) >= Decimal("0.01"):
        raise ValueError(f"Unbalanced auto-journal: debit={debit} credit={credit}")

    data = {"reference": (reference or "").strip(), "narration": narration or ""}
    ensure_doc_no(data, "reference", org, kind="journal", model=JournalEntry)

    je = JournalEntry.objects.create(
        organization=org,
        entry_date=entry_date,
        reference=data["reference"],
        narration=narration or "",
        status=JournalEntry.Status.POSTED,
        posted_at=timezone.now(),
        created_by=user,
        updated_by=user,
        submitted_by=user,
        approved_by=user,
    )
    for line in lines:
        JournalLine.objects.create(
            journal=je,
            account=line["account"],
            cost_center=line.get("cost_center"),
            debit=_d(line.get("debit")),
            credit=_d(line.get("credit")),
            description=(line.get("description") or "")[:255],
        )
    return je


def bank_gl_account(bank: BankAccount, org) -> Account:
    if bank.gl_account_id:
        return bank.gl_account
    # Fallback to system cash account
    return system_accounts(org)["cash"]


@transaction.atomic
def post_ap_payment(*, invoice, bank: BankAccount, user=None) -> JournalEntry:
    """
    Dr Trade payables (gross)
       Cr Bank (net paid)
       Cr WHT payable (wht)   [if wht > 0]
    """
    org = invoice.organization
    accts = system_accounts(org)
    cash = bank_gl_account(bank, org)
    gross = _d(invoice.amount)
    wht = _d(invoice.wht_amount)
    paid = _d(invoice.paid_amount) if invoice.paid_amount is not None else (gross - wht)
    if paid < 0:
        raise ValueError("Paid amount cannot be negative")
    # Prefer balancing: AP credit side = paid + wht should equal gross
    if abs((paid + wht) - gross) >= Decimal("0.01"):
        # Adjust paid to net of WHT if mismatch
        paid = gross - wht

    from finance.fx import invoice_base_rate

    rate = invoice_base_rate(invoice, org)
    if rate != Decimal("1"):
        gross = _d(gross * rate)
        paid = _d(paid * rate)
        wht = gross - paid

    lines = [
        {
            "account": accts["ap"],
            "debit": gross,
            "credit": 0,
            "description": f"Settle AP {invoice.invoice_no}",
        },
        {
            "account": cash,
            "debit": 0,
            "credit": paid,
            "description": f"Bank payment {invoice.payment_ref or ''}".strip(),
        },
    ]
    if wht > 0:
        lines.append(
            {
                "account": accts["wht"],
                "debit": 0,
                "credit": wht,
                "description": f"WHT on {invoice.invoice_no}",
            }
        )

    # Reduce bank book balance
    bank.current_balance = _d(bank.current_balance) - paid
    bank.save(update_fields=["current_balance", "updated_at"])

    return post_balanced_journal(
        org,
        entry_date=timezone.localdate(),
        reference="",
        narration=(
            f"Being payment of vendor invoice {invoice.invoice_no} "
            f"({getattr(invoice.vendor, 'name', 'vendor')}) "
            f"gross {_d(gross)} less WHT {_d(wht)}"
        ),
        lines=lines,
        user=user,
    )


@transaction.atomic
def post_ar_receipt(*, invoice, bank: BankAccount, user=None) -> JournalEntry:
    """
    Dr Bank
       Cr Trade receivables (AR)
    """
    org = invoice.organization
    accts = system_accounts(org)
    cash = bank_gl_account(bank, org)
    gross = _d(invoice.amount) + _d(getattr(invoice, "tax_amount", 0))
    paid = _d(invoice.paid_amount) if invoice.paid_amount else gross
    if paid <= 0:
        raise ValueError("Paid amount must be positive")
    if paid > gross:
        paid = gross

    from finance.fx import invoice_base_rate

    paid = _d(paid * invoice_base_rate(invoice, org))

    bank.current_balance = _d(bank.current_balance) + paid
    bank.save(update_fields=["current_balance", "updated_at"])

    return post_balanced_journal(
        org,
        entry_date=timezone.localdate(),
        reference="",
        narration=(
            f"Being receipt against AR invoice {invoice.invoice_no} "
            f"({getattr(invoice.customer, 'name', 'customer')}) amount {_d(paid)}"
        ),
        lines=[
            {
                "account": cash,
                "debit": paid,
                "credit": 0,
                "description": f"Bank receipt {invoice.payment_ref or ''}".strip(),
            },
            {
                "account": accts["ar"],
                "debit": 0,
                "credit": paid,
                "description": f"Settle AR {invoice.invoice_no}",
            },
        ],
        user=user,
    )


@transaction.atomic
def post_depreciation(*, asset, amount: Decimal, user=None) -> JournalEntry:
    """
    Dr Depreciation expense
       Cr Accumulated depreciation
    """
    org = asset.organization
    accts = system_accounts(org)
    amt = _d(amount)
    if amt <= 0:
        raise ValueError("Depreciation amount must be positive")
    return post_balanced_journal(
        org,
        entry_date=timezone.localdate(),
        reference="",
        narration=f"Being SL depreciation of asset {asset.asset_code} — {asset.name}",
        lines=[
            {
                "account": accts["dep_exp"],
                "debit": amt,
                "credit": 0,
                "description": asset.asset_code,
            },
            {
                "account": accts["accum_dep"],
                "debit": 0,
                "credit": amt,
                "description": asset.asset_code,
            },
        ],
        user=user,
    )


@transaction.atomic
def post_cheque_clearing(*, cheque, user=None, post_journal: bool = True):
    """
    Issued cheque clears the bank:
    Dr Trade payables (AP)
       Cr Bank
    Also reduces BankAccount.current_balance.
    """
    org = cheque.organization
    bank = cheque.bank_account
    amt = _d(cheque.amount)
    if amt <= 0:
        raise ValueError("Cheque amount must be positive")
    bank.current_balance = _d(bank.current_balance) - amt
    bank.save(update_fields=["current_balance", "updated_at"])
    if not post_journal:
        return None
    accts = system_accounts(org)
    return post_balanced_journal(
        org,
        entry_date=cheque.cleared_date or timezone.localdate(),
        reference="",
        narration=f"Being clearing of cheque {cheque.cheque_no} to {cheque.payee}",
        lines=[
            {
                "account": accts["ap"],
                "debit": amt,
                "credit": 0,
                "description": f"Cheque {cheque.cheque_no}",
            },
            {
                "account": bank_gl_account(bank, org),
                "debit": 0,
                "credit": amt,
                "description": f"Cheque {cheque.cheque_no}",
            },
        ],
        user=user,
    )


@transaction.atomic
def post_cheque_bounce_reversal(*, cheque, user=None):
    """Bounce of a previously cleared cheque: restore bank balance, reverse its journal."""
    bank = cheque.bank_account
    bank.current_balance = _d(bank.current_balance) + _d(cheque.amount)
    bank.save(update_fields=["current_balance", "updated_at"])
    if cheque.gl_journal_id and cheque.gl_journal.status == JournalEntry.Status.POSTED:
        return reverse_journal(journal=cheque.gl_journal, user=user)
    return None


@transaction.atomic
def post_intercompany_txn(*, txn, user=None) -> JournalEntry:
    """
    Receivable: Dr partner receivable account, Cr Intercompany clearing
    Payable:    Dr Intercompany clearing,     Cr partner payable account
    Amount is converted to org base currency when partner currency differs.
    """
    from finance.fx import convert

    org = txn.organization
    partner = txn.partner
    amt = _d(txn.amount)
    if amt <= 0:
        raise ValueError("Intercompany amount must be positive")
    base = (getattr(org, "currency", "") or "PKR").upper()
    ccy = (partner.currency or base).upper()
    if ccy != base:
        amt = convert(org, amt, ccy, base, txn.date)
    clearing = ensure_system_account(
        org, code="2900", name="Intercompany clearing", account_type="liability"
    )
    if txn.direction == txn.Direction.RECEIVABLE:
        if not partner.receivable_account_id:
            raise ValueError(f"Set a receivable account on partner {partner.code}.")
        lines = [
            {"account": partner.receivable_account, "debit": amt, "credit": 0,
             "description": f"IC AR {partner.code}"},
            {"account": clearing, "debit": 0, "credit": amt,
             "description": f"IC AR {partner.code}"},
        ]
    else:
        if not partner.payable_account_id:
            raise ValueError(f"Set a payable account on partner {partner.code}.")
        lines = [
            {"account": clearing, "debit": amt, "credit": 0,
             "description": f"IC AP {partner.code}"},
            {"account": partner.payable_account, "debit": 0, "credit": amt,
             "description": f"IC AP {partner.code}"},
        ]
    return post_balanced_journal(
        org,
        entry_date=txn.date,
        reference="",
        narration=(
            f"Being intercompany {txn.direction} with {partner.code} — {partner.name}"
            f" {txn.reference}".strip()
        ),
        lines=lines,
        user=user,
    )


@transaction.atomic
def reverse_journal(*, journal: JournalEntry, user=None, entry_date: date | None = None) -> JournalEntry:
    if journal.status != JournalEntry.Status.POSTED:
        raise ValueError("Only posted journals can be reversed")
    if (journal.narration or "").startswith("REVERSAL of "):
        raise ValueError("Cannot reverse a reversal voucher")
    org = journal.organization
    lines = []
    for line in journal.lines.select_related("account", "cost_center").all():
        lines.append(
            {
                "account": line.account,
                "cost_center": line.cost_center,
                "debit": line.credit,
                "credit": line.debit,
                "description": f"Rev: {line.description}"[:255],
            }
        )
    rev = post_balanced_journal(
        org,
        entry_date=entry_date or timezone.localdate(),
        reference="",
        narration=f"REVERSAL of {journal.reference or f'JE-{journal.pk}'} — {journal.narration}",
        lines=lines,
        user=user,
    )
    journal.narration = (
        f"{journal.narration}\n[Reversed by {rev.reference}]".strip()
    )[:4000] if hasattr(journal, "narration") else journal.narration
    # Keep narration update short
    note = f" [Reversed by {rev.reference}]"
    if note not in (journal.narration or ""):
        journal.narration = ((journal.narration or "") + note)[:4000]
        journal.save(update_fields=["narration", "updated_at"])
    return rev
