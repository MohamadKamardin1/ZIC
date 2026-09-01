import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.common.models import DomainEvent

from .events import (
    INSTALLMENT_PAYMENT_DUE,
    INSTALLMENT_PAYMENT_MISSED,
    INSTALLMENT_PLAN_COMPLETED,
)
from .models import OLMaturityInstallmentPlan
from .services.integration_service import notify_installment_event

logger = logging.getLogger(__name__)


@receiver(post_save, sender=DomainEvent, dispatch_uid="ol-maturity-installments-domain-event-integrations")
def route_installment_notifications(sender, instance, created, **kwargs):
    if not created or instance.event_type not in {
        INSTALLMENT_PAYMENT_DUE,
        INSTALLMENT_PAYMENT_MISSED,
        INSTALLMENT_PLAN_COMPLETED,
    }:
        return
    plan = (
        OLMaturityInstallmentPlan.objects.select_related("policy_ref", "partner", "policy_ref__partner")
        .filter(pk=instance.aggregate_id)
        .first()
    )
    if plan is None:
        logger.warning(
            "Installment notification skipped because aggregate was not found: %s", instance.aggregate_id
        )
        return
    payload = instance.payload if isinstance(instance.payload, dict) else {}
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    try:
        notify_installment_event(
            plan,
            instance.event_type,
            amount=str(metadata.get("amount") or ""),
            source_channel="EVENT",
        )
    except Exception:
        logger.exception(
            "OL Maturity installment notification integration failed",
            extra={"event_id": str(instance.pk), "event_type": instance.event_type, "plan_id": str(plan.pk)},
        )
        raise
