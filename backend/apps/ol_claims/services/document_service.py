import os
from uuid import uuid4

from django.core.files.storage import default_storage
from django.utils import timezone

from apps.governance.services.audit_service import AuditService
from apps.ol_parameters.models import OLClaimType
from apps.ol_policies.models import Policy

from ..errors import registry_error
from ..models import OLClaim, OLClaimDocument
from .validation import _active_claim_type


def get_required_documents(claim_type, on_date=None):
    """Return required document type codes from the current claim setup."""
    config = _active_claim_type(claim_type, on_date)
    return sorted({str(value).strip().upper() for value in (config.require_documents or []) if str(value).strip()})


def document_requirement_status(claim):
    required = get_required_documents(claim.claim_type, claim.claim_date)
    uploaded = {
        str(value).strip().upper()
        for value in claim.documents.values_list("document_type", flat=True)
        if str(value).strip()
    }
    missing = sorted(set(required) - uploaded)
    return {
        "required_document_types": required,
        "uploaded_document_types": sorted(uploaded),
        "missing_document_types": missing,
        "all_mandatory_uploaded": not missing,
    }


def can_proceed_to_assessment(claim_id, *, actor=None, source_channel="API"):
    claim = OLClaim.objects.select_related("policy_ref").filter(pk=claim_id).first()
    if not claim:
        raise registry_error("CLAIM_NOT_FOUND")
    status = document_requirement_status(claim)
    AuditService.log(
        action_type="VALIDATE",
        entity_type="ol_claims.claim_documents",
        entity_id=claim.pk,
        entity_repr=claim.claim_number,
        after_state=status,
        description=f"Mandatory claim document check for {claim.claim_number}.",
        actor=actor,
        reason="Claim progression document completeness check.",
        source_channel=source_channel,
        app_label="ol_claims",
        model_name="claim_documents",
        object_id=str(claim.pk),
        object_repr=claim.claim_number,
    )
    if status["missing_document_types"]:
        raise registry_error(
            "CLAIM_MANDATORY_DOC_MISSING",
            details={
                "claim_number": claim.claim_number,
                "missing_document_types": status["missing_document_types"],
                "required_document_types": status["required_document_types"],
            },
        )
    from .medical import assert_medical_ready

    assert_medical_ready(claim)
    return True


def _stored_file_reference(claim, uploaded_file):
    original_name = os.path.basename(getattr(uploaded_file, "name", "claim-document.bin"))
    safe_name = original_name.replace(" ", "_")
    path = f"claims/{claim.claim_number}/{uuid4().hex}_{safe_name}"
    return default_storage.save(path, uploaded_file)


def upload_document(*, claim, document_type, uploaded_file=None, file_reference="", actor=None, source_channel="API", request=None):
    document_type = str(document_type or "").strip().upper()
    if not document_type:
        raise registry_error(
            "CLAIM_DOCUMENT_REQUIRED",
            field_errors={"document_type": ["Select the type of document you are uploading."]},
        )
    if not uploaded_file and not str(file_reference or "").strip():
        raise registry_error(
            "CLAIM_DOCUMENT_REQUIRED",
            field_errors={"file": ["Choose a file or provide a managed storage reference."]},
        )
    if uploaded_file and getattr(uploaded_file, "size", 0) > 20 * 1024 * 1024:
        raise registry_error(
            "CLAIM_DOCUMENT_TOO_LARGE",
            field_errors={"file": ["The file must be 20 MB or smaller."]},
        )

    required = set(get_required_documents(claim.claim_type, claim.claim_date))
    stored_reference = _stored_file_reference(claim, uploaded_file) if uploaded_file else str(file_reference).strip()
    document, created = OLClaimDocument.objects.update_or_create(
        claim=claim,
        document_type=document_type,
        defaults={
            "file_reference": stored_reference,
            "mandatory_flag": document_type in required,
            "uploaded_by": actor if actor and getattr(actor, "is_authenticated", False) else None,
            "upload_date": timezone.now(),
        },
    )
    AuditService.log(
        action_type="DOCUMENT_UPLOAD",
        entity_type="ol_claims.claim_document",
        entity_id=document.pk,
        entity_repr=f"{claim.claim_number} — {document_type}",
        after_state={
            "claim_number": claim.claim_number,
            "document_type": document_type,
            "mandatory_flag": document.mandatory_flag,
            "file_reference": stored_reference,
        },
        description=f"Uploaded claim document {document_type} for {claim.claim_number}.",
        actor=actor,
        reason="Claim document uploaded.",
        source_channel=source_channel,
        request=request,
        app_label="ol_claims",
        model_name="claimdocument",
        object_id=str(document.pk),
        object_repr=str(document),
    )
    return document, created
