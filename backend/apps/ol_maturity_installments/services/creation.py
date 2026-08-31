"""Installment plan generation service.

Creates a plan (status CREATED) and its SCHEDULED items from a matured policy or
a settled maturity claim, running the calculation engine and emitting the
InstallmentPlanCreated event. Generation is idempotent via a unique
``X-Idempotency-Key`` that returns the originally created plan on replay.
"""

import hashlib
import json

from django.db import IntegrityError, transaction

from apps.governance.services.audit_service import AuditService
from apps.ol_policies.models import MaturityClaim, Policy

from ..errors import registry_error
from ..events import emit_installment_plan_created
from ..models import (
    InstallmentItemStatus,
    InstallmentPlanStatus,
    OLInstallmentItem,
    OLMaturityInstallmentConfig,
    OLMaturityInstallmentPlan,
)
from .calculation import calculate_schedule

MATURED_POLICY_STATUSES = ("MATURED", "MATURED_PENDING_PAYMENT")
SETTLED_CLAIM_STATUSES = ("APPROVED", "PAID")
CALCULATION_BASIS = "INSTALLMENT_RATE_TABLE"


def _idempotency_fingerprint(*, policy_id, maturity_claim_id, frequency, term_years):
    payload = {
        "policy_id": str(policy_id),
        "maturity_claim_id": str(maturity_claim_id) if maturity_claim_id else None,
        "frequency": str(frequency).strip().upper(),
        "term_years": int(term_years),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    return {"sha256": hashlib.sha256(encoded).hexdigest(), "payload": payload}


@transaction.atomic
def create_installment_plan(
    *,
    policy_id,
    maturity_claim_id=None,
    frequency,
    term_years,
    idempotency_key=None,
    actor=None,
    source_channel="API",
    request=None,
):
    """Generate and persist a maturity installment plan (returns ``(plan, created)``)."""
    key = str(idempotency_key or "").strip()
    if not key:
        raise registry_error("INSTALLMENT_IDEMPOTENCY_REQUIRED")
    if len(key) > 64:
        raise registry_error(
            "INSTALLMENT_IDEMPOTENCY_REQUIRED",
            message="The idempotency key is too long for maturity installment plan creation.",
            field_errors={"X-Idempotency-Key": ["Use at most 64 characters."]},
            resolution_steps=[
                "Send a unique X-Idempotency-Key containing no more than 64 characters.",
                "Reuse that same key only for the same unchanged submission.",
            ],
        )

    policy = Policy.objects.select_for_update().select_related("partner").filter(pk=policy_id).first()
    if not policy:
        raise registry_error("INSTALLMENT_POLICY_NOT_FOUND", details={"policy_id": str(policy_id)})

    claim = None
    if maturity_claim_id:
        claim = MaturityClaim.objects.select_for_update().filter(pk=maturity_claim_id).first()
        if not claim:
            raise registry_error("INSTALLMENT_CLAIM_NOT_FOUND", details={"maturity_claim_id": str(maturity_claim_id)})
        if claim.policy_id != policy.pk:
            raise registry_error(
                "INSTALLMENT_CLAIM_MISMATCH",
                details={"policy_id": str(policy.pk), "maturity_claim_id": str(claim.pk)},
            )
        if claim.status not in SETTLED_CLAIM_STATUSES:
            raise registry_error(
                "INSTALLMENT_CLAIM_NOT_SETTLED",
                details={"claim_number": claim.claim_number, "status": claim.status},
            )

    fingerprint = _idempotency_fingerprint(
        policy_id=policy.pk,
        maturity_claim_id=maturity_claim_id,
        frequency=frequency,
        term_years=term_years,
    )
    existing = OLMaturityInstallmentPlan.objects.filter(idempotency_key=key).first()
    if existing:
        if existing.idempotency_fingerprint.get("sha256") != fingerprint["sha256"]:
            raise registry_error("INSTALLMENT_IDEMPOTENCY_CONFLICT", details={"plan_number": existing.plan_number})
        return existing, False

    if not claim and policy.status not in MATURED_POLICY_STATUSES:
        raise registry_error(
            "PLAN_POLICY_NOT_MATURED",
            details={"policy_number": policy.policy_number, "policy_status": policy.status},
        )

    maturity_value = claim.net_payout if claim else policy.sum_assured
    schedule = calculate_schedule(
        policy,
        maturity_value,
        frequency,
        term_years,
        actor=actor,
        source_channel=source_channel,
    )

    plan = OLMaturityInstallmentPlan(
        policy_ref=policy,
        maturity_claim_ref=claim,
        partner=policy.partner,
        currency=policy.currency,
        total_maturity_value=schedule["total_maturity_value"],
        total_payable_amount=schedule["total_payable_amount"],
        installment_count=schedule["installment_count"],
        frequency=schedule["frequency"],
        start_date=schedule["start_date"],
        end_date=schedule["end_date"],
        status=InstallmentPlanStatus.CREATED,
        parameter_snapshot={
            "calculation_basis": CALCULATION_BASIS,
            "rate_used": schedule["rate_used"],
            "parameters_used": schedule["parameters_used"],
            "term_years": schedule["term_years"],
            "frequency_matches_policy": schedule["frequency_matches_policy"],
        },
        idempotency_key=key,
        idempotency_fingerprint=fingerprint,
        source_channel=source_channel,
        created_by=actor,
    )
    plan.full_clean()
    try:
        plan.save(force_insert=True)
    except IntegrityError:
        existing = OLMaturityInstallmentPlan.objects.filter(idempotency_key=key).first()
        if existing and existing.idempotency_fingerprint.get("sha256") == fingerprint["sha256"]:
            return existing, False
        raise

    for row in schedule["items"]:
        OLInstallmentItem.objects.create(
            plan_ref=plan,
            installment_number=row["installment_number"],
            due_date=row["date"],
            amount=row["amount"],
            status=InstallmentItemStatus.SCHEDULED,
            created_by=actor,
        )

    OLMaturityInstallmentConfig.objects.create(
        plan_ref=plan,
        calculation_basis=CALCULATION_BASIS,
        installment_rate_snapshot={
            "rate_used": schedule["rate_used"],
            "parameters_used": schedule["parameters_used"],
        },
        paid_up_rate_snapshot={},
        installment_charge_snapshot={},
        parameters_used=schedule["parameters_used"],
        assumptions={
            "amount_formula": "Maturity Value * (Rate / 100)",
            "rounding": "Largest remainder so the item total equals the maturity value.",
            "term_years": schedule["term_years"],
        },
        configured_by=actor,
    )

    emit_installment_plan_created(
        plan,
        actor=actor,
        reason="Installment plan created from a matured policy or settled maturity claim.",
        source_channel=source_channel,
        metadata={
            "policy_number": policy.policy_number,
            "maturity_claim_number": claim.claim_number if claim else None,
            "frequency": schedule["frequency"],
            "term_years": schedule["term_years"],
            "total_payable_amount": str(plan.total_payable_amount),
        },
    )

    AuditService.log_create(
        plan,
        actor=actor,
        request=request,
        reason="Installment plan created through the validated OL Maturity Installments service.",
        source_channel=source_channel,
    )
    return plan, True
