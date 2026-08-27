from datetime import date
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.governance.services.audit_service import AuditService
from apps.ol_parameters.models import OLMedicalLimit

from ..errors import registry_error
from ..events import emit_claim_medical_required, emit_claim_medical_result
from ..models import ClaimMedicalStatus, ClaimStatus, OLClaim
from .validation import _active_claim_type, _policy_product_codes, _effective_queryset



def _claim_amount(claim):
    return sum(
        (item.approved_amount if item.approved_amount is not None else item.calculated_amount)
        for item in claim.items.all()
    )


def _claim_age(claim):
    claimant = claim.claimant_ref or claim.claimants.filter(is_active=True).first()
    return getattr(claimant, "age", None) if claimant else None


def _medical_limit_applies(limit, claim, amount, age):
    if limit.product_id:
        product_codes = _policy_product_codes(claim.policy_ref)
        if not limit.product or limit.product.code.upper() not in product_codes:
            return False
    if limit.plan_id:
        plan_codes = _policy_product_codes(claim.policy_ref)
        if not limit.plan or limit.plan.code.upper() not in plan_codes:
            return False
    if age is not None and not (limit.age_from <= age <= limit.age_to):
        return False
    if age is None and limit.mandatory_flag and (limit.age_from > 0 or limit.age_to < 150):
        return False
    if limit.sum_assured_from is not None and amount < limit.sum_assured_from:
        return False
    if limit.sum_assured_to is not None and amount > limit.sum_assured_to:
        return False
    return True


def _active_medical_limits(claim):
    queryset = _effective_queryset(
        OLMedicalLimit.objects.select_related("medical_code", "product", "plan"),
        claim.claim_date,
    )
    return queryset.order_by("mandatory_flag", "limit_amount", "code")


def _medical_reasons(claim):
    config = _active_claim_type(claim.claim_type, claim.claim_date)
    rules = config.payable_to_rules if isinstance(config.payable_to_rules, dict) else {}
    reasons = []
    if rules.get("medical_required") or rules.get("require_medical"):
        reasons.append("claim type configuration requires medical review")
    required_documents = {str(value).strip().upper() for value in (config.require_documents or [])}
    if {"MEDICAL_REPORT", "DISABILITY_ASSESSMENT", "MEDICAL_CERTIFICATE"}.intersection(required_documents):
        reasons.append("claim type requires medical evidence")
    amount = _claim_amount(claim)
    age = _claim_age(claim)
    for limit in _active_medical_limits(claim):
        if not _medical_limit_applies(limit, claim, amount, age):
            continue
        if limit.mandatory_flag:
            reasons.append(f"medical parameter {limit.code} is mandatory")
        elif amount > limit.limit_amount:
            reasons.append(f"claim amount exceeds medical parameter {limit.code}")
    return sorted(set(reasons)), amount, age


def evaluate_medical_requirements(claim, *, actor=None, source_channel="API"):
    """Evaluate current claim type, claimant age, amount, and medical limits."""
    reasons, amount, age = _medical_reasons(claim)
    required = bool(reasons)
    before = claim.medical_status
    if required:
        if claim.medical_status not in {ClaimMedicalStatus.CLEARED, ClaimMedicalStatus.LOADING}:
            claim.medical_status = ClaimMedicalStatus.PENDING
            claim.status = ClaimStatus.PENDING_MEDICAL
        claim.medical_reason = "; ".join(reasons)
        claim.medical_requested_at = claim.medical_requested_at or timezone.now()
    elif claim.medical_status == ClaimMedicalStatus.NONE:
        claim.medical_reason = ""
    claim.save(update_fields=["medical_status", "medical_reason", "medical_requested_at", "status", "updated_at"])
    AuditService.log(
        action_type="MEDICAL_EVALUATE",
        entity_type="ol_claims.olclaim",
        entity_id=claim.pk,
        entity_repr=claim.claim_number,
        before_state={"medical_status": before},
        after_state={
            "medical_status": claim.medical_status,
            "claim_status": claim.status,
            "required": required,
            "reasons": reasons,
            "claim_amount": str(amount),
            "claimant_age": age,
        },
        description=f"Medical requirement evaluation completed for {claim.claim_number}.",
        actor=actor,
        reason="Claim medical requirement evaluation.",
        source_channel=source_channel,
        app_label="ol_claims",
        model_name="olclaim",
        object_id=str(claim.pk),
        object_repr=claim.claim_number,
    )
    return {
        "medical_required": required,
        "medical_status": claim.medical_status,
        "claim_status": claim.status,
        "reasons": reasons,
        "claim_amount": amount,
        "claimant_age": age,
    }


def assert_medical_ready(claim):
    if claim.medical_status == ClaimMedicalStatus.PENDING or claim.status == ClaimStatus.PENDING_MEDICAL:
        raise registry_error(
            "CLAIM_MEDICAL_REVIEW_REQUIRED",
            details={"claim_number": claim.claim_number, "medical_status": claim.medical_status},
        )
    if claim.medical_status == ClaimMedicalStatus.REJECTED:
        raise registry_error(
            "CLAIM_MEDICAL_REJECTED",
            details={"claim_number": claim.claim_number},
        )
    return True


@transaction.atomic
def require_medical_review(claim_id, *, actor=None, reason="", source_channel="API"):
    claim = OLClaim.objects.select_for_update().filter(pk=claim_id).first()
    if not claim:
        raise registry_error("CLAIM_NOT_FOUND")
    if claim.status in {ClaimStatus.SETTLED, ClaimStatus.CANCELLED, ClaimStatus.REJECTED}:
        raise registry_error("CLAIM_INVALID_STATUS", details={"claim_number": claim.claim_number, "status": claim.status})
    before = {"status": claim.status, "medical_status": claim.medical_status}
    claim.medical_status = ClaimMedicalStatus.PENDING
    claim.medical_result = "REQUIRED"
    claim.medical_reason = str(reason or "Medical review was requested by Claims Administration.").strip()
    claim.medical_requested_at = timezone.now()
    claim.status = ClaimStatus.PENDING_MEDICAL
    claim.save(update_fields=["status", "medical_status", "medical_result", "medical_reason", "medical_requested_at", "updated_at"])
    emit_claim_medical_required(
        claim,
        actor=actor,
        from_status=before["status"],
        to_status=claim.status,
        reason=claim.medical_reason,
        source_channel=source_channel,
    )
    AuditService.log(
        action_type="MEDICAL_REQUIRED",
        entity_type="ol_claims.olclaim",
        entity_id=claim.pk,
        entity_repr=claim.claim_number,
        before_state=before,
        after_state={"status": claim.status, "medical_status": claim.medical_status},
        description=f"Medical review required for {claim.claim_number}.",
        actor=actor,
        reason=claim.medical_reason,
        source_channel=source_channel,
        app_label="ol_claims",
        model_name="olclaim",
        object_id=str(claim.pk),
        object_repr=claim.claim_number,
    )
    return claim


def _loading_factor(loading_factor=None, loading_percentage=None):
    raw_factor = loading_factor
    if raw_factor in (None, "") and loading_percentage not in (None, ""):
        try:
            raw_factor = Decimal("1") + Decimal(str(loading_percentage)) / Decimal("100")
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise registry_error("CLAIM_LOADING_FACTOR_INVALID") from exc
    try:
        factor = Decimal(str(raw_factor))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise registry_error("CLAIM_LOADING_FACTOR_INVALID") from exc
    if factor <= 0 or factor > Decimal("10"):
        raise registry_error("CLAIM_LOADING_FACTOR_INVALID", details={"maximum_factor": "10"})
    return factor.quantize(Decimal("0.0001"))


@transaction.atomic
def record_medical_result(
    claim_id,
    *,
    result,
    reason="",
    loading_factor=None,
    loading_percentage=None,
    actor=None,
    source_channel="API",
):
    claim = OLClaim.objects.select_for_update().filter(pk=claim_id).first()
    if not claim:
        raise registry_error("CLAIM_NOT_FOUND")
    normalized = str(result or "").strip().upper()
    if normalized not in {ClaimMedicalStatus.CLEARED, ClaimMedicalStatus.REJECTED, ClaimMedicalStatus.LOADING}:
        raise registry_error(
            "CLAIM_INVALID_MEDICAL_RESULT",
            field_errors={"result": ["Choose Cleared, Rejected, or Loading."]},
        )
    if claim.medical_status != ClaimMedicalStatus.PENDING:
        raise registry_error(
            "CLAIM_INVALID_MEDICAL_STATUS",
            details={"claim_number": claim.claim_number, "medical_status": claim.medical_status},
        )
    if normalized == ClaimMedicalStatus.REJECTED and not str(reason or "").strip():
        raise registry_error(
            "CLAIM_INVALID_MEDICAL_RESULT",
            field_errors={"reason": ["Enter the medical reason when rejecting a claim."]},
        )

    before = {"status": claim.status, "medical_status": claim.medical_status}
    claim.medical_status = normalized
    claim.medical_result = normalized
    claim.medical_reason = str(reason or "").strip()
    claim.medical_reviewed_by = actor
    claim.medical_reviewed_at = timezone.now()
    metadata = {"result": normalized}
    if normalized == ClaimMedicalStatus.REJECTED:
        claim.status = ClaimStatus.REJECTED
    elif normalized == ClaimMedicalStatus.CLEARED:
        claim.status = ClaimStatus.REGISTERED if claim.status == ClaimStatus.PENDING_MEDICAL else claim.status
    else:
        factor = _loading_factor(loading_factor, loading_percentage)
        claim.medical_loading_factor = factor
        changed_items = []
        for item in claim.items.select_for_update().all():
            before_amount = item.calculated_amount
            item.calculated_amount = (item.calculated_amount * factor).quantize(Decimal("0.01"))
            item.adjustment_reason = (item.adjustment_reason + " " if item.adjustment_reason else "") + f"Medical loading factor {factor}."
            item.save(update_fields=["calculated_amount", "adjustment_reason", "updated_at"])
            changed_items.append({"benefit_type": item.benefit_type, "before": str(before_amount), "after": str(item.calculated_amount)})
        claim.status = ClaimStatus.REGISTERED if claim.status == ClaimStatus.PENDING_MEDICAL else claim.status
        metadata.update({"loading_factor": str(factor), "items": changed_items})
    update_fields = [
        "status", "medical_status", "medical_result", "medical_reason", "medical_reviewed_by",
        "medical_reviewed_at", "medical_loading_factor", "updated_at",
    ]
    claim.save(update_fields=update_fields)
    emit_claim_medical_result(
        claim,
        actor=actor,
        from_status=before["status"],
        to_status=claim.status,
        reason=claim.medical_reason,
        source_channel=source_channel,
        metadata=metadata,
    )
    AuditService.log(
        action_type="MEDICAL_RESULT",
        entity_type="ol_claims.olclaim",
        entity_id=claim.pk,
        entity_repr=claim.claim_number,
        before_state=before,
        after_state={"status": claim.status, "medical_status": claim.medical_status, **metadata},
        description=f"Medical result {normalized} recorded for {claim.claim_number}.",
        actor=actor,
        reason=claim.medical_reason or f"Medical result {normalized}.",
        source_channel=source_channel,
        app_label="ol_claims",
        model_name="olclaim",
        object_id=str(claim.pk),
        object_repr=claim.claim_number,
    )
    return claim
