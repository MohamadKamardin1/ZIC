"""OL Commitments — allocation service.

Single ownership boundary for applying a payment/allocation to a commitment.
The Front Office Receipts module, the manual record-payment action, and future
policies all delegate here instead of duplicating the balance/status/event
logic (docs/OL_PROPOSALS_RECEIPTS_SEAM.md: receipts write allocations; the
commitments module owns the money math).

Invariants enforced here are the source of truth: positive amount, positive
exchange rate, cross-currency rate requirement, and amount not exceeding the
outstanding balance. Status resolves to ``COMPLETED`` / ``PARTIALLY_PAID`` from
the OL Parameters catalog (never hardcoded).
"""

from decimal import Decimal, InvalidOperation

from apps.ol_commitments import events as commitment_events
from apps.ol_commitments.errors import CommitmentError
from apps.ol_commitments.models import OLCommitmentAllocation
from apps.ol_parameters.models import OLCommitmentStatus

ZERO = Decimal("0.00")
ONE = Decimal("1.000000")


def _resolve_status(code_like):
    row = (
        OLCommitmentStatus.objects.filter(is_active=True, code__icontains=code_like)
        .order_by("display_order", "code")
        .first()
    )
    return row.code if row else None


def _amount_error():
    return CommitmentError(
        "A payment amount greater than zero is required.",
        error_code="VALIDATION_ERROR",
        field_errors={"amount": ["Enter an amount greater than zero."]},
    )


def allocate_to_commitment(
    commitment,
    *,
    amount,
    receipt_reference="",
    payment_mode="",
    currency=None,
    exchange_rate=None,
    reason="",
    allocated_by=None,
    source_channel="API",
    from_status="",
):
    """Allocate money to a commitment and keep balance/status/events consistent.

    Returns ``(allocation, commitment)`` with the commitment's ``amount_paid``,
    ``balance``, and ``status`` already recomputed and persisted. The model-level
    unique non-reversal ``(commitment, receipt_reference)`` constraint keeps the
    operation idempotent; callers catch ``IntegrityError`` and reuse the existing
    allocation.
    """
    try:
        amount = Decimal(str(amount))
    except (InvalidOperation, TypeError, ValueError):
        raise _amount_error()
    if amount is None or amount <= 0:
        raise _amount_error()

    paid_currency = (currency or commitment.currency or "").strip().upper()
    target_currency = (commitment.currency or "").strip().upper()
    same_currency = paid_currency == target_currency

    # Same currency needs no rate; a cross-currency allocation requires an
    # explicit positive rate (prompt 5 — multi-currency is explicit, never
    # silently assumed at 1.0).
    if exchange_rate in (None, ""):
        if same_currency:
            exchange_rate = ONE
        else:
            raise CommitmentError(
                "A cross-currency allocation requires an exchange rate.",
                error_code="CURRENCY_MISMATCH",
                status_code=422,
                resolution_steps=[
                    "Provide the exchange rate from the receipt currency to the commitment currency.",
                    "Use the exchange-rate endpoint to look up a configured rate for the pair.",
                ],
                field_errors={"exchange_rate": ["An exchange rate greater than zero is required for cross-currency allocations."]},
            )
    try:
        exchange_rate = Decimal(str(exchange_rate))
    except (InvalidOperation, TypeError, ValueError):
        exchange_rate = None
    if exchange_rate is None or exchange_rate <= 0:
        raise CommitmentError(
            "An exchange rate greater than zero is required.",
            error_code="VALIDATION_ERROR",
            field_errors={"exchange_rate": ["Exchange rate must be greater than zero."]},
        )

    converted = (amount * exchange_rate).quantize(Decimal("0.01"))
    balance = Decimal(commitment.balance or ZERO)
    if converted > balance:
        raise CommitmentError(
            "The payment amount exceeds the outstanding balance of the commitment.",
            error_code="COMMITMENT_OVERPAYMENT",
            status_code=422,
            resolution_steps=[
                "Adjust the amount so it is equal to or below the outstanding balance.",
                "If you intentionally collected more, record the surplus as a credit.",
            ],
            field_errors={"amount": [f"Amount cannot exceed balance of {balance:.2f}."]},
        )

    from_status = (from_status or "").strip() or commitment.status
    actor = allocated_by if allocated_by and getattr(allocated_by, "is_authenticated", False) else None

    commitment.amount_paid = Decimal(commitment.amount_paid or ZERO) + converted
    commitment.recompute_balance()
    if reason:
        commitment.reason_text = reason
    if commitment.balance <= 0:
        commitment.status = _resolve_status("COMPLETED") or commitment.status
    else:
        commitment.status = _resolve_status("PARTIALLY_PAID") or commitment.status
    if actor is not None:
        commitment.updated_by = actor
    commitment.save()

    allocation = OLCommitmentAllocation.objects.create(
        commitment=commitment,
        receipt_reference=(receipt_reference or f"MANUAL-{commitment.commitment_number}").strip()[:120],
        amount=amount,
        converted_amount=converted,
        payment_mode=payment_mode or "",
        currency=paid_currency,
        exchange_rate=exchange_rate,
        reason=reason or "",
        allocated_by=actor,
        source_channel=source_channel,
    )
    commitment_events.emit_payment_allocated(
        commitment,
        allocation=allocation,
        actor=actor,
        from_status=from_status,
        reason=reason or "",
        source_channel=source_channel,
    )
    if commitment.balance <= 0:
        commitment_events.emit_completed(
            commitment,
            actor=actor,
            from_status=from_status,
            reason="Commitment fully settled.",
            source_channel=source_channel,
        )
    return allocation, commitment
