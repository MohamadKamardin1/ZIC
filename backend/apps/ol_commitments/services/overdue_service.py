"""Batch overdue processing for OL Commitments.

Safe, idempotent, and audited: marks commitments past their grace date as
``OVERDUE`` (parameter code), flags lapse reviews exactly once via
``lapse_review_flag``, and creates one notification-log row per applicable
``OLGracePeriodNotificationSchedule`` entry (unique constraint prevents
duplicates on re-runs). Every material change is written through the module
audit receivers with the batch source channel.
"""

from dataclasses import dataclass
from datetime import timedelta

from django.utils import timezone

from apps.governance.services.audit_service import AuditService
from apps.ol_commitments.events import emit_overdue
from apps.ol_commitments.models import (
    CommitmentSourceChannel,
    OLCommitment,
    OLCommitmentNotificationLog,
)
from apps.ol_commitments.services.parameter_resolver import compute_grace_envelope
from apps.ol_parameters.models import OLCommitmentStatus, OLGracePeriodNotificationSchedule


@dataclass
class OverdueRunResult:
    processed: int = 0
    overdue: int = 0
    notified: int = 0
    lapse_reviews: int = 0


def _overdue_status_code():
    status = (
        OLCommitmentStatus.objects.filter(is_active=True, code__icontains="OVERDUE")
        .order_by("display_order", "code")
        .first()
    )
    return status.code if status else None


def _terminal_statuses():
    return list(
        OLCommitmentStatus.objects.filter(is_active=True, is_terminal=True).values_list("code", flat=True)
    )


def _notification_rows(commitment, today):
    """Create overdue notification log rows per active schedule; returns created count."""
    created = 0
    schedules = OLGracePeriodNotificationSchedule.objects.filter(is_active=True)
    for schedule in schedules:
        dispatch_on = commitment.due_date + timedelta(days=schedule.days_offset)
        if dispatch_on > today:
            continue
        defaults = {
            "template_code": schedule.template_code or "",
            "recipient_type": schedule.recipient_type,
            "status": "PENDING",
            "payload": {"commitment": commitment.commitment_number},
        }
        _, was_created = OLCommitmentNotificationLog.objects.get_or_create(
            commitment=commitment,
            event_type=schedule.event_type,
            dispatch_on=dispatch_on,
            notification_channel=schedule.notification_channel,
            recipient_type=schedule.recipient_type,
            defaults=defaults,
        )
        if was_created:
            created += 1
    return created


def run_overdue_processing(
    *,
    actor=None,
    source_channel=CommitmentSourceChannel.BATCH,
    as_of=None,
):
    """Process overdue commitments idempotently and return run counts."""
    today = as_of or timezone.localdate()
    result = OverdueRunResult()
    overdue_code = _overdue_status_code()
    terminals = set(_terminal_statuses())

    candidates = OLCommitment.objects.filter(
        due_date__lt=today,
    ).exclude(status__in=terminals)

    for commitment in candidates.iterator():
        before = AuditService.snapshot(commitment)
        envelope = compute_grace_envelope(
            commitment.due_date,
            product=commitment.product,
            plan=commitment.plan,
            premium_frequency=commitment.premium_frequency,
            as_of=today,
        )
        if envelope.grace_date is None:
            # Missing OL Grace Period parameters — skip rather than guess.
            continue

        changed = False
        move_to_overdue = (
            (commitment.balance or 0) > 0
            and today > envelope.grace_date
            and commitment.status != overdue_code
        )
        if move_to_overdue and overdue_code:
            commitment.status = overdue_code
            commitment.reason_code = "OVERDUE"
            commitment.reason_text = f"Marked overdue {commitment.due_date} (grace {envelope.grace_date})."
            result.overdue += 1
            changed = True

        if today > envelope.lapse_date and not commitment.lapse_review_flag:
            commitment.lapse_review_flag = True
            result.lapse_reviews += 1
            changed = True

        if changed:
            commitment.save()
            AuditService.log_action(
                "MARK_OVERDUE",
                commitment,
                actor=actor,
                before_state=before,
                after_state=AuditService.snapshot(commitment),
                reason=commitment.reason_text or "Overdue batch processing.",
                source_channel=source_channel,
            )
            emit_overdue(
                commitment,
                actor=actor,
                from_status=before.get("status") or commitment.status,
                reason=commitment.reason_text or "Overdue batch processing.",
                source_channel=source_channel,
                metadata={"lapsed": commitment.lapse_review_flag},
            )

        result.processed += 1
        result.notified += _notification_rows(commitment, today)

    return result


def lapse_review_rows():
    """Commitments past their lapse date that still need a policy-level review."""
    rows = []
    for commitment in OLCommitment.objects.filter(lapse_review_flag=True).order_by("due_date"):
        rows.append(
            {
                "id": commitment.pk,
                "commitment_number": commitment.commitment_number,
                "source_reference": commitment.source_reference or "",
                "partner_name": commitment.partner_name_snapshot or "",
                "product_name": commitment.product_name_snapshot or "",
                "plan_name": commitment.plan_name_snapshot or "",
                "policy_reference": commitment.source_reference or "",
                "due_date": commitment.due_date,
                "lapse_date": commitment.lapse_date,
                "status": commitment.status,
                "recommended_action": (
                    "Initiate policy lapse review and schedule reinstatement window"
                    if commitment.balance and commitment.balance > 0
                    else "Close as fully recovered or completed"
                ),
            }
        )
    return rows