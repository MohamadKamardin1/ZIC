from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone

from apps.governance.services.audit_service import AuditService
from apps.ol_proposals.models import OLProposal
from apps.ol_proposals.services.first_premium_service import first_premium_posted
from apps.ol_proposals.services.lifecycle_service import transition_proposal
from apps.system_parameters.services.numbering_service import NumberingEngine

from ..errors import not_found, registry_error
from ..events import emit_policy_issued
from ..models import Policy, PolicyAuditLog, PolicyBenefit, PolicyMember, PolicyRider, generate_policy_number

ALLOWED_PROPOSAL_STATUSES = {"AWAITING_FIRST_PREMIUM", "PAYMENT_READY"}


def _decimal(value, default=Decimal("0.00")):
    if value is None or value == "":
        return default
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return default


def _add_years(value, years):
    try:
        return value.replace(year=value.year + years)
    except ValueError:
        # A 29 February commencement has a 28 February anniversary in a
        # non-leap year; this keeps date arithmetic deterministic.
        return value.replace(year=value.year + years, day=28)


def _policy_number():
    try:
        value = NumberingEngine.generate_number("OL_POLICY", Policy, field_name="policy_number")
        if value:
            return value
    except Exception:
        # Numbering parameters are optional in the foundation environment. The
        # UUID-backed fallback preserves uniqueness until policy parameters exist.
        pass
    return generate_policy_number()


def _selected_plan_configs(proposal):
    return list(
        proposal.plan_configs.filter(is_selected=True)
        .select_related("plan", "product_version__product")
        .order_by("section_number", "id")
    )


def _plan_snapshot(config):
    plan = config.plan
    product_version = config.product_version
    product = getattr(product_version, "product", None)
    plan_code = getattr(plan, "code", "") or config.sub_product_code or ""
    plan_name = getattr(plan, "name", "") or config.plan_name_snapshot or plan_code
    product_code = getattr(product, "code", "")
    return {
        "section_number": config.section_number,
        "product_code": product_code,
        "plan_code": plan_code,
        "plan_name": plan_name,
        "base_sum_assured": str(config.base_sum_assured),
        "term_years": config.term_years,
        "payment_period_years": config.payment_period_years,
        "premium_frequency": config.premium_frequency,
        "quote_basis": config.quote_basis,
        "estimated_maturity_value": str(config.estimated_maturity_value or Decimal("0.00")),
        "premium_factor": config.premium_factor,
        "premium_amount": str(config.premium_amount or Decimal("0.00")),
    }


def _reference_from_commitment(commitment):
    allocation = commitment.allocations.filter(reversal_of__isnull=True).order_by("allocated_at", "created_at").first()
    return allocation.receipt_reference if allocation else ""


def _raise_invalid(message, *, details=None, steps=None):
    return registry_error(
        "POLICY_ISSUANCE_INVALID",
        message=message,
        details=details,
        resolution_steps=steps,
    )


@transaction.atomic
def issue_policy_from_proposal(proposal_id, *, actor=None, request=None, source_channel="API"):
    """Issue the canonical policy snapshot from a fully funded OL proposal.

    The row lock and unique proposal relation make retries safe. A successful
    retry returns ``(existing_policy, False)`` and does not emit a duplicate
    PolicyIssued event.
    """
    try:
        proposal = (
            OLProposal.objects.select_for_update()
            .select_related("quotation", "partner", "agent_partner", "first_premium_commitment")
            .prefetch_related("plan_configs", "members", "riders", "benefits")
            .get(pk=proposal_id)
        )
    except OLProposal.DoesNotExist:
        raise not_found(proposal_id) from None

    existing = Policy.objects.filter(proposal_ref_id=proposal.pk).first()
    if existing:
        if proposal.policy_ref != existing.pk:
            proposal.policy_ref = existing.pk
            proposal.save(update_fields=["policy_ref", "updated_at"])
        return existing, False

    if proposal.policy_ref:
        existing = Policy.objects.filter(pk=proposal.policy_ref).first()
        if existing:
            return existing, False

    if proposal.converted_policy_id or (proposal.status or "").upper() == "CONVERTED":
        raise registry_error(
            "POLICY_ALREADY_ISSUED",
            details={"proposal_id": str(proposal.pk), "proposal_number": proposal.proposal_number},
        )

    current_status = (proposal.status or "").strip().upper()
    if current_status not in ALLOWED_PROPOSAL_STATUSES:
        raise _raise_invalid(
            f"Proposal status '{proposal.status}' is not eligible for policy issuance.",
            details={"proposal_status": proposal.status, "allowed_statuses": sorted(ALLOWED_PROPOSAL_STATUSES)},
            steps=[
                "Move the proposal to Awaiting First Premium or Payment Ready.",
                "Confirm that underwriting and payment readiness requirements are complete.",
            ],
        )

    if not first_premium_posted(proposal):
        raise registry_error(
            "POLICY_FIRST_PREMIUM_NOT_POSTED",
            details={
                "proposal_id": str(proposal.pk),
                "commitment_id": str(proposal.first_premium_commitment_id) if proposal.first_premium_commitment_id else None,
            },
        )

    configs = _selected_plan_configs(proposal)
    if not configs:
        raise _raise_invalid(
            "The proposal has no selected plan configuration to issue.",
            steps=[
                "Select at least one plan on the proposal.",
                "Save the plan terms and recalculate the proposal financial summary.",
            ],
        )

    plan_snapshots = [_plan_snapshot(config) for config in configs]
    financial_snapshot = proposal.financial_summary_snapshot if isinstance(proposal.financial_summary_snapshot, dict) else {}
    sum_assured = _decimal(financial_snapshot.get("total_sum_assured"))
    if sum_assured <= 0:
        sum_assured = sum((_decimal(config.base_sum_assured) for config in configs), Decimal("0.00"))
    premium_amount = _decimal(financial_snapshot.get("total_premium"))
    if premium_amount <= 0:
        premium_amount = sum((_decimal(config.premium_amount) for config in configs), Decimal("0.00"))
    if sum_assured <= 0 or premium_amount <= 0:
        raise _raise_invalid(
            "The proposal does not contain positive sum assured and premium values.",
            details={"sum_assured": str(sum_assured), "premium_amount": str(premium_amount)},
            steps=[
                "Review the selected plan sum assured and premium values.",
                "Run quotation and proposal calculation again before issuing the policy.",
            ],
        )

    commencement_date = getattr(proposal.quotation, "quote_date", None) or timezone.localdate()
    term_years = max(config.term_years for config in configs)
    maturity_date = _add_years(commencement_date, term_years)
    plan_refs = []
    for snapshot in plan_snapshots:
        ref = snapshot["plan_code"] or snapshot["product_code"] or snapshot["plan_name"]
        if ref and ref not in plan_refs:
            plan_refs.append(ref)
    product_plan_ref = ", ".join(plan_refs)[:160]
    frequency = (configs[0].premium_frequency or "").strip().upper()
    snapshot = {
        "proposal_number": proposal.proposal_number,
        "quotation_number": getattr(proposal.quotation, "quote_number", ""),
        "prospect": proposal.prospect_snapshot or {},
        "plans": plan_snapshots,
        "financial_summary": financial_snapshot,
        "members": [
            {
                "member_type": member.member_type,
                "name": member.full_name_snapshot or f"{member.first_name} {member.last_name}".strip(),
                "date_of_birth": member.date_of_birth.isoformat() if member.date_of_birth else None,
                "gender": member.gender,
                "relationship": member.relationship,
                "benefit_amount": str(member.member_sum_assured or Decimal("0.00")),
            }
            for member in proposal.members.all()
        ],
    }

    policy = Policy.objects.create(
        policy_number=_policy_number(),
        proposal_ref=proposal,
        partner=proposal.partner,
        agent=proposal.agent_partner,
        product_plan_ref=product_plan_ref or "OL_POLICY_PLAN",
        currency=(proposal.currency or "TZS").strip().upper(),
        sum_assured=sum_assured,
        premium_amount=premium_amount,
        premium_frequency=frequency,
        term_years=term_years,
        risk_commencement_date=commencement_date,
        maturity_date=maturity_date,
        status="ACTIVE",
        first_premium_receipt_ref=_reference_from_commitment(proposal.first_premium_commitment),
        contract_snapshot=snapshot,
        version=1,
        created_by=actor,
        updated_by=actor,
    )

    for member in proposal.members.all():
        PolicyMember.objects.create(
            policy=policy,
            member_relation=member.relationship or member.member_type,
            name=member.full_name_snapshot or f"{member.first_name} {member.last_name}".strip(),
            dob=member.date_of_birth or commencement_date,
            gender=member.gender or "UNKNOWN",
            benefit_amount=member.member_sum_assured or sum_assured,
            created_by=actor,
            updated_by=actor,
        )

    for rider in proposal.riders.filter(is_selected=True).select_related("rider"):
        PolicyRider.objects.create(
            policy=policy,
            rider_code=getattr(rider.rider, "code", "") or rider.rider_name_snapshot or str(rider.rider_id),
            sum_assured=rider.rider_sum_assured,
            amount=rider.benefit_value,
            premium=rider.premium_amount or Decimal("0.00"),
            created_by=actor,
            updated_by=actor,
        )

    for benefit in proposal.benefits.filter(is_selected=True):
        PolicyBenefit.objects.create(
            policy=policy,
            benefit_type=benefit.benefit_type or benefit.code,
            calculation_basis=benefit.basis,
            amount=benefit.value or benefit.sum_assured or Decimal("0.00"),
            created_by=actor,
            updated_by=actor,
        )

    proposal.policy_ref = policy.pk
    transition_proposal(
        proposal=proposal,
        to_status="CONVERTED",
        actor=actor,
        request=request,
        reason=f"Issued policy {policy.policy_number} from proposal {proposal.proposal_number}.",
        reason_code="POLICY_ISSUED",
        source_channel=source_channel,
        force=True,
    )
    proposal.save(update_fields=["policy_ref", "updated_at"])

    reason = f"Policy {policy.policy_number} issued from proposal {proposal.proposal_number}."
    PolicyAuditLog.objects.create(
        policy=policy,
        actor=actor,
        event_type="PolicyIssued",
        from_status="",
        to_status=policy.status,
        before_snapshot={},
        after_snapshot=AuditService.snapshot(policy),
        reason=reason,
        source_channel=source_channel,
        correlation_id=getattr(request, "request_id", "") if request else "",
    )
    AuditService.log_create(policy, actor=actor, request=request, reason=reason, source_channel=source_channel)
    emit_policy_issued(
        policy,
        actor=actor,
        reason=reason,
        source_channel=source_channel,
        metadata={
            "renewal_commitment_requested": bool(frequency and term_years > 1),
            "first_premium_commitment_id": str(proposal.first_premium_commitment_id)
            if proposal.first_premium_commitment_id
            else None,
        },
    )
    return policy, True
