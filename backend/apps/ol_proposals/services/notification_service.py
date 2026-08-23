"""Proposal notification seam mirroring the commitments notification centre.

Proposals publish into the same notification contract the commitments module
uses (``OLProposalNotificationLog`` mirrors ``OLCommitmentNotificationLog``).
The unique constraint on (proposal, event_type, dispatch_on, channel,
recipient) guarantees each notification is emitted exactly once per run.
"""

from apps.ol_commitments.models import (
    NotificationChannel,
    NotificationDispatchStatus,
    NotificationRecipientType,
)
from apps.ol_proposals.models import OLProposalNotificationLog

PROPOSAL_EXPIRING_SOON = "ProposalExpiringSoon"
PROPOSAL_PAYMENT_READY = "ProposalPaymentReady"
PROPOSAL_CONVERTED = "ProposalConverted"


def notify_event(
    *,
    proposal,
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
    from datetime import date

    log, created = OLProposalNotificationLog.objects.get_or_create(
        proposal=proposal,
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


def notify_payment_ready(*, proposal, actor=None, source_channel="API"):
    return notify_event(
        proposal=proposal,
        event_type=PROPOSAL_PAYMENT_READY,
        payload={"proposal_number": proposal.proposal_number, "status": proposal.status},
        source_channel=source_channel,
    )


def notify_converted(*, proposal, actor=None, source_channel="API"):
    return notify_event(
        proposal=proposal,
        event_type=PROPOSAL_CONVERTED,
        payload={"proposal_number": proposal.proposal_number, "status": proposal.status},
        source_channel=source_channel,
    )


def notify_expiring_soon(*, proposal, dispatch_on=None, source_channel="SYSTEM"):
    return notify_event(
        proposal=proposal,
        event_type=PROPOSAL_EXPIRING_SOON,
        dispatch_on=dispatch_on,
        payload={"proposal_number": proposal.proposal_number, "expiry_date": str(proposal.expiry_date or "")},
        recipient_type=NotificationRecipientType.STAFF,
        source_channel=source_channel,
    )


def expiring_soon_candidates(*, as_of=None, window_days=7):
    """Proposals expiring within the next N days that are not terminal."""
    from datetime import date, timedelta

    from apps.ol_proposals.models import OLProposal
    from apps.ol_proposals.services.parameter_resolver import terminal_proposal_statuses

    day = as_of or date.today()
    terminal = set(terminal_proposal_statuses() or ("CANCELLED", "EXPIRED", "CONVERTED"))
    return OLProposal.objects.filter(
        expiry_date__isnull=False,
        expiry_date__gt=day,
        expiry_date__lte=day + timedelta(days=window_days),
    ).exclude(status__in=terminal)