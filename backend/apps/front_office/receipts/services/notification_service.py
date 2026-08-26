"""Receipt notification seam mirroring the commitments/proposals notification centre.

Receipts publish into the same notification contract the commitments and
proposals modules use (``ReceiptNotificationLog`` mirrors
``OLProposalNotificationLog`` / ``OLCommitmentNotificationLog``). The unique
constraint on (receipt, event_type, dispatch_on, channel, recipient) guarantees
each notification is emitted exactly once per run.
"""

from datetime import date

from apps.front_office.receipts.models import ReceiptNotificationLog
from apps.ol_commitments.models import (
    NotificationChannel,
    NotificationDispatchStatus,
    NotificationRecipientType,
)

RECEIPT_POSTED = "ReceiptPosted"
RECEIPT_REVERSED = "ReceiptReversed"
FIRST_PREMIUM_RECEIVED = "FirstPremiumReceived"


def notify_event(
    *,
    receipt,
    event_type,
    dispatch_on=None,
    notification_channel=NotificationChannel.SYSTEM,
    recipient_type=NotificationRecipientType.STAFF,
    recipient_identifier="",
    template_code="",
    payload=None,
    source_channel="API",
):
    """Create one notification log row (idempotent via the unique constraint)."""
    log, created = ReceiptNotificationLog.objects.get_or_create(
        receipt=receipt,
        event_type=event_type,
        dispatch_on=dispatch_on or date.today(),
        notification_channel=notification_channel,
        recipient_type=recipient_type,
        defaults={
            "recipient_identifier": recipient_identifier or "",
            "template_code": template_code or "",
            "status": NotificationDispatchStatus.PENDING,
            "payload": dict(payload or {}),
            "source_channel": source_channel,
        },
    )
    return log, created


def notify_receipt_posted(*, receipt, actor=None, source_channel="API"):
    return notify_event(
        receipt=receipt,
        event_type=RECEIPT_POSTED,
        payload={
            "receipt_number": receipt.receipt_number,
            "amount": str(receipt.receipt_amount),
            "currency": receipt.currency,
            "status": receipt.status,
            "payer": receipt.payer_name,
        },
        recipient_identifier=getattr(actor, "username", "") if actor else "",
        source_channel=source_channel,
    )


def notify_receipt_reversed(*, receipt, actor=None, reason="", source_channel="API"):
    return notify_event(
        receipt=receipt,
        event_type=RECEIPT_REVERSED,
        payload={
            "receipt_number": receipt.receipt_number,
            "amount": str(receipt.receipt_amount),
            "currency": receipt.currency,
            "status": receipt.status,
            "payer": receipt.payer_name,
            "reason": reason or "",
        },
        recipient_identifier=getattr(actor, "username", "") if actor else "",
        source_channel=source_channel,
    )


def notify_first_premium_received(
    *,
    receipt,
    proposal_number="",
    commitment_number="",
    actor=None,
    source_channel="API",
):
    return notify_event(
        receipt=receipt,
        event_type=FIRST_PREMIUM_RECEIVED,
        payload={
            "receipt_number": receipt.receipt_number,
            "amount": str(receipt.receipt_amount),
            "currency": receipt.currency,
            "proposal_number": proposal_number or "",
            "commitment_number": commitment_number or "",
        },
        recipient_identifier=getattr(actor, "username", "") if actor else "",
        source_channel=source_channel,
    )
