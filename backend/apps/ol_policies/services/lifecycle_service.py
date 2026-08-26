from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import Q

from apps.governance.services.audit_service import AuditService
from apps.ol_commitments.models import OLCommitment
from apps.ol_commitments.services.parameter_resolver import compute_grace_envelope
from apps.ol_parameters.models import OLReinstatementWindow

from ..errors import registry_error
from ..events import emit_policy_expired, emit_policy_lapsed, emit_policy_reinstated
from ..models import Policy, PolicyAuditLog, PolicyStatus


@dataclass
class LifecycleRunResult:
    processed: int = 0
    changed: int = 0
    skipped: int = 0


def _as_date(value):
    if value is None:
        return date.today()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError):
        raise registry_error(
            "POLICY_INVALID_STATUS",
            message="The lifecycle evaluation date must use YYYY-MM-DD format.",
            field_errors={"as_of": ["Enter a valid date in YYYY-MM-DD format."]},
        ) from None


def _decimal(value, default=Decimal("0.00")):
    if value in (None, ""):
        return default
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return default


def _active_policy_commitments(policy):
    return OLCommitment.objects.filter(
        source_reference=policy.policy_number,
        balance__gt=0,
    ).exclude(status__in=["COMPLETED", "CANCELLED", "REVERSED", "WAIVED", "CLOSED"])


def _policy_plan_scope(policy):
    snapshot = policy.contract_snapshot if isinstance(policy.contract_snapshot, dict) else {}
    plan = next((item for item in snapshot.get("plans", []) if isinstance(item, dict)), {})
    return plan.get("product_id"), plan.get("plan_id"), plan.get("product_code"), plan.get("plan_code")


def _grace_for_commitment(commitment, as_of):
    return compute_grace_envelope(
        commitment.due_date,
        product=commitment.product,
        plan=commitment.plan,
        premium_frequency=commitment.premium_frequency,
        as_of=as_of,
    )


def _record_transition(policy, *, event_type, before, reason, actor=None, source_channel="SYSTEM", request=None, event_emitter=None, metadata=None):
    PolicyAuditLog.objects.create(
        policy=policy,
        actor=actor,
        event_type=event_type,
        from_status=before.get("status", ""),
        to_status=policy.status,
        before_snapshot=before,
        after_snapshot=AuditService.snapshot(policy),
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
        after_state=AuditService.snapshot(policy),
        changed_fields=["status", "lapsed_at", "reinstated_at", "expired_at"],
        reason=reason,
        source_channel=source_channel,
    )
    if event_emitter:
        event_emitter(
            policy,
            actor=actor,
            from_status=before.get("status", ""),
            reason=reason,
            source_channel=source_channel,
            metadata=metadata or {},
        )


def _snapshot(policy):
    return {
        "status": policy.status,
        "lapsed_at": policy.lapsed_at.isoformat() if policy.lapsed_at else None,
        "reinstated_at": policy.reinstated_at.isoformat() if policy.reinstated_at else None,
        "expired_at": policy.expired_at.isoformat() if policy.expired_at else None,
    }


@transaction.atomic
def mark_policy_lapsed(policy, *, as_of=None, actor=None, source_channel="BATCH", request=None):
    """Mark one policy lapsed once an unpaid commitment passes its parameterized lapse date."""
    as_of = _as_date(as_of)
    if policy.status != PolicyStatus.ACTIVE:
        return False
    commitments = list(_active_policy_commitments(policy).order_by("due_date", "created_at"))
    overdue = []
    for commitment in commitments:
        envelope = _grace_for_commitment(commitment, as_of)
        if envelope.lapse_date and as_of >= envelope.lapse_date:
            overdue.append((commitment, envelope))
    if not overdue:
        return False

    before = _snapshot(policy)
    policy.status = PolicyStatus.LAPSED
    policy.lapsed_at = as_of
    policy.updated_by = actor
    policy.save(update_fields=["status", "lapsed_at", "updated_by", "updated_at"])
    reason = f"Policy lapsed after unpaid commitment passed its configured lapse date on {as_of.isoformat()}."
    _record_transition(
        policy,
        event_type="PolicyLapsed",
        before=before,
        reason=reason,
        actor=actor,
        source_channel=source_channel,
        request=request,
        event_emitter=emit_policy_lapsed,
        metadata={"commitment_numbers": [item.commitment_number for item, _ in overdue]},
    )
    from .integration_service import notify_policy_event

    notify_policy_event(policy, "PolicyLapsed", actor=actor, source_channel=source_channel)
    return True


def _resolve_reinstatement_window(policy, as_of):
    product_id, plan_id, product_code, plan_code = _policy_plan_scope(policy)
    queryset = OLReinstatementWindow.objects.filter(is_active=True)
    if product_id:
        queryset = queryset.filter(Q(product_id=product_id) | Q(product__isnull=True))
    elif product_code:
        queryset = queryset.filter(Q(product__code=product_code) | Q(product__isnull=True))
    if plan_id:
        queryset = queryset.filter(Q(plan_id=plan_id) | Q(plan__isnull=True))
    elif plan_code:
        queryset = queryset.filter(Q(plan__code=plan_code) | Q(plan__isnull=True))
    queryset = queryset.filter(
        Q(effective_from__isnull=True) | Q(effective_from__lte=as_of),
        Q(effective_to__isnull=True) | Q(effective_to__gte=as_of),
    )
    return queryset.order_by("-effective_from", "code").first()


@transaction.atomic
def reinstate_policy(
    policy_id,
    *,
    payment_amount=0,
    medical_clearance=False,
    actor=None,
    request=None,
    as_of=None,
    source_channel="API",
):
    as_of = _as_date(as_of)
    policy = Policy.objects.select_for_update().filter(pk=policy_id).first()
    if policy is None:
        from ..errors import not_found

        raise not_found(policy_id)
    if policy.status != PolicyStatus.LAPSED:
        raise registry_error(
            "POLICY_INVALID_STATUS",
            message=f"Only a lapsed policy can be reinstated; current status is {policy.status}.",
            details={"status": policy.status},
        )

    window = _resolve_reinstatement_window(policy, as_of)
    if window is None:
        raise registry_error(
            "POLICY_LAPSED",
            message="No active reinstatement window is configured for this policy.",
            resolution_steps=[
                "Configure an active OL Reinstatement Window for the product or plan.",
                "Retry reinstatement while the policy remains within the permitted window.",
            ],
        )
    lapsed_at = policy.lapsed_at or as_of
    if as_of > lapsed_at + timedelta(days=window.days_after_lapse):
        raise registry_error(
            "POLICY_LAPSED",
            message="The policy is outside its configured reinstatement window.",
            details={
                "lapsed_at": lapsed_at.isoformat(),
                "window_days": window.days_after_lapse,
                "last_reinstatement_date": (lapsed_at + timedelta(days=window.days_after_lapse)).isoformat(),
            },
        )
    if window.require_medical_underwriting and not medical_clearance:
        raise registry_error(
            "POLICY_LAPSED",
            message="Medical underwriting clearance is required before reinstatement.",
            field_errors={"medical_clearance": ["Provide underwriting clearance for this reinstatement."]},
        )

    commitments = list(_active_policy_commitments(policy).order_by("due_date", "created_at"))
    outstanding = sum((_decimal(item.balance) for item in commitments), Decimal("0.00"))
    interest_rate = _decimal(window.interest_rate)
    penalty_rate = _decimal(window.penalty_rate)
    interest = outstanding * (interest_rate + penalty_rate) / Decimal("100")
    required_amount = outstanding + interest
    paid = _decimal(payment_amount)
    if window.require_outstanding_premium_payment and paid < required_amount:
        raise registry_error(
            "POLICY_LAPSED",
            message="All outstanding premiums, interest, and penalties must be paid before reinstatement.",
            details={
                "outstanding_premium": str(outstanding),
                "interest_and_penalty": str(interest.quantize(Decimal("0.01"))),
                "required_amount": str(required_amount.quantize(Decimal("0.01"))),
                "payment_amount": str(paid),
            },
            field_errors={"payment_amount": [f"Enter at least {required_amount.quantize(Decimal('0.01'))}. "]},
        )

    before = _snapshot(policy)
    for commitment in commitments:
        commitment.amount_paid = commitment.premium_amount
        commitment.balance = Decimal("0.00")
        commitment.status = "COMPLETED"
        commitment.reason_code = "POLICY_REINSTATED"
        commitment.reason_text = f"Outstanding premium settled during policy reinstatement on {as_of.isoformat()}."
        commitment.updated_by = actor
        commitment.save(update_fields=["amount_paid", "balance", "status", "reason_code", "reason_text", "updated_by", "updated_at"])
    policy.status = PolicyStatus.ACTIVE
    policy.reinstated_at = as_of
    policy.updated_by = actor
    policy.save(update_fields=["status", "reinstated_at", "updated_by", "updated_at"])
    reason = f"Policy reinstated after settlement of {required_amount.quantize(Decimal('0.01'))} {policy.currency}."
    _record_transition(
        policy,
        event_type="PolicyReinstated",
        before=before,
        reason=reason,
        actor=actor,
        source_channel=source_channel,
        request=request,
        event_emitter=emit_policy_reinstated,
        metadata={"paid_amount": str(paid), "required_amount": str(required_amount.quantize(Decimal("0.01")))},
    )
    return policy


@transaction.atomic
def expire_policy(policy, *, as_of=None, actor=None, source_channel="BATCH", request=None):
    as_of = _as_date(as_of)
    if policy.status != PolicyStatus.ACTIVE or policy.maturity_date > as_of:
        return False
    before = _snapshot(policy)
    policy.status = PolicyStatus.EXPIRED
    policy.expired_at = as_of
    policy.updated_by = actor
    policy.save(update_fields=["status", "expired_at", "updated_by", "updated_at"])
    reason = f"Policy expired at maturity on {policy.maturity_date.isoformat()} without a maturity action."
    _record_transition(
        policy,
        event_type="PolicyExpired",
        before=before,
        reason=reason,
        actor=actor,
        source_channel=source_channel,
        request=request,
        event_emitter=emit_policy_expired,
    )
    return True


def process_policy_lapses(*, as_of=None, actor=None, source_channel="BATCH"):
    result = LifecycleRunResult()
    for policy in Policy.objects.filter(status=PolicyStatus.ACTIVE).iterator():
        result.processed += 1
        if mark_policy_lapsed(policy, as_of=as_of, actor=actor, source_channel=source_channel):
            result.changed += 1
        else:
            result.skipped += 1
    return result


def process_policy_expiry(*, as_of=None, actor=None, source_channel="BATCH"):
    result = LifecycleRunResult()
    today = _as_date(as_of)
    for policy in Policy.objects.filter(status=PolicyStatus.ACTIVE, maturity_date__lte=today).iterator():
        result.processed += 1
        if expire_policy(policy, as_of=today, actor=actor, source_channel=source_channel):
            result.changed += 1
        else:
            result.skipped += 1
    return result
