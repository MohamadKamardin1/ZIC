"""Underwriting clearance seam for proposals."""

from datetime import date

from django.db import transaction

from apps.governance.services.audit_service import AuditService
from apps.ol_proposals import events as proposal_events
from apps.ol_proposals.errors import ProposalError

UNDERWRITING_DECISIONS = ("clear", "load", "decline")


def decide(*, proposal, decision, actor=None, request=None, reason="", source_channel="API"):
    decision = (decision or "").strip().lower()
    if decision not in UNDERWRITING_DECISIONS:
        raise ProposalError(
            f"Unknown underwriting decision '{decision}'.",
            error_code="VALIDATION_ERROR",
            status_code=422,
            field_errors={"decision": [f"Choose one of: {', '.join(UNDERWRITING_DECISIONS)}."]},
        )
    reason = (reason or "").strip()
    if decision == "decline" and not reason:
        raise ProposalError(
            "A reason is required to decline a proposal.",
            error_code="VALIDATION_ERROR",
            status_code=422,
            field_errors={"reason": ["A reason is required to decline."]},
        )

    if proposal.status in ("CONVERTED", "CANCELLED", "EXPIRED"):
        raise ProposalError(
            f"Cannot apply an underwriting decision to a '{proposal.status}' proposal.",
            error_code="PROPOSAL_INVALID_TRANSITION",
            status_code=422,
            resolution_steps=["Only non-terminal proposals can receive underwriting decisions."],
        )
    if proposal.expiry_date and proposal.expiry_date < date.today():
        raise ProposalError(
            "This proposal has expired.",
            error_code="PROPOSAL_EXPIRED",
            status_code=422,
            resolution_steps=["Create a fresh proposal."],
        )

    with transaction.atomic():
        before = AuditService.snapshot(proposal)
        if decision == "clear":
            proposal.underwriting_status = "CLEARED"
            proposal.medical_required = False
            proposal.status = "ENRICHMENT"
        elif decision == "load":
            proposal.underwriting_status = "CLEARED"
            proposal.medical_required = False
            proposal.reason_code = "MEDICAL_LOADING"
            proposal.reason_text = reason or "Underwriting loading applied."
            proposal.status = "ENRICHMENT"
        elif decision == "decline":
            proposal.underwriting_status = "DECLINED"
            proposal.reason_code = "UNDERWRITING_DECLINED"
            proposal.reason_text = reason
            proposal.status = "CANCELLED"
        proposal.source_channel = source_channel
        proposal.save()

        after = AuditService.snapshot(proposal)
        AuditService.log_action(
            "UNDERWRITING_DECIDE",
            proposal,
            actor=actor,
            request=request,
            before_state=before,
            after_state=after,
            changed_fields=["underwriting_status", "status", "reason_code", "reason_text"],
            reason=reason or f"Underwriting decision '{decision}' applied.",
            source_channel=source_channel,
        )
        proposal_events.emit_enriched(
            proposal,
            actor=actor,
            from_status=before.get("status") or proposal.status,
            to_status=proposal.status,
            reason=reason or f"Underwriting decision '{decision}' applied.",
            source_channel=source_channel,
        )
    return proposal