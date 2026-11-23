import re

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
from django.db.models.deletion import ProtectedError, RestrictedError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler


def _related_labels(exc: ProtectedError | RestrictedError) -> str:
    objs = getattr(exc, "protected_objects", None) or set()
    labels: list[str] = []
    seen: set[str] = set()
    for obj in objs:
        name = obj.__class__.__name__
        if name in seen:
            continue
        seen.add(name)
        labels.append(name)
    if labels:
        return ", ".join(labels)
    raw = str(exc)
    return raw if raw else "related records"


def friendly_protect_message(exc: ProtectedError | RestrictedError) -> str:
    related = _related_labels(exc)
    return (
        f"Cannot delete because it is still referenced by: {related}. "
        "Remove or reassign those records first."
    )


def friendly_integrity_message(exc: IntegrityError) -> str:
    cause = getattr(exc, "__cause__", None)
    diag = getattr(cause, "diag", None) if cause is not None else None
    detail = getattr(diag, "message_detail", None) if diag is not None else None
    blob = f"{detail or ''} {exc}".strip()
    lower = blob.lower()
    if "duplicate key" in lower or "unique constraint" in lower or "already exists" in lower:
        fields = _integrity_fields(blob)
        if fields:
            return f"A record with {fields} already exists."
        return "A record with these values already exists."
    if "not-null" in lower or "null value" in lower or "may not be null" in lower:
        return "A required value is missing."
    if "foreign key" in lower:
        return "That related record is missing or was deleted."
    return "Could not save this record because it conflicts with existing data."


def _integrity_fields(blob: str) -> str:
    match = re.search(r"Key \(([^)]+)\)", blob)
    if match:
        cols = [part.strip() for part in match.group(1).split(",")]
    else:
        match = re.search(r"UNIQUE constraint failed: ([^\n]+)", blob)
        if not match:
            return ""
        cols = [part.strip().split(".")[-1] for part in match.group(1).split(",")]
    labels = []
    for col in cols:
        if col in ("organization_id", "organization"):
            continue
        label = col[:-3] if col.endswith("_id") else col
        labels.append(label.replace("_", " "))
    return " and ".join(labels)


def custom_exception_handler(exc, context):
    if isinstance(exc, (ProtectedError, RestrictedError)):
        return Response(
            {
                "detail": friendly_protect_message(exc),
                "code": "protected",
            },
            status=status.HTTP_409_CONFLICT,
        )
    if isinstance(exc, IntegrityError):
        return Response(
            {"detail": friendly_integrity_message(exc), "code": "duplicate"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if isinstance(exc, DjangoValidationError):
        detail = getattr(exc, "message_dict", None) or {"detail": exc.messages}
        return Response(detail, status=status.HTTP_400_BAD_REQUEST)

    response = exception_handler(exc, context)
    return response
