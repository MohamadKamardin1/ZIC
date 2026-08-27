from django.db.models import Q
from django.utils import timezone

from apps.dashboard.models import DashboardNotification
from apps.ol_policies.models import PolicyNotificationLog
from apps.users.models import User


EVENT_COPY = {
    "ClaimRegistered": (
        "Claim registered",
        "Your claim {claim_number} has been registered and is now under review.",
    ),
    "ClaimAssessed": (
        "Claim assessed",
        "Your claim {claim_number} has completed assessment and is awaiting the next payment step.",
    ),
    "ClaimSettled": (
        "Claim settled",
        "Your claim {claim_number} has been settled. Payment reference: {payment_reference}.",
    ),
}


def _notification_recipients(claim):
    policy = claim.policy_ref
    partner = policy.partner
    recipients = set()
    email = getattr(partner, "email", "") or ""
    phone = getattr(partner, "mobile_number", "") or getattr(partner, "phone", "") or ""
    if email:
        recipients.add(("EMAIL", email))
    if phone:
        recipients.add(("SMS", phone))
    now = timezone.now()
    link_scope = Q(partner_links__partner_id=policy.partner_id, partner_links__link_status="ACTIVE") & (
        Q(partner_links__valid_from__isnull=True) | Q(partner_links__valid_from__lte=now)
    ) & (Q(partner_links__valid_to__isnull=True) | Q(partner_links__valid_to__gte=now))
    linked_users = User.objects.filter(Q(partner_id=policy.partner_id) | link_scope, is_active=True).distinct()
    for user in linked_users:
        if user.email:
            recipients.add(("EMAIL", user.email))
    return sorted(recipients), linked_users


def notify_claim_event(claim, event_type, *, actor=None, source_channel="EVENT"):
    title_template = EVENT_COPY.get(event_type)
    if not title_template:
        return {"created": 0, "channels": []}
    title, message_template = title_template
    payment_reference = getattr(claim, "payment_reference", "") or "not yet assigned"
    message = message_template.format(claim_number=claim.claim_number, payment_reference=payment_reference)
    recipients, linked_users = _notification_recipients(claim)
    for channel, recipient in recipients:
        PolicyNotificationLog.objects.update_or_create(
            policy=claim.policy_ref,
            event_type=event_type,
            channel=channel,
            recipient=recipient,
            defaults={
                "message": message,
                "external_key": f"claim:{claim.pk}:{event_type}",
                "status": "QUEUED",
            },
        )
    for user in linked_users:
        DashboardNotification.objects.update_or_create(
            owner=user,
            external_key=f"claim:{claim.pk}:{event_type}",
            defaults={
                "kind": "CLAIM",
                "title": title,
                "message": message,
                "status": claim.status,
                "route": f"/ordinary-life/claims/{claim.claim_number}",
                "entity_type": "OLClaim",
                "entity_id": str(claim.pk),
            },
        )
    return {"created": len(recipients), "channels": sorted({channel for channel, _ in recipients})}
