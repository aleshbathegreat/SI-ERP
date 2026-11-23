"""Turn org-scoped unique clashes into validation, and free soft-deleted keys."""

from django.db import models
from django.db.models import UniqueConstraint


def is_text_field(field) -> bool:
    return isinstance(field, (models.CharField, models.TextField))


def unique_field_sets(model) -> list[tuple[str, ...]]:
    found: list[tuple[str, ...]] = []
    for together in model._meta.unique_together or ():
        if together:
            found.append(tuple(together))
    for constraint in model._meta.constraints:
        fields = getattr(constraint, "fields", None)
        if (
            isinstance(constraint, UniqueConstraint)
            and fields
            and getattr(constraint, "condition", None) is None
        ):
            found.append(tuple(fields))
    for field in model._meta.local_concrete_fields:
        if field.unique and not field.primary_key:
            found.append((field.name,))
    return found


def _prefer_text_field(names: list[str]) -> str:
    for name in names:
        if name == "code" or name.endswith("_no") or name.endswith("_code"):
            return name
    for name in (
        "sku",
        "email",
        "name",
        "kind",
        "device_id",
        "loan_number",
        "connector_key",
        "employee_code",
    ):
        if name in names:
            return name
    return names[0]


def text_fields_to_release(instance) -> list[str]:
    chosen: list[str] = []
    for fields in unique_field_sets(instance.__class__):
        text: list[str] = []
        for name in fields:
            if name in ("organization", "id"):
                continue
            try:
                field = instance._meta.get_field(name)
            except Exception:
                continue
            if is_text_field(field):
                text.append(name)
        if text:
            chosen.append(_prefer_text_field(text))
    return list(dict.fromkeys(chosen))


def release_unique_text(instance) -> list[str]:
    """Suffix unique text values so a soft-deleted row no longer blocks a new one."""
    if not instance.pk:
        return []
    changed: list[str] = []
    suffix = f"-d{instance.pk}"
    for name in text_fields_to_release(instance):
        current = getattr(instance, name, None)
        if not current:
            continue
        base = str(current)
        if base.endswith(suffix):
            continue
        field = instance._meta.get_field(name)
        max_len = getattr(field, "max_length", None) or 64
        trimmed = base[: max(1, max_len - len(suffix))]
        setattr(instance, name, f"{trimmed}{suffix}")
        changed.append(name)
    return changed


def duplicate_message(lookup: dict) -> str:
    parts = []
    for key, value in lookup.items():
        if key in ("organization", "organization_id"):
            continue
        label = key[:-3] if key.endswith("_id") else key
        parts.append(f"{label.replace('_', ' ')} {value}")
    if not parts:
        return "A record with these values already exists."
    return f"A record with {' and '.join(parts)} already exists."


def _lookup_for(instance, fields: tuple[str, ...]) -> dict | None:
    lookup = {}
    has_text = False
    for name in fields:
        try:
            field = instance._meta.get_field(name)
        except Exception:
            return None
        if is_text_field(field):
            has_text = True
        value = getattr(instance, field.attname)
        if value is None or value == "":
            return None
        lookup[field.attname] = value
    if not lookup:
        return None
    return {"lookup": lookup, "has_text": has_text}


def reconcile_unique_on_create(instance) -> bool:
    """Before insert: reject a live duplicate, restore a deleted month-style row,
    or free a deleted text key. Returns True when the insert must be skipped.
    Also rejects an update that would collide with another live row.
    """
    if getattr(instance, "_unique_reconciled", False):
        return False
    adding = bool(instance._state.adding and not instance.pk)
    if not adding and not instance.pk:
        return False
    manager = getattr(instance.__class__, "all_objects", None)
    if manager is None or not hasattr(instance, "is_deleted"):
        return False

    from rest_framework.exceptions import ValidationError

    for fields in unique_field_sets(instance.__class__):
        spec = _lookup_for(instance, fields)
        if spec is None:
            continue
        qs = manager.filter(**spec["lookup"])
        if instance.pk:
            qs = qs.exclude(pk=instance.pk)
        existing = qs.first()
        if existing is None:
            continue
        if not existing.is_deleted:
            raise ValidationError(duplicate_message(spec["lookup"]))
        if spec["has_text"] or not adding:
            changed = release_unique_text(existing) if spec["has_text"] else []
            if changed:
                existing._unique_reconciled = True
                existing.save(update_fields=changed)
            elif not spec["has_text"]:
                raise ValidationError(duplicate_message(spec["lookup"]))
            continue
        for field in existing._meta.concrete_fields:
            if field.primary_key or getattr(field, "auto_now_add", False) or getattr(
                field, "auto_now", False
            ):
                continue
            setattr(existing, field.attname, getattr(instance, field.attname))
        existing.is_deleted = False
        existing.deleted_at = None
        existing.deleted_by = None
        existing._unique_reconciled = True
        existing.save()
        instance.pk = existing.pk
        instance._state.adding = False
        instance.refresh_from_db()
        return True
    return False
