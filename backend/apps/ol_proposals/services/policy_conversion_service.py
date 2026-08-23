"""BR-03-gated proposal → policy conversion.

Only a proposal whose first-premium commitment is fully allocated (Completed)
may become a policy. Idempotent: a second call returns the already-converted
policy without re-emitting anything.
"""

from datetime import date, timedelta

from apps.governance.services.audit_service import AuditService
from apps.ol_proposals import events as proposal_events
from apps.ol_proposals.errors import ProposalError, already_converted
from apps.ol_proposals.services.first_premium_service import ensure_first_premium_posted
from apps.ol_proposals.services.lifecycle_service import transition_proposal
from apps.ordinary_life.models import OLClient as LegacyOLClient
from apps.ordinary_life.models import OLPolicy as LegacyOLPolicy
from apps.ordinary_life.models import OLProposal as LegacyOLProposal
from apps.ordinary_life.models import OLQuotation as LegacyOLQuotation
from apps.system_parameters.services.numbering_service import NumberingEngine

LEGACY_DOB_FALLBACK = date(1970, 1, 1)


def _policy_params(proposal):
    plan_config = proposal.plan_configs.filter(is_selected=True).select_related("product_version", "plan").first()
    snapshot = proposal.financial_summary_snapshot or {}
    term_years = plan_config.term_years if plan_config else 1
    start_date = date.today()
    return {
        "product_version": plan_config.product_version if plan_config else None,
        "policyholder_partner": proposal.partner,
        "life_assured_partner": proposal.partner,
        "agent": proposal.agent_partner,
        "currency": proposal.currency,
        "sum_assured": snapshot.get("total_sum_assured") or (plan_config.base_sum_assured if plan_config else None),
        "premium_amount": snapshot.get("total_premium") or (plan_config.premium_amount if plan_config else None),
        "start_date": start_date,
        "end_date": start_date + timedelta(days=term_years * 365),
        "status": "ACTIVE",
    }


def _legacy_mirror(proposal):
    """Mirror the converted proposal into the legacy ordinary_life aggregates OLPolicy points at."""
    params = _policy_params(proposal)
    plan_config = (
        proposal.plan_configs.filter(is_selected=True)
        .select_related("product_version__product", "plan")
        .first()
    )
    partner = proposal.partner
    client, _ = LegacyOLClient.objects.get_or_create(
        id_number=getattr(partner, "partner_number", "") or f"OLP-{proposal.proposal_number}",
        defaults={
            "first_name": (getattr(partner, "first_name", "") or "-")[:100],
            "last_name": (getattr(partner, "surname", "") or "-")[:100],
            "date_of_birth": getattr(partner, "date_of_birth", None) or LEGACY_DOB_FALLBACK,
            "email": getattr(partner, "email", None),
        },
    )
    legacy_quotation, _ = LegacyOLQuotation.objects.get_or_create(
        quotation_number=proposal.quotation.quote_number,
        defaults={
            "client": client,
            "partner": partner,
            "product": plan_config.product_version.product if plan_config else None,
            "product_version": plan_config.product_version if plan_config else None,
            "sum_assured": params["sum_assured"] or 0,
            "premium_amount": params["premium_amount"] or 0,
            "currency": proposal.currency or "TZS",
            "status": "CONVERTED",
        },
    )
    legacy_proposal, _ = LegacyOLProposal.objects.get_or_create(
        quotation=legacy_quotation,
        defaults={
            "proposal_number": proposal.proposal_number,
            "underwriting_status": "APPROVED",
            "medical_required": bool(proposal.medical_required),
            "status": "APPROVED",
            "payment_required_amount": params["premium_amount"],
            "payment_currency": proposal.currency or "TZS",
        },
    )
    return legacy_proposal


def convert_proposal_to_policy(*, proposal, actor=None, request=None, source_channel="API"):
    """Convert a fully-funded proposal into a policy (idempotent, BR-03 enforced)."""
    if proposal.converted_policy_id:
        return proposal.converted_policy, False

    if proposal.status == "CONVERTED":
        raise already_converted()

    ensure_first_premium_posted(proposal)
    if proposal.status not in ("AWAITING_FIRST_PREMIUM", "PAYMENT_READY"):
        raise ProposalError(
            f"Cannot convert a '{proposal.status}' proposal to a policy.",
            error_code="PROPOSAL_INVALID_TRANSITION",
            status_code=422,
            resolution_steps=[
                "Complete the first-premium commitment so BR-03 passes.",
                "Only awaiting-first-premium (or payment-ready) proposals can convert.",
            ],
        )

    proposal.refresh_from_db()
    policy = LegacyOLPolicy.objects.create(
        policy_number=NumberingEngine.generate_number("OL_POLICY", LegacyOLPolicy, field_name="policy_number"),
        proposal=_legacy_mirror(proposal),
        version=1,
        **_policy_params(proposal),
    )

    proposal.converted_policy = policy
    proposal.save(update_fields=["converted_policy"])
    transition_proposal(
        proposal=proposal,
        to_status="CONVERTED",
        actor=actor,
        request=request,
        reason=f"Converted to policy {policy.policy_number}.",
        reason_code="CONVERTED",
        source_channel=source_channel,
    )

    proposal_events.emit_converted(
        proposal,
        actor=actor,
        reason=f"Proposal converted to policy {policy.policy_number}.",
        source_channel=source_channel,
        metadata={"policy_id": str(policy.pk), "policy_number": policy.policy_number},
    )

    AuditService.log_action(
        "CONVERT_TO_POLICY",
        proposal,
        actor=actor,
        request=request,
        after_state={"policy_number": policy.policy_number, "policy_id": str(policy.pk)},
        changed_fields=["converted_policy", "status"],
        reason=f"Converted proposal to policy {policy.policy_number}.",
        source_channel=source_channel,
    )
    return policy, True