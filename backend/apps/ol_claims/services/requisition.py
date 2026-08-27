from decimal import Decimal, InvalidOperation
from uuid import uuid4

from django.db import transaction
from django.utils import timezone

from apps.front_office.models import FORequisition
from apps.governance.models import ApprovalRequest
from apps.governance.services.approval_service import ApprovalService
from apps.governance.services.audit_service import AuditService
from apps.system_parameters.services.config_service import ConfigurationService

from ..errors import registry_error
from ..events import (
    emit_claim_approved,
    emit_claim_rejected,
    emit_claim_requisitioned,
)
from ..models import ClaimRequisitionStatus, ClaimStatus, OLClaim, OLClaimRequisition
from .loan_offset import calculate_net_payout


_ALLOWED_SOURCE_CHANNELS = {"API", "WEB", "PORTAL", "ADMIN", "SYSTEM", "BATCH"}
_ALLOWED_BANK_FIELDS = {
    "recipient_type",
    "recipient_name",
    "claimant_name",
    "partner_number",
    "account_name",
    "account_number",
    "bank_name",
    "branch_name",
    "account_type",
    "iban",
    "swift",
    "currency",
}


def normalize_source_channel(value):
    channel = str(value or "API").upper()
    return channel if channel in _ALLOWED_SOURCE_CHANNELS else "API"


def _approval_threshold():
    raw = ConfigurationService.get_str_parameter("OL_CLAIM_PAYMENT_APPROVAL_THRESHOLD", "0")
    try:
        return max(Decimal(str(raw)), Decimal("0.00")).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0.00")


def _clean_bank_details(value):
    if not isinstance(value, dict) or not value:
        raise registry_error(
            "CLAIM_REQUISITION_BANK_DETAILS_REQUIRED",
            field_errors={"bank_details": ["Provide the claimant or partner payment details before submitting."]},
        )
    cleaned = {
        str(key): str(item).strip()
        for key, item in value.items()
        if str(key) in _ALLOWED_BANK_FIELDS and item is not None and str(item).strip()
    }
    if not cleaned:
        raise registry_error(
            "CLAIM_REQUISITION_BANK_DETAILS_REQUIRED",
            field_errors={"bank_details": ["Include an account name and account number, or a valid claimant/partner payment reference."]},
        )
    has_account = bool(cleaned.get("account_number") or cleaned.get("iban"))
    has_recipient = bool(cleaned.get("recipient_name") or cleaned.get("claimant_name") or cleaned.get("partner_number"))
    if not (has_account and (cleaned.get("account_name") or has_recipient)):
        raise registry_error(
            "CLAIM_REQUISITION_BANK_DETAILS_REQUIRED",
            field_errors={
                "bank_details": [
                    "Provide account number or IBAN together with an account holder or claimant/partner reference."
                ]
            },
        )
    return cleaned


def _claim_snapshot(claim, requisition=None):
    return {
        "claim_number": claim.claim_number,
        "status": claim.status,
        "requisition_number": requisition.requisition_number if requisition else "",
        "requisition_status": requisition.status if requisition else "",
        "amount": str(requisition.amount) if requisition else "0.00",
    }


def _approval_data(claim, requisition, financial):
    return {
        "claim_number": claim.claim_number,
        "policy_number": claim.policy_ref.policy_number,
        "requisition_number": requisition.requisition_number,
        "amount": str(requisition.amount),
        "currency": claim.policy_ref.currency,
        "net_payout": str(financial["net_payout"]),
        "gross_amount": str(financial["gross_amount"]),
        "loan_offset": str(financial["loan_offset"]),
    }


@transaction.atomic
def raise_requisition(
    claim_id,
    *,
    bank_details,
    narration,
    actor=None,
    request=None,
    source_channel="API",
):
    source_channel = normalize_source_channel(source_channel)
    claim = (
        OLClaim.objects.select_for_update()
        .select_related("policy_ref")
        .prefetch_related("items")
        .filter(pk=claim_id)
        .first()
    )
    if claim is None:
        raise registry_error("CLAIM_NOT_FOUND")
    if claim.status != ClaimStatus.ASSESSED:
        raise registry_error(
            "CLAIM_REQUISITION_REQUIRED",
            details={"claim_number": claim.claim_number, "current_status": claim.status},
        )
    if hasattr(claim, "requisition"):
        raise registry_error(
            "CLAIM_REQUISITION_ALREADY_EXISTS",
            details={"claim_number": claim.claim_number, "requisition_number": claim.requisition.requisition_number},
        )
    cleaned_bank_details = _clean_bank_details(bank_details)
    narration = str(narration or "").strip()
    if not narration:
        raise registry_error(
            "CLAIM_REQUISITION_BANK_DETAILS_REQUIRED",
            field_errors={"narration": ["Explain the payment purpose before submitting the requisition."]},
        )

    financial = calculate_net_payout(claim.pk)
    net_payout = Decimal(financial["net_payout"]).quantize(Decimal("0.01"))
    if net_payout <= 0:
        raise registry_error(
            "CLAIM_REQUISITION_NET_ZERO",
            details={
                "claim_number": claim.claim_number,
                "gross_amount": str(financial["gross_amount"]),
                "loan_offset": str(financial["loan_offset"]),
                "net_payout": str(net_payout),
            },
        )

    fo_requisition = FORequisition.objects.create(
        requisition_number=f"FO-CLM-{timezone.localdate():%Y%m%d}-{uuid4().hex[:10].upper()}",
        department="CLAIMS",
        amount=net_payout,
        reason=f"Claim {claim.claim_number}: {narration}",
        status="PENDING",
    )
    claim_requisition = OLClaimRequisition.objects.create(
        claim=claim,
        amount=net_payout,
        bank_details_json=cleaned_bank_details,
        payment_requisition=fo_requisition,
        approval_required=net_payout > _approval_threshold(),
        narration=narration,
        status=ClaimRequisitionStatus.REQUISITIONED,
        created_by=actor,
        updated_by=actor,
    )
    approval_request = None
    if claim_requisition.approval_required:
        approval_request = ApprovalService.submit(
            module="OL_CLAIMS",
            entity_type="OLClaimRequisition",
            entity_id=claim_requisition.pk,
            action="PAYMENT",
            requested_data=_approval_data(claim, claim_requisition, financial),
            current_data={"status": claim_requisition.status, "claim_status": claim.status},
            entity_repr=claim_requisition.requisition_number,
            submitted_by=actor,
            comments=f"Payment approval requested for claim {claim.claim_number}.",
        )
        claim_requisition.approval_request = approval_request
        claim_requisition.save(update_fields=["approval_request", "updated_at"])

    before = _claim_snapshot(claim, None)
    claim.status = ClaimStatus.REQUISITIONED
    claim.updated_by = actor
    claim.save(update_fields=["status", "updated_by", "updated_at"])
    after = _claim_snapshot(claim, claim_requisition)
    emit_claim_requisitioned(
        claim,
        actor=actor,
        from_status=before["status"],
        to_status=claim.status,
        reason=narration,
        source_channel=source_channel,
        metadata={
            "requisition_number": claim_requisition.requisition_number,
            "front_office_requisition_number": fo_requisition.requisition_number,
            "amount": str(net_payout),
            "currency": claim.policy_ref.currency,
            "approval_required": claim_requisition.approval_required,
            "approval_threshold": str(_approval_threshold()),
        },
    )
    AuditService.log(
        action_type="CLAIM_REQUISITIONED",
        entity_type="ol_claims.olclaim",
        entity_id=claim.pk,
        entity_repr=claim.claim_number,
        before_state=before,
        after_state={
            **after,
            "policy_number": claim.policy_ref.policy_number,
            "front_office_requisition_number": fo_requisition.requisition_number,
            "currency": claim.policy_ref.currency,
            "approval_required": claim_requisition.approval_required,
            "approval_request_id": str(approval_request.pk) if approval_request else None,
        },
        description=f"Payment requisition {claim_requisition.requisition_number} raised for claim {claim.claim_number}.",
        actor=actor,
        reason=narration,
        source_channel=source_channel,
        request=request,
        app_label="ol_claims",
        model_name="olclaim",
        object_id=str(claim.pk),
        object_repr=claim.claim_number,
    )
    return claim_requisition


@transaction.atomic
def apply_approval_outcome(approval_request, *, actor=None, source_channel="SYSTEM", request=None):
    requisition = (
        OLClaimRequisition.objects.select_for_update()
        .select_related("claim", "claim__policy_ref", "payment_requisition")
        .filter(pk=approval_request.entity_id)
        .first()
    )
    if requisition is None:
        return None
    claim = OLClaim.objects.select_for_update().select_related("policy_ref").get(pk=requisition.claim_id)
    if approval_request.status == "APPROVED":
        target_claim_status = ClaimStatus.APPROVED
        target_req_status = ClaimRequisitionStatus.APPROVED
        event_type = "approved"
    elif approval_request.status == "REJECTED":
        target_claim_status = ClaimStatus.REJECTED
        target_req_status = ClaimRequisitionStatus.REJECTED
        event_type = "rejected"
    else:
        return requisition

    if claim.status == target_claim_status and requisition.status == target_req_status:
        return requisition
    before = _claim_snapshot(claim, requisition)
    requisition.status = target_req_status
    requisition.updated_by = actor or approval_request.reviewed_by
    requisition.save(update_fields=["status", "updated_by", "updated_at"])
    if requisition.payment_requisition_id:
        requisition.payment_requisition.status = "APPROVED" if event_type == "approved" else "REJECTED"
        requisition.payment_requisition.save(update_fields=["status", "updated_at"])
    claim.status = target_claim_status
    claim.updated_by = actor or approval_request.reviewed_by
    claim.save(update_fields=["status", "updated_by", "updated_at"])
    after = _claim_snapshot(claim, requisition)
    metadata = {
        "requisition_number": requisition.requisition_number,
        "front_office_requisition_number": requisition.payment_requisition.requisition_number if requisition.payment_requisition else "",
        "amount": str(requisition.amount),
        "currency": claim.policy_ref.currency,
        "approval_request_status": approval_request.status,
        "approval_comments": approval_request.comments,
    }
    kwargs = {
        "actor": actor or approval_request.reviewed_by,
        "from_status": before["status"],
        "to_status": claim.status,
        "reason": approval_request.comments or f"Claim payment {event_type} by governance approval.",
        "source_channel": normalize_source_channel(source_channel),
        "metadata": metadata,
    }
    if event_type == "approved":
        emit_claim_approved(claim, **kwargs)
    else:
        emit_claim_rejected(claim, **kwargs)
    AuditService.log(
        action_type="CLAIM_PAYMENT_APPROVED" if event_type == "approved" else "CLAIM_PAYMENT_REJECTED",
        entity_type="ol_claims.olclaim",
        entity_id=claim.pk,
        entity_repr=claim.claim_number,
        before_state=before,
        after_state={**after, **metadata},
        description=f"Claim payment {event_type} for {claim.claim_number}.",
        actor=actor or approval_request.reviewed_by,
        reason=approval_request.comments or f"Claim payment {event_type} by governance approval.",
        source_channel=normalize_source_channel(source_channel),
        request=request,
        app_label="ol_claims",
        model_name="olclaim",
        object_id=str(claim.pk),
        object_repr=claim.claim_number,
    )
    return requisition
