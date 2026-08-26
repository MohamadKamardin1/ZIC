from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.db import transaction

from apps.governance.services.audit_service import AuditService

from ..errors import LoanError, loan_not_found
from ..events import emit_loan_interest_accrued
from ..models import LoanScheduleStatus, LoanStatus, OLLoan, OLLoanInterestAccrual, OLLoanSchedule
from .parameter_resolver import LoanConfig, get_loan_config


MONEY_PLACES = Decimal("0.01")
PERCENT = Decimal("100")


@dataclass(frozen=True)
class AccrualResult:
    loan: OLLoan
    accrual: OLLoanInterestAccrual
    created: bool


def _money(value):
    return Decimal(str(value or "0")).quantize(MONEY_PLACES, rounding=ROUND_HALF_UP)


def _decimal(value, field_name):
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise LoanError(
            f"The configured {field_name.replace('_', ' ')} is not a valid decimal value.",
            error_code="LOAN_DISBURSEMENT_FAILED",
            status_code=422,
            field_errors={field_name: ["Correct the configured numeric value before accruing interest."]},
            resolution_steps=[
                "Open Ordinary Life Parameters > Loan Interest Control.",
                f"Correct the {field_name.replace('_', ' ')} value using a valid decimal number.",
                "Run the accrual period again after saving the effective configuration.",
            ],
        ) from None


def _period(value, field_name):
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError):
        raise LoanError(
            f"The accrual {field_name.replace('_', ' ')} must use YYYY-MM-DD format.",
            error_code="LOAN_INELIGIBLE",
            status_code=422,
            field_errors={field_name: ["Use a valid date such as 2026-08-27."]},
            resolution_steps=[
                "Enter the accrual period using YYYY-MM-DD dates.",
                "Ensure period end is on or after period start.",
                "Run the accrual again after correcting the dates.",
            ],
        ) from None


def _periods_per_year(compounding_frequency):
    return {
        "DAILY": Decimal("365"),
        "MONTHLY": Decimal("12"),
        "QUARTERLY": Decimal("4"),
        "SEMI_ANNUAL": Decimal("2"),
        "ANNUAL": Decimal("1"),
    }.get(str(compounding_frequency or "").strip().upper(), Decimal("1"))


def _day_denominator(config: LoanConfig):
    return Decimal("360") if config.interest_calculation_basis == "ACTUAL_360" else Decimal("365")


def calculate_interest(principal_base, annual_rate, days, config: LoanConfig):
    """Calculate unrounded interest for an exact period using the effective control."""
    if days <= 0 or principal_base <= 0 or annual_rate <= 0:
        return Decimal("0")
    rate = annual_rate / PERCENT
    denominator = _day_denominator(config)
    if config.interest_calculation_basis in {"SIMPLE", "ACTUAL_365", "ACTUAL_360"}:
        return principal_base * rate * Decimal(days) / denominator

    periods = _periods_per_year(config.compounding_frequency)
    periodic_rate = rate / periods
    elapsed_periods = Decimal(days) * periods / denominator
    return principal_base * ((Decimal("1") + periodic_rate) ** elapsed_periods - Decimal("1"))


def _previous_principal_paid(loan):
    principal_paid = Decimal("0")
    for repayment in loan.repayments.all():
        breakdown = repayment.allocation_breakdown if isinstance(repayment.allocation_breakdown, dict) else {}
        value = breakdown.get("principal") or breakdown.get("principal_paid") or breakdown.get("principal_component") or 0
        try:
            principal_paid += Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            continue
    return max(Decimal("0"), _decimal(loan.disbursed_amount, "disbursed_amount") - principal_paid)


def _principal_base(loan, config):
    if config.capitalize_interest:
        return max(Decimal("0"), _decimal(loan.outstanding_balance, "outstanding_balance"))
    return _previous_principal_paid(loan)


def _penalty_for_period(loan, config, period_start, period_end):
    rate = _decimal(config.penalty_rate, "penalty_rate")
    if rate <= 0:
        return Decimal("0")
    overdue_statuses = {
        LoanScheduleStatus.PENDING,
        LoanScheduleStatus.PARTIALLY_PAID,
        LoanScheduleStatus.OVERDUE,
    }
    penalty = Decimal("0")
    schedules = OLLoanSchedule.objects.filter(loan=loan, status__in=overdue_statuses).order_by("due_date", "installment_number")
    grace = timedelta(days=max(0, int(config.grace_days)))
    for schedule in schedules:
        overdue_from = schedule.due_date + grace
        if overdue_from >= period_end:
            continue
        penalty_start = max(period_start, overdue_from)
        overdue_days = (period_end - penalty_start).days
        if overdue_days <= 0:
            continue
        due_remaining = max(
            Decimal("0"),
            _decimal(schedule.principal_due, "principal_due")
            + _decimal(schedule.interest_due, "interest_due")
            + _decimal(schedule.penalty_due, "penalty_due")
            - _decimal(schedule.amount_paid, "amount_paid"),
        )
        penalty += due_remaining * rate / PERCENT * Decimal(overdue_days) / _day_denominator(config)
    return penalty


def _invalid_status(loan):
    raise LoanError(
        f"Loan {loan.loan_number} cannot accrue interest from status {loan.get_status_display()}.",
        error_code="LOAN_INVALID_STATUS",
        status_code=409,
        field_errors={"status": ["Only an Active loan can receive an interest accrual."]},
        resolution_steps=[
            "Confirm that the loan is Active and has a valid disbursement schedule.",
            "Do not accrue interest on Settled or Closed loans.",
            "Retry the period after the loan lifecycle status is corrected.",
        ],
        details={"loan_number": loan.loan_number, "current_status": loan.status, "required_status": LoanStatus.ACTIVE},
    )


@transaction.atomic
def accrue_loan_interest(
    loan_id,
    *,
    period_start,
    period_end,
    actor=None,
    request=None,
    source_channel="BATCH",
    correlation_id="",
):
    """Accrue one unique period and update the loan balance atomically."""
    start = _period(period_start, "period_start")
    end = _period(period_end, "period_end")
    if end <= start:
        raise LoanError(
            "The accrual period end must be after its start.",
            error_code="LOAN_INELIGIBLE",
            status_code=422,
            field_errors={"period_end": ["Choose a period end date after the start date."]},
            resolution_steps=[
                "Use a one-day range for daily accruals.",
                "Use the first day through the closing day for monthly accruals.",
                "Submit the corrected period again.",
            ],
        )

    loan = (
        OLLoan.objects.select_for_update()
        .select_related("policy_ref", "partner")
        .filter(pk=loan_id)
        .first()
    )
    if loan is None:
        raise loan_not_found(str(loan_id))
    if loan.status != LoanStatus.ACTIVE:
        _invalid_status(loan)

    existing = OLLoanInterestAccrual.objects.filter(
        loan=loan,
        period_start=start,
        period_end=end,
    ).first()
    if existing:
        return AccrualResult(loan=loan, accrual=existing, created=False)

    config = get_loan_config(
        loan.policy_ref,
        as_of=end,
        actor=actor,
        request=request,
        source_channel=source_channel,
    )
    days = (end - start).days
    principal_base = _principal_base(loan, config)
    interest_amount = _money(calculate_interest(principal_base, config.interest_rate, days, config))
    penalty_amount = _money(_penalty_for_period(loan, config, start, end))
    previous = loan.interest_accruals.order_by("-period_end", "-created_at").first()
    cumulative_interest = _money((previous.cumulative_interest if previous else Decimal("0")) + interest_amount)

    accrual = OLLoanInterestAccrual(
        loan=loan,
        period_start=start,
        period_end=end,
        principal_base=_money(principal_base),
        interest_amount=interest_amount,
        penalty_amount=penalty_amount,
        cumulative_interest=cumulative_interest,
        source_channel=source_channel,
        created_by=actor,
        updated_by=actor,
    )
    accrual.full_clean()
    accrual.save()

    before = AuditService.snapshot(loan)
    loan.outstanding_balance = _money(loan.outstanding_balance + interest_amount + penalty_amount)
    loan.updated_by = actor
    loan.save(update_fields=["outstanding_balance", "updated_by", "updated_at"])
    after = AuditService.snapshot(loan)
    after.update(
        {
            "period_start": start.isoformat(),
            "period_end": end.isoformat(),
            "principal_base": str(accrual.principal_base),
            "interest_amount": str(interest_amount),
            "penalty_amount": str(penalty_amount),
            "cumulative_interest": str(cumulative_interest),
            "compounding_frequency": config.compounding_frequency,
            "interest_calculation_basis": config.interest_calculation_basis,
            "correlation_id": correlation_id or getattr(request, "request_id", ""),
        }
    )
    AuditService.log(
        "LOAN_INTEREST_ACCRUED",
        "ol_loans.olloan",
        loan.pk,
        before_state=before,
        after_state=after,
        entity_repr=loan.loan_number,
        actor=actor,
        action="LOAN_INTEREST_ACCRUED",
        app_label="ol_loans",
        model_name="olloan",
        object_id=loan.pk,
        object_repr=loan.loan_number,
        changed_fields=["outstanding_balance"],
        reason="Interest and penalty accrued for a configured loan period.",
        source_channel=source_channel,
        request=request,
        request_id=correlation_id or "",
    )
    emit_loan_interest_accrued(
        loan,
        actor=actor,
        from_status=LoanStatus.ACTIVE,
        reason="Loan interest and penalty accrued.",
        source_channel=source_channel,
        payload_extra={
            "accrual_id": str(accrual.pk),
            "period_start": start.isoformat(),
            "period_end": end.isoformat(),
            "principal_base": str(accrual.principal_base),
            "interest_amount": str(interest_amount),
            "penalty_amount": str(penalty_amount),
            "cumulative_interest": str(cumulative_interest),
            "correlation_id": correlation_id or getattr(request, "request_id", ""),
        },
    )
    return AccrualResult(loan=loan, accrual=accrual, created=True)


def balance_for_loan(loan):
    accruals = loan.interest_accruals.all()
    accrued_interest = sum((accrual.interest_amount for accrual in accruals), Decimal("0"))
    penalty = sum((accrual.penalty_amount for accrual in accruals), Decimal("0"))
    principal = _previous_principal_paid(loan)
    return {
        "loan_id": str(loan.pk),
        "loan_number": loan.loan_number,
        "currency": loan.currency,
        "principal": str(_money(principal)),
        "accrued_interest": str(_money(accrued_interest)),
        "penalty": str(_money(penalty)),
        "total_outstanding": str(_money(loan.outstanding_balance)),
        "status": loan.status,
        "as_of": date.today().isoformat(),
    }


def accrue_batch(
    *,
    period_start,
    period_end,
    actor=None,
    loan_id=None,
    source_channel="BATCH",
    correlation_id="",
):
    queryset = OLLoan.objects.filter(status=LoanStatus.ACTIVE).order_by("loan_number")
    if loan_id:
        queryset = queryset.filter(pk=loan_id)
    results = []
    errors = []
    for loan in queryset:
        try:
            results.append(
                accrue_loan_interest(
                    loan.pk,
                    period_start=period_start,
                    period_end=period_end,
                    actor=actor,
                    source_channel=source_channel,
                    correlation_id=correlation_id,
                )
            )
        except LoanError as exc:
            errors.append(
                {
                    "loan_id": str(loan.pk),
                    "loan_number": loan.loan_number,
                    "error_code": exc.error_code,
                    "message": str(exc),
                }
            )
    AuditService.log(
        "LOAN_INTEREST_ACCRUAL_BATCH",
        "ol_loans.interest_accrual_batch",
        None,
        entity_repr=correlation_id or "OL interest accrual batch",
        description="OL Loan interest accrual batch completed.",
        actor=actor,
        action="LOAN_INTEREST_ACCRUAL_BATCH",
        app_label="ol_loans",
        model_name="interestaccrualbatch",
        object_repr=correlation_id or "OL interest accrual batch",
        reason="Daily/monthly OL Loan interest accrual batch.",
        source_channel=source_channel,
        request_id=correlation_id,
        after_state={
            "period_start": _period(period_start, "period_start").isoformat(),
            "period_end": _period(period_end, "period_end").isoformat(),
            "processed": len(results),
            "created": sum(1 for result in results if result.created),
            "replayed": sum(1 for result in results if not result.created),
            "errors": len(errors),
            "correlation_id": correlation_id,
        },
    )
    return results, errors
