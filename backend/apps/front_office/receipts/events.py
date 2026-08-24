"""Durable outbox events for the Front Office Receipts module.

All material financial transitions emit a typed event into the reliable outbox
(``apps.common.models.DomainEvent``) carrying the actor, status transition,
reason, and source channel. ``FirstPremiumReceived`` follows the event contract
defined in ``docs/OL_PROPOSALS_RECEIPTS_SEAM.md`` so proposals, policies,
reports, and the portal consume it asynchronously.
"""

from apps.common.models import DomainEvent

AGGREGATE_TYPE = "Receipt"

RECEIPT_CREATED = "ReceiptCreated"
RECEIPT_POSTED = "ReceiptPosted"
RECEIPT_ALLOCATED = "ReceiptAllocated"
RECEIPT_FULLY_ALLOCATED = "ReceiptFullyAllocated"
RECEIPT_REVERSED = "ReceiptReversed"
RECEIPT_CANCELLED = "ReceiptCancelled"
PREMIUM_RECEIVED = "PremiumReceived"
FIRST_PREMIUM_RECEIVED = "FirstPremiumReceived"

EVENT_TYPES = (
    RECEIPT_CREATED,
    RECEIPT_POSTED,
    RECEIPT_ALLOCATED,
    RECEIPT_FULLY_ALLOCATED,
    RECEIPT_REVERSED,
    RECEIPT_CANCELLED,
    PREMIUM_RECEIVED,
    FIRST_PREMIUM_RECEIVED,
)


def emit_receipt_event(
    event_type,
    receipt,
    *,
    actor=None,
    from_status="",
    to_status="",
    reason="",
    source_channel=None,
    metadata=None,
    payload_extra=None,
):
    """Persist a Receipt domain event to the outbox."""
    payload = {
        "receipt_number": receipt.receipt_number,
        "receipt_id": str(receipt.pk),
        "actor_id": str(actor.pk) if actor and getattr(actor, "pk", None) else None,
        "payer_name": receipt.payer_name,
        "partner_name": receipt.partner_name_snapshot,
        "currency": receipt.currency,
        "amount": str(receipt.receipt_amount),
        "from_status": from_status or "",
        "to_status": to_status or "",
        "reason": reason or "",
        "source_channel": source_channel or getattr(receipt, "source_channel", ""),
        "metadata": metadata or {},
    }
    if payload_extra:
        payload.update(payload_extra)
    return DomainEvent.objects.create(
        event_type=event_type,
        aggregate_type=AGGREGATE_TYPE,
        aggregate_id=str(receipt.pk),
        payload=payload,
    )


def emit_created(receipt, *, actor=None, reason="", source_channel=None, metadata=None):
    return emit_receipt_event(
        RECEIPT_CREATED,
        receipt,
        actor=actor,
        to_status=receipt.status,
        reason=reason,
        source_channel=source_channel,
        metadata=metadata,
    )


def emit_posted(receipt, *, actor=None, from_status="", reason="", source_channel=None, metadata=None):
    return emit_receipt_event(
        RECEIPT_POSTED,
        receipt,
        actor=actor,
        from_status=from_status,
        to_status=receipt.status,
        reason=reason,
        source_channel=source_channel,
        metadata=metadata,
    )


def emit_allocated(
    receipt, *, allocation=None, actor=None, from_status="", reason="", source_channel=None, metadata=None
):
    payload_extra = {}
    if allocation is not None:
        payload_extra["allocation_id"] = str(allocation.pk)
        payload_extra["allocation_target_type"] = allocation.target_type
        payload_extra["allocation_target_id"] = allocation.target_id
        payload_extra["allocation_amount"] = str(allocation.amount)
    return emit_receipt_event(
        RECEIPT_ALLOCATED,
        receipt,
        actor=actor,
        from_status=from_status,
        to_status=receipt.status,
        reason=reason,
        source_channel=source_channel,
        metadata=metadata,
        payload_extra=payload_extra,
    )


def emit_fully_allocated(receipt, *, actor=None, from_status="", reason="", source_channel=None, metadata=None):
    return emit_receipt_event(
        RECEIPT_FULLY_ALLOCATED,
        receipt,
        actor=actor,
        from_status=from_status,
        to_status=receipt.status,
        reason=reason,
        source_channel=source_channel,
        metadata=metadata,
    )


def emit_reversed(receipt, *, actor=None, from_status="", reason="", source_channel=None, metadata=None):
    return emit_receipt_event(
        RECEIPT_REVERSED,
        receipt,
        actor=actor,
        from_status=from_status,
        to_status=receipt.status,
        reason=reason,
        source_channel=source_channel,
        metadata=metadata,
    )


def emit_cancelled(receipt, *, actor=None, from_status="", reason="", source_channel=None, metadata=None):
    return emit_receipt_event(
        RECEIPT_CANCELLED,
        receipt,
        actor=actor,
        from_status=from_status,
        to_status=receipt.status,
        reason=reason,
        source_channel=source_channel,
        metadata=metadata,
    )


def emit_first_premium_received(
    receipt,
    *,
    allocation=None,
    commitment=None,
    proposal=None,
    actor=None,
    from_status="",
    to_status="",
    reason="",
    source_channel=None,
):
    """First-premium deposit event honoring the proposals receipts seam contract.

    Payload mirrors ``docs/OL_PROPOSALS_RECEIPTS_SEAM.md`` (PremiumReceived) so
    downstream consumers can reconcile proposal, commitment, and receipt state.
    """
    payload = {
        "proposal_number": proposal.proposal_number if proposal is not None else None,
        "commitment_number": commitment.commitment_number if commitment is not None else None,
        "receipt_reference": receipt.receipt_number,
        "amount": str(allocation.amount) if allocation is not None else str(receipt.receipt_amount),
        "currency": (allocation.currency if allocation is not None else receipt.currency),
        "payment_mode": receipt.payment_mode,
        "allocated_at": (allocation.allocated_at.isoformat() if allocation is not None and allocation.allocated_at else None),
        "allocated_by": str(actor.pk) if actor and getattr(actor, "pk", None) else None,
        "source_channel": source_channel or receipt.source_channel,
        "reason": reason or "",
        "reverse_of": None,
        "from_status": from_status or "",
        "to_status": to_status or "",
    }
    return DomainEvent.objects.create(
        event_type=FIRST_PREMIUM_RECEIVED,
        aggregate_type=AGGREGATE_TYPE,
        aggregate_id=str(receipt.pk),
        payload=payload,
    )


def emit_premium_received(
    receipt,
    *,
    allocation=None,
    commitment=None,
    actor=None,
    from_status="",
    to_status="",
    reason="",
    source_channel=None,
):
    """``PremiumReceived`` per ``docs/OL_PROPOSALS_RECEIPTS_SEAM.md``.

    Published in the same transaction as the ``OLCommitmentAllocation`` insert
    for every allocation (the seam's publishing rule). ``aggregate_type`` is
    ``OLCommitment`` so proposals/policies/reports reconcile on the commitment.
    """
    payload = {
        "proposal_number": None,
        "commitment_number": commitment.commitment_number if commitment is not None else None,
        "receipt_reference": receipt.receipt_number,
        "amount": str(allocation.amount) if allocation is not None else str(receipt.receipt_amount),
        "currency": (allocation.currency if allocation is not None else receipt.currency),
        "payment_mode": receipt.payment_mode,
        "allocated_at": (allocation.allocated_at.isoformat() if allocation is not None and allocation.allocated_at else None),
        "allocated_by": str(actor.pk) if actor and getattr(actor, "pk", None) else None,
        "source_channel": source_channel or receipt.source_channel,
        "reason": reason or "",
        "reverse_of": None,
        "from_status": from_status or "",
        "to_status": to_status or "",
    }
    if commitment is not None:
        payload.update(
            {
                "premium_amount": str(commitment.premium_amount),
                "amount_paid": str(commitment.amount_paid),
                "balance": str(commitment.balance),
            }
        )
        proposal = _resolve_source(commitment)
        if proposal is not None:
            payload["proposal_number"] = getattr(proposal, "proposal_number", None)
    return DomainEvent.objects.create(
        event_type=PREMIUM_RECEIVED,
        aggregate_type="OLCommitment",
        aggregate_id=str(commitment.pk) if commitment is not None else str(receipt.pk),
        payload=payload,
    )


def _resolve_source(commitment):
    if commitment is None or not commitment.source_content_type_id or not commitment.source_object_id:
        return None
    try:
        return commitment.source
    except Exception:
        return None
