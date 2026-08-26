from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from uuid import uuid4

from django.db import transaction

from apps.governance.models import ApprovalRequest
from apps.governance.services.audit_service import AuditService
from apps.ol_parameters.models import OLProduct
from apps.ol_policies.models import Policy, PolicyStatus

from ..errors import LoanError, loan_not_found
from ..events import emit_loan_requested
from ..models import LoanStatus, OLLoan
from .parameter_resolver import LoanConfig, get_loan_config


ACTIVE_LOAN_STATUSES = {
    LoanStatus.REQUESTED,
    LoanStatus.APPROVED,
    LoanStatus.DISBURSED,
    LoanStatus.ACTIVE,
    LoanStatus.PARTIALLY_REPAID,
    LoanStatus.DEFAULTED,
}


@dataclass(frozen=True)
class LoanRequestResult:
    loan: OLLoan
    created: bool


def _decimal(value, field_name):
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise LoanError(
            f"Enter a valid decimal value for {field_name.replace('_', ' ')}.",
            error_code="LOAN_INELIGIBLE",
            status_code=422,
            resolution_steps=[
                f"Enter a numeric {field_name.replace('_', ' ')} using digits and a decimal point.",
                "Review the loan request fields and submit again.",
            ],
            field_errors={field_name: ["Enter a valid decimal amount."]},
        ) from None
    return amount


def _date(value):
    if value in (None, ""):
        return date.today()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError):
        raise LoanError(
            "The loan request date must use YYYY-MM-DD format.",
            error_code="LOAN_INELIGIBLE",
            status_code=422,
            resolution_steps=["Enter a valid request date such as 2026-08-26.", "Submit the request again."],
            field_errors={"as_of": ["Use YYYY-MM-DD format."]},
        ) from None


def _policy_snapshot(policy):
    snapshot = policy.contract_snapshot if isinstance(policy.contract_snapshot, dict) else {}
    return snapshot


def _policy_cash_value(policy):
    snapshot = _policy_snapshot(policy)
    candidates = (
        snapshot.get("cash_value"),
        snapshot.get("cash_surrender_value"),
        snapshot.get("current_cash_surrender_value"),
    )
    for value in candidates:
        if value not in (None, ""):
            try:
                return max(Decimal("0.00"), Decimal(str(value)))
            except (InvalidOperation, TypeError, ValueError):
                continue
    return Decimal("0.00")


def _resolve_product(policy):
    snapshot = _policy_snapshot(policy)
    plan_rows = snapshot.get("plans") if isinstance(snapshot.get("plans"), list) else []
    plan_snapshot = next((row for row in plan_rows if isinstance(row, dict)), {})
    product_id = snapshot.get("product_id") or plan_snapshot.get("product_id")
    product_code = snapshot.get("product_code") or plan_snapshot.get("product_code")
    if product_id:
        product = OLProduct.objects.filter(pk=product_id).first()
        if product:
            return product
    if product_code:
        return OLProduct.objects.filter(code__iexact=str(product_code)).first()
    reference = getattr(policy, "product_plan_ref", "") or ""
    return OLProduct.objects.filter(code__iexact=reference).first()


def _option_codes(config: LoanConfig):
    codes = []
    for option in config.repayment_options:
        if isinstance(option, str):
            code = option
            enabled = True
        elif isinstance(option, dict):
            code = option.get("code") or option.get("value") or ""
            enabled = option.get("enabled", True) is not False
        else:
            continue
        code = str(code).strip().upper()
        if enabled and code and code not in codes:
            codes.append(code)
    return codes


def _term_allowed(config: LoanConfig, term_months):
    configured_terms = []
    for option in config.repayment_options:
        if not isinstance(option, dict):
            continue
        raw_terms = option.get("term_months", option.get("terms_months", option.get("terms")))
        if isinstance(raw_terms, (list, tuple)):
            configured_terms.extend(raw_terms)
        elif raw_terms not in (None, ""):
            configured_terms.append(raw_terms)
        min_term = option.get("min_term_months")
        max_term = option.get("max_term_months")
        if min_term not in (None, "") and term_months < int(min_term):
            return False
        if max_term not in (None, "") and term_months > int(max_term):
            return False
    if configured_terms:
        try:
            return term_months in {int(value) for value in configured_terms}
        except (TypeError, ValueError):
            return False
    return term_months > 0


def _ineligible(message, *, field_errors=None, details=None, steps=None):
    raise LoanError(
        message,
        error_code="LOAN_INELIGIBLE",
        status_code=422,
        resolution_steps=steps
        or [
            "Review the policy status and the active OL Loan Setup configuration.",
            "Correct the highlighted loan request fields and retry.",
            "Contact Loan Operations if the policy data or configured limits appear incorrect.",
        ],
        field_errors=field_errors,
        details=details,
    )


def _exceeds_limit(message, *, field_errors=None, details=None):
    raise LoanError(
        message,
        error_code="LOAN_EXCEEDS_LIMIT",
        status_code=422,
        resolution_steps=[
            "Reduce the requested amount to the available configured loan limit.",
            "Review the policy cash-value snapshot and existing loan balance.",
            "Ask an administrator to review the effective Loan System Setup limits if the value is unexpected.",
        ],
        field_errors=field_errors,
        details=details,
    )


def _active_loan_exists(policy):
    return OLLoan.objects.filter(policy_ref=policy, status__in=ACTIVE_LOAN_STATUSES).order_by("created_at").first()


@transaction.atomic
def request_policy_loan(
    policy_id,
    *,
    requested_amount,
    term_months,
    repayment_mode,
    reason,
    idempotency_key,
    actor=None,
    request=None,
    source_channel="API",
    as_of=None,
):
    """Create one REQUESTED loan after deterministic policy/configuration checks."""
    key = str(idempotency_key or "").strip()
    if not key:
        _ineligible(
            "An idempotency key is required to submit a loan request safely.",
            field_errors={"idempotency_key": ["Provide the X-Idempotency-Key request header."]},
            steps=[
                "Generate a unique X-Idempotency-Key for this user action.",
                "Retry the same request with that key so network retries cannot create duplicate loans.",
            ],
        )
    replay = OLLoan.objects.select_related("policy_ref", "partner").filter(idempotency_key=key).first()
    if replay:
        return LoanRequestResult(loan=replay, created=False)

    policy = Policy.objects.select_for_update().select_related("partner").filter(pk=policy_id).first()
    if policy is None:
        raise loan_not_found(str(policy_id))
    if policy.status not in {PolicyStatus.ACTIVE, PolicyStatus.PAID_UP}:
        _ineligible(
            f"A {policy.get_status_display()} policy cannot request a loan.",
            field_errors={"policy": ["Only Active or Paid-up policies can request a loan."]},
            steps=[
                "Open the policy and confirm it is Active or Paid-up.",
                "Reinstate or correct the policy lifecycle status before requesting a loan.",
            ],
        )

    as_of = _date(as_of)
    config = get_loan_config(policy, as_of=as_of, actor=actor, request=request, source_channel=source_channel)
    product = _resolve_product(policy)
    if product is not None and not product.allow_loans:
        _ineligible(
            "The selected OL product does not allow policy loans.",
            field_errors={"product": ["Choose a product with policy loans enabled."]},
            steps=[
                "Review the product’s Allow Loans setting under OL Parameters > Product Setup.",
                "Use a policy issued from a product that permits policy loans.",
            ],
        )
    if not config.allow_policy_loans:
        _ineligible(
            "Policy loans are disabled by the effective OL Loan System Setup.",
            field_errors={"policy": ["Loans are not enabled for this policy’s product or plan."]},
            steps=[
                "Open Ordinary Life Parameters > Loan Setup.",
                "Activate a Loan System Setup row with policy loans enabled for this product and plan.",
            ],
        )

    existing = _active_loan_exists(policy)
    if existing:
        raise LoanError(
            "This policy already has an active or pending loan.",
            error_code="LOAN_ACTIVE_EXISTS",
            status_code=409,
            resolution_steps=[
                f"Review existing loan {existing.loan_number} before creating another request.",
                "Repay, settle, or close the existing loan according to policy rules.",
                "Use the existing loan’s idempotency key if this is a retry of the same request.",
            ],
            details={"existing_loan_number": existing.loan_number, "existing_status": existing.status},
        )

    amount = _decimal(requested_amount, "requested_amount")
    try:
        term = int(term_months)
    except (TypeError, ValueError):
        _ineligible(
            "Loan term must be a whole number of months.",
            field_errors={"term_months": ["Enter a positive whole number of months."]},
        )
    mode = str(repayment_mode or "").strip().upper()
    allowed_modes = _option_codes(config)
    if not mode or (allowed_modes and mode not in allowed_modes):
        _ineligible(
            "The selected repayment mode is not active in the effective Loan System Setup.",
            field_errors={"repayment_mode": [f"Choose one of the configured modes: {', '.join(allowed_modes)}."]},
            details={"allowed_repayment_modes": allowed_modes},
        )
    if term <= 0 or not _term_allowed(config, term):
        _ineligible(
            "The selected loan term is outside the configured repayment terms.",
            field_errors={"term_months": ["Choose a term offered by the active loan configuration."]},
            details={"repayment_options": list(config.repayment_options)},
        )
    if amount <= 0:
        _ineligible(
            "Requested loan amount must be greater than zero.",
            field_errors={"requested_amount": ["Enter an amount greater than zero."]},
        )

    cash_value = _policy_cash_value(policy)
    available_limit = (cash_value * config.max_loan_percentage / Decimal("100")).quantize(Decimal("0.01"))
    minimum = config.min_loan_amount or Decimal("0.00")
    maximum = min(value for value in (available_limit, config.max_loan_amount) if value is not None)
    if amount < minimum:
        _exceeds_limit(
            "Requested amount is below the configured minimum loan amount.",
            field_errors={"requested_amount": [f"Enter at least {minimum} {config.loan_currency or policy.currency}. "]},
            details={"minimum_loan_amount": str(minimum), "requested_amount": str(amount)},
        )
    if amount > maximum:
        _exceeds_limit(
            "Requested amount exceeds the configured policy loan limit.",
            field_errors={"requested_amount": [f"Enter no more than {maximum} {config.loan_currency or policy.currency}. "]},
            details={
                "cash_value": str(cash_value),
                "max_loan_percentage": str(config.max_loan_percentage),
                "available_loan_limit": str(available_limit),
                "configured_maximum": str(config.max_loan_amount) if config.max_loan_amount is not None else None,
                "requested_amount": str(amount),
            },
        )

    reason = str(reason or "").strip()
    if not reason:
        _ineligible(
            "A reason is required for every loan request.",
            field_errors={"reason": ["Explain why the policyholder is requesting the loan."]},
        )

    approval_required = bool(
        config.require_approval
        or (config.auto_approve_limit is not None and amount > config.auto_approve_limit)
    )
    loan = OLLoan(
        loan_number=f"LOAN-{as_of:%Y%m%d}-{uuid4().hex[:10].upper()}",
        policy_ref=policy,
        partner=policy.partner,
        currency=(config.loan_currency or policy.currency or "TZS").upper(),
        principal_amount=amount,
        cash_value_snapshot=cash_value,
        disbursed_amount=Decimal("0.00"),
        repayment_mode=mode,
        interest_rate=config.interest_rate,
        compounding_frequency=config.compounding_frequency,
        term_months=term,
        status=LoanStatus.REQUESTED,
        total_repaid=Decimal("0.00"),
        outstanding_balance=Decimal("0.00"),
        approval_required=approval_required,
        reason=reason,
        source_channel=source_channel,
        idempotency_key=key,
        created_by=actor,
        updated_by=actor,
    )
    loan.full_clean()
    loan.save()
    if approval_required:
        approval_request = ApprovalRequest.objects.create(
            module="OL_LOANS",
            entity_type="OLLoan",
            entity_id=loan.pk,
            entity_repr=loan.loan_number,
            action="DISBURSE",
            requested_data={
                "loan_id": str(loan.pk),
                "loan_number": loan.loan_number,
                "requested_amount": str(amount),
                "policy_id": str(policy.pk),
                "reason": reason,
            },
            current_data={"status": loan.status, "approval_required": True},
            submitted_by=actor,
        )
        loan.approval_request = approval_request
        loan.save(update_fields=["approval_request", "updated_at"])
    AuditService.log_action(
        "LOAN_REQUESTED",
        loan,
        actor=actor,
        request=request,
        before_state={},
        after_state={
            "loan_number": loan.loan_number,
            "policy_id": str(policy.pk),
            "requested_amount": str(amount),
            "cash_value_snapshot": str(cash_value),
            "status": loan.status,
        },
        changed_fields=["status", "principal_amount", "policy_ref"],
        reason=reason,
        source_channel=source_channel,
    )
    emit_loan_requested(
        loan,
        actor=actor,
        reason=reason,
        source_channel=source_channel,
        payload_extra={
            "requested_amount": str(amount),
            "cash_value_snapshot": str(cash_value),
            "repayment_mode": mode,
            "term_months": term,
        },
    )
    return LoanRequestResult(loan=loan, created=True)
