"""Installment lifecycle service: missed detection, payment reversal, and plan cancellation.

Missed detection flags overdue installments for the daily batch; reversal
undoes a paid installment through the Front Office seam; cancellation closes an
unpaid plan. Every financial state change is audited with actor, before/after,
reason, and source channel.
"""

from dataclasses import dataclass, field
from datetime import date

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.front_office.models import FORequisition
from apps.governance.services.audit_service import AuditService
from apps.system_parameters.services.config_service import ConfigurationService
from apps.users.models import User

from ..errors import registry_error
from ..events import emit_installment_payment_missed
from ..models import (
    InstallmentItemStatus,
    InstallmentPlanStatus,
    OLInstallmentItem,
    OLMaturityInstallmentPlan,
)

REVERSAL_WINDOW_PARAMETER = "INSTALLMENT_REVERSAL_WINDOW_DAYS"
IRREVOCABLE_PARAMETER = "INSTALLMENT_PAYMENT_IRREVOCABLE"

MISSED_CANDIDATE_STATUSES = (InstallmentItemStatus.SCHEDULED, InstallmentItemStatus.PAYMENT_PENDING)
CANCELABLE_PLAN_STATUSES = (InstallmentPlanStatus.CREATED, InstallmentPlanStatus.ACTIVE)
TERMINAL_ITEM_STATUSES = (InstallmentItemStatus.PAID, InstallmentItemStatus.WAIVED)

SYSTEM_USERNAME = "system"
SYSTEM_EMAIL = "system@zic.local"


def system_actor():
    actor, _created = User.objects.get_or_create(
        username=SYSTEM_USERNAME,
        defaults={
            "email": SYSTEM_EMAIL,
            "first_name": "ZIC",
            "last_name": "System",
            "user_type": "SYSTEM_MANAGER",
            "status": User.AccountStatus.ACTIVE,
            "is_active": True,
            "is_approved": True,
        },
    )
    return actor


def _day(value):
    if value is None:
        return timezone.localdate()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError):
        raise registry_error(
            "INSTALLMENT_INVALID_FILTER",
            message="The as-of date must use YYYY-MM-DD format.",
            field_errors={"as_of": ["Use a valid date such as 2026-08-31."]},
        ) from None


def _requisition_for(item):
    if not item.payment_requisition_ref_id:
        return None
    return FORequisition.objects.filter(pk=item.payment_requisition_ref_id).first()


def _missed_snapshot(item):
    return {
        "installment_number": item.installment_number,
        "status": item.status,
        "due_date": str(item.due_date),
        "amount": str(item.amount),
        "missed_date": str(item.missed_date) if item.missed_date else "",
    }


def _reversal_snapshot(item, requisition=None):
    return {
        "installment_number": item.installment_number,
        "status": item.status,
        "due_date": str(item.due_date),
        "amount": str(item.amount),
        "requisition_number": getattr(requisition, "requisition_number", "") if requisition else "",
        "requisition_status": getattr(requisition, "status", "") if requisition else "",
        "paid_date": str(item.paid_date) if item.paid_date else "",
        "payment_reference": item.payment_reference or "",
    }


def _waive_snapshot(item, requisition=None):
    return {
        "installment_number": item.installment_number,
        "status": item.status,
        "due_date": str(item.due_date),
        "amount": str(item.amount),
        "requisition_number": getattr(requisition, "requisition_number", "") if requisition else "",
        "requisition_status": getattr(requisition, "status", "") if requisition else "",
        "paid_date": str(item.paid_date) if item.paid_date else "",
        "missed_date": str(item.missed_date) if item.missed_date else "",
        "waived_date": str(item.waived_date) if item.waived_date else "",
    }


def _plan_snapshot(plan):
    return {
        "plan_number": plan.plan_number,
        "status": plan.status,
        "start_date": str(plan.start_date),
        "end_date": str(plan.end_date),
        "total_payable_amount": str(plan.total_payable_amount),
        "paid_item_count": plan.items.filter(status=InstallmentItemStatus.PAID).count(),
        "waived_item_count": plan.items.filter(status=InstallmentItemStatus.WAIVED).count(),
        "cancelled_at": str(plan.cancelled_at) if plan.cancelled_at else "",
    }


@dataclass
class MissedDetectionResult:
    processed: int = 0
    missed: int = 0
    skipped: int = 0
    errors: list = field(default_factory=list)


@transaction.atomic
def detect_missed_installments(
    *,
    as_of=None,
    plan_id=None,
    correlation_id="",
    actor=None,
    source_channel="SYSTEM",
):
    """Mark installments past their due date as MISSED for a daily batch.

    Idempotent: only SCHEDULED/PAYMENT_PENDING items with ``due_date < as_of``
    are touched, so re-runs are safe. Returns a ``MissedDetectionResult``.
    """
    day = _day(as_of)
    result = MissedDetectionResult()
    candidates = (
        OLInstallmentItem.objects.filter(status__in=MISSED_CANDIDATE_STATUSES)
        .order_by("plan_ref_id", "installment_number")
        .select_related("plan_ref", "plan_ref__policy_ref")
    )
    if plan_id:
        candidates = candidates.filter(plan_ref_id=plan_id)

    for candidate in candidates:
        result.processed += 1
        if candidate.due_date and candidate.due_date >= day:
            result.skipped += 1
            continue
        item = (
            OLInstallmentItem.objects.select_for_update()
            .select_related("plan_ref", "plan_ref__policy_ref")
            .filter(pk=candidate.pk)
            .first()
        )
        if item is None or item.status not in MISSED_CANDIDATE_STATUSES:
            result.skipped += 1
            continue
        if item.due_date and item.due_date >= day:
            result.skipped += 1
            continue

        before = _missed_snapshot(item)
        item.status = InstallmentItemStatus.MISSED
        item.missed_date = day
        item.updated_by = actor
        item.save(update_fields=["status", "missed_date", "updated_by", "updated_at"])
        after = _missed_snapshot(item)
        reason = (
            f"Installment {item.installment_number} on plan {item.plan_ref.plan_number} "
            f"was due on {item.due_date} and was missed as of {day}."
        )
        emit_installment_payment_missed(
            item.plan_ref,
            item=item,
            actor=actor,
            from_status=before["status"],
            to_status=item.status,
            reason=reason,
            source_channel=source_channel,
            metadata={
                "policy_number": item.plan_ref.policy_ref.policy_number,
                "installment_number": item.installment_number,
                "due_date": str(item.due_date),
                "amount": str(item.amount),
                "as_of": day.isoformat(),
                "correlation_id": correlation_id,
            },
        )
        AuditService.log_action(
            "INSTALLMENT_PAYMENT_MISSED",
            item,
            actor=actor,
            before_state=before,
            after_state=after,
            changed_fields=["status", "missed_date"],
            reason=reason,
            source_channel=source_channel,
        )
        result.missed += 1

    AuditService.log(
        "INSTALLMENT_MISSED_DETECTION_BATCH",
        "ol_maturity_installments.misseddetectionbatch",
        None,
        entity_repr=correlation_id or "OL maturity installment missed detection batch",
        description="OL maturity installment missed detection batch completed.",
        actor=actor,
        action="INSTALLMENT_MISSED_DETECTION_BATCH",
        app_label="ol_maturity_installments",
        model_name="misseddetectionbatch",
        object_repr=correlation_id or "OL maturity installment missed detection batch",
        reason="Daily OL maturity installment missed detection batch.",
        source_channel=source_channel,
        request_id=correlation_id,
        after_state={
            "as_of": day.isoformat(),
            "processed": result.processed,
            "missed": result.missed,
            "skipped": result.skipped,
            "errors": len(result.errors),
            "correlation_id": correlation_id,
        },
    )
    return result


@transaction.atomic
def reverse_item_payment(
    *,
    item_id,
    reason,
    actor=None,
    source_channel="API",
    request=None,
):
    """Reverse a paid installment within the configured reversal window.

    The Front Office requisition is marked REVERSED and the item returns to
    SCHEDULED (or MISSED when its due date has passed). Returns
    ``(item, requisition)``.
    """
    reason = (reason or "").strip()
    if not reason:
        raise registry_error("INSTALLMENT_REVERSAL_REASON_REQUIRED")

    item = (
        OLInstallmentItem.objects.select_for_update()
        .select_related("plan_ref", "plan_ref__policy_ref", "payment_requisition_ref")
        .filter(pk=item_id)
        .first()
    )
    if item is None:
        raise registry_error("INSTALLMENT_ITEM_NOT_FOUND", details={"item_id": str(item_id)})

    if item.status != InstallmentItemStatus.PAID:
        raise registry_error(
            "INSTALLMENT_REVERSAL_NOT_ALLOWED",
            details={
                "installment_number": item.installment_number,
                "current_status": item.status,
                "message": "An installment can only be reversed while it is paid; a reversed installment is no longer paid.",
            },
        )

    today = timezone.localdate()
    window_days = ConfigurationService.get_int_parameter(REVERSAL_WINDOW_PARAMETER, default=7)
    if item.paid_date and window_days is not None and (today - item.paid_date).days > window_days:
        raise registry_error(
            "INSTALLMENT_REVERSAL_WINDOW_EXPIRED",
            details={
                "installment_number": item.installment_number,
                "paid_date": str(item.paid_date),
                "window_days": window_days,
                "days_since_paid": (today - item.paid_date).days,
            },
        )

    plan = OLMaturityInstallmentPlan.objects.select_for_update().get(pk=item.plan_ref_id)
    requisition = _requisition_for(item)
    before = _reversal_snapshot(item, requisition)

    if requisition:
        requisition.status = "REVERSED"
        requisition.save(update_fields=["status", "updated_at"])

    item.status = (
        InstallmentItemStatus.MISSED if (item.due_date and item.due_date < today) else InstallmentItemStatus.SCHEDULED
    )
    item.paid_date = None
    item.paid_by = None
    item.payment_reference = ""
    item.payment_requisition_ref = None
    item.updated_by = actor
    item.save(
        update_fields=[
            "status",
            "paid_date",
            "paid_by",
            "payment_reference",
            "payment_requisition_ref",
            "updated_by",
            "updated_at",
        ]
    )

    after = _reversal_snapshot(item, requisition)
    full_reason = f"Installment {item.installment_number} payment reversed: {reason}"
    AuditService.log(
        action_type="INSTALLMENT_PAYMENT_REVERSED",
        entity_type="ol_maturity_installments.olinstallmentitem",
        entity_id=item.pk,
        entity_repr=f"{plan.plan_number}: installment {item.installment_number}",
        before_state=before,
        after_state=after,
        description=(
            f"Payment for installment {item.installment_number} reversed"
            f"{f' against requisition {requisition.requisition_number}' if requisition else ''}; item restored to {item.status}."
        ),
        actor=actor,
        reason=full_reason,
        source_channel=source_channel,
        request=request,
        app_label="ol_maturity_installments",
        model_name="olinstallmentitem",
        object_id=str(item.pk),
        object_repr=f"{plan.plan_number}: installment {item.installment_number}",
    )
    return item, requisition


@transaction.atomic
def cancel_installment_plan(
    *,
    plan_id,
    reason,
    actor=None,
    source_channel="API",
    request=None,
):
    """Cancel an unpaid maturity installment plan.

    The plan moves to CANCELLED, remaining payable installments are waived, and
    any still-pending disbursement requisitions are cancelled. Returns the plan.
    """
    reason = (reason or "").strip()
    if not reason:
        raise registry_error("INSTALLMENT_CANCELLATION_REASON_REQUIRED")

    plan = OLMaturityInstallmentPlan.objects.select_for_update().filter(pk=plan_id).first()
    if plan is None:
        raise registry_error("INSTALLMENT_PLAN_NOT_FOUND", details={"plan_id": str(plan_id)})

    if plan.status not in CANCELABLE_PLAN_STATUSES:
        raise registry_error(
            "INSTALLMENT_PLAN_CANNOT_CANCEL",
            details={
                "plan_number": plan.plan_number,
                "current_status": plan.status,
                "message": "A completed, terminated, or cancelled plan is terminal and cannot be cancelled.",
            },
        )

    paid_count = plan.items.filter(status=InstallmentItemStatus.PAID).count()
    if paid_count >= plan.installment_count:
        raise registry_error(
            "INSTALLMENT_PLAN_CANNOT_CANCEL",
            details={
                "plan_number": plan.plan_number,
                "paid_item_count": paid_count,
                "installment_count": plan.installment_count,
                "message": "A fully paid plan cannot be cancelled.",
            },
        )
    if paid_count > 0 and ConfigurationService.get_bool_parameter(IRREVOCABLE_PARAMETER, default=False):
        raise registry_error(
            "INSTALLMENT_PLAN_IRREVOCABLE",
            details={
                "plan_number": plan.plan_number,
                "paid_item_count": paid_count,
                "message": "Paid installments are irrevocable under the configured parameters.",
            },
        )

    before = _plan_snapshot(plan)
    today = timezone.localdate()
    plan.status = InstallmentPlanStatus.CANCELLED
    plan.cancelled_at = timezone.now()
    plan.cancelled_by = actor
    plan.save(update_fields=["status", "cancelled_at", "cancelled_by", "updated_at"])

    waived = []
    for item in (
        plan.items.select_for_update().filter(~Q(status__in=TERMINAL_ITEM_STATUSES)).order_by("installment_number")
    ):
        requisition = _requisition_for(item)
        if requisition and requisition.status == "PENDING":
            requisition.status = "CANCELLED"
            requisition.save(update_fields=["status", "updated_at"])
        item_before = _waive_snapshot(item, requisition)
        item.status = InstallmentItemStatus.WAIVED
        item.waived_date = today
        item.updated_by = actor
        item.save(update_fields=["status", "waived_date", "updated_by", "updated_at"])
        item_after = _waive_snapshot(item, requisition)
        AuditService.log_action(
            "INSTALLMENT_ITEM_WAIVED",
            item,
            actor=actor,
            request=request,
            before_state=item_before,
            after_state=item_after,
            changed_fields=["status", "waived_date"],
            reason=f"Plan {plan.plan_number} cancelled: {reason}",
            source_channel=source_channel,
        )
        waived.append(item.installment_number)

    after = _plan_snapshot(plan)
    full_reason = f"Plan {plan.plan_number} cancelled: {reason}"
    AuditService.log_action(
        "INSTALLMENT_PLAN_CANCELLED",
        plan,
        actor=actor,
        request=request,
        before_state=before,
        after_state={**after, "waived_installments": waived},
        changed_fields=["status", "cancelled_at", "cancelled_by"],
        reason=full_reason,
        source_channel=source_channel,
    )
    return plan
