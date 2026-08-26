"""ERP/GL seam: durable outbox payloads for future accounting postings.

The receipts module never writes to the general ledger directly. Instead every
material financial transition emits a typed ``DomainEvent`` into the reliable
outbox (``apps.common.models.DomainEvent``) that an ERP/GL consumer can pick up
and post. This module owns the two GL-facing payloads — receipt posting and
receipt reversal — and documents the assumed account mapping so the accounting
team can review it before wiring the consumer.

Mapping assumptions (reviewed, not yet enforced):

- A posted receipt is assumed to be a *debit to the bank/cash account* (or a
  partner bank account when one is named) with the *credit* landing in a
  premium suspense/clearing account until the receipt is allocated.
- Allocation moves the money from suspense into the premium income /
  commitment ledger — that transition is owned by the commitments module
  (``PremiumReceived``), so this seam deliberately stays at posting/reversal.
- A receipt reversal books the mirror-image journal (credit bank/cash, debit
  suspense), using the original posting as ``reverses_receipt`` provenance.
"""

from datetime import date
from decimal import Decimal

from apps.common.models import DomainEvent

AGGREGATE_TYPE = "Receipt"

GL_RECEIPT_POSTING = "GLReceiptPosting"
GL_RECEIPT_REVERSAL = "GLReceiptReversal"


def _iso_date(value):
    if value is None:
        return None
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def _actor_id(actor):
    return str(actor.pk) if actor and getattr(actor, "pk", None) else None


# Documented DR/CR mapping assumptions. Account codes are left as semantic
# placeholders for the accounting team to map to the real chart of accounts.
GL_MAPPING = {
    GL_RECEIPT_POSTING: {
        "dr": "BANK_OR_CASH",
        "cr": "PREMIUM_SUSPENSE",
        "note": "Posting credits the premium suspense account; allocation later "
        "clears it into the commitment ledger.",
    },
    GL_RECEIPT_REVERSAL: {
        "dr": "PREMIUM_SUSPENSE",
        "cr": "BANK_OR_CASH",
        "note": "Reversal mirrors the original posting to unwind the bank/cash "
        "and suspense legs.",
    },
}


def _base_payload(receipt, *, event_type, actor=None, reason="", source_channel=None):
    mapping = GL_MAPPING[event_type]
    return {
        "receipt_id": str(receipt.pk),
        "receipt_number": receipt.receipt_number,
        "receipt_date": _iso_date(receipt.receipt_date),
        "amount": str(receipt.receipt_amount),
        "currency": receipt.currency,
        "exchange_rate": str(receipt.exchange_rate or Decimal("1.000000")),
        "payment_mode": receipt.payment_mode,
        "payment_reference": receipt.payment_reference or "",
        "branch": receipt.branch_name_snapshot or (str(receipt.branch) if receipt.branch_id else ""),
        "branch_id": str(receipt.branch_id) if receipt.branch_id else None,
        "partner": receipt.partner_name_snapshot or (str(receipt.partner) if receipt.partner_id else ""),
        "partner_id": str(receipt.partner_id) if receipt.partner_id else None,
        "payer": receipt.payer_name or "",
        "source_module": receipt.source_module or "",
        "source_reference": receipt.source_reference_id or "",
        "status": receipt.status,
        "cashier_id": _actor_id(receipt.posted_by),
        "actor_id": _actor_id(actor),
        "reason": reason or "",
        "source_channel": source_channel or getattr(receipt, "source_channel", ""),
        "mapping": mapping,
    }


def emit_gl_posting(receipt, *, actor=None, reason="", source_channel=None, metadata=None):
    """Emit the GL posting outbox payload for a posted receipt."""
    payload = _base_payload(
        receipt, event_type=GL_RECEIPT_POSTING, actor=actor, reason=reason, source_channel=source_channel
    )
    if metadata:
        payload["metadata"] = metadata
    return DomainEvent.objects.create(
        event_type=GL_RECEIPT_POSTING,
        aggregate_type=AGGREGATE_TYPE,
        aggregate_id=str(receipt.pk),
        payload=payload,
    )


def emit_gl_reversal(receipt, *, actor=None, reason="", source_channel=None, metadata=None):
    """Emit the GL reversal outbox payload for a reversed receipt."""
    payload = _base_payload(
        receipt, event_type=GL_RECEIPT_REVERSAL, actor=actor, reason=reason, source_channel=source_channel
    )
    payload["reversed_at"] = receipt.reversed_at.isoformat() if receipt.reversed_at else None
    payload["reversed_by_id"] = _actor_id(receipt.reversed_by)
    if metadata:
        payload["metadata"] = metadata
    return DomainEvent.objects.create(
        event_type=GL_RECEIPT_REVERSAL,
        aggregate_type=AGGREGATE_TYPE,
        aggregate_id=str(receipt.pk),
        payload=payload,
    )
