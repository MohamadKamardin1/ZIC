"""Front Office Receipts — foundation service operations.

Prompt 1 scope: create a draft receipt, update a draft receipt, and keep
amount/status/audit invariants consistent. Posting, allocation, reversal, and
cancellation actions land in later prompts; every one of those will reuse the
invariant helpers defined here (``record_status_history``, amount recompute,
and the idempotency guard).
"""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.front_office.receipts import events as receipt_events
from apps.front_office.receipts.errors import ReceiptError, invalid_status, not_found
from apps.front_office.receipts.models import Receipt, ReceiptStatus, ReceiptStatusHistory
from apps.front_office.receipts.services.parameter_resolver import default_currency
from apps.front_office.receipts.services.receipt_numbering import ReceiptNumberingService

ZERO = Decimal("0.00")


def _receipt_number(branch_id=None):
    return ReceiptNumberingService.next_number(branch_id=branch_id)


def record_status_history(
    receipt,
    *,
    from_status="",
    to_status=None,
    actor=None,
    reason="",
    source_channel=None,
):
    """Append a status transition row and update the receipt status."""
    to_status = to_status or receipt.status
    ReceiptStatusHistory.objects.create(
        receipt=receipt,
        from_status=(from_status or "").strip().upper(),
        to_status=(to_status or "").strip().upper(),
        reason=reason or "",
        changed_by=actor if actor and getattr(actor, "is_authenticated", False) else None,
        source_channel=source_channel or receipt.source_channel,
    )
    if (to_status or "").strip().upper() != (receipt.status or "").strip().upper():
        receipt.status = to_status
        receipt.save(update_fields=["status", "updated_at"])


def _validate_amount(amount):
    if amount is None:
        raise ReceiptError(
            "A receipt amount is required.",
            error_code="RECEIPT_AMOUNT_INVALID",
            status_code=422,
            field_errors={"receipt_amount": ["Enter the confirmed receipt amount."]},
        )
    try:
        amount = Decimal(str(amount))
    except (TypeError, ValueError):
        raise ReceiptError(
            "The receipt amount is not a valid number.",
            error_code="RECEIPT_AMOUNT_INVALID",
            status_code=422,
            field_errors={"receipt_amount": ["Enter a valid number."]},
        )
    if amount <= ZERO:
        raise ReceiptError(
            "The receipt amount must be greater than zero.",
            error_code="RECEIPT_AMOUNT_INVALID",
            status_code=422,
            field_errors={"receipt_amount": ["Amount must be greater than zero."]},
        )
    return amount


def create_draft(*, actor=None, request=None, source_channel="API", **fields):
    """Create a DRAFT receipt idempotently by ``idempotency_key``.

    Returns ``(receipt, created)``. A repeated submission carrying the same
    idempotency key returns the existing receipt without duplicating it.
    """
    idempotency_key = (fields.get("idempotency_key") or "").strip() or None
    if idempotency_key:
        existing = Receipt.objects.filter(idempotency_key=idempotency_key).first()
        if existing is not None:
            return existing, False

    receipt_amount = _validate_amount(fields.get("receipt_amount"))

    actor_instance = actor if actor and getattr(actor, "is_authenticated", False) else None
    receipt = Receipt(
        receipt_number=fields.get("receipt_number") or _receipt_number(branch_id=fields.get("branch_id")),
        idempotency_key=idempotency_key,
        receipt_date=fields.get("receipt_date") or timezone.localdate(),
        branch_id=fields.get("branch_id"),
        partner_id=fields.get("partner_id"),
        payer_name=fields.get("payer_name") or "",
        payer_identity=fields.get("payer_identity") or "",
        source_module=(fields.get("source_module") or "MANUAL").strip().upper(),
        source_reference_type=(fields.get("source_reference_type") or "").strip(),
        source_reference_id=(fields.get("source_reference_id") or "").strip(),
        currency=(fields.get("currency") or default_currency()).strip().upper(),
        exchange_rate=Decimal(str(fields.get("exchange_rate") or "1.000000")),
        receipt_amount=receipt_amount,
        payment_mode=(fields.get("payment_mode") or "CASH").strip().upper(),
        payment_reference=(fields.get("payment_reference") or "").strip(),
        bank_account_id=fields.get("bank_account_id"),
        narration=fields.get("narration") or "",
        status=ReceiptStatus.DRAFT,
        created_by=actor_instance,
        updated_by=actor_instance,
        source_channel=(source_channel or "API"),
    )
    try:
        receipt.full_clean_ex()
    except ValidationError as exc:
        raise ReceiptError(
            "The receipt could not be saved; correct the highlighted fields.",
            error_code="RECEIPT_AMOUNT_INVALID" if "receipt_amount" in getattr(exc, "message_dict", {}) else "VALIDATION_ERROR",
            status_code=422,
            field_errors=exc.message_dict,
        )
    receipt.save()
    receipt_events.emit_created(
        receipt,
        actor=actor_instance,
        reason="Receipt draft created.",
        source_channel=source_channel,
        metadata={"branch": receipt.branch_name_snapshot, "payment_mode": receipt.payment_mode},
    )
    record_status_history(receipt, to_status=ReceiptStatus.DRAFT, actor=actor_instance, reason="Receipt draft created.", source_channel=source_channel)
    return receipt, True


def get_receipt_or_404(receipt_id):
    receipt = Receipt.objects.filter(pk=receipt_id).first()
    if not receipt:
        raise not_found()
    return receipt


def update_draft(receipt, *, actor=None, source_channel=None, **fields):
    """Update a DRAFT receipt; posted/reversed/cancelled receipts are locked."""
    if receipt.status != ReceiptStatus.DRAFT:
        raise invalid_status("update", receipt.status)

    amount = fields.get("receipt_amount")
    if amount is not None:
        receipt.receipt_amount = _validate_amount(amount)

    actor_instance = actor if actor and getattr(actor, "is_authenticated", False) else None
    for field, value in fields.items():
        if value is None or field in ("receipt_amount", "idempotency_key"):
            continue
        if field in ("branch_id", "partner_id", "bank_account_id"):
            setattr(receipt, field, value)
        elif hasattr(receipt, field):
            setattr(receipt, field, value)
    if actor_instance is not None:
        receipt.updated_by = actor_instance
    receipt.source_channel = source_channel or receipt.source_channel

    try:
        receipt.full_clean_ex()
    except ValidationError as exc:
        raise ReceiptError(
            "The receipt could not be updated; correct the highlighted fields.",
            error_code="VALIDATION_ERROR",
            status_code=422,
            field_errors=exc.message_dict,
        )
    receipt.save()
    return receipt


def recompute_and_save(receipt, *, actor=None, source_channel=None):
    """Recompute amounts/status and persist; used by posting/allocation flows."""
    receipt.recompute_allocated()
    receipt._derive_status()
    receipt.updated_by = actor if actor and getattr(actor, "is_authenticated", False) else receipt.updated_by
    receipt.save()
    return receipt
