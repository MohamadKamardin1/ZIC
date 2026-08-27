from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from uuid import uuid4

from django.db import transaction

from apps.front_office.receipts.models import ReceiptAllocation, ReceiptAllocationStatus
from apps.governance.services.audit_service import AuditService

from ..errors import LoanError, loan_not_found
from ..events import emit_loan_repaid, emit_loan_settled
from ..models import LoanScheduleStatus, LoanStatus, OLLoan, OLLoanRepayment, OLLoanSchedule


MONEY_PLACES = Decimal("0.01")
ZERO = Decimal("0.00")


@dataclass(frozen=True)
class RepaymentResult:
    loan: OLLoan
    repayment: OLLoanRepayment
    created: bool


def _money(value):
    return Decimal(str(value or "0")).quantize(MONEY_PLACES, rounding=ROUND_HALF_UP)


def _decimal(value, field_name):
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise LoanError(
            f"Enter a valid decimal value for {field_name.replace('_', ' ')}.",
            error_code="LOAN_INELIGIBLE",
            status_code=422,
            field_errors={field_name: ["Enter a numeric amount using digits and a decimal point."]},
            resolution_steps=[
                f"Enter a valid {field_name.replace('_', ' ')}.",
                "Use a decimal point and do not include currency symbols.",
                "Submit the repayment again after correcting the highlighted field.",
            ],
        ) from None


def _payment_date(value):
    if value in (None, ""):
        return date.today()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError):
        raise LoanError(
            "The repayment date must use YYYY-MM-DD format.",
            error_code="LOAN_INELIGIBLE",
            status_code=422,
            field_errors={"payment_date": ["Use a valid date such as 2026-08-27."]},
            resolution_steps=[
                "Enter the repayment date in YYYY-MM-DD format.",
                "Confirm the date is not in an invalid calendar format.",
                "Submit the repayment again.",
            ],
        ) from None


def _invalid_status(loan):
    raise LoanError(
        f"Loan {loan.loan_number} cannot receive a repayment from status {loan.get_status_display()}.",
        error_code="LOAN_INVALID_STATUS",
        status_code=409,
        field_errors={"status": ["Only an Active or Partially Repaid loan can receive a repayment."]},
        resolution_steps=[
            "Confirm the loan has been disbursed and is currently Active or Partially Repaid.",
            "Do not post repayments to Settled, Closed, or Rejected loans.",
            "Retry after correcting the loan lifecycle state.",
        ],
    )


def _breakdown_value(repayment, *keys):
    breakdown = repayment.allocation_breakdown if isinstance(repayment.allocation_breakdown, dict) else {}
    for key in keys:
        if key in breakdown:
            try:
                return _decimal(breakdown[key], key)
            except LoanError:
                return ZERO
    return ZERO


def _previously_allocated(loan, bucket):
    key_map = {
        "penalty": ("penalty", "penalty_paid"),
        "interest": ("interest", "interest_paid"),
        "principal": ("principal", "principal_paid"),
    }
    return sum(
        (_breakdown_value(repayment, *key_map[bucket]) for repayment in loan.repayments.all()),
        ZERO,
    )


def _schedule_remaining(schedule, component):
    due = _decimal(getattr(schedule, f"{component}_due"), f"{component}_due")
    paid = _decimal(getattr(schedule, f"{component}_paid"), f"{component}_paid")
    return max(ZERO, due - paid)


def _active_receipt_allocation(receipt_ref, loan, currency):
    reference = str(receipt_ref or "").strip()
    if not reference:
        return None
    allocation = (
        ReceiptAllocation.objects.select_for_update()
        .select_related("receipt")
        .filter(
            receipt__receipt_number__iexact=reference,
            allocation_status=ReceiptAllocationStatus.ACTIVE,
        )
        .order_by("-allocated_at", "-created_at")
        .first()
    )
    if allocation is None:
        raise LoanError(
            f"Receipt allocation '{reference}' could not be found or is no longer active.",
            error_code="LOAN_INELIGIBLE",
            status_code=422,
            field_errors={"receipt_ref": ["Provide the receipt number of an active front-office receipt allocation."]},
            resolution_steps=[
                "Open Front Office > Receipts and confirm the receipt has an active allocation.",
                "Copy the human-readable receipt number, not its internal identifier.",
                "Retry the repayment with the verified receipt reference.",
            ],
        )
    if allocation.receipt.currency.upper() != str(currency or "").upper():
        raise LoanError(
            "The repayment currency must match the linked receipt allocation currency.",
            error_code="LOAN_INELIGIBLE",
            status_code=422,
            field_errors={"currency": [f"Use {allocation.receipt.currency.upper()} for this receipt allocation."]},
            details={"receipt_currency": allocation.receipt.currency.upper(), "repayment_currency": currency},
            resolution_steps=[
                "Use the same currency as the front-office receipt allocation.",
                "If a cross-currency repayment is required, post it through the configured exchange-rate workflow.",
                "Retry after correcting the currency.",
            ],
        )
    return allocation


def _overpayment(loan, applied_amount):
    outstanding = _money(loan.outstanding_balance)
    if applied_amount <= outstanding:
        return
    raise LoanError(
        f"Repayment amount {applied_amount} exceeds the loan outstanding balance of {outstanding} {loan.currency}.",
        error_code="LOAN_REPAYMENT_OVERPAYMENT",
        status_code=422,
        field_errors={"amount": [f"Enter no more than {outstanding} {loan.currency}."]},
        details={
            "requested_amount": str(applied_amount),
            "outstanding_balance": str(outstanding),
            "currency": loan.currency,
        },
        resolution_steps=[
            f"Reduce the repayment to {outstanding} {loan.currency} or less.",
            "Ask Finance to confirm the current balance before retrying.",
            "Use a separate configured credit-hold workflow if excess funds must be retained.",
        ],
    )


def _bucket_targets(schedules, payment_date, bucket):
    if bucket == "principal":
        return schedules
    due = [schedule for schedule in schedules if schedule.due_date <= payment_date]
    # Accruals can be payable before the next scheduled due date, so interest
    # and penalty still need an earliest schedule target for traceability.
    return due or schedules[:1]


def _accrued_unallocated(loan, bucket):
    if bucket == "interest":
        total = sum((accrual.interest_amount for accrual in loan.interest_accruals.all()), ZERO)
    elif bucket == "penalty":
        total = sum((accrual.penalty_amount for accrual in loan.interest_accruals.all()), ZERO)
    else:
        return ZERO
    return max(ZERO, _money(total) - _money(_previously_allocated(loan, bucket)))


def _bucket_due(loan, schedules, payment_date, bucket):
    targets = _bucket_targets(schedules, payment_date, bucket)
    if bucket == "principal":
        scheduled = sum((_schedule_remaining(schedule, bucket) for schedule in targets), ZERO)
    else:
        due_targets = [schedule for schedule in schedules if schedule.due_date <= payment_date]
        scheduled = sum((_schedule_remaining(schedule, bucket) for schedule in due_targets), ZERO)
        # Accrual rows represent interest/penalty that is not yet stored on a
        # schedule component. Add the unallocated amount to scheduled dues.
        scheduled += _accrued_unallocated(loan, bucket)
    return _money(scheduled), targets


def _apply_bucket(targets, bucket, amount):
    remaining = _money(amount)
    applied = ZERO
    paid_field = f"{bucket}_paid"
    due_field = f"{bucket}_due"
    for schedule in targets:
        if remaining <= ZERO:
            break
        available = _schedule_remaining(schedule, bucket)
        applied_now = min(remaining, available)
        if applied_now <= ZERO:
            continue
        setattr(schedule, paid_field, _money(getattr(schedule, paid_field) + applied_now))
        schedule.amount_paid = _money(schedule.amount_paid + applied_now)
        applied += applied_now
        remaining = _money(remaining - applied_now)

    # Interest and penalty generated by the accrual engine may not have existed
    # when the contractual schedule was created. Put any such amount on the
    # earliest schedule so the payment remains fully explainable.
    if remaining > ZERO and targets and bucket in {"interest", "penalty"}:
        schedule = targets[0]
        setattr(schedule, due_field, _money(getattr(schedule, due_field) + remaining))
        setattr(schedule, paid_field, _money(getattr(schedule, paid_field) + remaining))
        schedule.amount_paid = _money(schedule.amount_paid + remaining)
        applied = _money(applied + remaining)
    return _money(applied)


def _refresh_schedule(schedule, payment_date):
    remaining = sum(
        (_schedule_remaining(schedule, component) for component in ("penalty", "interest", "principal")),
        ZERO,
    )
    schedule.balance = _money(remaining)
    if remaining <= ZERO:
        schedule.status = LoanScheduleStatus.PAID
    elif schedule.amount_paid > ZERO:
        schedule.status = (
            LoanScheduleStatus.OVERDUE
            if schedule.due_date < payment_date
            else LoanScheduleStatus.PARTIALLY_PAID
        )
    elif schedule.due_date < payment_date:
        schedule.status = LoanScheduleStatus.OVERDUE
    else:
        schedule.status = LoanScheduleStatus.PENDING
    return schedule


@transaction.atomic
def repay_loan(
    loan_id,
    *,
    amount,
    currency,
    payment_mode="",
    exchange_rate=None,
    receipt_ref="",
    reason="",
    payment_date=None,
    idempotency_key="",
    actor=None,
    request=None,
    source_channel="API",
):
    loan = (
        OLLoan.objects.select_for_update()
        .select_related("policy_ref", "partner")
        .filter(pk=loan_id)
        .first()
    )
    if loan is None:
        raise loan_not_found(str(loan_id))

    requested_key = str(idempotency_key or "").strip()
    if requested_key:
        existing = OLLoanRepayment.objects.select_related("receipt_allocation").filter(idempotency_key=requested_key).first()
        if existing:
            if existing.loan_id != loan.pk:
                raise LoanError(
                    "This idempotency key belongs to another loan repayment.",
                    error_code="LOAN_INELIGIBLE",
                    status_code=409,
                    field_errors={"idempotency_key": ["Use a unique idempotency key for this loan repayment."]},
                    resolution_steps=[
                        "Generate a new unique X-Idempotency-Key for this loan action.",
                        "Do not reuse a repayment key from another loan.",
                        "Retry the repayment with the new key.",
                    ],
                )
            return RepaymentResult(loan=loan, repayment=existing, created=False)
    receipt_reference = str(receipt_ref or "").strip()
    if receipt_reference:
        existing = OLLoanRepayment.objects.filter(loan=loan, receipt_ref__iexact=receipt_reference).order_by("-created_at").first()
        if existing:
            return RepaymentResult(loan=loan, repayment=existing, created=False)
    if loan.status not in {LoanStatus.ACTIVE, LoanStatus.PARTIALLY_REPAID}:
        _invalid_status(loan)

    normalized_currency = str(currency or "").strip().upper()
    if len(normalized_currency) != 3 or not normalized_currency.isalpha():
        raise LoanError(
            "Repayment currency must be a three-letter code.",
            error_code="LOAN_INELIGIBLE",
            status_code=422,
            field_errors={"currency": ["Enter a valid three-letter currency code such as TZS."]},
            resolution_steps=[
                "Use the currency shown on the loan.",
                "Enter the ISO-style three-letter code.",
                "Submit the repayment again.",
            ],
        )
    amount_value = _decimal(amount, "amount")
    if amount_value <= ZERO:
        raise LoanError(
            "Repayment amount must be greater than zero.",
            error_code="LOAN_INELIGIBLE",
            status_code=422,
            field_errors={"amount": ["Enter an amount greater than zero."]},
            resolution_steps=[
                "Enter a positive repayment amount.",
                "Confirm the amount is in the selected currency.",
                "Submit the repayment again.",
            ],
        )
    if normalized_currency != loan.currency.upper() and exchange_rate is None:
        raise LoanError(
            "An exchange rate is required when repayment currency differs from the loan currency.",
            error_code="LOAN_INELIGIBLE",
            status_code=422,
            field_errors={"exchange_rate": [f"Provide the approved rate from {normalized_currency} to {loan.currency.upper()}."]},
            details={"loan_currency": loan.currency.upper(), "repayment_currency": normalized_currency},
            resolution_steps=[
                "Enter the approved exchange rate for this cross-currency repayment.",
                "Confirm the rate is valid for the payment date.",
                "Submit the repayment again.",
            ],
        )
    rate = _decimal(exchange_rate if exchange_rate is not None else "1", "exchange_rate")
    if rate <= ZERO:
        raise LoanError(
            "Exchange rate must be greater than zero.",
            error_code="LOAN_INELIGIBLE",
            status_code=422,
            field_errors={"exchange_rate": ["Enter a positive exchange rate."]},
            resolution_steps=[
                "Use 1.000000 when repayment and loan currencies match.",
                "Use the approved configured rate for a cross-currency repayment.",
                "Submit the repayment again.",
            ],
        )
    applied_amount = _money(amount_value * rate)
    _overpayment(loan, applied_amount)
    paid_on = _payment_date(payment_date)
    allocation = _active_receipt_allocation(receipt_ref, loan, normalized_currency)

    key = requested_key
    if not key:
        key = f"loan-repayment-{loan.pk}-{receipt_reference.upper() or paid_on.isoformat()}-{amount_value}-{normalized_currency}"
    existing = OLLoanRepayment.objects.select_related("receipt_allocation").filter(idempotency_key=key).first()
    if existing:
        if existing.loan_id != loan.pk:
            raise LoanError(
                "This idempotency key belongs to another loan repayment.",
                error_code="LOAN_INELIGIBLE",
                status_code=409,
                field_errors={"idempotency_key": ["Use a unique idempotency key for this loan repayment."]},
                resolution_steps=[
                    "Generate a new unique X-Idempotency-Key for this loan action.",
                    "Do not reuse a repayment key from another loan.",
                    "Retry the repayment with the new key.",
                ],
            )
        return RepaymentResult(loan=loan, repayment=existing, created=False)
    if allocation:
        existing = OLLoanRepayment.objects.filter(receipt_allocation=allocation).order_by("-created_at").first()
        if existing:
            if existing.loan_id != loan.pk:
                raise LoanError(
                    "This receipt allocation is already linked to another loan repayment.",
                    error_code="LOAN_INELIGIBLE",
                    status_code=409,
                    field_errors={"receipt_ref": ["Use an active receipt allocation that has not already been applied to another loan."]},
                    resolution_steps=[
                        "Open Front Office > Receipts and select an unused active allocation.",
                        "Verify the receipt reference belongs to this loan payment.",
                        "Retry after correcting the receipt reference.",
                    ],
                )
            return RepaymentResult(loan=loan, repayment=existing, created=False)

    schedules = list(OLLoanSchedule.objects.select_for_update().filter(loan=loan).order_by("due_date", "installment_number"))
    if not schedules:
        raise LoanError(
            "This loan has no repayment schedule to receive the repayment.",
            error_code="LOAN_INELIGIBLE",
            status_code=422,
            field_errors={"loan": ["Generate the loan repayment schedule before posting a repayment."]},
            resolution_steps=[
                "Confirm the loan was disbursed successfully.",
                "Generate or restore the contractual repayment schedule.",
                "Retry the repayment after the schedule is available.",
            ],
        )

    penalty_due, penalty_targets = _bucket_due(loan, schedules, paid_on, "penalty")
    interest_due, interest_targets = _bucket_due(loan, schedules, paid_on, "interest")
    principal_due, principal_targets = _bucket_due(loan, schedules, paid_on, "principal")
    remaining = applied_amount
    penalty_applied = min(remaining, penalty_due)
    remaining = _money(remaining - penalty_applied)
    interest_applied = min(remaining, interest_due)
    remaining = _money(remaining - interest_applied)
    principal_applied = min(remaining, principal_due)
    remaining = _money(remaining - principal_applied)
    if remaining > ZERO:
        # This can only occur when the persisted loan balance is lower than
        # contractual schedule components. Never create an unallocated surplus.
        _overpayment(loan, applied_amount + remaining)

    _apply_bucket(penalty_targets, "penalty", penalty_applied)
    _apply_bucket(interest_targets, "interest", interest_applied)
    _apply_bucket(principal_targets, "principal", principal_applied)
    for schedule in schedules:
        _refresh_schedule(schedule, paid_on)
        schedule.updated_by = actor
        schedule.save(
            update_fields=[
                "principal_due",
                "interest_due",
                "penalty_due",
                "principal_paid",
                "interest_paid",
                "penalty_paid",
                "amount_paid",
                "balance",
                "status",
                "updated_by",
                "updated_at",
            ]
        )

    breakdown = {
        "penalty": str(_money(penalty_applied)),
        "interest": str(_money(interest_applied)),
        "principal": str(_money(principal_applied)),
        "amount": str(_money(amount_value)),
        "applied_amount": str(applied_amount),
        "currency": normalized_currency,
        "payment_mode": str(payment_mode or "").strip().upper(),
        "exchange_rate": str(rate),
        "receipt_ref": receipt_reference,
        "allocation_order": ["penalty", "interest", "principal"],
    }
    before = AuditService.snapshot(loan)
    loan.total_repaid = _money(loan.total_repaid + applied_amount)
    loan.outstanding_balance = _money(max(ZERO, loan.outstanding_balance - applied_amount))
    fully_settled = loan.outstanding_balance <= ZERO
    loan.status = LoanStatus.SETTLED if fully_settled else LoanStatus.PARTIALLY_REPAID
    loan.updated_by = actor
    loan.save(update_fields=["total_repaid", "outstanding_balance", "status", "updated_by", "updated_at"])

    repayment = OLLoanRepayment(
        loan=loan,
        receipt_ref=receipt_reference,
        receipt_allocation=allocation,
        idempotency_key=key,
        amount=_money(amount_value),
        currency=normalized_currency,
        exchange_rate=rate,
        allocation_breakdown=breakdown,
        reason=str(reason or f"Repayment posted for OL loan {loan.loan_number}.").strip(),
        source_channel=source_channel,
        created_by=actor,
        updated_by=actor,
    )
    repayment.full_clean()
    repayment.save()

    after = AuditService.snapshot(loan)
    after.update(
        {
            "repayment_id": str(repayment.pk),
            "repayment_amount": str(repayment.amount),
            "applied_amount": str(applied_amount),
            "allocation_breakdown": breakdown,
            "receipt_ref": repayment.receipt_ref,
            "receipt_allocation_id": str(allocation.pk) if allocation else None,
        }
    )
    AuditService.log_action(
        "LOAN_REPAID",
        loan,
        actor=actor,
        request=request,
        before_state=before,
        after_state=after,
        changed_fields=["total_repaid", "outstanding_balance", "status"],
        reason=repayment.reason,
        source_channel=source_channel,
    )
    emit_loan_repaid(
        loan,
        actor=actor,
        from_status=before.get("status", ""),
        reason=repayment.reason,
        source_channel=source_channel,
        payload_extra={
            "repayment_id": str(repayment.pk),
            "amount": str(repayment.amount),
            "applied_amount": str(applied_amount),
            "currency": normalized_currency,
            "payment_mode": str(payment_mode or "").strip().upper(),
            "exchange_rate": str(rate),
            "allocation_breakdown": breakdown,
            "receipt_ref": repayment.receipt_ref,
            "receipt_allocation_id": str(allocation.pk) if allocation else None,
        },
    )
    if fully_settled:
        AuditService.log_action(
            "LOAN_SETTLED",
            loan,
            actor=actor,
            request=request,
            before_state={"status": before.get("status", ""), "outstanding_balance": before.get("outstanding_balance")},
            after_state={"status": loan.status, "outstanding_balance": str(loan.outstanding_balance)},
            changed_fields=["status", "outstanding_balance"],
            reason=f"Loan {loan.loan_number} settled after repayment.",
            source_channel=source_channel,
        )
        emit_loan_settled(
            loan,
            actor=actor,
            from_status=before.get("status", ""),
            reason=f"Loan {loan.loan_number} settled after repayment.",
            source_channel=source_channel,
            payload_extra={"repayment_id": str(repayment.pk), "receipt_ref": repayment.receipt_ref},
        )
    return RepaymentResult(loan=loan, repayment=repayment, created=True)
