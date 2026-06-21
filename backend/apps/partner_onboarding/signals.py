import logging

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import PartnerApplication, PartnerApplicationDocument

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=PartnerApplication)
def track_status_change(sender, instance, **kwargs):
    """
    Track previous status before save for status change detection.
    """
    if instance.pk:
        try:
            old_instance = sender.objects.get(pk=instance.pk)
            instance._old_status = old_instance.status
        except sender.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


@receiver(post_save, sender=PartnerApplication)
def handle_application_status_change(sender, instance, created, **kwargs):
    """
    Handle application status changes and trigger appropriate actions.
    """
    if created:
        logger.info(f"Application created: {instance.application_number}")
        return

    old_status = getattr(instance, "_old_status", None)
    new_status = instance.status

    if old_status == new_status:
        return

    logger.info(
        f"Application status changed: {instance.application_number} | "
        f"{old_status} → {new_status}"
    )

    if new_status == "SUBMITTED":
        from .tasks import notify_reviewers
        notify_reviewers.delay(str(instance.pk))

    elif new_status == "COMPLIANCE_CHECK":
        from .tasks import run_compliance_check
        run_compliance_check.delay(str(instance.pk))

    elif new_status in ("APPROVED", "REJECTED", "SUSPENDED", "CONVERTED"):
        from .tasks import send_application_notification
        notification_type = new_status.lower()
        send_application_notification.delay(str(instance.pk), notification_type)


@receiver(post_save, sender=PartnerApplicationDocument)
def log_document_upload(sender, instance, created, **kwargs):
    """
    Log document uploads.
    """
    if created:
        logger.info(
            f"Document uploaded: {instance.document_type} | "
            f"Application: {instance.application.application_number} | "
            f"File: {instance.document_name}"
        )
