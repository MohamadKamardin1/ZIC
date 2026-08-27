from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from uuid import uuid4

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.front_office.models import FORequisition
from apps.governance.services.audit_service import AuditService
from apps.ol_parameters.models import OLLoanInterestControl, OLLoanSystemSetup
from apps.system_parameters.services.numbering_service import NumberingEngine

from ..errors import registry_error
from ..events import (
    POLICY_LOAN_APPROVED,
    POLICY_LOAN_DISBURSED,
    POLICY_LOAN_REPAID,
    POLICY_LOAN_REQUESTED,
    POLICY_WITHDRAWAL_REQUESTED,
    emit_policy_loan_event,
)
from ..models import (
    LoanStatus,
    Policy,
    PolicyAuditLog,
    PolicyLoan,
    PolicyLoanRepayment,
    PolicyStatus,
    WithdrawalPayment,
    WithdrawalRequest,
    WithdrawalStatus,
)

TERMINAL_POLICY_STATUSES = {
    PolicyStatus.CANCELLED,
    PolicyStatus.EXPIRED,
    PolicyStatus.SURRENDERED,
    PolicyStatus.TERMINATED,
    PolicyStatus.CLAIM_SETTLED,
}


def _date(value, default=None):
    if value in (None, ""):
        return default or date.today()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError):
        raise registry_error(
            "POLICY_LOAN_BLOCKED",
            message="The finance processing date must use YYYY-MM-DD format.",
            field_errors={"as_of": ["Enter a valid date in YYYY-MM-DD format."]},
        ) from None


def _decimal(value, default=Decimal("0.00")):
    if value in (None, ""):
        return default
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return default


def _scope(policy):
    snapshot = policy.contract_snapshot if isinstance(policy.contract_snapshot, dict) else {}
    plan = next((row for row in snapshot.get("plans", []) if isinstance(row, dict)), {})
    return plan.get("product_id"), plan.get("plan_id"), plan.get("product_code"), plan.get("plan_code")


def _effective_scope(queryset, policy, as_of):
    product_id, plan_id, product_code, plan_code = _scope(policy)
    if product_id:
        queryset = queryset.filter(Q(product_id=product_id) | Q(product__isnull=True))
    elif product_code:
        queryset = queryset.filter(Q(product__code=product_code) | Q(product__isnull=True))
    if plan_id:
        queryset = queryset.filter(Q(plan_id=plan_id) | Q(plan__isnull=True))
    elif plan_code:
        queryset = queryset.filter(Q(plan__code=plan_code) | Q(plan__isnull=True))
    return queryset.filter(
        Q(effective_from__isnull=True) | Q(effective_from__lte=as_of),
        Q(effective_to__isnull=True) | Q(effective_to__gte=as_of),
    ).order_by("-effective_from", "code")


def _loan_setup(policy, as_of):
    return _effective_scope(OLLoanSystemSetup.objects.filter(is_active=True), policy, as_of).first()


def _interest_control(policy, as_of):
    return _effective_scope(OLLoanInterestControl.objects.filter(is_active=True), policy, as_of).first()


def _cash_value(policy):
    snapshot = policy.contract_snapshot if isinstance(policy.contract_snapshot, dict) else {}
    return _decimal(snapshot.get("cash_value"))


def _loan_balance(policy):
    return sum(
        (
            _decimal(loan.outstanding_principal) + _decimal(loan.outstanding_interest)
            for loan in policy.loans.filter(status__in=[LoanStatus.DISBURSED, LoanStatus.PARTIALLY_REPAID])
        ),
        Decimal("0.00"),
    )


def _requisition_number(prefix):
    try:
        value = NumberingEngine.generate_number("FO_REQUISITION", FORequisition, field_name="requisition_number")
        if value:
            return value
    except Exception:
        pass
    return f"{prefix}-{date.today():%Y%m%d}-{uuid4().hex[:10].upper()}"


def _create_requisition(policy, amount, reason, prefix="REQ"):
    return FORequisition.objects.create(
        requisition_number=_requisition_number(prefix),
        department="OL_POLICY_FINANCE",
        amount=max(_decimal(amount), Decimal("0.00")),
        reason=reason,
        status="PENDING",
    )


def _policy_snapshot(policy):
    return {
        "status": policy.status,
        "cash_value": str(_cash_value(policy)),
        "loan_balance": str(_loan_balance(policy)),
        "contract_snapshot": policy.contract_snapshot,
    }


def _audit_event(policy, event_type, before, reason, *, actor=None, request=None, source_channel="API", event_type_code=None, metadata=None):
    after = AuditService.snapshot(policy)
    PolicyAuditLog.objects.create(
        policy=policy,
        actor=actor,
        event_type=event_type,
        from_status=before.get("status", ""),
        to_status=policy.status,
        before_snapshot=before,
        after_snapshot=after,
        reason=reason,
        source_channel=source_channel,
        correlation_id=getattr(request, "request_id", "") if request else "",
    )
    AuditService.log_action(
        event_type.upper(),
        policy,
        actor=actor,
        request=request,
        before_state=before,
        after_state=after,
        changed_fields=["status", "contract_snapshot"],
        reason=reason,
        source_channel=source_channel,
    )
    if event_type_code:
        emit_policy_loan_event(
            event_type_code,
            policy,
            actor=actor,
            from_status=before.get("status", ""),
            reason=reason,
            source_channel=source_channel,
            metadata=metadata,
        )


@transaction.atomic
def request_policy_loan(policy_id, *, amount, reason="", as_of=None, actor=None, request=None, source_channel="API"):
    as_of = _date(as_of)
    policy = Policy.objects.select_for_update().filter(pk=policy_id).first()
    if policy is None:
        from ..errors import not_found

        raise not_found(policy_id)
    if policy.status not in {PolicyStatus.ACTIVE, PolicyStatus.PAID_UP}:
        raise registry_error("POLICY_LOAN_BLOCKED", message=f"A {policy.get_status_display()} policy cannot request a loan.")
    setup = _loan_setup(policy, as_of)
    if setup is None or not setup.allow_policy_loans:
        raise registry_error("POLICY_LOAN_BLOCKED", message="Policy loans are not enabled for this product or plan.")
    amount = _decimal(amount)
    cash_value = _cash_value(policy)
    available = cash_value * _decimal(setup.max_loan_percentage_of_cash_value) / Decimal("100")
    existing = _loan_balance(policy)
    remaining = max(Decimal("0.00"), available - existing)
    minimum = _decimal(setup.min_loan_amount)
    maximum = _decimal(setup.max_loan_amount, remaining) if setup.max_loan_amount is not None else remaining
    if amount <= 0 or (minimum and amount < minimum) or amount > maximum or amount > remaining:
        raise registry_error(
            "POLICY_LOAN_BLOCKED",
            message="The requested loan is outside the configured cash-value and amount limits.",
            details={
                "cash_value": str(cash_value),
                "existing_loan_balance": str(existing),
                "available_loan_limit": str(remaining),
                "minimum_loan_amount": str(minimum),
                "maximum_loan_amount": str(maximum),
                "requested_amount": str(amount),
            },
            field_errors={"amount": [f"Enter an amount between {minimum} and {maximum}. "]},
        )
    control = _interest_control(policy, as_of)
    interest_rate = _decimal(control.interest_rate if control else 0)
    approval_required = bool(setup.require_approval)
    status = LoanStatus.REQUESTED if approval_required else LoanStatus.APPROVED
    approved_at = as_of if not approval_required else None
    reason = (reason or "Policy loan request.").strip()
    loan = PolicyLoan.objects.create(
        policy=policy,
        requested_at=as_of,
        approved_at=approved_at,
        principal_amount=amount,
        outstanding_principal=amount,
        interest_rate=interest_rate,
        currency=setup.loan_currency or policy.currency,
        status=status,
        last_interest_date=as_of if not approval_required else None,
        approval_required=approval_required,
        repayment_options=setup.repayment_options or [],
        reason=reason,
        created_by=actor,
        updated_by=actor,
    )
    _audit_event(
        policy,
        "PolicyLoanRequested",
        _policy_snapshot(policy),
        reason,
        actor=actor,
        request=request,
        source_channel=source_channel,
        event_type_code=POLICY_LOAN_REQUESTED,
        metadata={"loan_number": loan.loan_number, "amount": str(amount), "approval_required": approval_required},
    )
    return loan


@transaction.atomic
def approve_policy_loan(loan_id, *, as_of=None, actor=None, request=None, source_channel="API"):
    as_of = _date(as_of)
    loan = PolicyLoan.objects.select_for_update().select_related("policy").filter(pk=loan_id).first()
    if loan is None:
        raise registry_error("POLICY_LOAN_BLOCKED", message="The requested policy loan was not found.")
    if loan.status != LoanStatus.REQUESTED:
        raise registry_error("POLICY_LOAN_BLOCKED", message=f"Only requested loans can be approved; current status is {loan.status}.")
    before = _policy_snapshot(loan.policy)
    loan.status = LoanStatus.APPROVED
    loan.approved_at = as_of
    loan.updated_by = actor
    loan.save(update_fields=["status", "approved_at", "updated_by", "updated_at"])
    reason = f"Policy loan {loan.loan_number} approved."
    _audit_event(loan.policy, "PolicyLoanApproved", before, reason, actor=actor, request=request, source_channel=source_channel, event_type_code=POLICY_LOAN_APPROVED, metadata={"loan_number": loan.loan_number})
    return loan


@transaction.atomic
def disburse_policy_loan(loan_id, *, as_of=None, actor=None, request=None, source_channel="API"):
    as_of = _date(as_of)
    loan = PolicyLoan.objects.select_for_update().select_related("policy").filter(pk=loan_id).first()
    if loan is None:
        raise registry_error("POLICY_LOAN_BLOCKED", message="The requested policy loan was not found.")
    if loan.status != LoanStatus.APPROVED:
        raise registry_error("POLICY_LOAN_BLOCKED", message="Only an approved policy loan can be disbursed.")
    requisition = loan.payment_requisition or _create_requisition(loan.policy, loan.principal_amount, f"Disburse policy loan {loan.loan_number}.", prefix="LOAN")
    before = _policy_snapshot(loan.policy)
    loan.status = LoanStatus.DISBURSED
    loan.disbursed_at = as_of
    loan.payment_requisition = requisition
    loan.updated_by = actor
    loan.save(update_fields=["status", "disbursed_at", "payment_requisition", "updated_by", "updated_at"])
    reason = f"Policy loan {loan.loan_number} disbursed."
    _audit_event(loan.policy, "PolicyLoanDisbursed", before, reason, actor=actor, request=request, source_channel=source_channel, event_type_code=POLICY_LOAN_DISBURSED, metadata={"loan_number": loan.loan_number, "requisition_number": requisition.requisition_number})
    return loan


@transaction.atomic
def repay_policy_loan(loan_id, *, amount, payment_date=None, actor=None, request=None, source_channel="API"):
    payment_date = _date(payment_date)
    amount = _decimal(amount)
    loan = PolicyLoan.objects.select_for_update().select_related("policy").filter(pk=loan_id).first()
    if loan is None:
        raise registry_error("POLICY_LOAN_BLOCKED", message="The requested policy loan was not found.")
    if loan.status not in {LoanStatus.DISBURSED, LoanStatus.PARTIALLY_REPAID}:
        raise registry_error("POLICY_LOAN_BLOCKED", message="Only a disbursed or partially repaid loan can receive a repayment.")
    if amount <= 0:
        raise registry_error("POLICY_LOAN_BLOCKED", message="Repayment amount must be greater than zero.", field_errors={"amount": ["Enter a positive repayment amount."]})
    control = _interest_control(loan.policy, payment_date)
    rate = _decimal(control.interest_rate if control else loan.interest_rate)
    days = max(0, (payment_date - (loan.last_interest_date or loan.disbursed_at or loan.requested_at)).days)
    accrued = (_decimal(loan.outstanding_principal) * rate / Decimal("100") * Decimal(days) / Decimal("365")).quantize(Decimal("0.01"))
    loan.outstanding_interest += accrued
    loan.accrued_interest += accrued
    total_before = loan.outstanding_principal + loan.outstanding_interest
    if amount > total_before:
        amount = total_before
    interest_component = min(amount, loan.outstanding_interest)
    principal_component = amount - interest_component
    loan.outstanding_interest -= interest_component
    loan.outstanding_principal = max(Decimal("0.00"), loan.outstanding_principal - principal_component)
    loan.status = LoanStatus.REPAID if loan.outstanding_principal == 0 and loan.outstanding_interest == 0 else LoanStatus.PARTIALLY_REPAID
    loan.last_interest_date = payment_date
    loan.updated_by = actor
    loan.save(update_fields=["accrued_interest", "outstanding_interest", "outstanding_principal", "status", "last_interest_date", "updated_by", "updated_at"])
    repayment = PolicyLoanRepayment.objects.create(
        loan=loan,
        payment_date=payment_date,
        amount=amount,
        interest_component=interest_component,
        principal_component=principal_component,
        reason="Policy loan repayment.",
        created_by=actor,
        updated_by=actor,
    )
    reason = f"Policy loan {loan.loan_number} repayment posted."
    _audit_event(loan.policy, "PolicyLoanRepaid", _policy_snapshot(loan.policy), reason, actor=actor, request=request, source_channel=source_channel, event_type_code=POLICY_LOAN_REPAID, metadata={"loan_number": loan.loan_number, "repayment_number": repayment.repayment_number, "amount": str(amount), "interest_component": str(interest_component), "principal_component": str(principal_component)})
    return repayment


@transaction.atomic
def request_policy_withdrawal(policy_id, *, amount, reason="", as_of=None, actor=None, request=None, source_channel="API"):
    as_of = _date(as_of)
    policy = Policy.objects.select_for_update().filter(pk=policy_id).first()
    if policy is None:
        from ..errors import not_found

        raise not_found(policy_id)
    if policy.status not in {PolicyStatus.ACTIVE, PolicyStatus.PAID_UP}:
        raise registry_error("WITHDRAWAL_POLICY_INELIGIBLE", message=f"A {policy.get_status_display()} policy cannot request a withdrawal.")
    snapshot = dict(policy.contract_snapshot or {})
    if snapshot.get("allow_withdrawals") is False:
        raise registry_error("WITHDRAWAL_POLICY_INELIGIBLE", message="Withdrawals are not enabled for this policy product.")
    amount = _decimal(amount)
    cash_value = _cash_value(policy)
    loan_balance = _loan_balance(policy)
    previous = _decimal(snapshot.get("withdrawals_total"))
    available = max(Decimal("0.00"), cash_value - loan_balance - previous)
    if amount <= 0 or amount > available:
        raise registry_error(
            "WITHDRAWAL_LIMIT_EXCEEDED",
            message="The requested withdrawal exceeds the available cash value after loan balances and prior withdrawals.",
            details={"cash_value": str(cash_value), "loan_balance": str(loan_balance), "prior_withdrawals": str(previous), "available": str(available), "available_limit": str(available), "requested_amount": str(amount)},
            field_errors={"amount": [f"Enter an amount no greater than {available}. "]},
        )
    requires_approval = bool(snapshot.get("withdrawal_requires_approval", False))
    status = WithdrawalStatus.REQUESTED if requires_approval else WithdrawalStatus.APPROVED
    requisition = _create_requisition(policy, amount, f"Policy withdrawal {policy.policy_number}.", prefix="WITH")
    withdrawal = WithdrawalRequest.objects.create(
        policy=policy,
        request_date=as_of,
        amount=amount,
        cash_value_before=cash_value,
        loan_balance_before=loan_balance,
        net_amount=amount,
        status=status,
        payment_requisition=requisition,
        reason=(reason or "Policy withdrawal request.").strip(),
        created_by=actor,
        updated_by=actor,
    )
    snapshot["withdrawals_total"] = str(previous + amount)
    policy.contract_snapshot = snapshot
    policy.updated_by = actor
    policy.save(update_fields=["contract_snapshot", "updated_by", "updated_at"])
    _audit_event(
        policy,
        "PolicyWithdrawalRequested",
        _policy_snapshot(policy),
        withdrawal.reason,
        actor=actor,
        request=request,
        source_channel=source_channel,
        event_type_code=POLICY_WITHDRAWAL_REQUESTED,
        metadata={"withdrawal_number": withdrawal.request_number, "amount": str(amount), "requisition_number": requisition.requisition_number},
    )
    return withdrawal


def _withdrawal_finance_context(policy, as_of):
    snapshot = policy.contract_snapshot if isinstance(policy.contract_snapshot, dict) else {}
    cash_value = _cash_value(policy)
    loan_balance = _loan_balance(policy)
    previous = _decimal(snapshot.get("withdrawals_total"))
    available = max(Decimal("0.00"), cash_value - loan_balance - previous)
    configured_rate = snapshot.get("withdrawal_fee_rate", snapshot.get("withdrawal_fee_percent", "0"))
    fee_rate = _decimal(configured_rate)
    fee_basis = str(snapshot.get("withdrawal_fee_basis", "NONE") or "NONE").upper()
    if fee_rate > 0 and fee_basis == "NONE":
        fee_basis = "PERCENTAGE"
    return {
        "as_of": as_of,
        "cash_value": cash_value,
        "loan_balance": loan_balance,
        "prior_withdrawals": previous,
        "available": available,
        "fee_rate": fee_rate,
        "fee_basis": fee_basis,
    }


def _withdrawal_fee(amount, context):
    basis = context["fee_basis"]
    rate = context["fee_rate"]
    if basis in {"PERCENTAGE", "PERCENT", "RATE"}:
        return (amount * rate / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if basis in {"FIXED", "FIXED_AMOUNT"}:
        return min(amount, rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return Decimal("0.00")


def withdrawal_eligibility(policy_id, *, as_of=None):
    as_of = _date(as_of)
    policy = Policy.objects.select_related("partner", "agent").filter(pk=policy_id).first()
    if policy is None:
        from ..errors import not_found

        raise not_found(policy_id)
    context = _withdrawal_finance_context(policy, as_of)
    eligible = policy.status in {PolicyStatus.ACTIVE, PolicyStatus.PAID_UP} and (policy.contract_snapshot or {}).get("allow_withdrawals") is not False
    return policy, context, eligible


def estimate_policy_withdrawal(policy_id, *, amount, as_of=None):
    policy, context, eligible = withdrawal_eligibility(policy_id, as_of=as_of)
    amount = _decimal(amount, Decimal("-1"))
    if amount <= 0:
        raise registry_error("WITHDRAWAL_AMOUNT_REQUIRED", field_errors={"amount": ["Enter an amount greater than zero."]})
    if not eligible:
        raise registry_error("WITHDRAWAL_POLICY_INELIGIBLE")
    if amount > context["available"]:
        raise registry_error(
            "WITHDRAWAL_LIMIT_EXCEEDED",
            details={"available_limit": str(context["available"]), "requested_amount": str(amount)},
            field_errors={"amount": [f"Enter an amount no greater than {context['available']:.2f} {policy.currency}."]},
        )
    fee = _withdrawal_fee(amount, context)
    return policy, context, {"requested_amount": amount, "fee": fee, "net": amount - fee}


@transaction.atomic
def request_staff_withdrawal(policy_id, *, amount, reason="", as_of=None, actor=None, request=None, source_channel="WEB", idempotency_key=""):
    as_of = _date(as_of)
    policy = Policy.objects.select_for_update().select_related("partner", "agent").filter(pk=policy_id).first()
    if policy is None:
        from ..errors import not_found

        raise not_found(policy_id)
    reason = (reason or "").strip()
    if not reason:
        raise registry_error("WITHDRAWAL_REASON_REQUIRED", field_errors={"reason": ["Explain why the withdrawal is being requested."]})
    if idempotency_key:
        existing = WithdrawalRequest.objects.filter(policy=policy, idempotency_key=idempotency_key).first()
        if existing:
            return existing
    context = _withdrawal_finance_context(policy, as_of)
    amount = _decimal(amount, Decimal("-1"))
    if amount <= 0:
        raise registry_error("WITHDRAWAL_AMOUNT_REQUIRED", field_errors={"amount": ["Enter an amount greater than zero."]})
    if policy.status not in {PolicyStatus.ACTIVE, PolicyStatus.PAID_UP} or (policy.contract_snapshot or {}).get("allow_withdrawals") is False:
        raise registry_error("WITHDRAWAL_POLICY_INELIGIBLE")
    if amount > context["available"]:
        raise registry_error(
            "WITHDRAWAL_LIMIT_EXCEEDED",
            details={"cash_value": str(context["cash_value"]), "loan_balance": str(context["loan_balance"]), "prior_withdrawals": str(context["prior_withdrawals"]), "available": str(context["available"]), "available_limit": str(context["available"]), "requested_amount": str(amount)},
            field_errors={"amount": [f"Enter an amount no greater than {context['available']:.2f} {policy.currency}."]},
        )
    fee = _withdrawal_fee(amount, context)
    before = _policy_snapshot(policy)
    requires_approval = bool((policy.contract_snapshot or {}).get("withdrawal_requires_approval", True))
    status = WithdrawalStatus.REQUESTED if requires_approval else WithdrawalStatus.APPROVED
    now = timezone.now()
    requisition = _create_requisition(policy, amount - fee, f"Policy withdrawal {policy.policy_number}.", prefix="WITH")
    withdrawal = WithdrawalRequest.objects.create(
        policy=policy,
        request_date=as_of,
        amount=amount,
        cash_value_before=context["cash_value"],
        loan_balance_before=context["loan_balance"],
        cash_value_after=context["cash_value"] - amount,
        fee_amount=fee,
        fee_rate=context["fee_rate"],
        fee_basis=context["fee_basis"],
        net_amount=amount - fee,
        status=status,
        approved_at=now if status == WithdrawalStatus.APPROVED else None,
        payment_requisition=requisition,
        reason=reason,
        approval_reason="Automatically approved by policy configuration." if status == WithdrawalStatus.APPROVED else "",
        idempotency_key=idempotency_key or "",
        created_by=actor,
        updated_by=actor,
    )
    snapshot = dict(policy.contract_snapshot or {})
    snapshot["withdrawals_total"] = str(context["prior_withdrawals"] + amount)
    policy.contract_snapshot = snapshot
    policy.updated_by = actor
    policy.save(update_fields=["contract_snapshot", "updated_by", "updated_at"])
    _audit_event(policy, "PolicyWithdrawalRequested", before, reason, actor=actor, request=request, source_channel=source_channel, event_type_code=POLICY_WITHDRAWAL_REQUESTED, metadata={"withdrawal_number": withdrawal.request_number, "amount": str(amount), "fee_amount": str(fee), "net_amount": str(amount - fee), "requisition_number": requisition.requisition_number})
    return withdrawal


def _restore_withdrawal_amount(policy, amount, actor=None):
    snapshot = dict(policy.contract_snapshot or {})
    previous = _decimal(snapshot.get("withdrawals_total"))
    snapshot["withdrawals_total"] = str(max(Decimal("0.00"), previous - amount))
    policy.contract_snapshot = snapshot
    policy.updated_by = actor
    policy.save(update_fields=["contract_snapshot", "updated_by", "updated_at"])


@transaction.atomic
def transition_policy_withdrawal(withdrawal_id, *, action, reason="", payment_mode="", receipt_reference="", actor=None, request=None, source_channel="WEB"):
    withdrawal = WithdrawalRequest.objects.select_for_update().select_related("policy", "policy__partner", "policy__agent").filter(pk=withdrawal_id).first()
    if withdrawal is None:
        raise registry_error("WITHDRAWAL_NOT_FOUND")
    action = (action or "").lower().replace("-", "_")
    reason = (reason or "").strip()
    if action in {"approve", "reject", "cancel", "reverse"} and not reason:
        raise registry_error("WITHDRAWAL_REASON_REQUIRED", field_errors={"reason": ["Enter a clear reason before confirming this action."]})
    allowed = {
        "approve": {WithdrawalStatus.REQUESTED},
        "reject": {WithdrawalStatus.REQUESTED},
        "process_payout": {WithdrawalStatus.APPROVED},
        "cancel": {WithdrawalStatus.REQUESTED, WithdrawalStatus.APPROVED},
        "reverse": {WithdrawalStatus.PAID},
        "offset": {WithdrawalStatus.APPROVED, WithdrawalStatus.PROCESSING, WithdrawalStatus.PAID},
    }
    if action not in allowed or withdrawal.status not in allowed[action]:
        raise registry_error("WITHDRAWAL_ACTION_INVALID", details={"action": action, "current_status": withdrawal.status})
    policy = withdrawal.policy
    before = _policy_snapshot(policy)
    now = timezone.now()
    if action == "approve":
        withdrawal.status = WithdrawalStatus.APPROVED
        withdrawal.approved_at = now
        withdrawal.approval_reason = reason
    elif action == "reject":
        withdrawal.status = WithdrawalStatus.DECLINED
        withdrawal.cancellation_reason = reason
        _restore_withdrawal_amount(policy, withdrawal.amount, actor)
    elif action == "cancel":
        withdrawal.status = WithdrawalStatus.CANCELLED
        withdrawal.cancelled_at = now
        withdrawal.cancellation_reason = reason
        _restore_withdrawal_amount(policy, withdrawal.amount, actor)
    elif action == "reverse":
        withdrawal.status = WithdrawalStatus.REVERSED
        withdrawal.reversed_at = now
        withdrawal.reversal_reason = reason
        _restore_withdrawal_amount(policy, withdrawal.amount, actor)
        withdrawal.cash_value_after = withdrawal.cash_value_before
    elif action == "process_payout":
        if not str(payment_mode or "").strip() or not str(receipt_reference or "").strip():
            raise registry_error("WITHDRAWAL_PAYMENT_REQUIRED", field_errors={"payment_mode": ["Select a payment mode."], "receipt_reference": ["Enter the official receipt or transaction reference."]})
        withdrawal.status = WithdrawalStatus.PAID
        withdrawal.processed_at = now
        withdrawal.paid_at = now
        withdrawal.payment_mode = str(payment_mode).strip()
        withdrawal.receipt_reference = str(receipt_reference).strip()
        WithdrawalPayment.objects.create(withdrawal=withdrawal, payment_mode=withdrawal.payment_mode, receipt_reference=withdrawal.receipt_reference, amount=withdrawal.net_amount, currency=policy.currency, payment_date=now, status="COMPLETED", created_by=actor, updated_by=actor)
    elif action == "offset":
        reason = reason or "Withdrawal offset recorded during reconciliation."
    withdrawal.updated_by = actor
    withdrawal.save()
    _audit_event(policy, f"PolicyWithdrawal{action.title().replace('_', '')}", before, reason or f"Withdrawal {action} completed.", actor=actor, request=request, source_channel=source_channel, metadata={"withdrawal_number": withdrawal.request_number, "action": action, "payment_mode": payment_mode, "receipt_reference": receipt_reference})
    return withdrawal
