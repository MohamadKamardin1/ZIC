from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.db import transaction
from django.utils import timezone

from apps.governance.services.audit_service import AuditService
from apps.users.models import User

from ..errors import LoanError, loan_not_found
from ..events import emit_loan_defaulted, emit_loan_offset
from ..models import LoanOffsetSourceType, LoanScheduleStatus, LoanStatus, OLLoan, OLLoanOffset, OLLoanSchedule
from .parameter_resolver import get_loan_config


MONEY_PLACES = Decimal("0.01")
ZERO = Decimal("0.00")
DEFAULT_SYSTEM_USERNAME = "system"
DEFAULT_SYSTEM_EMAIL = "system@zic.local"


@dataclass
class DefaultDetectionResult:
    processed: int = 0
    defaulted: int = 0
    skipped: int = 0
    errors: list = field(default_factory=list)


@dataclass(frozen=True)
class OffsetResult:
    loan: OLLoan
    offset: OLLoanOffset
    created: bool


def system_actor():
    actor, _created = User.objects.get_or_create(
        username=DEFAULT_SYSTEM_USERNAME,
        defaults={
            "email": DEFAULT_SYSTEM_EMAIL,
            "first_name": "ZIC",
            "last_name": "System",
            "user_type": "SYSTEM_MANAGER",
            "status": User.AccountStatus.ACTIVE,
            "is_active": True,
            "is_approved": True,
        },
    )
    return actor


def _money(value):
    return Decimal(str(value or "0")).quantize(MONEY_PLACES, rounding=ROUND_HALF_UP)


def _decimal(value, field_name):
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise LoanError(
            f"The {field_name.replace('_', ' ')} must be a valid monetary amount.",
            error_code="LOAN_OFFSET_INVALID",
            status_code=422,
            field_errors={field_name: ["Enter a numeric amount using digits and a decimal point."]},
            resolution_steps=[
                f"Enter a valid {field_name.replace('_', ' ')}.",
                "Do not include currency symbols or thousands separators.",
                "Submit the lifecycle action again after correcting the amount.",
            ],
        ) from None


def _day(value):
    if value is None:
        return timezone.localdate()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError):
        raise LoanError(
            "The as-of date must use YYYY-MM-DD format.",
            error_code="LOAN_INELIGIBLE",
            status_code=422,
            field_errors={"as_of": ["Use a valid date such as 2026-08-27."]},
            resolution_steps=[
                "Enter the processing date in YYYY-MM-DD format.",
                "Use a date on or after the overdue installment due date.",
                "Retry the lifecycle action after correcting the date.",
            ],
        ) from None


def _defaultable_schedule(loan, *, as_of, grace_days, penalty_period_days):
    threshold_days = max(0, int(grace_days)) + max(0, int(penalty_period_days))
    statuses = {
        LoanScheduleStatus.PENDING,
        LoanScheduleStatus.PARTIALLY_PAID,
        LoanScheduleStatus.OVERDUE,
    }
    eligible = []
    for schedule in loan.schedules.filter(status__in=statuses).order_by("due_date", "installment_number"):
        if schedule.balance <= ZERO or schedule.due_date >= as_of:
            continue
        overdue_days = (as_of - schedule.due_date).days
        if overdue_days > threshold_days:
            eligible.append((schedule, overdue_days, threshold_days))
    return eligible


@transaction.atomic
def detect_loan_defaults(*, as_of=None, actor=None, source_channel="BATCH", correlation_id="", loan_id=None):
    day = _day(as_of)
    result = DefaultDetectionResult()
    candidates = OLLoan.objects.filter(status__in={LoanStatus.ACTIVE, LoanStatus.PARTIALLY_REPAID}).order_by("loan_number")
    if loan_id:
        candidates = candidates.filter(pk=loan_id)

    for candidate in candidates:
        result.processed += 1
        loan = (
            OLLoan.objects.select_for_update()
            .select_related("policy_ref", "partner")
            .filter(pk=candidate.pk)
            .first()
        )
        if loan is None:
            result.skipped += 1
            continue
        try:
            config = get_loan_config(
                loan.policy_ref,
                as_of=day,
                actor=actor,
                source_channel=source_channel,
            )
            overdue = _defaultable_schedule(
                loan,
                as_of=day,
                grace_days=config.grace_days,
                penalty_period_days=config.penalty_period_days,
            )
        except LoanError as exc:
            result.errors.append(
                {
                    "loan_id": str(loan.pk),
                    "loan_number": loan.loan_number,
                    "error_code": exc.error_code,
                    "message": str(exc),
                }
            )
            result.skipped += 1
            continue
        if not overdue:
            result.skipped += 1
            continue

        before = AuditService.snapshot(loan)
        loan.status = LoanStatus.DEFAULTED
        loan.updated_by = actor
        loan.save(update_fields=["status", "updated_by", "updated_at"])
        max_overdue_days = max(item[1] for item in overdue)
        max_threshold_days = max(item[2] for item in overdue)
        schedule_numbers = [item[0].installment_number for item in overdue]
        reason = (
            f"Loan {loan.loan_number} defaulted after installment(s) {', '.join(map(str, schedule_numbers))} "
            f"exceeded the configured grace and penalty period ({max_threshold_days} days)."
        )
        after = AuditService.snapshot(loan)
        after.update(
            {
                "as_of": day.isoformat(),
                "overdue_schedule_numbers": schedule_numbers,
                "max_overdue_days": max_overdue_days,
                "threshold_days": max_threshold_days,
                "correlation_id": correlation_id,
            }
        )
        AuditService.log_action(
            "LOAN_DEFAULTED",
            loan,
            actor=actor,
            before_state=before,
            after_state=after,
            changed_fields=["status"],
            reason=reason,
            source_channel=source_channel,
        )
        emit_loan_defaulted(
            loan,
            actor=actor,
            from_status=before.get("status", ""),
            reason=reason,
            source_channel=source_channel,
            payload_extra={
                "as_of": day.isoformat(),
                "overdue_schedule_numbers": schedule_numbers,
                "max_overdue_days": max_overdue_days,
                "threshold_days": max_threshold_days,
                "correlation_id": correlation_id,
            },
        )
        result.defaulted += 1

    AuditService.log(
        "LOAN_DEFAULT_DETECTION_BATCH",
        "ol_loans.default_detection_batch",
        None,
        entity_repr=correlation_id or "OL loan default detection batch",
        description="OL Loan default detection batch completed.",
        actor=actor,
        action="LOAN_DEFAULT_DETECTION_BATCH",
        app_label="ol_loans",
        model_name="defaultdetectionbatch",
        object_repr=correlation_id or "OL loan default detection batch",
        reason="Daily OL Loan default detection batch.",
        source_channel=source_channel,
        request_id=correlation_id,
        after_state={
            "as_of": day.isoformat(),
            "processed": result.processed,
            "defaulted": result.defaulted,
            "skipped": result.skipped,
            "errors": len(result.errors),
            "correlation_id": correlation_id,
        },
    )
    return result


def _offset_source(value):
    source = str(value or "").strip().upper()
    if source not in {choice for choice, _label in LoanOffsetSourceType.choices}:
        raise LoanError(
            "Offset source must be SURRENDER, MATURITY, or CLAIM.",
            error_code="LOAN_OFFSET_INVALID",
            status_code=422,
            field_errors={"source_type": ["Choose SURRENDER, MATURITY, or CLAIM."]},
            resolution_steps=[
                "Use the payout lifecycle source that created the deduction.",
                "Provide the source transaction's human-readable reference.",
                "Retry the offset with the corrected source type.",
            ],
        )
    return source


def _offset_status(source_type):
    return {
        LoanOffsetSourceType.SURRENDER: LoanStatus.OFFSET_ON_SURRENDER,
        LoanOffsetSourceType.MATURITY: LoanStatus.OFFSET_ON_MATURITY,
        LoanOffsetSourceType.CLAIM: LoanStatus.OFFSET_ON_CLAIM,
    }[source_type]


@transaction.atomic
def process_loan_offset(
    loan,
    source_type,
    source_id,
    payout_amount,
    *,
    actor=None,
    request=None,
    source_channel="API",
    reason="",
):
    loan_id = getattr(loan, "pk", loan)
    locked_loan = (
        OLLoan.objects.select_for_update()
        .select_related("policy_ref", "partner")
        .filter(pk=loan_id)
        .first()
    )
    if locked_loan is None:
        raise loan_not_found(str(loan_id))
    source = _offset_source(source_type)
    reference = str(source_id or "").strip()
    if not reference:
        raise LoanError(
            "A payout source reference is required to reconcile a loan offset.",
            error_code="LOAN_OFFSET_INVALID",
            status_code=422,
            field_errors={"source_id": ["Enter the surrender, maturity, or claim reference."]},
            resolution_steps=[
                "Copy the human-readable source transaction number.",
                "Use the same reference on retries so the offset remains idempotent.",
                "Retry the payout offset after entering the source reference.",
            ],
        )
    payout = _money(_decimal(payout_amount, "payout_amount"))
    if payout <= ZERO:
        raise LoanError(
            "Payout amount must be greater than zero.",
            error_code="LOAN_OFFSET_INVALID",
            status_code=422,
            field_errors={"payout_amount": ["Enter a payout amount greater than zero."]},
            resolution_steps=[
                "Confirm the source payout has a positive gross amount.",
                "Enter the amount in the loan currency.",
                "Retry the offset after correcting the payout amount.",
            ],
        )

    existing = OLLoanOffset.objects.filter(
        loan=locked_loan,
        source_type=source,
        source_id=reference,
    ).first()
    if existing:
        return OffsetResult(
            loan=locked_loan,
            offset=existing,
            created=False,
        )
    if locked_loan.status in {LoanStatus.SETTLED, LoanStatus.CLOSED}:
        raise LoanError(
            f"Loan {locked_loan.loan_number} is already {locked_loan.get_status_display()} and cannot be offset.",
            error_code="LOAN_OFFSET_INVALID",
            status_code=409,
            field_errors={"status": ["Settled and closed loans cannot receive another payout offset."]},
            resolution_steps=[
                "Confirm that the source payout belongs to an unsettled loan.",
                "Review the existing repayment and offset history before retrying.",
                "Do not reverse a settled offset through this endpoint; use the approved correction workflow.",
            ],
        )
    outstanding = _money(locked_loan.outstanding_balance)
    if outstanding <= ZERO:
        raise LoanError(
            f"Loan {locked_loan.loan_number} has no outstanding balance to offset.",
            error_code="LOAN_OFFSET_INVALID",
            status_code=409,
            field_errors={"outstanding_balance": ["The loan balance is already zero."]},
            resolution_steps=[
                "Review the loan repayment and interest history.",
                "Confirm the payout source is linked to the correct loan.",
                "Use a financial correction workflow if the balance is incorrect.",
            ],
        )

    offset_amount = _money(min(outstanding, payout))
    remaining_payout = _money(payout - offset_amount)
    before = AuditService.snapshot(locked_loan)
    locked_loan.outstanding_balance = _money(outstanding - offset_amount)
    locked_loan.status = LoanStatus.CLOSED if locked_loan.outstanding_balance <= ZERO else _offset_status(source)
    locked_loan.updated_by = actor
    locked_loan.save(update_fields=["outstanding_balance", "status", "updated_by", "updated_at"])
    resolved_reason = str(reason or f"Loan {locked_loan.loan_number} offset against {source.lower()} {reference}.").strip()
    offset = OLLoanOffset(
        loan=locked_loan,
        source_type=source,
        source_id=reference,
        offset_amount=offset_amount,
        remaining_payout=remaining_payout,
        reason=resolved_reason,
        source_channel=source_channel,
        created_by=actor,
        updated_by=actor,
    )
    offset.full_clean()
    offset.save()
    after = AuditService.snapshot(locked_loan)
    after.update(
        {
            "offset_id": str(offset.pk),
            "source_type": source,
            "source_id": reference,
            "payout_amount": str(payout),
            "offset_amount": str(offset_amount),
            "remaining_payout": str(remaining_payout),
        }
    )
    AuditService.log_action(
        "LOAN_OFFSET",
        locked_loan,
        actor=actor,
        request=request,
        before_state=before,
        after_state=after,
        changed_fields=["outstanding_balance", "status"],
        reason=resolved_reason,
        source_channel=source_channel,
    )
    emit_loan_offset(
        locked_loan,
        actor=actor,
        from_status=before.get("status", ""),
        reason=resolved_reason,
        source_channel=source_channel,
        payload_extra={
            "offset_id": str(offset.pk),
            "source_type": source,
            "source_id": reference,
            "payout_amount": str(payout),
            "offset_amount": str(offset_amount),
            "remaining_payout": str(remaining_payout),
        },
    )
    return OffsetResult(loan=locked_loan, offset=offset, created=True)
