from apps.common.models import DomainEvent

AGGREGATE_TYPE = "OLMaturityInstallmentPlan"
INSTALLMENT_PLAN_CREATED = "InstallmentPlanCreated"
INSTALLMENT_PAYMENT_DUE = "InstallmentPaymentDue"
INSTALLMENT_PAYMENT_MISSED = "InstallmentPaymentMissed"
INSTALLMENT_PLAN_COMPLETED = "InstallmentPlanCompleted"

INSTALLMENT_DOMAIN_EVENTS = (
    INSTALLMENT_PLAN_CREATED,
    INSTALLMENT_PAYMENT_DUE,
    INSTALLMENT_PAYMENT_MISSED,
    INSTALLMENT_PLAN_COMPLETED,
)


def _plan_context(plan):
    return {
        "plan_id": str(plan.pk),
        "plan_number": plan.plan_number,
        "policy_id": str(plan.policy_ref_id),
        "policy_number": getattr(plan.policy_ref, "policy_number", ""),
        "maturity_claim_id": str(plan.maturity_claim_ref_id) if plan.maturity_claim_ref_id else None,
        "maturity_claim_number": getattr(plan.maturity_claim_ref, "claim_number", "")
        if plan.maturity_claim_ref_id
        else "",
        "currency": plan.currency,
        "total_payable_amount": str(plan.total_payable_amount),
    }


def emit_installment_event(
    event_type,
    plan,
    *,
    item=None,
    actor=None,
    from_status="",
    to_status="",
    reason="",
    source_channel="API",
    metadata=None,
):
    """Write a durable, replayable maturity installment event to the shared outbox."""
    payload = _plan_context(plan)
    payload.update(
        {
            "item_id": str(item.pk) if item else None,
            "installment_number": item.installment_number if item else None,
            "actor_id": str(actor.pk) if actor and getattr(actor, "pk", None) else None,
            "from_status": from_status,
            "to_status": to_status or plan.status,
            "reason": reason,
            "source_channel": source_channel,
            "metadata": metadata or {},
        }
    )
    return DomainEvent.objects.create(
        event_type=event_type,
        aggregate_type=AGGREGATE_TYPE,
        aggregate_id=str(plan.pk),
        payload=payload,
    )


def emit_installment_plan_created(plan, **kwargs):
    kwargs.setdefault("to_status", plan.status)
    return emit_installment_event(INSTALLMENT_PLAN_CREATED, plan, **kwargs)


def emit_installment_payment_due(plan, *, item, **kwargs):
    kwargs.setdefault("to_status", item.status)
    return emit_installment_event(INSTALLMENT_PAYMENT_DUE, plan, item=item, **kwargs)


def emit_installment_payment_missed(plan, *, item, **kwargs):
    kwargs.setdefault("to_status", item.status)
    return emit_installment_event(INSTALLMENT_PAYMENT_MISSED, plan, item=item, **kwargs)


def emit_installment_plan_completed(plan, **kwargs):
    kwargs.setdefault("to_status", plan.status)
    return emit_installment_event(INSTALLMENT_PLAN_COMPLETED, plan, **kwargs)
