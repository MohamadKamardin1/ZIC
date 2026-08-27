from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone

from apps.dashboard.models import DashboardNotification
from apps.governance.services.audit_service import AuditService
from apps.ol_policies.models import Policy
from apps.users.models import User

from ..models import LoanStatus, OLLoan
from .default_service import process_loan_offset


ZERO = Decimal("0.00")


SETTLEMENT_EVENT_MAP = {
    "PolicyClaimSettledApplied": ("CLAIM", "claim_id", "settlement_amount"),
    "PolicyMaturityPaid": ("MATURITY", "claim_number", "maturity_value"),
    "PolicySurrenderPaid": ("SURRENDER", "surrender_request_number", "settlement_amount"),
    "PolicySurrenderSettled": ("SURRENDER", "surrender_request_number", "settlement_amount"),
}


def _decimal(value, default=ZERO):
    if value in (None, ""):
        return default
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError):
        return default


def _partner_name(partner):
    return getattr(partner, "legal_name", "") or getattr(partner, "partner_number", "") or "Policyholder"


def _policy_snapshot(policy):
    value = getattr(policy, "contract_snapshot", None)
    return value if isinstance(value, dict) else {}


def policy_loan_summary(policy_id):
    loans = list(
        OLLoan.objects.filter(policy_ref_id=policy_id)
        .select_related("partner", "policy_ref")
        .order_by("loan_number")
    )
    by_status = Counter(loan.status for loan in loans)
    return {
        "count": len(loans),
        "outstanding_balance": str(sum((_decimal(loan.outstanding_balance) for loan in loans), ZERO)),
        "active_count": sum(by_status.get(status, 0) for status in (LoanStatus.ACTIVE, LoanStatus.PARTIALLY_REPAID)),
        "defaulted_count": by_status.get(LoanStatus.DEFAULTED, 0),
        "settled_count": by_status.get(LoanStatus.SETTLED, 0) + by_status.get(LoanStatus.CLOSED, 0),
        "loans": [
            {
                "loan_number": loan.loan_number,
                "policy_number": getattr(loan.policy_ref, "policy_number", "Not recorded"),
                "policyholder": _partner_name(loan.partner),
                "status": loan.status,
                "status_display": loan.get_status_display(),
                "currency": loan.currency,
                "principal_amount": str(loan.principal_amount),
                "outstanding_balance": str(loan.outstanding_balance),
                "disbursement_date": loan.disbursement_date,
                "maturity_date": loan.maturity_date,
            }
            for loan in loans
        ],
    }


def blocking_defaulted_loans(policy_id):
    return list(
        OLLoan.objects.filter(
            policy_ref_id=policy_id,
            status=LoanStatus.DEFAULTED,
            outstanding_balance__gt=ZERO,
        )
        .select_related("policy_ref")
        .order_by("loan_number")
    )


def reinstatement_loan_guard(policy_id):
    loans = blocking_defaulted_loans(policy_id)
    return {
        "allowed": not loans,
        "blocking_loans": [
            {
                "loan_number": loan.loan_number,
                "outstanding_balance": str(loan.outstanding_balance),
                "currency": loan.currency,
                "status": loan.get_status_display(),
            }
            for loan in loans
        ],
    }


def _actor_from_event(payload):
    actor_id = payload.get("actor_id")
    if not actor_id:
        return None
    return User.objects.filter(pk=actor_id, is_active=True).first()


def _event_metadata(payload):
    metadata = payload.get("metadata")
    return metadata if isinstance(metadata, dict) else {}


def _settlement_reference_and_amount(event_type, payload, policy):
    source_type, reference_key, amount_key = SETTLEMENT_EVENT_MAP[event_type]
    metadata = _event_metadata(payload)
    reference = payload.get(reference_key) or metadata.get(reference_key) or metadata.get("claim_number") or metadata.get("surrender_request_number")
    if event_type == "PolicyMaturityPaid" and not reference:
        reference = metadata.get("claim_number") or "maturity"
    amount = _decimal(payload.get(amount_key))
    if event_type == "PolicyMaturityPaid" and amount <= ZERO:
        from apps.ol_policies.models import MaturityClaim

        claim = MaturityClaim.objects.filter(policy=policy, claim_number=reference).first()
        if claim is not None:
            amount = _decimal(claim.maturity_value or (claim.net_payout + claim.loan_deduction))
    return source_type, str(reference or "").strip(), amount


@transaction.atomic
def settle_policy_payout(
    *,
    policy_id,
    source_type,
    source_id,
    gross_payout,
    actor=None,
    request=None,
    source_channel="SYSTEM",
    reason="",
):
    policy = Policy.objects.select_for_update().filter(pk=policy_id).first()
    if policy is None:
        return {
            "policy_id": str(policy_id),
            "source_type": str(source_type).upper(),
            "source_id": str(source_id),
            "gross_payout": str(_decimal(gross_payout)),
            "offset_amount": "0.00",
            "net_payout": "0.00",
            "offsets": [],
            "changed": False,
        }
    gross = _decimal(gross_payout)
    offsets = []
    for loan in OLLoan.objects.filter(policy_ref=policy, outstanding_balance__gt=ZERO).exclude(
        status__in={LoanStatus.SETTLED, LoanStatus.CLOSED}
    ).order_by("loan_number"):
        result = process_loan_offset(
            loan,
            source_type,
            source_id,
            gross,
            actor=actor,
            request=request,
            source_channel=source_channel,
            reason=reason or f"{source_type.title()} payout offset for policy {policy.policy_number}.",
        )
        offsets.append(result.offset)
    offset_amount = sum((_decimal(offset.offset_amount) for offset in offsets), ZERO)
    net_payout = max(ZERO, gross - offset_amount).quantize(Decimal("0.01"))
    AuditService.log_action(
        action="POLICY_LOAN_NET_PAYOUT",
        instance=policy,
        actor=actor,
        request=request,
        after_state={
            "source_type": str(source_type).upper(),
            "source_id": str(source_id),
            "gross_payout": str(gross),
            "offset_amount": str(offset_amount),
            "net_payout": str(net_payout),
        },
        reason=reason or "Policy payout reconciled against OL Loan balances.",
        source_channel=source_channel,
    )
    return {
        "policy_id": str(policy.pk),
        "policy_number": policy.policy_number,
        "source_type": str(source_type).upper(),
        "source_id": str(source_id),
        "gross_payout": str(gross),
        "offset_amount": str(offset_amount),
        "net_payout": str(net_payout),
        "currency": policy.currency,
        "offsets": [
            {
                "source_type": offset.source_type,
                "source_id": offset.source_id,
                "offset_amount": str(offset.offset_amount),
                "remaining_payout": str(offset.remaining_payout),
            }
            for offset in offsets
        ],
        "changed": bool(offsets),
    }


@transaction.atomic
def apply_settlement_event(event, *, request=None):
    if event.event_type not in SETTLEMENT_EVENT_MAP:
        return None
    payload = event.payload if isinstance(event.payload, dict) else {}
    policy_id = payload.get("policy_id") or event.aggregate_id
    policy = Policy.objects.filter(pk=policy_id).first()
    if policy is None:
        return None
    source_type, source_id, amount = _settlement_reference_and_amount(event.event_type, payload, policy)
    if not source_id or amount <= ZERO:
        return {
            "policy_id": str(policy.pk),
            "source_type": source_type,
            "source_id": source_id,
            "gross_payout": str(amount),
            "offset_amount": "0.00",
            "net_payout": str(amount),
            "offsets": [],
            "changed": False,
            "skipped": True,
        }
    return settle_policy_payout(
        policy_id=policy.pk,
        source_type=source_type,
        source_id=source_id,
        gross_payout=amount,
        actor=_actor_from_event(payload),
        request=request,
        source_channel="SYSTEM",
        reason=f"Automatic OL Loan reconciliation for {event.event_type} {source_id}.",
    )


def _notification_recipients(policy):
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


def notify_loan_event(loan, event_type, *, actor=None, source_channel="EVENT"):
    from apps.ol_policies.models import PolicyNotificationLog

    messages = {
        "LoanDisbursed": ("Loan disbursed", f"Loan {loan.loan_number} has been disbursed."),
        "LoanDefaulted": ("Loan defaulted", f"Loan {loan.loan_number} requires attention because an installment is in default."),
        "LoanSettled": ("Loan settled", f"Loan {loan.loan_number} has been settled."),
        "LoanOffset": ("Loan offset", f"Loan {loan.loan_number} was offset against an eligible policy payout."),
    }
    title, message = messages.get(event_type, ("Loan update", f"There is an update to loan {loan.loan_number}."))
    recipients = _notification_recipients(loan.policy_ref)
    for channel, recipient in recipients:
        PolicyNotificationLog.objects.update_or_create(
            policy=loan.policy_ref,
            event_type=event_type,
            channel=channel,
            recipient=recipient,
            defaults={
                "message": message,
                "external_key": f"loan:{loan.pk}:{event_type}",
                "status": "QUEUED",
            },
        )
    linked_users = User.objects.filter(
        partner_links__partner_id=loan.partner_id,
        partner_links__link_status="ACTIVE",
        is_active=True,
    ).distinct()
    for user in linked_users:
        DashboardNotification.objects.update_or_create(
            owner=user,
            external_key=f"loan:{loan.pk}:{event_type}",
            defaults={
                "kind": "LOAN",
                "title": title,
                "message": message,
                "status": loan.status,
                "route": f"/ordinary-life/loans/{loan.pk}",
                "entity_type": "OLLoan",
                "entity_id": str(loan.pk),
            },
        )
    return len(recipients)


def loan_dashboard_hooks(queryset=None):
    queryset = queryset or OLLoan.objects.select_related("policy_ref")
    by_branch = defaultdict(lambda: {"loan_count": 0, "outstanding_balance": ZERO})
    by_product = defaultdict(lambda: {"loan_count": 0, "outstanding_balance": ZERO})
    total = 0
    defaulted = 0
    for loan in queryset:
        total += 1
        defaulted += int(loan.status == LoanStatus.DEFAULTED)
        snapshot = _policy_snapshot(loan.policy_ref)
        branch = str(snapshot.get("branch_name") or snapshot.get("branch_code") or snapshot.get("branch") or "Not recorded")
        product = str(snapshot.get("product_name") or snapshot.get("plan_name") or loan.policy_ref.product_plan_ref or "Not recorded")
        for target, key in ((by_branch, branch), (by_product, product)):
            target[key]["loan_count"] += 1
            target[key]["outstanding_balance"] += _decimal(loan.outstanding_balance)
    def normalize(values):
        return [
            {"name": name, "loan_count": row["loan_count"], "outstanding_balance": str(row["outstanding_balance"].quantize(Decimal("0.01")))}
            for name, row in sorted(values.items())
        ]
    return {
        "by_branch": normalize(by_branch),
        "by_product": normalize(by_product),
        "defaulted_count": defaulted,
        "loan_count": total,
        "default_rate": round(defaulted / total, 6) if total else 0,
        "timestamp": timezone.now(),
    }
