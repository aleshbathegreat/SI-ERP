"""Soft-delete helpers for AuditModel descendants."""

from django.conf import settings
from django.db import models
from django.utils import timezone


class SoftDeleteQuerySet(models.QuerySet):
    def alive(self):
        return self.filter(is_deleted=False)

    def deleted(self):
        return self.filter(is_deleted=True)

    def delete(self):
        """Soft-delete matching rows (bulk)."""
        return self.update(
            is_deleted=True,
            deleted_at=timezone.now(),
        )


class SoftDeleteManager(models.Manager):
    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).filter(is_deleted=False)


class AllObjectsManager(models.Manager):
    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db)


def soft_delete_instance(instance, user=None):
    """Mark one instance deleted without removing FK-protected children."""
    instance.is_deleted = True
    instance.deleted_at = timezone.now()
    if user is not None and hasattr(instance, "deleted_by_id"):
        instance.deleted_by = user
    if hasattr(instance, "is_active"):
        instance.is_active = False
    from core.uniqueness import release_unique_text

    released = release_unique_text(instance)
    update_fields = ["is_deleted", "deleted_at", "updated_at", *released]
    if user is not None and hasattr(instance, "deleted_by_id"):
        update_fields.append("deleted_by")
    if hasattr(instance, "is_active"):
        update_fields.append("is_active")
    instance._unique_reconciled = True
    instance.save(update_fields=list(dict.fromkeys(update_fields)))
    return instance


class SoftDeleteDestroyMixin:
    """ViewSet mixin: destroy / bulk-delete soft-deletes instead of hard DELETE."""

    def perform_destroy(self, instance):
        soft_delete_instance(instance, user=getattr(self.request, "user", None))
