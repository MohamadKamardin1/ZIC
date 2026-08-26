from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.common.models import DomainEvent
from apps.dashboard.models import DashboardNotification
from apps.governance.services.audit_service import AuditService
from apps.users.models import User

from ..errors import not_found
from ..models import Policy, PolicyAuditLog, PolicyNotificationLog, PolicyStatus

POLICY_MATURING_SOON = "PolicyMaturingSoon"
POLICY_CLAIM_SETTLED_APPLIED = "PolicyClaimSettledApplied"
ACTIVE_COVERAGE_STATUSES = {PolicyStatus.ACTIVE, PolicyStatus.PAID_UP}


def _decimal(value, default=Decimal("0.00")):
    if value in (None, ""):
        return default
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return default


def _age(dob, as_of=None):
    if not dob:
        return None
    as_of = as_of or date.today()
    return as_of.year - dob.year - ((as_of.month, as_of.day) < (dob.month, dob.day))


def _recipient_users(policy):
    now = timezone.now()
    link_scope = Q(
        partner_links__partner_id=policy.partner_id,
        partner_links__link_status="ACTIVE",
        partner_links__valid_from__lte=now,
    ) & (Q(partner_links__valid_to__isnull=True) | Q(partner_links__valid_to__gte=now))
    return User.objects.filter(is_active=True).filter(Q(partner_id=policy.partner_id) | link_scope).distinct()


def _policy_recipient_values(policy):
    partner = policy.partner
    recipients = []
    email = getattr(partner, "email", "") or ""
    phone = getattr(partner, "mobile_number", "") or getattr(partner, "phone", "") or ""
    if email:
        recipients.append(("EMAIL", email))
    if phone:
        recipients.append(("SMS", phone))
    for user in _recipient_users(policy):
        if user.email:
            recipients.append(("EMAIL", user.email))
    return sorted(set(recipients))


def notify_policy_event(policy, event_type, *, actor=None, source_channel="SYSTEM"):
    messages = {
        "PolicyIssued": ("Policy issued", f"Policy {policy.policy_number} has been issued and is now available."),
        "PolicyLapsed": ("Policy lapsed", f"Policy {policy.policy_number} has lapsed. Please contact ZIC to discuss reinstatement."),
        POLICY_MATURING_SOON: ("Policy maturity reminder", f"Policy {policy.policy_number} is approaching maturity on {policy.maturity_date.isoformat()} ."),
    }
    title, message = messages.get(event_type, ("Policy update", f"There is an update to policy {policy.policy_number}."))
    for channel, recipient in _policy_recipient_values(policy):
        external_key = f"policy:{policy.pk}:{event_type}:{policy.status}"
        PolicyNotificationLog.objects.get_or_create(
            policy=policy,
            event_type=event_type,
            channel=channel,
            recipient=recipient,
            defaults={"message": message, "external_key": external_key, "status": "QUEUED"},
        )
    for user in _recipient_users(policy):
        DashboardNotification.objects.update_or_create(
            owner=user,
            external_key=f"policy:{policy.pk}:{event_type}",
            defaults={
                "kind": "POLICY",
                "title": title,
                "message": message,
                "status": policy.status,
                "route": f"/ordinary-life/policies/{policy.pk}",
                "entity_type": "Policy",
                "entity_id": str(policy.pk),
            },
        )
    return PolicyNotificationLog.objects.filter(policy=policy, event_type=event_type).count()


def _policy_risk_details(policy, as_of=None):
    snapshot = policy.contract_snapshot if isinstance(policy.contract_snapshot, dict) else {}
    partner = policy.partner
    dob = getattr(partner, "date_of_birth", None) or snapshot.get("date_of_birth")
    if isinstance(dob, str):
        try:
            dob = date.fromisoformat(dob)
        except ValueError:
            dob = None
    occupation = (
        getattr(partner, "occupation", None)
        or getattr(partner, "occupation_name", None)
        or snapshot.get("occupation")
        or snapshot.get("occupation_name")
        or ""
    )
    return {
        "policy_number": policy.policy_number,
        "policy_id": str(policy.pk),
        "status": policy.status,
        "product_plan_ref": policy.product_plan_ref,
        "sum_assured": str(policy.sum_assured),
        "currency": policy.currency,
        "age": _age(dob, as_of),
        "date_of_birth": dob.isoformat() if isinstance(dob, date) else None,
        "occupation": str(occupation),
        "risk_commencement_date": policy.risk_commencement_date.isoformat(),
        "maturity_date": policy.maturity_date.isoformat(),
    }


def claim_registration_data(policy_id, *, actor=None):
    policy = Policy.objects.select_related("partner").prefetch_related("members", "benefits", "riders").filter(pk=policy_id).first()
    if policy is None:
        raise not_found(policy_id)
    return {
        "policy_number": policy.policy_number,
        "policy_id": str(policy.pk),
        "partner_name": str(policy.partner),
        "status": policy.status,
        "coverage_available": policy.status in ACTIVE_COVERAGE_STATUSES,
        "risk_commencement_date": policy.risk_commencement_date.isoformat(),
        "maturity_date": policy.maturity_date.isoformat(),
        "currency": policy.currency,
        "sum_assured": str(policy.sum_assured),
        "members": [
            {"relation": member.member_relation, "name": member.name, "benefit_amount": str(member.benefit_amount)}
            for member in policy.members.filter(is_active=True)
        ],
        "benefits": [
            {"benefit_type": benefit.benefit_type, "calculation_basis": benefit.calculation_basis, "amount": str(benefit.amount)}
            for benefit in policy.benefits.all()
        ],
        "riders": [
            {"rider_code": rider.rider_code, "sum_assured": str(rider.sum_assured or 0), "amount": str(rider.amount or 0)}
            for rider in policy.riders.all()
        ],
    }


def reinsurance_risk_data(policy_id, *, actor=None):
    policy = Policy.objects.select_related("partner").filter(pk=policy_id).first()
    if policy is None:
        raise not_found(policy_id)
    return _policy_risk_details(policy)


@transaction.atomic
def apply_claim_settled(*, policy_id=None, claim_id="", claim_type="", settlement_amount=None, exhausted=False, actor=None, request=None, source_channel="EVENT"):
    policy_id = policy_id or ""
    policy = Policy.objects.select_for_update().filter(pk=policy_id).first()
    if policy is None:
        raise not_found(policy_id)
    existing = DomainEvent.objects.filter(
        event_type=POLICY_CLAIM_SETTLED_APPLIED,
        aggregate_id=str(policy.pk),
        payload__claim_id=str(claim_id),
    ).first()
    if existing:
        return policy, False
    before = {"status": policy.status, "policy_number": policy.policy_number}
    exhausted = bool(exhausted) or str(claim_type).upper() in {"DEATH", "TOTAL_DISABILITY", "FULL_SA"}
    if exhausted:
        policy.status = PolicyStatus.CLAIM_SETTLED
        policy.save(update_fields=["status", "updated_by", "updated_at"] if actor else ["status", "updated_at"])
    after = {"status": policy.status, "policy_number": policy.policy_number}
    reason = f"Claim {claim_id or 'settlement'} settled against policy {policy.policy_number}."
    PolicyAuditLog.objects.create(
        policy=policy,
        actor=actor,
        event_type=POLICY_CLAIM_SETTLED_APPLIED,
        from_status=before["status"],
        to_status=after["status"],
        before_snapshot=before,
        after_snapshot=after,
        reason=reason,
        source_channel=source_channel,
        correlation_id=getattr(request, "request_id", "") if request else "",
    )
    AuditService.log_action(
        action=POLICY_CLAIM_SETTLED_APPLIED.upper(),
        instance=policy,
        actor=actor,
        request=request,
        before_state=before,
        after_state=after,
        changed_fields=["status"] if exhausted else [],
        reason=reason,
        source_channel=source_channel,
    )
    DomainEvent.objects.create(
        event_type=POLICY_CLAIM_SETTLED_APPLIED,
        aggregate_type="OLPolicy",
        aggregate_id=str(policy.pk),
        payload={
            "policy_id": str(policy.pk),
            "claim_id": str(claim_id),
            "claim_type": str(claim_type),
            "settlement_amount": str(_decimal(settlement_amount)),
            "exhausted": exhausted,
            "status": policy.status,
        },
    )
    return policy, True


def process_maturing_soon(*, as_of=None, window_days=30, actor=None, source_channel="BATCH"):
    as_of = as_of or date.today()
    end_date = as_of + timedelta(days=int(window_days))
    processed = 0
    for policy in Policy.objects.filter(status__in=ACTIVE_COVERAGE_STATUSES, maturity_date__gt=as_of, maturity_date__lte=end_date).iterator():
        processed += 1
        already = DomainEvent.objects.filter(
            event_type=POLICY_MATURING_SOON,
            aggregate_id=str(policy.pk),
            payload__notification_date=as_of.isoformat(),
        ).exists()
        if already:
            continue
        DomainEvent.objects.create(
            event_type=POLICY_MATURING_SOON,
            aggregate_type="OLPolicy",
            aggregate_id=str(policy.pk),
            payload={"policy_id": str(policy.pk), "policy_number": policy.policy_number, "maturity_date": policy.maturity_date.isoformat(), "notification_date": as_of.isoformat(), "window_days": int(window_days)},
        )
        notify_policy_event(policy, POLICY_MATURING_SOON, actor=actor, source_channel=source_channel)
    return {"processed": processed}


def policy_dashboard_hooks():
    active = Policy.objects.filter(status__in=ACTIVE_COVERAGE_STATUSES)
    annualized = Decimal("0.00")
    frequency_multiplier = {"ANNUALLY": Decimal("1"), "SEMI_ANNUALLY": Decimal("2"), "QUARTERLY": Decimal("4"), "MONTHLY": Decimal("12"), "SINGLE": Decimal("1")}
    for policy in active.only("premium_amount", "premium_frequency"):
        annualized += _decimal(policy.premium_amount) * frequency_multiplier.get(str(policy.premium_frequency).upper(), Decimal("1"))
    total = Policy.objects.count()
    lapsed = Policy.objects.filter(status=PolicyStatus.LAPSED).count()
    return {
        "active_policy_count": active.count(),
        "premium_income_annualized": str(annualized.quantize(Decimal("0.01"))),
        "currency": "TZS",
        "lapsed_ratio": round((lapsed / total) if total else 0, 6),
        "timestamp": timezone.now().isoformat(),
    }
