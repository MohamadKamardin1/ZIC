import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.common.models import DomainEvent

from .events import LOAN_DEFAULTED, LOAN_DISBURSED, LOAN_OFFSET, LOAN_SETTLED
from .services.integration_service import apply_settlement_event, notify_loan_event

logger = logging.getLogger(__name__)


@receiver(post_save, sender=DomainEvent, dispatch_uid="ol-loans-domain-event-integrations")
def route_loan_integrations(sender, instance, created, **kwargs):
    if not created:
        return
    if instance.event_type in {
        "PolicyClaimSettledApplied",
        "PolicyMaturityPaid",
        "PolicySurrenderPaid",
        "PolicySurrenderSettled",
    }:
        try:
            apply_settlement_event(instance)
        except Exception:
            logger.exception(
                "OL Loan settlement integration failed",
                extra={"event_id": str(instance.pk), "event_type": instance.event_type},
            )
            raise
        return
    if instance.event_type not in {LOAN_DISBURSED, LOAN_DEFAULTED, LOAN_SETTLED, LOAN_OFFSET}:
        return
    loan_id = instance.aggregate_id
    from .models import OLLoan

    loan = OLLoan.objects.select_related("policy_ref", "partner").filter(pk=loan_id).first()
    if loan is None:
        logger.warning("Loan notification skipped because aggregate was not found: %s", loan_id)
        return
    try:
        notify_loan_event(loan, instance.event_type, source_channel="EVENT")
    except Exception:
        logger.exception(
            "OL Loan notification integration failed",
            extra={"event_id": str(instance.pk), "event_type": instance.event_type, "loan_id": str(loan.pk)},
        )
