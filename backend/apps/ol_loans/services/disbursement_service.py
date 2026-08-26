from calendar import monthrange
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from uuid import uuid4

from django.db import transaction

from apps.front_office.models import FORequisition
from apps.front_office.receipts.config_models import CompanyBankAccount, ReceiptPaymentModeRule
from apps.governance.services.audit_service import AuditService

from ..errors import LoanError, loan_not_found, parameter_missing
from ..events import emit_loan_disbursed
from ..models import LoanScheduleStatus, LoanStatus, OLLoan, OLLoanDisbursement, OLLoanSchedule
from .parameter_resolver import LoanConfig, get_loan_config


MONEY_PLACES = Decimal("0.01")
ONE_HUNDRED = Decimal("100")
MONTHS_PER_YEAR = Decimal("12")


@dataclass(frozen=True)
class DisbursementResult:
    loan: OLLoan
    disbursement: OLLoanDisbursement
    schedules: tuple
    changed: bool


def _money(value):
    return Decimal(str(value or "0")).quantize(MONEY_PLACES, rounding=ROUND_HALF_UP)


def _add_months(value, months):
    month_index = value.month - 1 + int(months)
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    return date(year, month, min(value.day, monthrange(year, month)[1]))


def _disbursement_error(message, *, field_errors=None, details=None, status_code=422, steps=None):
    raise LoanError(
        message,
        error_code="LOAN_DISBURSEMENT_FAILED",
        status_code=status_code,
        resolution_steps=steps
        or [
            "Review the effective OL Loan Setup and Interest Control configuration.",
            "Confirm a valid active payment mode and bank account are configured.",
            "Correct the highlighted disbursement details and retry the operation.",
        ],
        field_errors=field_errors,
        details=details,
    )


def _parse_date(value):
    if value in (None, ""):
        return date.today()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError):
        _disbursement_error(
            "The disbursement date must use YYYY-MM-DD format.",
            field_errors={"as_of": ["Enter a valid date such as 2026-08-27."]},
        )


def _option_for_mode(config: LoanConfig, mode):
    for raw in config.repayment_options:
        if isinstance(raw, str) and raw.strip().upper() == mode:
            return {"code": mode}
        if isinstance(raw, dict):
            code = str(raw.get("code") or raw.get("value") or "").strip().upper()
            if code == mode:
                return raw
    return {}


def _mode_family(config: LoanConfig, mode):
    option = _option_for_mode(config, mode)
    configured_method = str(
        option.get("schedule_method")
        or option.get("calculation_method")
        or option.get("repayment_method")
        or ""
    ).strip().upper().replace("-", "_")
    if configured_method in {"EQUAL_PRINCIPAL", "PRINCIPAL", "REDUCING_PRINCIPAL"}:
        return "EQUAL_PRINCIPAL"
    if configured_method in {"EQUAL_INSTALLMENT", "EQUAL_INSTALMENT", "EMI", "ANNUITY"}:
        return "EQUAL_INSTALLMENT"
    if configured_method in {"LUMP_SUM", "BULLET", "SINGLE"}:
        return "LUMP_SUM"

    normalized = mode.replace("-", "_")
    if normalized in {"EQUAL_PRINCIPAL", "PRINCIPAL", "REDUCING_PRINCIPAL"}:
        return "EQUAL_PRINCIPAL"
    if normalized in {"EQUAL_INSTALLMENT", "EQUAL_INSTALMENT", "EMI", "ANNUITY", "PAYMENT_SCHEDULE", "SCHEDULE"}:
        return "EQUAL_INSTALLMENT"
    if normalized in {"LUMP_SUM", "BULLET", "SINGLE", "DEDUCT_FROM_BENEFIT"}:
        return "LUMP_SUM"
    return ""


def _configured_modes(config: LoanConfig):
    modes = []
    for raw in config.repayment_options:
        if isinstance(raw, str):
            code = raw
            enabled = True
        elif isinstance(raw, dict):
            code = raw.get("code") or raw.get("value") or ""
            enabled = raw.get("enabled", True) is not False
        else:
            continue
        code = str(code).strip().upper()
        if enabled and code and code not in modes:
            modes.append(code)
    return modes


def _validate_payment_setup(payment_mode, bank_account_code, currency):
    mode = str(payment_mode or "").strip().upper()
    if not mode:
        _disbursement_error(
            "A configured payment mode is required before a loan can be disbursed.",
            field_errors={"payment_mode": ["Select an active payment mode configured for outgoing payments."]},
        )
    rule = ReceiptPaymentModeRule.objects.filter(payment_mode__iexact=mode, is_active=True).first()
    if rule is None:
        _disbursement_error(
            f"Payment mode '{mode}' is not configured or active.",
            field_errors={"payment_mode": ["Choose an active payment mode from Front Office > Receipt Payment Mode Rules."]},
            details={"payment_mode": mode},
        )

    requested_code = str(bank_account_code or "").strip()
    accounts = CompanyBankAccount.objects.filter(is_active=True)
    if requested_code:
        account = accounts.filter(code__iexact=requested_code).first()
    else:
        account = accounts.filter(is_default=True).first() or accounts.order_by("code").first()
    if rule.requires_bank_account and account is None:
        _disbursement_error(
            "An active company bank account is required for the selected payment mode.",
            field_errors={"bank_account_code": ["Configure or select an active company bank account before disbursing."]},
        )
    if requested_code and account is None:
        _disbursement_error(
            f"Bank account '{requested_code}' was not found or is inactive.",
            field_errors={"bank_account_code": ["Select an active company bank account from Front Office configuration."]},
        )
    if account and account.currency.upper() != str(currency or "").upper():
        _disbursement_error(
            "The selected bank account currency does not match the loan currency.",
            field_errors={"bank_account_code": [f"Select an account denominated in {currency}."]},
            details={"loan_currency": currency, "bank_account_currency": account.currency},
        )
    return mode, rule, account


def _monthly_rate(loan, config):
    try:
        annual_rate = Decimal(str(loan.interest_rate)) / ONE_HUNDRED
    except (InvalidOperation, TypeError, ValueError):
        _disbursement_error(
            "The approved loan has an invalid interest rate and cannot be scheduled.",
            field_errors={"interest_rate": ["Review the effective OL Loan Interest Control and approve the loan again."]},
        )
    # Repayment installments are monthly because the loan term is stored in months.
    # The effective compounding and interest basis remain on the loan/configuration
    # for the accrual engine; monthly amortization uses a pro-rated nominal rate.
    return annual_rate / MONTHS_PER_YEAR


def _interest_amount(balance, monthly_rate, months=1):
    return _money(balance * monthly_rate * Decimal(str(months)))


def _schedule_rows(loan, config, disbursement_date):
    family = _mode_family(config, loan.repayment_mode)
    if not family:
        _disbursement_error(
            f"Repayment mode '{loan.repayment_mode}' is configured but has no supported schedule method.",
            field_errors={"repayment_mode": ["Configure the repayment option as Equal Principal, Equal Installment, or Lump Sum before disbursing."]},
            details={"configured_repayment_modes": _configured_modes(config)},
        )

    term_months = int(loan.term_months)
    monthly_rate = _monthly_rate(loan, config)
    first_due = (
        disbursement_date + timedelta(days=config.grace_days)
        if config.grace_days > 0
        else _add_months(disbursement_date, 1)
    )
    principal = _money(loan.principal_amount)
    rows = []

    if family == "LUMP_SUM":
        if config.interest_calculation_basis == "SIMPLE":
            interest = _interest_amount(principal, monthly_rate, term_months)
        else:
            interest = _interest_amount(principal, monthly_rate, term_months)
        rows.append(
            {
                "installment_number": 1,
                "due_date": _add_months(disbursement_date, term_months),
                "principal_due": principal,
                "interest_due": interest,
                "amount": _money(principal + interest),
            }
        )
        return rows

    if family == "EQUAL_PRINCIPAL":
        principal_installment = _money(principal / Decimal(term_months))
        remaining_principal = principal
        for number in range(1, term_months + 1):
            principal_due = remaining_principal if number == term_months else principal_installment
            interest_due = _interest_amount(remaining_principal, monthly_rate)
            remaining_principal = _money(remaining_principal - principal_due)
            rows.append(
                {
                    "installment_number": number,
                    "due_date": _add_months(first_due, number - 1),
                    "principal_due": principal_due,
                    "interest_due": interest_due,
                    "amount": _money(principal_due + interest_due),
                }
            )
        return rows

    # Equal-installment/annuity calculation. The final row absorbs currency
    # rounding so all principal is repaid exactly and the final balance is zero.
    if monthly_rate == 0:
        installment = _money(principal / Decimal(term_months))
    else:
        growth = (Decimal("1") + monthly_rate) ** term_months
        installment = _money(principal * monthly_rate * growth / (growth - Decimal("1")))
    remaining_principal = principal
    for number in range(1, term_months + 1):
        interest_due = _interest_amount(remaining_principal, monthly_rate)
        principal_due = _money(installment - interest_due)
        if number == term_months:
            principal_due = remaining_principal
        amount = _money(principal_due + interest_due)
        remaining_principal = _money(remaining_principal - principal_due)
        rows.append(
            {
                "installment_number": number,
                "due_date": _add_months(first_due, number - 1),
                "principal_due": principal_due,
                "interest_due": interest_due,
                "amount": amount,
            }
        )
    return rows


def _create_requisition(loan, amount, reason):
    number = f"LOAN-{date.today():%Y%m%d}-{uuid4().hex[:10].upper()}"
    return FORequisition.objects.create(
        requisition_number=number,
        department="OL_LOAN_FINANCE",
        amount=amount,
        reason=reason,
        status="PENDING",
    )


@transaction.atomic
def disburse_loan(
    loan_id,
    *,
    payment_mode,
    bank_account_code="",
    as_of=None,
    reason="",
    idempotency_key="",
    actor=None,
    request=None,
    source_channel="API",
):
    """Release an approved loan and create its complete contractual schedule atomically."""
    loan = (
        OLLoan.objects.select_for_update()
        .select_related("policy_ref", "partner")
        .filter(pk=loan_id)
        .first()
    )
    if loan is None:
        raise loan_not_found(str(loan_id))

    existing = OLLoanDisbursement.objects.select_related("requisition").filter(loan=loan).first()
    if existing:
        schedules = tuple(loan.schedules.order_by("installment_number"))
        return DisbursementResult(loan=loan, disbursement=existing, schedules=schedules, changed=False)

    key = str(idempotency_key or "").strip() or f"loan-disbursement-{loan.pk}"
    key_owner = OLLoanDisbursement.objects.select_related("loan").filter(idempotency_key=key).first()
    if key_owner and key_owner.loan_id != loan.pk:
        _disbursement_error(
            "This idempotency key has already been used for another loan disbursement.",
            status_code=409,
            field_errors={"idempotency_key": ["Use a new unique key for this loan action."]},
        )
    if loan.status != LoanStatus.APPROVED:
        raise LoanError(
            f"Loan {loan.loan_number} cannot be disbursed from status {loan.get_status_display()}.",
            error_code="LOAN_INVALID_STATUS",
            status_code=409,
            resolution_steps=[
                "Confirm that the loan has been approved and is not rejected, already disbursed, or closed.",
                "Complete the approval workflow before retrying disbursement.",
                "Use the existing disbursement record when this request is a retry.",
            ],
            field_errors={"status": ["Only an approved loan can be disbursed."]},
            details={"loan_number": loan.loan_number, "current_status": loan.status, "required_status": LoanStatus.APPROVED},
        )

    disbursement_date = _parse_date(as_of)
    config = get_loan_config(
        loan.policy_ref,
        as_of=disbursement_date,
        actor=actor,
        request=request,
        source_channel=source_channel,
    )
    if not config.allow_policy_loans:
        raise parameter_missing("Loan System Setup policy-loan allowance", "Ordinary Life Parameters > Loan Setup")
    configured_modes = _configured_modes(config)
    normalized_repayment_mode = str(loan.repayment_mode or "").strip().upper()
    if configured_modes and normalized_repayment_mode not in configured_modes:
        _disbursement_error(
            "The approved loan repayment mode is no longer active in the effective Loan System Setup.",
            field_errors={"repayment_mode": [f"Configure or select one of: {', '.join(configured_modes)}."]},
            details={"approved_repayment_mode": normalized_repayment_mode, "configured_repayment_modes": configured_modes},
        )

    normalized_payment_mode, payment_rule, bank_account = _validate_payment_setup(
        payment_mode,
        bank_account_code,
        loan.currency,
    )
    reason = str(reason or f"Disbursement of OL loan {loan.loan_number}.").strip()
    if not reason:
        reason = f"Disbursement of OL loan {loan.loan_number}."

    schedule_data = _schedule_rows(loan, config, disbursement_date)
    if not schedule_data:
        _disbursement_error(
            "No repayment schedule could be generated for this loan.",
            steps=[
                "Review the approved loan term and repayment mode.",
                "Configure a supported schedule method in OL Parameters > Loan Setup.",
                "Retry disbursement after the configuration is effective.",
            ],
        )

    requisition = _create_requisition(loan, _money(loan.principal_amount), reason)
    disbursement = OLLoanDisbursement(
        loan=loan,
        requisition=requisition,
        amount=_money(loan.principal_amount),
        currency=loan.currency,
        payment_mode=normalized_payment_mode,
        bank_account_code=bank_account.code if bank_account else "",
        disbursement_date=disbursement_date,
        idempotency_key=key,
        reason=reason,
        source_channel=source_channel,
        created_by=actor,
        updated_by=actor,
    )
    disbursement.full_clean()
    disbursement.save()

    schedules = []
    for row in schedule_data:
        schedule = OLLoanSchedule(
            loan=loan,
            installment_number=row["installment_number"],
            due_date=row["due_date"],
            principal_due=row["principal_due"],
            interest_due=row["interest_due"],
            penalty_due=Decimal("0.00"),
            amount_paid=Decimal("0.00"),
            balance=_money(sum(item["amount"] for item in schedule_data[row["installment_number"] :])),
            status=LoanScheduleStatus.PENDING,
            reason=reason,
            source_channel=source_channel,
            created_by=actor,
            updated_by=actor,
        )
        schedule.full_clean()
        schedule.save()
        schedules.append(schedule)

    before = AuditService.snapshot(loan)
    maturity_date = _add_months(disbursement_date, int(loan.term_months))
    loan.status = LoanStatus.ACTIVE
    loan.disbursement_date = disbursement_date
    loan.maturity_date = maturity_date
    loan.disbursed_amount = _money(loan.principal_amount)
    loan.outstanding_balance = _money(loan.principal_amount)
    loan.updated_by = actor
    loan.save(
        update_fields=[
            "status",
            "disbursement_date",
            "maturity_date",
            "disbursed_amount",
            "outstanding_balance",
            "updated_by",
            "updated_at",
        ]
    )

    after = AuditService.snapshot(loan)
    after.update(
        {
            "disbursement_amount": str(disbursement.amount),
            "schedule_count": len(schedules),
            "payment_mode": normalized_payment_mode,
            "bank_account_code": disbursement.bank_account_code,
            "requisition_number": requisition.requisition_number,
        }
    )
    AuditService.log_action(
        "LOAN_DISBURSED",
        loan,
        actor=actor,
        request=request,
        before_state=before,
        after_state=after,
        changed_fields=[
            "status",
            "disbursement_date",
            "maturity_date",
            "disbursed_amount",
            "outstanding_balance",
        ],
        reason=reason,
        source_channel=source_channel,
    )
    emit_loan_disbursed(
        loan,
        actor=actor,
        from_status=LoanStatus.APPROVED,
        reason=reason,
        source_channel=source_channel,
        payload_extra={
            "amount": str(disbursement.amount),
            "currency": disbursement.currency,
            "payment_mode": normalized_payment_mode,
            "bank_account_code": disbursement.bank_account_code,
            "requisition_number": requisition.requisition_number,
            "disbursement_id": str(disbursement.pk),
            "schedule_count": len(schedules),
            "grace_days": config.grace_days,
            "compounding_frequency": config.compounding_frequency,
            "repayment_mode": normalized_repayment_mode,
        },
    )
    return DisbursementResult(loan=loan, disbursement=disbursement, schedules=tuple(schedules), changed=True)
