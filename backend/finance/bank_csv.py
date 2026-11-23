"""Flexible bank-statement CSV parsing helpers."""

from __future__ import annotations

import csv
import io
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

DATE_ALIASES = (
    "txn_date",
    "date",
    "transaction_date",
    "value_date",
    "posting_date",
    "trans date",
    "tran date",
    "valuedate",
)
DESC_ALIASES = (
    "description",
    "narration",
    "details",
    "memo",
    "particulars",
    "narrative",
    "remarks",
)
AMOUNT_ALIASES = ("amount", "amt", "transaction_amount", "txn_amount", "value")
DEBIT_ALIASES = ("debit", "withdrawal", "dr", "debit_amount", "withdrawals")
CREDIT_ALIASES = ("credit", "deposit", "cr", "credit_amount", "deposits")
REF_ALIASES = (
    "reference",
    "ref",
    "cheque_no",
    "check_no",
    "cheque",
    "check",
    "txn_ref",
    "transaction_ref",
    "tran_id",
    "id",
)

DATE_FORMATS = (
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%m/%d/%Y",
    "%d/%m/%y",
    "%Y/%m/%d",
    "%d.%m.%Y",
)


def _norm_key(key: str | None) -> str:
    if not key:
        return ""
    return re.sub(r"[\s\-]+", "_", key.strip().lower())


def _pick(keys: dict[str, str], aliases: tuple[str, ...]) -> str:
    for alias in aliases:
        if alias in keys and keys[alias] not in (None, ""):
            return str(keys[alias]).strip()
        underscored = alias.replace(" ", "_")
        if underscored in keys and keys[underscored] not in (None, ""):
            return str(keys[underscored]).strip()
    return ""


def _parse_date(raw: str) -> date | None:
    s = (raw or "").strip()
    if not s:
        return None
    # ISO datetime → date
    if "T" in s:
        s = s.split("T", 1)[0]
    s10 = s[:10]
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(s10 if len(fmt) <= 10 else s[: len(fmt) + 2], fmt).date()
        except ValueError:
            continue
    # try full string against formats that need more than 10 chars
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _parse_decimal(raw: str) -> Decimal | None:
    if raw is None:
        return None
    s = str(raw).strip()
    if not s or s in ("-", "—"):
        return None
    # (1,234.56) accounting negative
    neg = False
    if s.startswith("(") and s.endswith(")"):
        neg = True
        s = s[1:-1]
    s = s.replace(",", "").replace(" ", "")
    if s.startswith("+"):
        s = s[1:]
    try:
        val = Decimal(s)
    except (InvalidOperation, ValueError):
        return None
    return -val if neg else val


def _row_amount(keys: dict[str, str]) -> Decimal | None:
    amt = _parse_decimal(_pick(keys, AMOUNT_ALIASES))
    if amt is not None:
        return amt
    debit = _parse_decimal(_pick(keys, DEBIT_ALIASES))
    credit = _parse_decimal(_pick(keys, CREDIT_ALIASES))
    if debit is None and credit is None:
        return None
    # Credits increase balance (+); debits decrease (−)
    d = abs(debit) if debit is not None else Decimal("0")
    c = abs(credit) if credit is not None else Decimal("0")
    if c and not d:
        return c
    if d and not c:
        return -d
    return c - d


def parse_bank_statement_csv(raw: str) -> tuple[list[dict], list[str]]:
    """
    Parse CSV text into line dicts: txn_date, description, amount, reference.
    Returns (rows, errors).
    """
    text = (raw or "").strip()
    if not text:
        return [], ["CSV content is empty"]

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return [], ["CSV has no header row"]

    normalized_headers = [_norm_key(h) for h in reader.fieldnames if h]
    has_date = any(h in DATE_ALIASES or h.replace(" ", "_") in DATE_ALIASES for h in normalized_headers)
    has_amount = any(
        h in AMOUNT_ALIASES or h in DEBIT_ALIASES or h in CREDIT_ALIASES for h in normalized_headers
    )
    if not has_date:
        return [], [
            "Missing date column. Expected one of: date, txn_date, transaction_date, value_date"
        ]
    if not has_amount:
        return [], [
            "Missing amount column. Expected amount, or debit/credit columns"
        ]

    rows: list[dict] = []
    errors: list[str] = []
    for i, row in enumerate(reader, start=2):
        keys = {_norm_key(k): (v if v is not None else "") for k, v in row.items() if k}
        date_s = _pick(keys, DATE_ALIASES)
        if not date_s:
            continue
        txn_date = _parse_date(date_s)
        if not txn_date:
            errors.append(f"Row {i}: invalid date '{date_s}'")
            continue
        amount = _row_amount(keys)
        if amount is None:
            errors.append(f"Row {i}: missing/invalid amount")
            continue
        desc = _pick(keys, DESC_ALIASES)
        ref = _pick(keys, REF_ALIASES)
        rows.append(
            {
                "txn_date": txn_date,
                "description": desc[:255],
                "amount": amount,
                "reference": ref[:128],
            }
        )

    if not rows and not errors:
        errors.append("No usable data rows found in CSV")
    return rows, errors


def read_upload_text(request) -> str:
    raw = request.data.get("csv") or ""
    upload = request.FILES.get("file") or request.FILES.get("csv_file")
    if upload:
        raw = upload.read().decode("utf-8-sig", errors="ignore")
    return raw or ""
