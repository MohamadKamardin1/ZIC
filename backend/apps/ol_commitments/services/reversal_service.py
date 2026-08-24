"""OL Commitments — allocation reversal service.

Mirror of ``allocation_service.allocate_to_commitment`` for the reversal
direction: reversing a committed allocation never deletes history. The original
``OLCommitmentAllocation`` row is kept and a linked reversal row
(``reversal_of``) is created; the commitment's ``amount_paid`` is reduced by the
original's ``converted_amount``, the balance is recomputed, status is re-resolved
from the OL Parameters catalog, and a ``CommitmentPaymentReversed`` event is
emitted in the same transaction (docs/OL_PROPOSALS_RECEIPTS_SEAM.md: receipts
write allocations; the commitments module owns the money math).
"""

from decimal import Decimal

from apps.ol_commitments import events as commitment_events
from apps.ol_commitments.errors import CommitmentError
from apps.ol_commitments.models import OLCommitmentAllocation
from apps.ol_commitments.services.allocation_service import _resolve_status

ZERO = Decimal("0.00")


def _already_reversed_error():
    return CommitmentError(
        "This commitment allocation has already been reversed.",
        error_code="ALLOCATION_ALREADY_REVERSED",
        status_code=409,
        resolution_steps=[
            "A reversed allocation is closed and cannot be reversed again.",
            "Create a fresh receipt and allocation if a re-collection is required.",
        ],
    )


def reverse_allocation_to_commitment(
    commitment_allocation,
    *,
    reason="",
    reversed_by=None,
    source_channel="API",
):
    """Reverse one ``OLCommitmentAllocation`` and restore the commitment state.

    Idempotent: reversing an allocation that already has a reversal row returns
    the existing reversal without double-applying to the commitment balance.
    Returns ``(reversal_allocation, commitment)``.
    """
    original = commitment_allocation
    if original.reversal_of_id is not None:
        raise _already_reversed_error()

    existing = OLCommitmentAllocation.objects.filter(
        commitment=original.commitment,
        receipt_reference=original.receipt_reference,
        reversal_of=original,
    ).first()
    if existing is not None:
        original.commitment.refresh_from_db()
        return existing, original.commitment

    commitment = original.commitment
    actor = reversed_by if reversed_by and getattr(reversed_by, "is_authenticated", False) else None
    from_status = commitment.status

    converted = Decimal(original.converted_amount or ZERO)
    commitment.amount_paid = max(Decimal(commitment.amount_paid or ZERO) - converted, ZERO)
    commitment.recompute_balance()
    if reason:
        commitment.reason_text = reason
    if Decimal(commitment.balance or ZERO) <= 0:
        commitment.status = _resolve_status("COMPLETED") or commitment.status
    elif Decimal(commitment.amount_paid or ZERO) > 0:
        commitment.status = _resolve_status("PARTIALLY_PAID") or commitment.status
    else:
        commitment.status = _resolve_status("PENDING") or commitment.status
    if actor is not None:
        commitment.updated_by = actor
    commitment.save()

    reversal = OLCommitmentAllocation.objects.create(
        commitment=commitment,
        receipt_reference=original.receipt_reference,
        amount=original.amount,
        converted_amount=converted,
        payment_mode=original.payment_mode,
        currency=original.currency,
        exchange_rate=original.exchange_rate,
        reason=reason or f"Reversal of {original.receipt_reference}",
        reversal_of=original,
        allocated_by=actor,
        source_channel=source_channel,
    )
    commitment_events.emit_payment_reversed(
        commitment,
        allocation=reversal,
        reversed_allocation=original,
        actor=actor,
        from_status=from_status,
        reason=reason or "",
        source_channel=source_channel,
    )
    return reversal, commitment
