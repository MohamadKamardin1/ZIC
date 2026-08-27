from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone

from apps.governance.services.audit_service import AuditService
from apps.ol_parameters.models import OLClaimType
from apps.ol_policies.models import PolicyRider, PolicyRiderStatus, PolicyStatus
from apps.ol_policies.services.integration_service import apply_claim_settled

from ..errors import registry_error
from ..events import emit_claim_settled
from ..models import ClaimRequisitionStatus, ClaimStatus, OLClaim
from .loan_offset import apply_loan_offset, calculate_net_payout


DEATH_CLAIM_TYPES = {"DEATH", "TOTAL_DISABILITY", "FULL_SA"}
MATURITY_CLAIM_TYPES = {"MATURITY", "MATURITY_BENEFIT", "ENDOWMENT_MATURITY"}
PARTIAL_CLAIM_TYPES = {"CRITICAL_ILLNESS", "PARTIAL", "PARTIAL_DISABILITY"}
CONFIRMED_PAYMENT_STATUSES = {"CONFIRMED", "PAID", "COMPLETED"}


def _decimal(value, default=Decimal("0.00")):
    try:
        return Decimal(str(value)) if value not in (None, "") else default
    except (InvalidOperation, TypeError, ValueError):
        return default


def _claim_type_group(claim_type):
    code = str(claim_type or "").upper()
    configured = OLClaimType.objects.filter(code=claim_type, is_active=True).order_by("-effective_from", "-created_at").first()
    category = str(configured.claim_category if configured else code).upper()
    if code in MATURITY_CLAIM_TYPES or category in {"MATURITY", "MATURITY_CLAIM", "ENDOWMENT"}:
        return "MATURITY"
    if code in PARTIAL_CLAIM_TYPES or category in {"CRITICAL_ILLNESS", "PARTIAL", "PARTIAL_DISABILITY", "DISABILITY"}:
        return "PARTIAL"
    return "DEATH"


def _reinsurance_snapshot(claim, settlement_amount):
    contract_snapshot = claim.policy_ref.contract_snapshot if isinstance(claim.policy_ref.contract_snapshot, dict) else {}
    configured_retention = contract_snapshot.get("reinsurance_retention_amount")
    retention_rate = _decimal(contract_snapshot.get("reinsurance_retention_rate"), Decimal("0.00"))
    if configured_retention not in (None, ""):
        retention = min(max(_decimal(configured_retention), Decimal("0.00")), settlement_amount)
        basis = "configured_amount"
    elif retention_rate > 0:
        retention = min((settlement_amount * retention_rate / Decimal("100.00")), settlement_amount).quantize(Decimal("0.01"))
        basis = "configured_percentage"
    else:
        retention = settlement_amount
        basis = "conservative_default"
    ceded = max(settlement_amount - retention, Decimal("0.00")).quantize(Decimal("0.01"))
    return {
        "currency": claim.policy_ref.currency,
        "settlement_amount": str(settlement_amount.quantize(Decimal("0.01"))),
        "retention_amount": str(retention.quantize(Decimal("0.01"))),
        "ceded_amount": str(ceded),
        "retention_basis": basis,
        "treaty_calculation_pending": True,
    }


def on_claim_settled(claim, *, settlement_amount, actor=None, request=None, source_channel="API"):
    group = _claim_type_group(claim.claim_type)
    policy_status_before = claim.policy_ref.status
    target_policy_status = {
        "DEATH": PolicyStatus.CLAIM_SETTLED,
        "MATURITY": PolicyStatus.MATURITY_SETTLED,
    }.get(group)
    policy, policy_changed = apply_claim_settled(
        policy_id=claim.policy_ref_id,
        claim_id=claim.claim_number,
        claim_type=claim.claim_type,
        settlement_amount=settlement_amount,
        exhausted=group in {"DEATH", "MATURITY"},
        target_status=target_policy_status,
        actor=actor,
        request=request,
        source_channel=source_channel,
    )

    rider_updates = []
    sum_assured_update = None
    contract_snapshot = policy.contract_snapshot if isinstance(policy.contract_snapshot, dict) else {}
    if group == "PARTIAL" and bool(contract_snapshot.get("reduce_sum_assured_on_claim", False)):
        before_sum_assured = policy.sum_assured
        policy.sum_assured = max(policy.sum_assured - settlement_amount, Decimal("0.00"))
        policy.updated_by = actor
        policy.save(update_fields=["sum_assured", "updated_by", "updated_at"])
        sum_assured_update = {
            "before": str(before_sum_assured),
            "after": str(policy.sum_assured),
            "reduction": str(settlement_amount.quantize(Decimal("0.01"))),
        }
        AuditService.log_action(
            "POLICY_SUM_ASSURED_REDUCED",
            policy,
            actor=actor,
            request=request,
            before_state={"policy_number": policy.policy_number, "sum_assured": str(before_sum_assured)},
            after_state={"policy_number": policy.policy_number, "sum_assured": str(policy.sum_assured)},
            changed_fields=["sum_assured"],
            reason=f"Partial claim {claim.claim_number} reduced the configured policy sum assured.",
            source_channel=source_channel,
        )
    if group == "PARTIAL":
        benefit_codes = {str(item.benefit_type).upper() for item in claim.items.all()}
        riders = list(
            PolicyRider.objects.select_for_update()
            .filter(policy_id=claim.policy_ref_id, status=PolicyRiderStatus.ACTIVE)
            .order_by("rider_code", "created_at")
        )
        affected_riders = [rider for rider in riders if rider.rider_code.upper() in benefit_codes]
        if not affected_riders and riders:
            affected_riders = riders[:1]
        for rider in affected_riders:
            before = {"rider_code": rider.rider_code, "status": rider.status, "sum_assured": str(rider.sum_assured or 0)}
            rider.status = PolicyRiderStatus.EXHAUSTED
            rider.exhausted_at = timezone.localdate()
            rider.updated_by = actor
            rider.save(update_fields=["status", "exhausted_at", "updated_by", "updated_at"])
            rider_updates.append({**before, "status": rider.status, "exhausted_at": rider.exhausted_at.isoformat()})

    policy_update = {
        "policy_number": policy.policy_number,
        "policy_status_before": policy_status_before,
        "policy_status_after": policy.status,
        "policy_changed": policy_changed,
        "riders_exhausted": rider_updates,
        "sum_assured_update": sum_assured_update,
    }
    return policy, policy_update


@transaction.atomic
def settle_claim(
    claim_id,
    *,
    payment_reference,
    payment_status="CONFIRMED",
    actor=None,
    request=None,
    source_channel="API",
):
    claim = (
        OLClaim.objects.select_for_update()
        .select_related("policy_ref", "requisition", "requisition__payment_requisition")
        .prefetch_related("items")
        .filter(pk=claim_id)
        .first()
    )
    if claim is None:
        raise registry_error("CLAIM_NOT_FOUND")
    if claim.status == ClaimStatus.SETTLED:
        return claim, False
    if claim.status not in {ClaimStatus.APPROVED, ClaimStatus.REQUISITIONED}:
        raise registry_error(
            "CLAIM_SETTLEMENT_NOT_READY",
            details={"claim_number": claim.claim_number, "current_status": claim.status},
        )
    requisition = getattr(claim, "requisition", None)
    if requisition is None:
        raise registry_error(
            "CLAIM_SETTLEMENT_REQUISITION_REQUIRED",
            details={"claim_number": claim.claim_number},
        )
    if requisition.approval_required and claim.status != ClaimStatus.APPROVED:
        raise registry_error(
            "CLAIM_SETTLEMENT_APPROVAL_REQUIRED",
            details={"claim_number": claim.claim_number, "requisition_number": requisition.requisition_number},
        )
    payment_status = str(payment_status or "").upper()
    if payment_status not in CONFIRMED_PAYMENT_STATUSES:
        raise registry_error(
            "CLAIM_SETTLEMENT_PAYMENT_NOT_CONFIRMED",
            field_errors={"payment_status": ["Choose Confirmed, Paid, or Completed after Front Office confirms the payment."]},
        )
    payment_reference = str(payment_reference or "").strip()
    if not payment_reference:
        raise registry_error(
            "CLAIM_SETTLEMENT_PAYMENT_REFERENCE_REQUIRED",
            field_errors={"payment_reference": ["Enter the Front Office payment reference before settling the claim."]},
        )

    financial = calculate_net_payout(claim.pk)
    offset = apply_loan_offset(
        claim.pk,
        actor=actor,
        request=request,
        source_channel=source_channel,
        reason=f"Loan offset applied during settlement of claim {claim.claim_number}.",
    )
    settlement_amount = offset.net_payout if offset else _decimal(financial["net_payout"])
    before = {
        "claim_number": claim.claim_number,
        "status": claim.status,
        "settlement_amount": str(claim.settlement_amount or 0),
        "payment_reference": claim.payment_reference,
    }
    reinsurance = _reinsurance_snapshot(claim, settlement_amount)
    claim.status = ClaimStatus.SETTLED
    claim.settled_date = timezone.localdate()
    claim.settlement_amount = settlement_amount.quantize(Decimal("0.01"))
    claim.payment_reference = payment_reference
    claim.reinsurance_snapshot = reinsurance
    claim.updated_by = actor
    policy, policy_update = on_claim_settled(
        claim,
        settlement_amount=settlement_amount,
        actor=actor,
        request=request,
        source_channel=source_channel,
    )
    policy_update["policy_status_before"] = policy_update.get("policy_status_before") or policy.status
    claim.policy_update_snapshot = policy_update
    claim.save(
        update_fields=[
            "status",
            "settled_date",
            "settlement_amount",
            "payment_reference",
            "reinsurance_snapshot",
            "policy_update_snapshot",
            "updated_by",
            "updated_at",
        ]
    )
    requisition.status = ClaimRequisitionStatus.PAID
    requisition.updated_by = actor
    requisition.save(update_fields=["status", "updated_by", "updated_at"])
    if requisition.payment_requisition_id:
        requisition.payment_requisition.status = "PAID"
        requisition.payment_requisition.save(update_fields=["status", "updated_at"])
    after = {
        **before,
        "status": claim.status,
        "settled_date": claim.settled_date.isoformat(),
        "settlement_amount": str(claim.settlement_amount),
        "payment_reference": claim.payment_reference,
        "policy_update": policy_update,
        "reinsurance": reinsurance,
    }
    emit_claim_settled(
        claim,
        actor=actor,
        from_status=before["status"],
        to_status=claim.status,
        reason=f"Front Office payment {payment_reference} confirmed.",
        source_channel=source_channel,
        metadata={
            "payment_reference": payment_reference,
            "payment_status": payment_status,
            "settlement_amount": str(settlement_amount),
            "currency": claim.policy_ref.currency,
            "loan_offset": str(offset.offset_amount) if offset else "0.00",
            "policy_update": policy_update,
            "reinsurance": reinsurance,
        },
    )
    AuditService.log(
        action_type="CLAIM_SETTLED",
        entity_type="ol_claims.olclaim",
        entity_id=claim.pk,
        entity_repr=claim.claim_number,
        before_state=before,
        after_state=after,
        description=f"Claim {claim.claim_number} settled after payment confirmation.",
        actor=actor,
        reason=f"Front Office payment {payment_reference} confirmed.",
        source_channel=source_channel,
        request=request,
        app_label="ol_claims",
        model_name="olclaim",
        object_id=str(claim.pk),
        object_repr=claim.claim_number,
    )
    return claim, True
