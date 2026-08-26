from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from uuid import uuid4

from django.db import transaction
from django.db.models import Q, Sum

from apps.front_office.models import FORequisition
from apps.governance.services.audit_service import AuditService
from apps.ol_commitments.models import OLCommitment
from apps.ol_parameters.models import OLPaidUpRate, OLPaidUpSetup, OLSurrenderSetup, OLSurrenderValueRate
from apps.system_parameters.services.numbering_service import NumberingEngine

from ..errors import registry_error
from ..events import emit_policy_cancelled, emit_policy_paid_up, emit_policy_surrender_requested
from ..models import Policy, PolicyAuditLog, PolicyStatus, SurrenderRequest, SurrenderStatus

TERMINAL_STATUSES = {
    PolicyStatus.SURRENDERED,
    PolicyStatus.MATURED,
    PolicyStatus.EXPIRED,
    PolicyStatus.CANCELLED,
    PolicyStatus.CLAIM_SETTLED,
    PolicyStatus.TERMINATED,
}


def _decimal(value, default=Decimal("0.00")):
    if value in (None, ""):
        return default
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return default


def _date(value, default=None):
    if value in (None, ""):
        return default or date.today()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError):
        raise registry_error(
            "POLICY_ENDORSEMENT_INVALID",
            message="The policy servicing date must use YYYY-MM-DD format.",
            field_errors={"as_of": ["Enter a valid date in YYYY-MM-DD format."]},
        ) from None


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


def _surrender_setup(policy, as_of):
    return _effective_scope(OLSurrenderSetup.objects.filter(is_active=True), policy, as_of).first()


def _paid_up_setup(policy, as_of):
    return _effective_scope(OLPaidUpSetup.objects.filter(is_active=True), policy, as_of).first()


def _rate_row(model, policy, *, policy_year, as_of):
    queryset = _effective_scope(model.objects.filter(is_active=True), policy, as_of)
    return queryset.filter(
        Q(policy_year_from__isnull=True) | Q(policy_year_from__lte=policy_year),
        Q(policy_year_to__isnull=True) | Q(policy_year_to__gte=policy_year),
    ).order_by("-policy_year_from", "row_order", "code").first()


def _policy_year(policy, as_of):
    if as_of <= policy.risk_commencement_date:
        return 1
    return max(1, as_of.year - policy.risk_commencement_date.year + (as_of.timetuple().tm_yday >= policy.risk_commencement_date.timetuple().tm_yday))


def _policy_months(policy, as_of):
    months = (as_of.year - policy.risk_commencement_date.year) * 12 + as_of.month - policy.risk_commencement_date.month
    return max(0, months - (as_of.day < policy.risk_commencement_date.day))


def _commitments(policy):
    return OLCommitment.objects.filter(source_reference=policy.policy_number)


def _paid_premiums(policy):
    total = _commitments(policy).aggregate(value=Sum("amount_paid"))["value"] or 0
    return _decimal(total)


def _completed_premium_count(policy):
    return _commitments(policy).filter(status="COMPLETED").count()


def _active_loan_balance(policy):
    snapshot = policy.contract_snapshot if isinstance(policy.contract_snapshot, dict) else {}
    return _decimal(snapshot.get("active_loan_balance"))


def _requisition_number():
    try:
        value = NumberingEngine.generate_number("FO_REQUISITION", FORequisition, field_name="requisition_number")
        if value:
            return value
    except Exception:
        pass
    return f"REQ-{date.today():%Y%m%d}-{uuid4().hex[:10].upper()}"


def _create_requisition(policy, amount, reason):
    return FORequisition.objects.create(
        requisition_number=_requisition_number(),
        department="OL_POLICY_SERVICING",
        amount=max(_decimal(amount), Decimal("0.00")),
        reason=reason,
        status="PENDING",
    )


def _snapshot(policy):
    return {
        "status": policy.status,
        "sum_assured": str(policy.sum_assured),
        "premium_amount": str(policy.premium_amount),
        "contract_snapshot": policy.contract_snapshot,
    }


def _audit_transition(policy, *, event_type, before, reason, actor=None, request=None, source_channel="API", emitter=None, metadata=None):
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
        changed_fields=["status", "sum_assured", "contract_snapshot"],
        reason=reason,
        source_channel=source_channel,
    )
    if emitter:
        emitter(
            policy,
            actor=actor,
            from_status=before.get("status", ""),
            reason=reason,
            source_channel=source_channel,
            metadata=metadata or {},
        )


@transaction.atomic
def request_policy_surrender(policy_id, *, as_of=None, actor=None, request=None, source_channel="API"):
    as_of = _date(as_of)
    policy = Policy.objects.select_for_update().filter(pk=policy_id).first()
    if policy is None:
        from ..errors import not_found

        raise not_found(policy_id)
    existing = policy.surrender_requests.filter(status=SurrenderStatus.PENDING_PAYMENT).first()
    if existing:
        return existing, False
    if policy.status in TERMINAL_STATUSES or policy.status != PolicyStatus.ACTIVE:
        raise registry_error(
            "POLICY_SURRENDER_BLOCKED",
            message=f"A {policy.get_status_display()} policy is not eligible for surrender.",
            details={"status": policy.status},
        )
    loan_balance = _active_loan_balance(policy)
    if loan_balance > 0:
        raise registry_error(
            "POLICY_SURRENDER_BLOCKED",
            message="Surrender is blocked while an active policy loan remains unsettled.",
            details={"outstanding_loan_amount": str(loan_balance)},
            resolution_steps=[
                "Settle the active policy loan and its interest.",
                "Retry surrender after the loan balance is zero.",
            ],
        )
    setup = _surrender_setup(policy, as_of)
    if setup is None:
        raise registry_error(
            "POLICY_SURRENDER_BLOCKED",
            message="No active surrender setup is configured for this policy.",
            resolution_steps=["Configure OL Surrender Setup for the product or plan.", "Retry the surrender request."],
        )
    months = _policy_months(policy, as_of)
    paid_count = _completed_premium_count(policy)
    paid_amount = _paid_premiums(policy)
    expected_paid = policy.premium_amount * max(paid_count, 1)
    paid_ratio = (paid_amount / expected_paid * Decimal("100")) if expected_paid > 0 else Decimal("0")
    if months < setup.minimum_policy_months or paid_count < setup.minimum_premiums_paid or paid_ratio < setup.minimum_premium_paid_ratio:
        raise registry_error(
            "POLICY_SURRENDER_BLOCKED",
            message="The policy has not met the configured surrender eligibility thresholds.",
            details={
                "policy_months": months,
                "minimum_policy_months": setup.minimum_policy_months,
                "premiums_paid": paid_count,
                "minimum_premiums_paid": setup.minimum_premiums_paid,
                "paid_ratio": str(paid_ratio.quantize(Decimal("0.01"))),
                "minimum_premium_paid_ratio": str(setup.minimum_premium_paid_ratio),
            },
        )
    rate = _rate_row(OLSurrenderValueRate, policy, policy_year=_policy_year(policy, as_of), as_of=as_of)
    if rate is None:
        snapshot = policy.contract_snapshot if isinstance(policy.contract_snapshot, dict) else {}
        factor = _decimal(snapshot.get("surrender_value_rate"), Decimal("-1"))
    else:
        factor = _decimal(rate.rate_factor, Decimal("-1"))
    if factor < 0:
        raise registry_error(
            "POLICY_SURRENDER_BLOCKED",
            message="No active surrender-value rate is configured for the policy dimensions.",
            resolution_steps=["Configure an OL Surrender Value Rate row for the product, plan, and policy year.", "Retry the surrender request."],
        )
    surrender_value = (policy.sum_assured * factor).quantize(Decimal("0.01"))
    charge_type = (setup.surrender_charge_type or "NONE").upper()
    if charge_type == "PERCENTAGE":
        charges = surrender_value * _decimal(setup.surrender_charge_value) / Decimal("100")
    elif charge_type == "FACTOR":
        charges = surrender_value * _decimal(setup.surrender_charge_value)
    else:
        charges = _decimal(setup.surrender_charge_value) if charge_type == "FIXED" else Decimal("0.00")
    charges = charges.quantize(Decimal("0.01"))
    net_value = max(Decimal("0.00"), surrender_value - charges - loan_balance).quantize(Decimal("0.01"))
    reason = f"Surrender requested for policy {policy.policy_number}; net payout {net_value} {policy.currency}."
    requisition = _create_requisition(policy, net_value, reason)
    surrender = SurrenderRequest.objects.create(
        policy=policy,
        request_date=as_of,
        surrender_value=surrender_value,
        outstanding_loan_amount=loan_balance,
        charges=charges,
        net_surrender_value=net_value,
        status=SurrenderStatus.PENDING_PAYMENT,
        payment_requisition=requisition,
        reason=reason,
        created_by=actor,
        updated_by=actor,
    )
    before = _snapshot(policy)
    policy.status = PolicyStatus.SURRENDER_PENDING
    policy.updated_by = actor
    policy.save(update_fields=["status", "updated_by", "updated_at"])
    _audit_transition(
        policy,
        event_type="PolicySurrenderRequested",
        before=before,
        reason=reason,
        actor=actor,
        request=request,
        source_channel=source_channel,
        emitter=emit_policy_surrender_requested,
        metadata={"surrender_request_number": surrender.request_number, "requisition_number": requisition.requisition_number},
    )
    return surrender, True


@transaction.atomic
def convert_policy_to_paid_up(policy_id, *, as_of=None, actor=None, request=None, source_channel="API"):
    as_of = _date(as_of)
    policy = Policy.objects.select_for_update().filter(pk=policy_id).first()
    if policy is None:
        from ..errors import not_found

        raise not_found(policy_id)
    if policy.status != PolicyStatus.LAPSED:
        raise registry_error("POLICY_INVALID_STATUS", message="Only a lapsed policy can be converted to paid-up status.")
    setup = _paid_up_setup(policy, as_of)
    if setup is None or not setup.allow_paidup:
        raise registry_error("POLICY_LAPSED", message="Paid-up conversion is not configured for this policy.")
    months = _policy_months(policy, as_of)
    paid_count = _completed_premium_count(policy)
    if months < setup.minimum_policy_months or paid_count < setup.minimum_premiums_paid:
        raise registry_error(
            "POLICY_LAPSED",
            message="The policy has not met the configured paid-up eligibility thresholds.",
            details={"policy_months": months, "minimum_policy_months": setup.minimum_policy_months, "premiums_paid": paid_count, "minimum_premiums_paid": setup.minimum_premiums_paid},
        )
    rate = _rate_row(OLPaidUpRate, policy, policy_year=_policy_year(policy, as_of), as_of=as_of)
    if rate is None:
        raise registry_error(
            "POLICY_LAPSED",
            message="No active paid-up rate is configured for the policy dimensions.",
            resolution_steps=["Configure an OL Paid-Up Rate row for the product, plan, and policy year.", "Retry paid-up conversion."],
        )
    factor = _decimal(rate.rate_factor)
    new_sum_assured = (policy.sum_assured * factor).quantize(Decimal("0.01"))
    before = _snapshot(policy)
    snapshot = dict(policy.contract_snapshot or {})
    snapshot["paid_up"] = {
        "conversion_basis": setup.paidup_conversion_basis,
        "rate_factor": str(factor),
        "original_sum_assured": str(policy.sum_assured),
        "effective_date": as_of.isoformat(),
    }
    policy.sum_assured = new_sum_assured
    policy.status = PolicyStatus.PAID_UP
    policy.contract_snapshot = snapshot
    policy.updated_by = actor
    policy.save(update_fields=["sum_assured", "status", "contract_snapshot", "updated_by", "updated_at"])
    cancelled = 0
    for commitment in _commitments(policy).filter(balance__gt=0).exclude(status__in=["COMPLETED", "CANCELLED", "REVERSED", "WAIVED", "CLOSED"]):
        commitment.status = "CANCELLED"
        commitment.reason_code = "POLICY_PAID_UP"
        commitment.reason_text = "Future premium commitment stopped by paid-up conversion."
        commitment.amount_waived = max(
            Decimal("0.00"),
            _decimal(commitment.premium_amount) - _decimal(commitment.amount_paid),
        )
        commitment.balance = Decimal("0.00")
        commitment.updated_by = actor
        commitment.save(
            update_fields=[
                "status",
                "reason_code",
                "reason_text",
                "amount_waived",
                "balance",
                "updated_by",
                "updated_at",
            ]
        )
        cancelled += 1
    reason = f"Policy converted to paid-up status; sum assured reduced to {new_sum_assured} {policy.currency}."
    _audit_transition(
        policy,
        event_type="PolicyPaidUp",
        before=before,
        reason=reason,
        actor=actor,
        request=request,
        source_channel=source_channel,
        emitter=emit_policy_paid_up,
        metadata={"cancelled_commitments": cancelled, "rate_factor": str(factor)},
    )
    return policy


@transaction.atomic
def cancel_policy(policy_id, *, reason="", as_of=None, actor=None, request=None, source_channel="API"):
    as_of = _date(as_of)
    reason = (reason or "").strip()
    if not reason:
        raise registry_error(
            "POLICY_ENDORSEMENT_INVALID",
            message="A cancellation reason is required.",
            field_errors={"reason": ["Explain why the policy is being cancelled."]},
        )
    policy = Policy.objects.select_for_update().filter(pk=policy_id).first()
    if policy is None:
        from ..errors import not_found

        raise not_found(policy_id)
    if policy.status in TERMINAL_STATUSES:
        raise registry_error("POLICY_INVALID_STATUS", message=f"A {policy.get_status_display()} policy is already terminal.")
    snapshot = dict(policy.contract_snapshot or {})
    try:
        free_look_days = int(snapshot.get("free_look_days", 30))
    except (TypeError, ValueError):
        free_look_days = 30
    within_free_look = as_of <= policy.risk_commencement_date + timedelta(days=free_look_days)
    refund_amount = _paid_premiums(policy) if within_free_look else Decimal("0.00")
    requisition = _create_requisition(
        policy,
        refund_amount,
        f"{'Free-look full refund' if within_free_look else 'Standard cancellation'} for policy {policy.policy_number}.",
    ) if refund_amount > 0 else None
    before = _snapshot(policy)
    snapshot["cancellation"] = {
        "reason": reason,
        "effective_date": as_of.isoformat(),
        "within_free_look": within_free_look,
        "refund_amount": str(refund_amount.quantize(Decimal("0.01"))),
        "requisition_number": requisition.requisition_number if requisition else None,
    }
    policy.status = PolicyStatus.CANCELLED
    policy.contract_snapshot = snapshot
    policy.updated_by = actor
    policy.save(update_fields=["status", "contract_snapshot", "updated_by", "updated_at"])
    for commitment in _commitments(policy).filter(balance__gt=0).exclude(status__in=["COMPLETED", "CANCELLED", "REVERSED", "WAIVED", "CLOSED"]):
        commitment.status = "CANCELLED"
        commitment.reason_code = "POLICY_CANCELLED"
        commitment.reason_text = reason
        commitment.amount_waived = max(
            Decimal("0.00"),
            _decimal(commitment.premium_amount) - _decimal(commitment.amount_paid),
        )
        commitment.balance = Decimal("0.00")
        commitment.updated_by = actor
        commitment.save(
            update_fields=[
                "status",
                "reason_code",
                "reason_text",
                "amount_waived",
                "balance",
                "updated_by",
                "updated_at",
            ]
        )
    full_reason = f"Policy cancelled: {reason}"
    _audit_transition(
        policy,
        event_type="PolicyCancelled",
        before=before,
        reason=full_reason,
        actor=actor,
        request=request,
        source_channel=source_channel,
        emitter=emit_policy_cancelled,
        metadata={"within_free_look": within_free_look, "refund_amount": str(refund_amount), "requisition_number": requisition.requisition_number if requisition else None},
    )
    return policy, requisition
