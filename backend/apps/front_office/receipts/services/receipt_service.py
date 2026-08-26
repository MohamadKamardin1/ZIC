"""Front Office Receipts — foundation service operations.

Prompt 1 scope: create a draft receipt, update a draft receipt, and keep
amount/status/audit invariants consistent. Posting, allocation, reversal, and
cancellation actions land in later prompts; every one of those will reuse the
invariant helpers defined here (``record_status_history``, amount recompute,
and the idempotency guard).
"""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.front_office.receipts import events as receipt_events
from apps.front_office.receipts.config_models import ReceiptPaymentModeRule
from apps.front_office.receipts.errors import (
    ReceiptError,
    already_posted,
    bank_account_required,
    invalid_status,
    not_found,
    parameter_missing,
    payment_reference_required,
)
from apps.front_office.receipts.models import Receipt, ReceiptStatus, ReceiptStatusHistory
from apps.front_office.receipts.services.parameter_resolver import configured_currencies, default_currency
from apps.front_office.receipts.services.receipt_numbering import ReceiptNumberingService
from apps.partner_onboarding.models import Branch
from apps.partners.models import Partner

ZERO = Decimal("0.00")

# Core receipt identity/economic fields frozen once a receipt is posted. Drafts
# are fully editable; posted receipts are immutable except allocation/reversal
# actions (Prompt 3 mandatory rule).
IMMUTABLE_AFTER_POST = (
    "payer_name",
    "payer_identity",
    "receipt_amount",
    "currency",
    "exchange_rate",
    "payment_mode",
    "receipt_date",
    "branch_id",
    "partner_id",
)


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
        ) from None
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
        # Drafts are numbered at posting time by the numbering service.
        receipt_number=(fields.get("receipt_number") or "").strip() or None,
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
        ) from exc
    try:
        with transaction.atomic():
            receipt.save()
            receipt_events.emit_created(
                receipt,
                actor=actor_instance,
                reason="Receipt draft created.",
                source_channel=source_channel,
                metadata={"branch": receipt.branch_name_snapshot, "payment_mode": receipt.payment_mode},
            )
            record_status_history(receipt, to_status=ReceiptStatus.DRAFT, actor=actor_instance, reason="Receipt draft created.", source_channel=source_channel)
    except IntegrityError:
        # A concurrent submission with the same idempotency key won the insert;
        # return the already-created receipt so retries are safe.
        if idempotency_key:
            existing = Receipt.objects.filter(idempotency_key=idempotency_key).first()
            if existing is not None:
                return existing, False
        raise
    return receipt, True


def get_receipt_or_404(receipt_id):
    receipt = Receipt.objects.filter(pk=receipt_id).first()
    if not receipt:
        raise not_found()
    return receipt


def update_draft(receipt, *, actor=None, source_channel=None, **fields):
    """Update a DRAFT receipt; posted receipts are immutable.

    Once posted, a receipt's core fields (payer, amount, currency, payment
    mode, receipt date, branch) are frozen; allocation/reversal actions are the
    only permitted mutations afterwards.
    """
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
        ) from exc
    receipt.save()
    return receipt


def _validate_active_reference_data(receipt):
    """Reject posting when a referenced catalog record is inactive or missing."""
    if receipt.branch_id and not Branch.objects.filter(pk=receipt.branch_id, is_active=True).exists():
        raise parameter_missing("RECEIPT_BRANCHES")
    if receipt.partner_id and not Partner.objects.filter(pk=receipt.partner_id, is_active=True).exists():
        raise parameter_missing("RECEIPT_PARTNERS")
    if (receipt.currency or "").strip().upper() not in configured_currencies():
        raise parameter_missing("RECEIPT_CURRENCIES")


def _validate_payment_mode_rule(receipt):
    """Validate the configured payment-mode rule and its requirements."""
    rule = ReceiptPaymentModeRule.objects.filter(
        payment_mode=(receipt.payment_mode or "").strip().upper(), is_active=True
    ).first()
    if rule is None:
        raise parameter_missing("RECEIPT_PAYMENT_MODES")

    amount = Decimal(receipt.receipt_amount or ZERO)
    if rule.min_amount is not None and amount < rule.min_amount:
        raise ReceiptError(
            f"The receipt amount is below the minimum ({rule.min_amount}) allowed for {rule.payment_mode}.",
            error_code="RECEIPT_AMOUNT_INVALID",
            status_code=422,
            field_errors={"receipt_amount": [f"Amount must be at least {rule.min_amount} for {rule.payment_mode}."]},
        )
    if rule.max_amount is not None and amount > rule.max_amount:
        raise ReceiptError(
            f"The receipt amount exceeds the maximum ({rule.max_amount}) allowed for {rule.payment_mode}.",
            error_code="RECEIPT_AMOUNT_INVALID",
            status_code=422,
            field_errors={"receipt_amount": [f"Amount cannot exceed {rule.max_amount} for {rule.payment_mode}."]},
        )
    if rule.requires_reference and not (receipt.payment_reference or "").strip():
        raise payment_reference_required()
    if rule.requires_bank_account and not receipt.bank_account_id:
        raise bank_account_required()
    return rule


def post_receipt(receipt, *, actor=None, reason="", source_channel=None):
    """Post a draft receipt.

    Assigns the receipt number (if not already assigned), validates the
    active reference data and the payment-mode rule, then marks the receipt
    POSTED with ``posted_at``/``posted_by``, emits ``ReceiptPosted``, and
    records the status transition. The signal receivers persist the before/
    after audit row.

    Idempotent: retrying a post of an already-posted receipt raises
    ``RECEIPT_ALREADY_POSTED`` (409) with no side effects — no renumbering, no
    duplicate event, no double audit.
    """
    posted_states = (
        ReceiptStatus.POSTED,
        ReceiptStatus.PARTIALLY_ALLOCATED,
        ReceiptStatus.FULLY_ALLOCATED,
    )
    if receipt.status in posted_states:
        raise already_posted()
    if receipt.status != ReceiptStatus.DRAFT:
        raise invalid_status("post", receipt.status)

    _validate_amount(receipt.receipt_amount)

    if not (receipt.receipt_number or "").strip():
        receipt.receipt_number = _receipt_number(branch_id=receipt.branch_id)

    _validate_active_reference_data(receipt)
    _validate_payment_mode_rule(receipt)

    from_status = receipt.status
    actor_instance = actor if actor and getattr(actor, "is_authenticated", False) else None
    receipt.status = ReceiptStatus.POSTED
    receipt.posted_at = timezone.now()
    receipt.posted_by = actor_instance
    receipt.updated_by = actor_instance
    receipt.source_channel = source_channel or receipt.source_channel
    try:
        receipt.full_clean_ex()
    except ValidationError as exc:
        raise ReceiptError(
            "The receipt could not be posted; correct the highlighted fields.",
            error_code="VALIDATION_ERROR",
            status_code=422,
            field_errors=exc.message_dict,
        ) from exc
    receipt.save()
    receipt_events.emit_posted(
        receipt,
        actor=actor_instance,
        from_status=from_status,
        reason=reason or "Receipt posted.",
        source_channel=source_channel,
    )
    from apps.front_office.receipts.services.gl_seam import emit_gl_posting
    from apps.front_office.receipts.services.notification_service import notify_receipt_posted

    emit_gl_posting(
        receipt,
        actor=actor_instance,
        reason=reason or "Receipt posted.",
        source_channel=source_channel,
    )
    notify_receipt_posted(receipt=receipt, actor=actor_instance, source_channel=source_channel)
    record_status_history(
        receipt,
        from_status=from_status,
        to_status=ReceiptStatus.POSTED,
        actor=actor_instance,
        reason=reason or "Receipt posted.",
        source_channel=source_channel,
    )
    return receipt


def recompute_and_save(receipt, *, actor=None, source_channel=None):
    """Recompute amounts/status and persist; used by posting/allocation flows."""
    receipt.recompute_allocated()
    receipt._derive_status()
    receipt.updated_by = actor if actor and getattr(actor, "is_authenticated", False) else receipt.updated_by
    receipt.save()
    return receipt
