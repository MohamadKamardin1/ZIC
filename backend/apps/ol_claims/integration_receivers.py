import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.common.models import DomainEvent

logger = logging.getLogger(__name__)


@receiver(post_save, sender=DomainEvent, dispatch_uid="ol-claims-domain-event-integrations")
def route_claim_integrations(sender, instance, created, **kwargs):
    if not created or instance.event_type not in {"ClaimRegistered", "ClaimAssessed", "ClaimSettled"}:
        return
    from .models import OLClaim
    from .services.notifications import notify_claim_event

    claim = OLClaim.objects.select_related("policy_ref", "policy_ref__partner").filter(pk=instance.aggregate_id).first()
    if claim is None:
        logger.warning("Claim notification skipped because aggregate was not found: %s", instance.aggregate_id)
        return
    try:
        notify_claim_event(claim, instance.event_type, source_channel="EVENT")
    except Exception:
        logger.exception(
            "OL Claim notification integration failed",
            extra={"event_id": str(instance.pk), "event_type": instance.event_type, "claim_id": str(claim.pk)},
        )
        raise
