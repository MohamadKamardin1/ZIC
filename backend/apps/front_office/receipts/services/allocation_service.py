"""Front Office Receipts — allocation engine.

Allocates posted receipt funds against OL commitments. The commitments module
owns the money math (``ol_commitments.services.allocation_service``); this
module is the receipts write path that mirrors each commitment allocation with
a ``ReceiptAllocation``, keeps the receipt amount/status split consistent, and
emits the seam events (``PremiumReceived`` on every allocation,
``FirstPremiumReceived`` when a PROPOSAL first-premium commitment is
discharged) — docs/OL_PROPOSALS_RECEIPTS_SEAM.md.
"""

import uuid
from decimal import Decimal, InvalidOperation

from django.db import IntegrityError, transaction

from apps.front_office.receipts import events as receipt_events
from apps.front_office.receipts.errors import (
    allocation_invalid,
    currency_mismatch,
    invalid_status,
    overallocation,
)
from apps.front_office.receipts.models import (
    ZERO,
    ReceiptAllocation,
    ReceiptAllocationStatus,
    ReceiptAllocationTargetType,
    ReceiptStatus,
)
from apps.front_office.receipts.services.receipt_service import record_status_history
from apps.ol_commitments.errors import CommitmentError
from apps.ol_commitments.models import OLCommitment
from apps.ol_commitments.services.allocation_service import (
    allocate_to_commitment as ol_allocate_to_commitment,
)
from apps.ol_parameters.models import OLCommitmentStatus

ALLOCATABLE_STATUSES = (ReceiptStatus.POSTED, ReceiptStatus.PARTIALLY_ALLOCATED)

_TWO_DP = Decimal("0.01")


def _fmt(value):
    return str(Decimal(value or ZERO).quantize(_TWO_DP))


def _terminal_codes():
    return list(
        OLCommitmentStatus.objects.filter(is_active=True, is_terminal=True).values_list("code", flat=True)
    )


def _open_commitments(receipt):
    """Unsettled, non-terminal commitments for the receipt partner/payer."""
    queryset = OLCommitment.objects.filter(balance__gt=0)
    terminal = _terminal_codes()
    if terminal:
        queryset = queryset.exclude(status__in=terminal)
    if receipt.partner_id:
        queryset = queryset.filter(partner_id=receipt.partner_id)
    elif receipt.partner_name_snapshot:
        queryset = queryset.filter(partner_name_snapshot__iexact=receipt.partner_name_snapshot)
    return queryset


def _resolve_commitment(target_id):
    value = (target_id or "").strip()
    if not value:
        return None
    try:
        uuid.UUID(value)
    except (ValueError, TypeError):
        return OLCommitment.objects.filter(commitment_number__iexact=value).first()
    return (
        OLCommitment.objects.filter(pk=value).first()
        or OLCommitment.objects.filter(commitment_number__iexact=value).first()
    )


def _resolve_source(commitment):
    if commitment is None or not commitment.source_content_type_id or not commitment.source_object_id:
        return None
    try:
        return commitment.source
    except Exception:
        return None


def commitment_option(commitment):
    source = _resolve_source(commitment)
    source_type = (commitment.source_type or "").strip().upper()
    proposal_number = None
    policy_number = None
    if source_type == "PROPOSAL":
        proposal_number = getattr(source, "proposal_number", None) or (commitment.source_reference or None)
        source_display = f"OL Proposal {proposal_number}" if proposal_number else "OL Proposal"
    elif source_type == "POLICY":
        policy_number = getattr(source, "policy_number", None) or (commitment.source_reference or None)
        source_display = f"OL Policy {policy_number}" if policy_number else "OL Policy"
    else:
        source_display = commitment.source_reference or "Manual"
    return {
        "id": str(commitment.pk),
        "commitment_number": commitment.commitment_number,
        "source_type": source_type,
        "source_display": source_display,
        "proposal_number": proposal_number,
        "policy_number": policy_number,
        "product_display": commitment.plan_name_snapshot or commitment.product_name_snapshot or "",
        "plan_display": commitment.plan_name_snapshot or "",
        "due_date": commitment.due_date.isoformat() if commitment.due_date else None,
        "amount_due": _fmt(commitment.premium_amount),
        "amount_paid": _fmt(commitment.amount_paid),
        "balance": _fmt(commitment.balance),
        "currency": commitment.currency,
        "status": commitment.status,
        "installment_number": commitment.installment_number,
    }


def allocation_options(receipt):
    commitments = _open_commitments(receipt).order_by("due_date", "-created_at")
    return [commitment_option(commitment) for commitment in commitments]


def _guard_allocatable(receipt, action="allocate"):
    if receipt.status not in ALLOCATABLE_STATUSES:
        raise invalid_status(action, receipt.status)


def _validate_allocation_amount(amount):
    try:
        amount = Decimal(str(amount))
    except (InvalidOperation, TypeError, ValueError):
        raise allocation_invalid(
            message="The allocation amount is not valid.",
            field_errors={"amount": ["Enter a valid allocation amount."]},
        )
    if amount <= 0:
        raise allocation_invalid(
            message="The allocation amount must be greater than zero.",
            field_errors={"amount": ["Enter an amount greater than zero."]},
        )
    return amount


def _raise_mapped_commitment_error(exc):
    code = getattr(exc, "error_code", "")
    if code == "COMMITMENT_OVERPAYMENT":
        raise overallocation(
            message="The allocation exceeds the commitment's outstanding balance.",
            field_errors=getattr(exc, "field_errors", None),
        )
    if code == "CURRENCY_MISMATCH":
        raise currency_mismatch()
    raise exc


def allocate(receipt, *, target_type, target_id, amount, narration="", actor=None, source_channel="API"):
    """Resolve an OL commitment target and delegate to the allocation engine."""
    if (target_type or "").strip().upper() != ReceiptAllocationTargetType.OL_COMMITMENT:
        raise allocation_invalid(
            message="Only OL_COMMITMENT allocations are supported.",
            field_errors={"target_type": ["Only OL_COMMITMENT allocations are supported."]},
        )
    commitment = _resolve_commitment(target_id)
    if commitment is None:
        raise allocation_invalid(
            message="The allocation target commitment was not found.",
            field_errors={"target_id": ["Commitment not found or not open for allocation."]},
        )
    return allocate_to_commitment(
        receipt,
        commitment,
        amount=amount,
        narration=narration,
        actor=actor,
        source_channel=source_channel,
    )


def allocate_to_commitment(receipt, commitment, *, amount, narration="", actor=None, source_channel="API"):
    """Allocate ``amount`` of a posted receipt to an OL commitment.

    Returns ``(allocation, receipt, created)``. Idempotent per (receipt,
    commitment): a repeated allocation returns the existing active
    ``ReceiptAllocation`` without double-applying to either ledger.

    Constraints enforced before/within the commitment write:
      - receipt must be POSTED or PARTIALLY_ALLOCATED (``RECEIPT_INVALID_STATUS``)
      - amount > 0 (``RECEIPT_ALLOCATION_INVALID``)
      - amount <= receipt unallocated balance (``RECEIPT_OVERALLOCATION``)
      - amount <= commitment balance (delegated, mapped to ``RECEIPT_OVERALLOCATION``)
      - same currency (``RECEIPT_CURRENCY_MISMATCH``)
    """
    # Idempotency first: a retry for an already-allocated (receipt, commitment)
    # returns the existing allocation without re-running the status/amount guards
    # or double-applying to either ledger.
    existing = ReceiptAllocation.objects.filter(
        receipt=receipt,
        commitment=commitment,
        allocation_status=ReceiptAllocationStatus.ACTIVE,
        reversal_of__isnull=True,
    ).first()
    if existing is not None:
        receipt.refresh_from_db()
        return existing, receipt, False

    _guard_allocatable(receipt, "allocate")
    amount = _validate_allocation_amount(amount)

    if (receipt.currency or "").strip().upper() != (commitment.currency or "").strip().upper():
        raise currency_mismatch()

    unallocated = Decimal(receipt.unallocated_amount or ZERO)
    if amount > unallocated:
        raise overallocation(available=unallocated)

    from_status = receipt.status
    commitment_from_status = commitment.status
    commitment_was_settled = Decimal(commitment.balance or ZERO) <= 0
    actor_instance = actor if actor and getattr(actor, "is_authenticated", False) else None

    try:
        with transaction.atomic():
            ol_allocation, commitment = ol_allocate_to_commitment(
                commitment,
                amount=amount,
                receipt_reference=receipt.receipt_number,
                payment_mode=receipt.payment_mode,
                currency=receipt.currency,
                exchange_rate=Decimal("1.000000"),
                reason=narration or "",
                allocated_by=actor_instance,
                source_channel=source_channel,
                from_status=commitment.status,
            )
            allocation = ReceiptAllocation.objects.create(
                receipt=receipt,
                target_type=ReceiptAllocationTargetType.OL_COMMITMENT,
                target_id=commitment.commitment_number,
                target_display=commitment.commitment_number,
                commitment=commitment,
                ol_commitment_allocation=ol_allocation,
                amount=amount,
                currency=receipt.currency,
                exchange_rate=ol_allocation.exchange_rate,
                narration=narration or "",
                allocated_by=actor_instance,
                source_channel=source_channel,
            )
            receipt.recompute_allocated()
            receipt._derive_status()
            if actor_instance is not None:
                receipt.updated_by = actor_instance
            receipt.save()
            _emit_allocation_events(
                receipt,
                allocation,
                commitment,
                from_status=from_status,
                commitment_from_status=commitment_from_status,
                commitment_was_settled=commitment_was_settled,
                actor=actor_instance,
                source_channel=source_channel,
                narration=narration,
            )
            record_status_history(
                receipt,
                from_status=from_status,
                to_status=receipt.status,
                actor=actor_instance,
                reason=narration or "Receipt allocated.",
                source_channel=source_channel,
            )
    except IntegrityError:
        # Concurrent duplicate (commitment, receipt_reference) — reuse the winner.
        existing = ReceiptAllocation.objects.filter(
            receipt=receipt, commitment=commitment, reversal_of__isnull=True
        ).first()
        if existing is not None:
            receipt.refresh_from_db()
            return existing, receipt, False
        raise
    except CommitmentError as exc:
        _raise_mapped_commitment_error(exc)
        raise
    return allocation, receipt, True


def _emit_allocation_events(
    receipt,
    allocation,
    commitment,
    *,
    from_status,
    commitment_from_status,
    commitment_was_settled,
    actor,
    source_channel,
    narration,
):
    receipt_events.emit_allocated(
        receipt,
        allocation=allocation,
        actor=actor,
        from_status=from_status,
        reason=narration or "Receipt allocated.",
        source_channel=source_channel,
    )
    if receipt.status == ReceiptStatus.FULLY_ALLOCATED and from_status != ReceiptStatus.FULLY_ALLOCATED:
        receipt_events.emit_fully_allocated(
            receipt,
            actor=actor,
            from_status=from_status,
            reason="Receipt fully allocated.",
            source_channel=source_channel,
        )
    # Seam publishing rule: PremiumReceived in the same transaction as the insert.
    # from_status/to_status describe the commitment transition per the seam contract.
    receipt_events.emit_premium_received(
        receipt,
        allocation=allocation,
        commitment=commitment,
        actor=actor,
        from_status=commitment_from_status,
        to_status=commitment.status,
        reason=narration or "",
        source_channel=source_channel,
    )
    is_first_premium = (
        (commitment.source_type or "").strip().upper() == "PROPOSAL" and commitment.installment_number == 1
    )
    now_settled = Decimal(commitment.balance or ZERO) <= 0
    if is_first_premium and now_settled and not commitment_was_settled:
        receipt_events.emit_first_premium_received(
            receipt,
            allocation=allocation,
            commitment=commitment,
            proposal=_resolve_source(commitment),
            actor=actor,
            from_status=from_status,
            to_status=receipt.status,
            reason=narration or "First premium received.",
            source_channel=source_channel,
        )


def auto_allocate(receipt, *, actor=None, source_channel="API"):
    """Allocate a posted receipt oldest-due-first, same currency first.

    Returns a detailed result: per-commitment allocations with balances before/
    after, the total allocated, remaining unallocated, and the resulting receipt
    status.
    """
    _guard_allocatable(receipt, "auto-allocate")
    commitments = list(_open_commitments(receipt).order_by("due_date", "-created_at"))
    commitments.sort(key=lambda item: (item.currency != receipt.currency, item.due_date, item.created_at))

    remaining = Decimal(receipt.unallocated_amount or ZERO)
    actor_instance = actor if actor and getattr(actor, "is_authenticated", False) else None
    results = []
    for commitment in commitments:
        if remaining <= 0:
            break
        balance = Decimal(commitment.balance or ZERO)
        if balance <= 0:
            continue
        amount = min(remaining, balance)
        balance_before = balance
        allocation, receipt, _created = allocate_to_commitment(
            receipt,
            commitment,
            amount=amount,
            narration="Auto-allocation: oldest due commitments first.",
            actor=actor_instance,
            source_channel=source_channel,
        )
        results.append(
            {
                "commitment_number": commitment.commitment_number,
                "amount": _fmt(amount),
                "currency": commitment.currency,
                "balance_before": _fmt(balance_before),
                "balance_after": _fmt(commitment.balance),
                "status": commitment.status,
                "receipt_allocation_id": str(allocation.pk),
                "ol_commitment_allocation_id": str(allocation.ol_commitment_allocation_id)
                if allocation.ol_commitment_allocation_id
                else None,
            }
        )
        remaining -= amount

    return {
        "allocations": results,
        "total_allocated": _fmt(receipt.allocated_amount),
        "remaining_unallocated": _fmt(receipt.unallocated_amount),
        "receipt_status": receipt.status,
        "commitments_count": len(results),
        "exhausted": remaining <= 0,
    }
