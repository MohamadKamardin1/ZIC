"""Proposal document requirements (BR-12) and upload handling."""

from django.utils import timezone

from apps.governance.services.audit_service import AuditService
from apps.ol_parameters.models import OLProposalDocumentRequirement
from apps.ol_proposals.errors import ProposalError
from apps.ol_proposals.models import OLProposalDocument, ProposalDocumentStatus


def proposal_product_and_plan(proposal):
    plan_config = proposal.plan_configs.filter(is_selected=True).first()
    if plan_config is None:
        return None, None
    product_id = getattr(getattr(plan_config, "product_version", None), "product_id", None)
    return product_id, plan_config.plan_id


def applicable_requirements(proposal):
    """Resolve active document requirements by scope: plan+product → product → plan → global."""
    product_id, plan_id = proposal_product_and_plan(proposal)
    queryset = OLProposalDocumentRequirement.objects.filter(is_active=True)
    candidates = list(queryset)
    scored = []
    for row in candidates:
        score = (
            0 if (row.product_id == product_id and product_id) else 1 if product_id else 2,
            0 if (row.plan_id == plan_id and plan_id) else 1 if plan_id else 2,
            row.code,
        )
        scored.append((score, row))
    scored.sort(key=lambda item: (item[0][0], item[0][1], item[0][2]))
    return [row for _score, row in scored]


def missing_mandatory_documents(proposal):
    """Document types that are required by parameters but not uploaded/verified."""
    uploaded = set(
        proposal.documents.filter(status__in=(ProposalDocumentStatus.UPLOADED, ProposalDocumentStatus.VERIFIED))
        .values_list("document_type", flat=True)
    )
    required = {row.document_type for row in applicable_requirements(proposal) if row.mandatory}
    return sorted(required - uploaded)


def ensure_documents_ok(proposal):
    """Raise PROPOSAL_MANDATORY_DOCUMENTS_MISSING when required documents are absent."""
    missing = missing_mandatory_documents(proposal)
    if missing:
        raise ProposalError(
            f"Missing mandatory documents: {', '.join(missing)}.",
            error_code="PROPOSAL_MANDATORY_DOCUMENTS_MISSING",
            status_code=422,
            resolution_steps=[
                "Upload each required document (identity document, signature, KYC form as applicable).",
                "Confirm the document status is Uploaded.",
                "Retry once all mandatory documents are uploaded.",
            ],
        )
    return True


def upload_document(*, proposal, document_type, file_reference, actor, source_channel="API"):
    document_type = (document_type or "").strip().upper()
    file_reference = (file_reference or "").strip()
    if not document_type:
        raise ProposalError(
            "A document type is required.",
            error_code="VALIDATION_ERROR",
            status_code=422,
            field_errors={"document_type": ["A document type is required."]},
        )
    requirement = next((row for row in applicable_requirements(proposal) if row.document_type == document_type), None)
    document, created = OLProposalDocument.objects.update_or_create(
        proposal=proposal,
        document_type=document_type,
        defaults={
            "file_reference": file_reference,
            "mandatory": requirement.mandatory if requirement else False,
            "status": ProposalDocumentStatus.UPLOADED,
            "uploaded_by": actor if actor and getattr(actor, "is_authenticated", False) else None,
            "uploaded_at": timezone.now(),
        },
    )
    AuditService.log_action(
        "PROPOSAL_DOCUMENT_UPLOAD",
        proposal,
        actor=actor,
        after_state={"document_type": document.document_type, "file_reference": document.file_reference},
        changed_fields=["documents"],
        reason=f"Uploaded '{document.document_type}'.",
        source_channel=source_channel,
    )
    return document, created