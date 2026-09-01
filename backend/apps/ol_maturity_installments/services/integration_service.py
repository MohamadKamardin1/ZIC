"""Integration seam for OL Maturity Installments.

Cross-context behaviour lives here so the core payment and lifecycle services
stay decoupled: the policy detail summary, the policy cancellation/surrender
guard, the claim status update on plan activation, and policyholder
notifications driven by the durable domain-event outbox.
"""

from collections import Counter
from decimal import Decimal

from django.db.models import Q
from django.utils import timezone

from apps.dashboard.models import DashboardNotification
from apps.governance.services.audit_service import AuditService
from apps.system_parameters.services.config_service import ConfigurationService
from apps.users.models import User

from ..events import (
    INSTALLMENT_PAYMENT_DUE,
    INSTALLMENT_PAYMENT_MISSED,
    INSTALLMENT_PLAN_COMPLETED,
)
from ..models import InstallmentItemStatus, InstallmentPlanStatus, OLMaturityInstallmentPlan

ZERO = Decimal("0.00")

ACTIVE_PLAN_STATUSES = (InstallmentPlanStatus.CREATED, InstallmentPlanStatus.ACTIVE)
ALLOW_POLICY_ACTION_PARAMETER = "INSTALLMENT_ALLOW_POLICY_ACTION_WITH_ACTIVE_PLAN"

CLAIM_PAID_VIA_INSTALLMENTS = "PAID_VIA_INSTALLMENTS"
CLAIM_ELIGIBLE_STATUSES = ("APPROVED", "PAID")

PENDING_ITEM_STATUSES = (InstallmentItemStatus.SCHEDULED, InstallmentItemStatus.PAYMENT_PENDING)


def _decimal(value, default=ZERO):
    if value in (None, ""):
        return default
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except (TypeError, ValueError):
        return default


def _money(value):
    return f"{_decimal(value):,.2f}"


def _partner_name(partner):
    return getattr(partner, "legal_name", "") or getattr(partner, "partner_number", "") or "Policyholder"


def _plan_totals(plan):
    paid = sum(
        (_decimal(item.amount) for item in plan.items.all() if item.status == InstallmentItemStatus.PAID),
        ZERO,
    )
    total = _decimal(plan.total_payable_amount)
    return total, paid, max(ZERO, total - paid)


def _next_due_date(plan):
    for item in (
        plan.items.filter(status__in=PENDING_ITEM_STATUSES).order_by("installment_number").only("due_date")
    ):
        return item.due_date
    return None


def _policy_recipients(policy):
    now = timezone.now()
    partner = policy.partner
    recipients = set()
    if getattr(partner, "email", ""):
        recipients.add(("EMAIL", partner.email))
    phone = getattr(partner, "mobile_number", "") or getattr(partner, "phone", "")
    if phone:
        recipients.add(("SMS", phone))
    links = Q(partner_links__partner_id=policy.partner_id, partner_links__link_status="ACTIVE") & (
        Q(partner_links__valid_from__isnull=True) | Q(partner_links__valid_from__lte=now)
    ) & (Q(partner_links__valid_to__isnull=True) | Q(partner_links__valid_to__gte=now))
    for user in User.objects.filter(links, is_active=True).distinct():
        if user.email:
            recipients.add(("EMAIL", user.email))
    return sorted(recipients)


def _linked_users(partner):
    return User.objects.filter(
        partner_links__partner_id=partner.pk,
        partner_links__link_status="ACTIVE",
        is_active=True,
    ).distinct()


def policy_installment_plan_summary(policy_id):
    """Active plan summary exposed on the policy detail payload."""
    plans = list(
        OLMaturityInstallmentPlan.objects.filter(policy_ref_id=policy_id)
        .select_related("policy_ref", "partner", "maturity_claim_ref")
        .prefetch_related("items")
        .order_by("plan_number")
    )
    by_status = Counter(plan.status for plan in plans)
    active = [plan for plan in plans if plan.status in ACTIVE_PLAN_STATUSES]
    active_outstanding = sum(_plan_totals(plan)[2] for plan in active)
    rows = []
    for plan in plans:
        total, paid, balance = _plan_totals(plan)
        rows.append(
            {
                "plan_number": plan.plan_number,
                "policy_number": plan.policy_ref.policy_number,
                "status": plan.status,
                "status_display": plan.get_status_display(),
                "currency": plan.currency,
                "total_amount": str(total),
                "paid_amount": str(paid),
                "balance": str(balance),
                "frequency": plan.frequency,
                "start_date": str(plan.start_date),
                "end_date": str(plan.end_date),
                "next_due_date": str(_next_due_date(plan)) if _next_due_date(plan) else "",
                "linked_claim_number": plan.maturity_claim_ref.claim_number if plan.maturity_claim_ref_id else "",
            }
        )
    return {
        "count": len(plans),
        "active_count": len(active),
        "completed_count": by_status.get(InstallmentPlanStatus.COMPLETED, 0),
        "cancelled_count": by_status.get(InstallmentPlanStatus.CANCELLED, 0),
        "terminated_count": by_status.get(InstallmentPlanStatus.TERMINATED, 0),
        "total_outstanding_amount": str(active_outstanding),
        "currency": plans[0].currency if plans else "TZS",
        "plans": rows,
    }


def blocking_active_installment_plans(policy_id):
    return list(
        OLMaturityInstallmentPlan.objects.filter(policy_ref_id=policy_id, status__in=ACTIVE_PLAN_STATUSES)
        .select_related("policy_ref", "partner")
        .order_by("plan_number")
    )


def installment_plan_policy_action_guard(policy_id):
    """Gate policy cancellation/surrender while a plan is still paying out.

    Returns ``{"allowed": ...}``; allowed only when no non-terminal plan exists
    or the configured System Parameter explicitly permits the action.
    """
    blocking = blocking_active_installment_plans(policy_id)
    parameter_allows = ConfigurationService.get_bool_parameter(ALLOW_POLICY_ACTION_PARAMETER, default=False)
    return {
        "allowed": not blocking or parameter_allows,
        "blocking_plans": [
            {
                "plan_number": plan.plan_number,
                "status": plan.status,
                "status_display": plan.get_status_display(),
                "currency": plan.currency,
                "total_amount": str(_decimal(plan.total_payable_amount)),
            }
            for plan in blocking
        ],
        "parameter": ALLOW_POLICY_ACTION_PARAMETER,
        "parameter_allows": parameter_allows,
    }


def _claim_snapshot(claim):
    return {
        "claim_number": claim.claim_number,
        "status": claim.status,
        "maturity_value": str(claim.maturity_value),
        "net_payout": str(claim.net_payout),
        "payout_method": claim.payout_method,
    }


def mark_claim_paid_via_installments(plan, *, actor=None, request=None, source_channel="API"):
    """Move a claim-backed plan's linked maturity claim to 'Paid via Installments'."""
    claim = plan.maturity_claim_ref
    if claim is None or claim.status == CLAIM_PAID_VIA_INSTALLMENTS:
        return claim, False
    if claim.status not in CLAIM_ELIGIBLE_STATUSES:
        return claim, False
    before = _claim_snapshot(claim)
    claim.status = CLAIM_PAID_VIA_INSTALLMENTS
    if actor:
        claim.updated_by = actor
    claim.save(update_fields=["status", "updated_by", "updated_at"] if actor else ["status", "updated_at"])
    after = _claim_snapshot(claim)
    reason = f"Maturity claim {claim.claim_number} is being paid through installment plan {plan.plan_number}."
    AuditService.log_action(
        "MATURITY_CLAIM_PAID_VIA_INSTALLMENTS",
        claim,
        actor=actor,
        request=request,
        before_state=before,
        after_state=after,
        changed_fields=["status"],
        reason=reason,
        source_channel=source_channel,
    )
    return claim, True


def activate_installment_plan(plan, *, item=None, actor=None, request=None, source_channel="API"):
    """Start a created plan when its first installment is confirmed paid.

    Moves CREATED -> ACTIVE and marks a linked maturity claim as paid via
    installments. Returns ``(plan, activated)``.
    """
    if plan.status != InstallmentPlanStatus.CREATED:
        return plan, False
    before = {"status": plan.status, "activated_at": str(plan.activated_at) if plan.activated_at else ""}
    plan.status = InstallmentPlanStatus.ACTIVE
    plan.activated_at = timezone.now()
    plan.activated_by = actor
    plan.save(update_fields=["status", "activated_at", "activated_by", "updated_at"])
    after = {"status": plan.status, "activated_at": str(plan.activated_at)}
    reason = (
        f"Plan {plan.plan_number} started when installment "
        f"{item.installment_number if item else 1} was confirmed paid."
    )
    AuditService.log_action(
        "INSTALLMENT_PLAN_ACTIVATED",
        plan,
        actor=actor,
        request=request,
        before_state=before,
        after_state=after,
        changed_fields=["status", "activated_at", "activated_by"],
        reason=reason,
        source_channel=source_channel,
    )
    if plan.maturity_claim_ref_id:
        mark_claim_paid_via_installments(plan, actor=actor, request=request, source_channel=source_channel)
    return plan, True


def _notification_copy(event_type, plan, *, amount=""):
    policy = plan.policy_ref
    currency = plan.currency
    if event_type == INSTALLMENT_PAYMENT_DUE:
        return (
            "Maturity installment payment due",
            f"A maturity installment of {amount} {currency} on plan {plan.plan_number} "
            f"for policy {policy.policy_number} is now due for payment.",
        )
    if event_type == INSTALLMENT_PAYMENT_MISSED:
        return (
            "Maturity installment missed",
            f"A maturity installment of {amount} {currency} on plan {plan.plan_number} "
            f"for policy {policy.policy_number} was missed and needs attention.",
        )
    if event_type == INSTALLMENT_PLAN_COMPLETED:
        return (
            "Maturity installment plan completed",
            f"Maturity installment plan {plan.plan_number} for policy {policy.policy_number} "
            f"has been fully paid and is now complete.",
        )
    return (
        "Maturity installment update",
        f"There is an update to maturity installment plan {plan.plan_number}.",
    )


def notify_installment_event(plan, event_type, *, amount="", source_channel="EVENT"):
    """Queue SMS/email and dashboard notifications for a plan domain event.

    Idempotent per (plan, event_type): the shared external key collapses
    duplicate dispatches, so an event is surfaced once to each channel.
    """
    from apps.ol_policies.models import PolicyNotificationLog

    policy = plan.policy_ref
    title, message = _notification_copy(event_type, plan, amount=amount)
    external_key = f"installment:{plan.pk}:{event_type}"
    recipients = _policy_recipients(policy)
    for channel, recipient in recipients:
        PolicyNotificationLog.objects.update_or_create(
            policy=policy,
            event_type=event_type,
            channel=channel,
            recipient=recipient,
            defaults={"message": message, "external_key": external_key, "status": "QUEUED"},
        )
    for user in _linked_users(plan.partner):
        DashboardNotification.objects.update_or_create(
            owner=user,
            external_key=external_key,
            defaults={
                "kind": "MATURITY_INSTALLMENT",
                "title": title,
                "message": message,
                "status": plan.status,
                "route": f"/ordinary-life/maturity-installments/{plan.pk}",
                "entity_type": "OLMaturityInstallmentPlan",
                "entity_id": str(plan.pk),
            },
        )
    return len(recipients)
