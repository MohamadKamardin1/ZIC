"""Durable outbox events for the OL Proposals module (outbox: ``DomainEvent``)."""

from apps.common.models import DomainEvent

AGGREGATE_TYPE = "OLProposal"

PROPOSAL_CREATED = "ProposalCreated"
PROPOSAL_ENRICHED = "ProposalEnriched"
PROPOSAL_PAYMENT_READY = "ProposalPaymentReady"
PROPOSAL_CONVERTED = "ProposalConverted"
PROPOSAL_CANCELLED = "ProposalCancelled"
PROPOSAL_EXPIRED = "ProposalExpired"
MEDICAL_REQUIREMENT_RAISED = "MedicalRequirementRaised"


def emit_proposal_event(
    event_type,
    proposal,
    *,
    actor=None,
    from_status="",
    to_status="",
    reason="",
    source_channel=None,
    payload_extra=None,
):
    payload = {
        "proposal_number": proposal.proposal_number,
        "proposal_id": str(proposal.pk),
        "actor_id": str(actor.pk) if actor and getattr(actor, "pk", None) else None,
        "from_status": from_status or "",
        "to_status": to_status or proposal.status or "",
        "reason": reason or "",
        "source_channel": source_channel or getattr(proposal, "source_channel", ""),
        "metadata": {},
    }
    if payload_extra:
        payload.update(payload_extra)
    return DomainEvent.objects.create(
        event_type=event_type,
        aggregate_type=AGGREGATE_TYPE,
        aggregate_id=str(proposal.pk),
        payload=payload,
    )


def emit_created(proposal, *, actor=None, reason="", source_channel=None):
    return emit_proposal_event(PROPOSAL_CREATED, proposal, actor=actor, to_status=proposal.status, reason=reason, source_channel=source_channel)


def emit_enriched(proposal, *, actor=None, from_status="", to_status="", reason="", source_channel=None):
    return emit_proposal_event(PROPOSAL_ENRICHED, proposal, actor=actor, from_status=from_status, to_status=to_status or proposal.status, reason=reason, source_channel=source_channel)


def emit_payment_ready(proposal, *, actor=None, from_status="", reason="", source_channel=None, metadata=None, payload_extra=None):
    payload_extra_payload = dict(payload_extra or {})
    payload_extra_payload["metadata"] = metadata or {}
    return emit_proposal_event(
        PROPOSAL_PAYMENT_READY,
        proposal,
        actor=actor,
        from_status=from_status,
        to_status=proposal.status,
        reason=reason,
        source_channel=source_channel,
        payload_extra=payload_extra_payload,
    )


def emit_converted(proposal, *, actor=None, from_status="", reason="", source_channel=None, metadata=None):
    return emit_proposal_event(PROPOSAL_CONVERTED, proposal, actor=actor, from_status=from_status, to_status=proposal.status, reason=reason, source_channel=source_channel, payload_extra={"metadata": metadata or {}})


def emit_cancelled(proposal, *, actor=None, from_status="", reason="", source_channel=None):
    return emit_proposal_event(PROPOSAL_CANCELLED, proposal, actor=actor, from_status=from_status, to_status=proposal.status, reason=reason, source_channel=source_channel)


def emit_expired(proposal, *, actor=None, from_status="", reason="", source_channel=None):
    return emit_proposal_event(PROPOSAL_EXPIRED, proposal, actor=actor, from_status=from_status, to_status=proposal.status, reason=reason, source_channel=source_channel)


def emit_medical_requirement(proposal, *, actor=None, reason="", source_channel=None, metadata=None):
    return emit_proposal_event(
        MEDICAL_REQUIREMENT_RAISED,
        proposal,
        actor=actor,
        to_status=proposal.status,
        reason=reason,
        source_channel=source_channel,
        payload_extra={"metadata": metadata or {}},
    )