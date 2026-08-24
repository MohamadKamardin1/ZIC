"""Front Office Receipts — reversal and cancellation service.

Prompt 6: full receipt reversal, single-allocation reversal, and draft
cancellation. Reversal never deletes history: original ``ReceiptAllocation``
rows are kept (marked ``REVERSED``) and linked reversal rows (``reversal_of``)
are created; each linked commitment allocation is reversed through the OL
Commitments reversal service so the commitment balance/status restore
consistently; and the receipt carries a first-class ``ReceiptReversal`` record
with a frozen snapshot and the acting user's mandatory reason.
"""

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.front_office.receipts import events as receipt_events
from apps.front_office.receipts.errors import (
    already_reversed,
    invalid_status,
    not_found,
    reason_required,
    reversal_locked,
)
from apps.front_office.receipts.models import (
    ReceiptAllocation,
    ReceiptAllocationStatus,
    ReceiptReversal,
    ReceiptStatus,
)
from apps.front_office.receipts.services.receipt_numbering import ReceiptNumberingService
from apps.front_office.receipts.services.receipt_service import record_status_history
from apps.system_parameters.services.config_service import ConfigurationService

REVERSAL_LOCK_DAYS_PARAM = "RECEIPT_REVERSAL_LOCK_DAYS"
REVERSAL_NUMBERING_RULE = "RVR_DEFAULT"

REVERSABLE_STATUSES = (
    ReceiptStatus.POSTED,
    ReceiptStatus.PARTIALLY_ALLOCATED,
    ReceiptStatus.FULLY_ALLOCATED,
)


def _reversal_lock_days():
    try:
        return int(ConfigurationService.get_parameter(REVERSAL_LOCK_DAYS_PARAM, 0) or 0)
    except (TypeError, ValueError):
        return 0


def _reason(value):
    return (value or "").strip()


def _guard_reversable(receipt):
    if receipt.status == ReceiptStatus.REVERSED:
        raise already_reversed("The receipt has already been reversed.")
    if receipt.status == ReceiptStatus.CANCELLED:
        raise invalid_status("reverse", receipt.status)
    if receipt.status not in REVERSABLE_STATUSES:
        raise invalid_status("reverse", receipt.status)


def _guard_lock_period(receipt):
    days = _reversal_lock_days()
    if not days or days <= 0:
        return
    age = (timezone.localdate() - receipt.receipt_date).days
    if age > days:
        raise reversal_locked(days, receipt.receipt_date)


def _reversal_number(receipt):
    return ReceiptNumberingService.next_number(
        branch_id=receipt.branch_id, rule_code=REVERSAL_NUMBERING_RULE
    )


def _reversal_snapshot_entry(allocation, reversal_row, ol_reversal):
    return {
        "allocation_id": str(allocation.pk),
        "reversal_allocation_id": str(reversal_row.pk),
        "target_type": allocation.target_type,
        "target_id": allocation.target_id,
        "target_display": allocation.target_display,
        "amount": str(allocation.amount),
        "currency": allocation.currency,
        "exchange_rate_used": str(allocation.exchange_rate_used),
        "converted_amount": str(allocation.converted_amount),
        "converted_currency": allocation.converted_currency,
        "ol_commitment_allocation_id": str(allocation.ol_commitment_allocation_id)
        if allocation.ol_commitment_allocation_id
        else None,
        "ol_reversal_allocation_id": str(ol_reversal.pk) if ol_reversal is not None else None,
    }


def _reverse_single_allocation(receipt, allocation, *, reason, actor=None, source_channel="API"):
    """Reverse one active allocation; called inside the caller's transaction.

    Reverses the linked OL commitment allocation (when present), mirrors it with
    a reversal ``ReceiptAllocation`` row, and marks the original ``REVERSED``.
    The receipt amounts/status are recomputed by the caller.
    """
    actor_instance = actor if actor and getattr(actor, "is_authenticated", False) else None
    ol_reversal = None
    if allocation.ol_commitment_allocation_id:
        from apps.ol_commitments.services.reversal_service import (
            reverse_allocation_to_commitment,
        )

        ol_reversal, _ = reverse_allocation_to_commitment(
            allocation.ol_commitment_allocation,
            reason=reason,
            reversed_by=actor_instance,
            source_channel=source_channel,
        )
    reversal_row = ReceiptAllocation.objects.create(
        receipt=receipt,
        target_type=allocation.target_type,
        target_id=allocation.target_id,
        target_display=allocation.target_display,
        commitment_id=allocation.commitment_id,
        ol_commitment_allocation_id=ol_reversal.pk if ol_reversal is not None else None,
        amount=allocation.amount,
        currency=allocation.currency,
        exchange_rate=allocation.exchange_rate,
        exchange_rate_used=allocation.exchange_rate_used,
        exchange_rate_source=f"REVERSAL_OF:{allocation.pk}",
        converted_amount=allocation.converted_amount,
        converted_currency=allocation.converted_currency,
        allocation_status=ReceiptAllocationStatus.REVERSED,
        reversal_of=allocation,
        narration=reason,
        allocated_by=actor_instance,
        created_by=actor_instance,
        source_channel=source_channel,
    )
    allocation.allocation_status = ReceiptAllocationStatus.REVERSED
    if actor_instance is not None:
        allocation.updated_by = actor_instance
    allocation.save(update_fields=["allocation_status", "updated_by", "updated_at"])
    return reversal_row, ol_reversal


def reverse_allocation(receipt, allocation, *, reason="", actor=None, source_channel="API"):
    """Reverse a single active allocation of a posted receipt.

    Returns ``(receipt, reversal_allocation)``. The original allocation row is
    kept (marked ``REVERSED``), a linked reversal row is created, the receipt
    allocated/unallocated amounts are recomputed, the commitment balance/status
    are restored, and the receipt status is recalculated from the amount split.
    """
    reason = _reason(reason)
    if not reason:
        raise reason_required("reversing the allocation")
    if allocation.receipt_id != receipt.pk:
        raise not_found()
    _guard_reversable(receipt)
    _guard_lock_period(receipt)
    if (
        allocation.reversal_of_id is not None
        or allocation.allocation_status != ReceiptAllocationStatus.ACTIVE
    ):
        raise already_reversed("This allocation has already been reversed.")

    actor_instance = actor if actor and getattr(actor, "is_authenticated", False) else None
    from_status = receipt.status
    with transaction.atomic():
        reversal_row, _ol_reversal = _reverse_single_allocation(
            receipt,
            allocation,
            reason=reason,
            actor=actor_instance,
            source_channel=source_channel,
        )
        receipt.recompute_allocated()
        receipt._derive_status()
        if actor_instance is not None:
            receipt.updated_by = actor_instance
        receipt.save()
        record_status_history(
            receipt,
            from_status=from_status,
            to_status=receipt.status,
            actor=actor_instance,
            reason=f"Allocation reversed: {reason}",
            source_channel=source_channel,
        )
    return receipt, reversal_row


def reverse_receipt(receipt, *, reason="", actor=None, source_channel="API"):
    """Reverse a posted/allocated receipt and all its active allocations.

    Returns ``(receipt, reversal_record)``. Every active allocation is reversed
    (OL commitment side included), the receipt is marked ``REVERSED`` with
    ``reversed_at``/``reversed_by``, a first-class ``ReceiptReversal`` record
    carries the mandatory reason plus a frozen per-allocation snapshot (with the
    linked OL commitment allocation reversal references), and ``ReceiptReversed``
    is emitted. History is never deleted.
    """
    reason = _reason(reason)
    if not reason:
        raise reason_required("reversing the receipt")
    _guard_reversable(receipt)
    _guard_lock_period(receipt)

    active = list(
        receipt.allocations.filter(
            reversal_of__isnull=True,
            allocation_status=ReceiptAllocationStatus.ACTIVE,
        )
    )
    actor_instance = actor if actor and getattr(actor, "is_authenticated", False) else None
    from_status = receipt.status
    snapshot = []
    with transaction.atomic():
        for allocation in active:
            reversal_row, ol_reversal = _reverse_single_allocation(
                receipt,
                allocation,
                reason=reason,
                actor=actor_instance,
                source_channel=source_channel,
            )
            snapshot.append(_reversal_snapshot_entry(allocation, reversal_row, ol_reversal))
        reversal_record = ReceiptReversal.objects.create(
            receipt=receipt,
            reversal_number=_reversal_number(receipt),
            reason=reason,
            reversed_allocations=snapshot,
            reversed_by=actor_instance,
            created_by=actor_instance,
        )
        receipt.status = ReceiptStatus.REVERSED
        receipt.reversed_at = timezone.now()
        receipt.reversed_by = actor_instance
        if actor_instance is not None:
            receipt.updated_by = actor_instance
        receipt.recompute_allocated()
        receipt.save()
        receipt_events.emit_reversed(
            receipt,
            actor=actor_instance,
            from_status=from_status,
            reason=reason,
            source_channel=source_channel,
            metadata={"reversal_number": reversal_record.reversal_number},
        )
        record_status_history(
            receipt,
            from_status=from_status,
            to_status=ReceiptStatus.REVERSED,
            actor=actor_instance,
            reason=reason,
            source_channel=source_channel,
        )
    return receipt, reversal_record


def cancel_draft(receipt, *, reason="", actor=None, source_channel="API"):
    """Cancel a DRAFT receipt (with a mandatory reason) before any money posts.

    Returns the receipt marked ``CANCELLED`` with ``cancellation_reason`` set.
    A draft has no receipt number; cancelling keeps the draft row (no hard
    delete) and emits ``ReceiptCancelled``.
    """
    reason = _reason(reason)
    if not reason:
        raise reason_required("cancelling the receipt")
    if receipt.status != ReceiptStatus.DRAFT:
        raise invalid_status("cancel", receipt.status)

    from_status = receipt.status
    actor_instance = actor if actor and getattr(actor, "is_authenticated", False) else None
    receipt.status = ReceiptStatus.CANCELLED
    receipt.cancellation_reason = reason
    if actor_instance is not None:
        receipt.updated_by = actor_instance
    receipt.save()
    receipt_events.emit_cancelled(
        receipt,
        actor=actor_instance,
        from_status=from_status,
        reason=reason,
        source_channel=source_channel,
    )
    record_status_history(
        receipt,
        from_status=from_status,
        to_status=ReceiptStatus.CANCELLED,
        actor=actor_instance,
        reason=reason,
        source_channel=source_channel,
    )
    return receipt
