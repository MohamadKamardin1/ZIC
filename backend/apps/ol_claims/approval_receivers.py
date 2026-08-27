from django.dispatch import receiver

from apps.governance.signals import approval_status_changed


@receiver(approval_status_changed, dispatch_uid="ol-claims-payment-approval-status")
def handle_claim_payment_approval(sender, approval_request, **kwargs):
    """Apply governance outcomes to the linked claim payment requisition."""
    if approval_request.module != "OL_CLAIMS" or approval_request.entity_type != "OLClaimRequisition":
        return
    from .services.requisition import apply_approval_outcome

    apply_approval_outcome(approval_request, actor=approval_request.reviewed_by, source_channel="SYSTEM")
