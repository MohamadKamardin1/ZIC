from apps.common.models import DomainEvent

AGGREGATE_TYPE = "Policy"
POLICY_ISSUED = "PolicyIssued"
POLICY_ENDORSED = "PolicyEndorsed"


def emit_policy_endorsed(policy, endorsement, *, actor=None, reason="", source_channel="API", metadata=None):
    payload = {
        "policy_id": str(policy.pk),
        "policy_number": policy.policy_number,
        "endorsement_id": str(endorsement.pk),
        "endorsement_number": endorsement.endorsement_number,
        "endorsement_type": endorsement.endorsement_type,
        "from_status": endorsement.before_snapshot.get("status", ""),
        "to_status": policy.status,
        "actor_id": str(actor.pk) if actor and getattr(actor, "pk", None) else None,
        "reason": reason,
        "source_channel": source_channel,
        "metadata": metadata or {},
    }
    return DomainEvent.objects.create(
        event_type=POLICY_ENDORSED,
        aggregate_type=AGGREGATE_TYPE,
        aggregate_id=str(policy.pk),
        payload=payload,
    )


def emit_policy_issued(policy, *, actor=None, reason="", source_channel="API", metadata=None):
    payload = {
        "policy_id": str(policy.pk),
        "policy_number": policy.policy_number,
        "proposal_id": str(policy.proposal_ref_id),
        "proposal_number": getattr(policy.proposal_ref, "proposal_number", ""),
        "partner_id": str(policy.partner_id),
        "product_plan_ref": policy.product_plan_ref,
        "currency": policy.currency,
        "sum_assured": str(policy.sum_assured),
        "premium_amount": str(policy.premium_amount),
        "premium_frequency": policy.premium_frequency,
        "term_years": policy.term_years,
        "status": policy.status,
        "actor_id": str(actor.pk) if actor and getattr(actor, "pk", None) else None,
        "reason": reason,
        "source_channel": source_channel,
        "metadata": metadata or {},
    }
    return DomainEvent.objects.create(
        event_type=POLICY_ISSUED,
        aggregate_type=AGGREGATE_TYPE,
        aggregate_id=str(policy.pk),
        payload=payload,
    )
