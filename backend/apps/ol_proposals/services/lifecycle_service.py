"""Proposal lifecycle: allowed actions, guarded transitions, cancel, reactivate.

Transition legality is read exclusively from the ``OL Proposal Status`` catalog
(``ol_parameters.OLProposalStatus.allowed_transitions``). Invalid transitions
raise ``PROPOSAL_INVALID_TRANSITION`` listing the allowed next states.
Reactivating an ``EXPIRED`` proposal is a documented, parameter-driven rule:
enabled only while ``PROPOSAL_REACTIVATE_FROM_EXPIRY`` is an active system
parameter.
"""

from datetime import date

from apps.ol_proposals import events as proposal_events
from apps.ol_proposals.errors import ProposalError, invalid_transition
from apps.ol_proposals.permissions import has_ol_proposal_permission
from apps.ol_proposals.services import parameter_resolver

STATUS_ACTIONS = {
    "DRAFT": ["view", "enrich", "cancel"],
    "ENRICHMENT": ["view", "enrich", "upload_documents", "mark_payment_ready", "cancel"],
    "PENDING_UNDERWRITING": ["view", "enrich", "upload_documents", "cancel"],
    "PAYMENT_READY": ["view", "enrich", "upload_documents", "mark_payment_ready", "cancel"],
    "AWAITING_FIRST_PREMIUM": ["view", "cancel"],
    "CONVERTED": ["view", "print"],
    "CANCELLED": ["view"],
    "EXPIRED": ["view"],
}

REACTIVATE_PARAMETER_KEY = "PROPOSAL_REACTIVATE_FROM_EXPIRY"


def _reactivate_parameter_enabled():
    from apps.ol_parameters.models import OLDefaultSystemParameter

    row = OLDefaultSystemParameter.objects.filter(
        parameter_key=REACTIVATE_PARAMETER_KEY, is_active=True
    ).first()
    return bool(row and row.boolean_value)


def reactivate_from_expiry_allowed():
    """Parameter-driven rule: only enabled while the revert system param is active."""
    return bool(_reactivate_parameter_enabled())


def state_allowed_actions(status):
    status = (status or "").strip().upper()
    actions = list(STATUS_ACTIONS.get(status, ["view"]))
    if status == "EXPIRED" and reactivate_from_expiry_allowed():
        actions.append("reactivate")
    return actions


def allowed_actions(proposal, actor=None):
    """Return action codes allowed for a proposal, filtered by actor permission."""
    actions = state_allowed_actions(proposal.status)
    if actor is None or not getattr(actor, "is_authenticated", False):
        return actions if actor is None else []
    return [action for action in actions if has_ol_proposal_permission(actor, action)]


def _catalog_transition(proposal, target):
    """Return (allowed, allowed_list) for a transition per the status catalog.

    A catalog row that exists with an empty transition list forbids every
    move (terminal status). A missing row keeps the legacy permissive default.
    """
    from apps.ol_parameters.models import OLProposalStatus

    row = OLProposalStatus.objects.filter(
        code__iexact=proposal.status, applies_to__iexact="PROPOSAL", is_active=True
    ).first()
    if row is None:
        return True, []
    allowed_list = [item for item in (row.allowed_transitions or []) if item]
    return target in allowed_list, allowed_list


def transition_proposal(*, proposal, to_status, actor=None, request=None, reason="", reason_code="", source_channel="API", force=False):
    from apps.governance.services.audit_service import AuditService

    target = (to_status or "").strip().upper()
    if not target:
        raise ProposalError(
            "A target status is required.",
            error_code="VALIDATION_ERROR",
            status_code=422,
            field_errors={"to_status": ["A target status is required."]},
        )

    current = (proposal.status or "").strip().upper()
    if current == target:
        return proposal

    if not force:
        allowed, allowed_list = _catalog_transition(proposal, target)
        if not allowed:
            raise invalid_transition("transition", proposal.status, allowed=allowed_list)

    before = AuditService.snapshot(proposal)
    proposal.status = target
    proposal.reason_code = reason_code or ""
    proposal.reason_text = (reason or "").strip()
    proposal.save()

    AuditService.log_action(
        "PROPOSAL_TRANSITION",
        proposal,
        actor=actor,
        request=request,
        before_state=before,
        after_state=AuditService.snapshot(proposal),
        changed_fields=["status", "reason_code", "reason_text"],
        reason=(reason or "").strip() or f"Proposal transitioned from {current} to {target}.",
        source_channel=source_channel,
    )

    if target == "CANCELLED":
        proposal_events.emit_cancelled(proposal, actor=actor, from_status=current, reason=reason, source_channel=source_channel)
    elif target == "EXPIRED":
        proposal_events.emit_expired(proposal, actor=actor, from_status=current, reason=reason, source_channel=source_channel)
    else:
        proposal_events.emit_enriched(proposal, actor=actor, from_status=current, to_status=target, reason=reason or f"Transitioned to {target}.", source_channel=source_channel)
    if target == "CONVERTED":
        from apps.ol_proposals.services.notification_service import notify_converted

        notify_converted(proposal=proposal, actor=actor, source_channel=source_channel)
    return proposal


def cancel_proposal(*, proposal, actor=None, request=None, reason="", source_channel="API"):
    """Cancel a proposal. Reason is mandatory; audited with the transition."""
    reason = (reason or "").strip()
    if not reason:
        raise ProposalError(
            "A reason is required to cancel a proposal.",
            error_code="VALIDATION_ERROR",
            status_code=422,
            field_errors={"reason": ["A reason is required to cancel a proposal."]},
        )
    return transition_proposal(
        proposal=proposal,
        to_status="CANCELLED",
        actor=actor,
        request=request,
        reason=reason,
        reason_code="PROPOSAL_CANCELLED",
        source_channel=source_channel,
    )


def reactivate_proposal(*, proposal, actor=None, request=None, reason="", source_channel="API"):
    """Reactivate an expired proposal when the parameter-driven rule permits it."""
    if (proposal.status or "").strip().upper() != "EXPIRED":
        raise invalid_transition(
            "reactivate",
            proposal.status,
            allowed=parameter_resolver.allowed_transitions(proposal.status),
        )
    if not reactivate_from_expiry_allowed():
        raise ProposalError(
            "Reactivating an expired proposal is disabled by parameter.",
            error_code="PROPOSAL_INVALID_TRANSITION",
            status_code=422,
            resolution_steps=[
                "Enable the PROPOSAL_REACTIVATE_FROM_EXPIRY parameter in OL Parameters.",
                "Retry reactivation once the parameter is active.",
            ],
        )
    return transition_proposal(
        proposal=proposal,
        to_status="ENRICHMENT",
        actor=actor,
        request=request,
        reason=reason or "Proposal reactivated from expiry.",
        reason_code="",
        source_channel=source_channel,
        force=True,
    )


def mark_expired(*, proposal, actor=None, request=None, reason="", source_channel="SYSTEM"):
    """System-driven expiry used by the batch command; idempotent."""
    from apps.governance.services.audit_service import AuditService

    current = (proposal.status or "").strip().upper()
    if current == "EXPIRED":
        return proposal
    reason = (reason or "").strip() or f"Proposal expired on {date.today().isoformat()}."

    before = AuditService.snapshot(proposal)
    proposal.status = "EXPIRED"
    proposal.reason_code = "EXPIRED"
    proposal.reason_text = reason
    proposal.save()

    AuditService.log_action(
        "PROPOSAL_EXPIRE",
        proposal,
        actor=actor,
        request=request,
        before_state=before,
        after_state=AuditService.snapshot(proposal),
        changed_fields=["status", "reason_code", "reason_text"],
        reason=reason,
        source_channel=source_channel,
    )
    proposal_events.emit_expired(proposal, actor=actor, from_status=current, reason=reason, source_channel=source_channel)
    return proposal