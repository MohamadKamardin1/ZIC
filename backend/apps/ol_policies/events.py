from apps.common.models import DomainEvent

AGGREGATE_TYPE = "Policy"
POLICY_ISSUED = "PolicyIssued"
POLICY_ENDORSED = "PolicyEndorsed"
POLICY_LAPSED = "PolicyLapsed"
POLICY_REINSTATED = "PolicyReinstated"
POLICY_EXPIRED = "PolicyExpired"
POLICY_SURRENDER_REQUESTED = "PolicySurrenderRequested"
POLICY_PAID_UP = "PolicyPaidUp"
POLICY_CANCELLED = "PolicyCancelled"
POLICY_LOAN_REQUESTED = "PolicyLoanRequested"
POLICY_LOAN_APPROVED = "PolicyLoanApproved"
POLICY_LOAN_DISBURSED = "PolicyLoanDisbursed"
POLICY_LOAN_REPAID = "PolicyLoanRepaid"
POLICY_WITHDRAWAL_REQUESTED = "PolicyWithdrawalRequested"


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


def emit_lifecycle_event(event_type, policy, *, actor=None, from_status="", reason="", source_channel="SYSTEM", metadata=None):
    payload = {
        "policy_id": str(policy.pk),
        "policy_number": policy.policy_number,
        "actor_id": str(actor.pk) if actor and getattr(actor, "pk", None) else None,
        "from_status": from_status,
        "to_status": policy.status,
        "reason": reason,
        "source_channel": source_channel,
        "metadata": metadata or {},
    }
    return DomainEvent.objects.create(
        event_type=event_type,
        aggregate_type=AGGREGATE_TYPE,
        aggregate_id=str(policy.pk),
        payload=payload,
    )


def emit_policy_lapsed(policy, **kwargs):
    return emit_lifecycle_event(POLICY_LAPSED, policy, **kwargs)


def emit_policy_reinstated(policy, **kwargs):
    return emit_lifecycle_event(POLICY_REINSTATED, policy, **kwargs)


def emit_policy_expired(policy, **kwargs):
    return emit_lifecycle_event(POLICY_EXPIRED, policy, **kwargs)


def emit_policy_surrender_requested(policy, *, actor=None, from_status="ACTIVE", reason="", source_channel="API", metadata=None):
    return emit_lifecycle_event(
        POLICY_SURRENDER_REQUESTED,
        policy,
        actor=actor,
        from_status=from_status,
        reason=reason,
        source_channel=source_channel,
        metadata=metadata,
    )


def emit_policy_paid_up(policy, *, actor=None, from_status="LAPSED", reason="", source_channel="API", metadata=None):
    return emit_lifecycle_event(
        POLICY_PAID_UP,
        policy,
        actor=actor,
        from_status=from_status,
        reason=reason,
        source_channel=source_channel,
        metadata=metadata,
    )


def emit_policy_cancelled(policy, *, actor=None, from_status="", reason="", source_channel="API", metadata=None):
    return emit_lifecycle_event(
        POLICY_CANCELLED,
        policy,
        actor=actor,
        from_status=from_status,
        reason=reason,
        source_channel=source_channel,
        metadata=metadata,
    )


def emit_policy_finance_event(event_type, policy, *, actor=None, from_status="", reason="", source_channel="API", metadata=None):
    return emit_lifecycle_event(
        event_type,
        policy,
        actor=actor,
        from_status=from_status,
        reason=reason,
        source_channel=source_channel,
        metadata=metadata,
    )


def emit_policy_loan_event(event_type, policy, *, actor=None, from_status="", reason="", source_channel="API", metadata=None):
    return emit_policy_finance_event(
        event_type,
        policy,
        actor=actor,
        from_status=from_status,
        reason=reason,
        source_channel=source_channel,
        metadata=metadata,
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
