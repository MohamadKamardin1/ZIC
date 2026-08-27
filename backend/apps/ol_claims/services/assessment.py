from copy import deepcopy
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone

from apps.governance.services.audit_service import AuditService

from ..errors import registry_error
from ..events import emit_claim_assessed
from ..models import ClaimStatus, OLClaim, OLClaimFileNote
from .document_service import can_proceed_to_assessment
from .validation import _active_claim_type



def _calculated_maximum(claim):
    return sum((item.calculated_amount for item in claim.items.all()), Decimal("0.00")).quantize(Decimal("0.01"))


def _as_amount(value):
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise registry_error(
            "CLAIM_ASSESSMENT_AMOUNT_INVALID",
            field_errors={"assessed_amount": ["Enter a valid amount using numbers only."]},
        ) from exc


@transaction.atomic
def assess_claim(
    claim_id,
    *,
    assessed_amount,
    assessment_notes,
    fraud_flag_reason="",
    fraud_flag=False,
    waiver_of_premium_days=0,
    actor=None,
    source_channel="API",
    request=None,
):
    claim = (
        OLClaim.objects.select_for_update()
        .select_related("policy_ref")
        .prefetch_related("items")
        .filter(pk=claim_id)
        .first()
    )
    if not claim:
        raise registry_error("CLAIM_NOT_FOUND")
    if claim.status not in {ClaimStatus.REGISTERED, ClaimStatus.ASSESSMENT}:
        raise registry_error(
            "CLAIM_INVALID_STATUS",
            details={"claim_number": claim.claim_number, "status": claim.status},
        )
    if not str(assessment_notes or "").strip():
        raise registry_error(
            "CLAIM_ASSESSMENT_REQUIRED",
            field_errors={"assessment_notes": ["Enter the assessment findings before saving the assessment."]},
        )

    can_proceed_to_assessment(claim.pk, actor=actor, source_channel=source_channel)
    amount = _as_amount(assessed_amount).quantize(Decimal("0.01"))
    maximum = _calculated_maximum(claim)
    if amount < 0 or amount > maximum:
        raise registry_error(
            "CLAIM_ASSESSMENT_AMOUNT_INVALID",
            details={
                "claim_number": claim.claim_number,
                "calculated_maximum": str(maximum),
                "assessed_amount": str(amount),
            },
            field_errors={"assessed_amount": [f"Enter an amount from 0.00 through {maximum:.2f}."]},
        )

    fraud_reason = str(fraud_flag_reason or "").strip()
    fraud_enabled = bool(fraud_flag or fraud_reason)
    if fraud_enabled and not fraud_reason:
        raise registry_error(
            "CLAIM_FRAUD_REASON_REQUIRED",
            field_errors={"fraud_flag_reason": ["Explain why this claim requires fraud review."]},
        )

    try:
        waiver_days = int(waiver_of_premium_days or 0)
    except (TypeError, ValueError) as exc:
        raise registry_error("CLAIM_WAIVER_INPUT_INVALID") from exc
    if waiver_days < 0:
        raise registry_error("CLAIM_WAIVER_INPUT_INVALID")

    config = _active_claim_type(claim.claim_type, claim.claim_date)
    if waiver_days and not config.allow_waiver_of_premium:
        raise registry_error(
            "CLAIM_WAIVER_INPUT_INVALID",
            details={"claim_type": config.code, "allow_waiver_of_premium": False},
            field_errors={"waiver_of_premium_days": ["This claim type does not allow waiver of premium."]},
        )

    items = list(claim.items.select_for_update().all())
    before = {
        "status": claim.status,
        "fraud_flag": claim.fraud_flag,
        "approved_amount": str(sum((item.approved_amount or Decimal("0.00") for item in items), Decimal("0.00"))),
    }
    claim.status = ClaimStatus.ASSESSED
    claim.assessment_notes = str(assessment_notes).strip()
    claim.fraud_flag = fraud_enabled
    claim.fraud_flag_reason = fraud_reason
    claim.waiver_of_premium_days = waiver_days
    claim.waiver_of_premium_applied = bool(waiver_days)
    claim.waiver_of_premium_until = claim.claim_date + timedelta(days=waiver_days) if waiver_days else None
    claim.admitted_date = claim.admitted_date or claim.claim_date
    claim.admitted_by = actor
    claim.save(
        update_fields=[
            "status", "assessment_notes", "fraud_flag", "fraud_flag_reason", "waiver_of_premium_days",
            "waiver_of_premium_applied", "waiver_of_premium_until", "admitted_date", "admitted_by", "updated_at",
        ]
    )
    remaining = amount
    total_item_maximum = sum((item.calculated_amount for item in items), Decimal("0.00"))
    for index, item in enumerate(items):
        if index == len(items) - 1:
            item_amount = remaining
        elif total_item_maximum:
            item_amount = (amount * item.calculated_amount / total_item_maximum).quantize(Decimal("0.01"))
            item_amount = min(item_amount, item.calculated_amount)
        else:
            item_amount = Decimal("0.00")
        item.approved_amount = item_amount
        item.save(update_fields=["approved_amount", "updated_at"])
        remaining = (remaining - item_amount).quantize(Decimal("0.01"))

    policy_update = None
    if waiver_days:
        snapshot = deepcopy(claim.policy_ref.contract_snapshot or {})
        snapshot["premium_waiver"] = {
            "active": True,
            "claim_number": claim.claim_number,
            "days": waiver_days,
            "until": claim.waiver_of_premium_until.isoformat(),
        }
        claim.policy_ref.contract_snapshot = snapshot
        claim.policy_ref.save(update_fields=["contract_snapshot", "updated_at"])
        policy_update = snapshot["premium_waiver"]

    emit_claim_assessed(
        claim,
        actor=actor,
        from_status=before["status"],
        to_status=claim.status,
        reason=claim.assessment_notes,
        source_channel=source_channel,
        metadata={
            "assessed_amount": str(amount),
            "calculated_maximum": str(maximum),
            "fraud_flag": fraud_enabled,
            "waiver_of_premium": policy_update,
        },
    )
    AuditService.log(
        action_type="ASSESS",
        entity_type="ol_claims.olclaim",
        entity_id=claim.pk,
        entity_repr=claim.claim_number,
        before_state=before,
        after_state={
            "status": claim.status,
            "assessed_amount": str(amount),
            "calculated_maximum": str(maximum),
            "fraud_flag": fraud_enabled,
            "waiver_of_premium": policy_update,
        },
        description=f"Claim {claim.claim_number} assessed.",
        actor=actor,
        reason=claim.assessment_notes,
        source_channel=source_channel,
        request=request,
        app_label="ol_claims",
        model_name="olclaim",
        object_id=str(claim.pk),
        object_repr=claim.claim_number,
    )
    return claim


def add_file_note(claim_id, *, note_text, actor=None, source_channel="API", request=None):
    claim = OLClaim.objects.filter(pk=claim_id).first()
    if not claim:
        raise registry_error("CLAIM_NOT_FOUND")
    text = str(note_text or "").strip()
    if not text:
        raise registry_error(
            "CLAIM_NOTE_REQUIRED",
            field_errors={"note_text": ["Enter the internal note before saving it."]},
        )
    note = OLClaimFileNote.objects.create(claim=claim, note_text=text, created_by=actor)
    AuditService.log(
        action_type="NOTE_CREATE",
        entity_type="ol_claims.claim_file_note",
        entity_id=note.pk,
        entity_repr=f"{claim.claim_number} — internal note",
        after_state={"claim_number": claim.claim_number, "note_text": text},
        description=f"Internal claim note added to {claim.claim_number}.",
        actor=actor,
        reason="Internal claims note added.",
        source_channel=source_channel,
        request=request,
        app_label="ol_claims",
        model_name="claimfilenote",
        object_id=str(note.pk),
        object_repr=str(note),
    )
    return note
