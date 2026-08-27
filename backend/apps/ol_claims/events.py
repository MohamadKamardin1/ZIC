from apps.common.models import DomainEvent


AGGREGATE_TYPE = "OLClaim"
CLAIM_REGISTERED = "ClaimRegistered"
CLAIM_ASSESSED = "ClaimAssessed"
CLAIM_DOCUMENT_UPLOADED = "ClaimDocumentUploaded"
CLAIM_MEDICAL_REQUIRED = "ClaimMedicalRequired"
CLAIM_MEDICAL_RESULT_RECORDED = "ClaimMedicalResultRecorded"
CLAIM_LOAN_OFFSET_APPLIED = "ClaimLoanOffsetApplied"
CLAIM_REQUISITIONED = "ClaimRequisitioned"
CLAIM_APPROVED = "ClaimApproved"
CLAIM_SETTLED = "ClaimSettled"
CLAIM_CANCELLED = "ClaimCancelled"

CLAIM_DOMAIN_EVENTS = (
    CLAIM_REGISTERED,
    CLAIM_ASSESSED,
    CLAIM_DOCUMENT_UPLOADED,
    CLAIM_MEDICAL_REQUIRED,
    CLAIM_MEDICAL_RESULT_RECORDED,
    CLAIM_LOAN_OFFSET_APPLIED,
    CLAIM_REQUISITIONED,
    CLAIM_APPROVED,
    CLAIM_SETTLED,
    CLAIM_CANCELLED,
)


def emit_claim_event(
    event_type,
    claim,
    *,
    actor=None,
    from_status="",
    to_status="",
    reason="",
    source_channel="API",
    metadata=None,
):
    """Write a durable, replayable claim event to the shared outbox."""
    payload = {
        "claim_id": str(claim.pk),
        "claim_number": claim.claim_number,
        "policy_id": str(claim.policy_ref_id),
        "policy_number": getattr(claim.policy_ref, "policy_number", ""),
        "actor_id": str(actor.pk) if actor and getattr(actor, "pk", None) else None,
        "from_status": from_status,
        "to_status": to_status or claim.status,
        "reason": reason,
        "source_channel": source_channel,
        "metadata": metadata or {},
    }
    return DomainEvent.objects.create(
        event_type=event_type,
        aggregate_type=AGGREGATE_TYPE,
        aggregate_id=str(claim.pk),
        payload=payload,
    )


def emit_claim_registered(claim, **kwargs):
    kwargs.setdefault("to_status", claim.status)
    return emit_claim_event(CLAIM_REGISTERED, claim, **kwargs)


def emit_claim_assessed(claim, **kwargs):
    kwargs.setdefault("to_status", claim.status)
    return emit_claim_event(CLAIM_ASSESSED, claim, **kwargs)


def emit_claim_document_uploaded(claim, **kwargs):
    kwargs.setdefault("to_status", claim.status)
    return emit_claim_event(CLAIM_DOCUMENT_UPLOADED, claim, **kwargs)


def emit_claim_medical_required(claim, **kwargs):
    kwargs.setdefault("to_status", claim.status)
    return emit_claim_event(CLAIM_MEDICAL_REQUIRED, claim, **kwargs)


def emit_claim_medical_result(claim, **kwargs):
    kwargs.setdefault("to_status", claim.status)
    return emit_claim_event(CLAIM_MEDICAL_RESULT_RECORDED, claim, **kwargs)


def emit_claim_loan_offset_applied(claim, **kwargs):
    kwargs.setdefault("to_status", claim.status)
    return emit_claim_event(CLAIM_LOAN_OFFSET_APPLIED, claim, **kwargs)


def emit_claim_requisitioned(claim, **kwargs):
    kwargs.setdefault("to_status", claim.status)
    return emit_claim_event(CLAIM_REQUISITIONED, claim, **kwargs)


def emit_claim_approved(claim, **kwargs):
    kwargs.setdefault("to_status", claim.status)
    return emit_claim_event(CLAIM_APPROVED, claim, **kwargs)


def emit_claim_settled(claim, **kwargs):
    kwargs.setdefault("to_status", claim.status)
    return emit_claim_event(CLAIM_SETTLED, claim, **kwargs)


def emit_claim_cancelled(claim, **kwargs):
    kwargs.setdefault("to_status", claim.status)
    return emit_claim_event(CLAIM_CANCELLED, claim, **kwargs)
