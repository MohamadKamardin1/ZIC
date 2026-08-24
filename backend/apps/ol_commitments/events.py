"""Durable outbox events for the OL Commitments module.

Publishing follows the repository convention of ``apps.common.models.DomainEvent``
(reliable outbox with PENDING/PUBLISHED/FAILED states). All material state
changes emit a typed event carrying actor, transitions, reason, and the source
channel so downstream consumers (proposals, policies, receipts, reports, portal,
dashboard) integrate through a clean seam.
"""

from apps.common.models import DomainEvent

AGGREGATE_TYPE = "OLCommitment"

COMMITMENT_GENERATED = "CommitmentGenerated"
COMMITMENT_PAYMENT_ALLOCATED = "CommitmentPaymentAllocated"
COMMITMENT_OVERDUE = "CommitmentOverdue"
COMMITMENT_SUSPENDED = "CommitmentSuspended"
COMMITMENT_WAIVED = "CommitmentWaived"
COMMITMENT_CANCELLED = "CommitmentCancelled"
COMMITMENT_COMPLETED = "CommitmentCompleted"

EVENT_TYPES = (
    COMMITMENT_GENERATED,
    COMMITMENT_PAYMENT_ALLOCATED,
    COMMITMENT_OVERDUE,
    COMMITMENT_SUSPENDED,
    COMMITMENT_WAIVED,
    COMMITMENT_CANCELLED,
    COMMITMENT_COMPLETED,
)


def emit_commitment_event(
    event_type,
    commitment,
    *,
    actor=None,
    from_status="",
    to_status="",
    reason="",
    source_channel=None,
    metadata=None,
    payload_extra=None,
):
    """Persist a Commitment domain event to the outbox."""
    payload = {
        "commitment_number": commitment.commitment_number,
        "commitment_id": str(commitment.pk),
        "actor_id": str(actor.pk) if actor and getattr(actor, "pk", None) else None,
        "from_status": from_status or "",
        "to_status": to_status or "",
        "reason": reason or "",
        "source_channel": source_channel or getattr(commitment, "source_channel", ""),
        "metadata": metadata or {},
    }
    if payload_extra:
        payload.update(payload_extra)
    return DomainEvent.objects.create(
        event_type=event_type,
        aggregate_type=AGGREGATE_TYPE,
        aggregate_id=str(commitment.pk),
        payload=payload,
    )


def emit_generated(commitment, *, actor=None, reason="", source_channel=None, metadata=None):
    return emit_commitment_event(
        COMMITMENT_GENERATED,
        commitment,
        actor=actor,
        to_status=commitment.status,
        reason=reason,
        source_channel=source_channel,
        metadata=metadata,
    )


def emit_payment_allocated(
    commitment, *, allocation=None, actor=None, from_status="", reason="", source_channel=None, metadata=None
):
    payload_extra = {}
    if allocation is not None:
        payload_extra["allocation_id"] = str(allocation.pk)
        payload_extra["receipt_reference"] = allocation.receipt_reference
        payload_extra["amount"] = str(allocation.amount)
        payload_extra["currency"] = allocation.currency
        payload_extra["exchange_rate"] = str(allocation.exchange_rate)
        payload_extra["converted_amount"] = str(allocation.converted_amount)
    return emit_commitment_event(
        COMMITMENT_PAYMENT_ALLOCATED,
        commitment,
        actor=actor,
        from_status=from_status,
        to_status=commitment.status,
        reason=reason,
        source_channel=source_channel,
        metadata=metadata,
        payload_extra=payload_extra,
    )


def emit_overdue(commitment, *, actor=None, from_status="", reason="", source_channel=None, metadata=None):
    return emit_commitment_event(
        COMMITMENT_OVERDUE,
        commitment,
        actor=actor,
        from_status=from_status,
        to_status=commitment.status,
        reason=reason,
        source_channel=source_channel,
        metadata=metadata,
    )


def emit_suspended(commitment, *, actor=None, from_status="", reason="", source_channel=None, metadata=None):
    return emit_commitment_event(
        COMMITMENT_SUSPENDED,
        commitment,
        actor=actor,
        from_status=from_status,
        to_status=commitment.status,
        reason=reason,
        source_channel=source_channel,
        metadata=metadata,
    )


def emit_waived(commitment, *, actor=None, from_status="", reason="", source_channel=None, metadata=None):
    return emit_commitment_event(
        COMMITMENT_WAIVED,
        commitment,
        actor=actor,
        from_status=from_status,
        to_status=commitment.status,
        reason=reason,
        source_channel=source_channel,
        metadata=metadata,
    )


def emit_cancelled(commitment, *, actor=None, from_status="", reason="", source_channel=None, metadata=None):
    return emit_commitment_event(
        COMMITMENT_CANCELLED,
        commitment,
        actor=actor,
        from_status=from_status,
        to_status=commitment.status,
        reason=reason,
        source_channel=source_channel,
        metadata=metadata,
    )


def emit_completed(commitment, *, actor=None, from_status="", reason="", source_channel=None, metadata=None):
    return emit_commitment_event(
        COMMITMENT_COMPLETED,
        commitment,
        actor=actor,
        from_status=from_status,
        to_status=commitment.status,
        reason=reason,
        source_channel=source_channel,
        metadata=metadata,
    )
