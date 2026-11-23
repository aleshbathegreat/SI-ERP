import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from finance.models import CustomerInvoice

log = logging.getLogger(__name__)


@receiver(post_save, sender=CustomerInvoice)
def auto_create_einvoice_draft(sender, instance, created, **kwargs):
    """When an AR invoice is approved/paid, create a draft FBR e-invoice submission."""
    if instance.is_deleted or instance.status not in (
        CustomerInvoice.Status.APPROVED,
        CustomerInvoice.Status.PAID,
    ):
        return
    try:
        from django.db import transaction

        from finance.fbr import ensure_draft_submission

        with transaction.atomic():
            ensure_draft_submission(instance)
    except Exception:  # never block invoice workflow
        log.exception("Could not auto-create e-invoice draft for invoice %s", instance.pk)
