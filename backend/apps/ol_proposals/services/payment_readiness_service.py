"""Payment readiness evaluation engine (BR checklist).

Every checklist item is teachable: a failed item always carries an
``error_code``, a human ``message``, ``resolution_steps``, and a ``deep_link``
to the screen that fixes it. The same evaluation powers the read-only
checklist endpoint and the ``mark-payment-ready`` transition.
"""

from django.db import transaction
from django.utils import timezone

from apps.governance.services.audit_service import AuditService
from apps.ol_proposals import events as proposal_events
from apps.ol_proposals.errors import ProposalError
from apps.ol_proposals.models import UnderwritingStatus
from apps.ol_proposals.services import document_service, enrichment_service, parameter_resolver

CHECKLIST_ITEMS = (
    "partner_verified",
    "enrichment_complete",
    "beneficiaries_valid",
    "mandatory_documents_complete",
    "underwriting_cleared_or_not_required",
    "not_expired",
    "quotation_version_current",
)

# Item contract: key, error code, fix message, resolution steps, deep link.
# ``deep_link`` is a format string receiving the proposal pk (names, never UUIDs).
_SPECS = (
    {
        "key": "partner_verified",
        "error_code": "PROPOSAL_PARTNER_NOT_VERIFIED",
        "message": "The proposal policyholder is not partner-verified.",
        "resolution_steps": [
            "Open the proposal and confirm the policyholder is an ACTIVE partner.",
            "Verify the partner under Partner Onboarding, then re-run payment readiness.",
        ],
        "deep_link": "/proposals/{id}/partner",
    },
    {
        "key": "enrichment_complete",
        "error_code": "PROPOSAL_ENRICHMENT_INCOMPLETE",
        "message": "Enrichment sections are incomplete.",
        "resolution_steps": [
            "Complete the declarations (PEP/AML) and bank details for the policyholder.",
            "Confirm the required enrichment sections show a green check on the proposal.",
        ],
        "deep_link": "/proposals/{id}/enrichment",
    },
    {
        "key": "beneficiaries_valid",
        "error_code": "PROPOSAL_BENEFICIARY_SHARES_INVALID",
        "message": "Beneficiaries are missing or invalid.",
        "resolution_steps": [
            "Add at least one primary beneficiary.",
            "Make the share percentages sum to exactly 100%.",
            "Attach a guardian to every minor beneficiary.",
        ],
        "deep_link": "/proposals/{id}/beneficiaries",
    },
    {
        "key": "mandatory_documents_complete",
        "error_code": "PROPOSAL_MANDATORY_DOCUMENTS_MISSING",
        "message": "One or more mandatory documents are missing.",
        "resolution_steps": [
            "Upload every required document (identity document, signature, KYC form as applicable).",
            "Confirm each uploaded document has status Uploaded.",
        ],
        "deep_link": "/proposals/{id}/documents",
    },
    {
        "key": "underwriting_cleared_or_not_required",
        "error_code": "PROPOSAL_UNDERWRITING_PENDING",
        "message": "Underwriting has not cleared for this proposal.",
        "resolution_steps": [
            "Complete the underwriting review (medical requirements if raised).",
            "Apply a clear or load underwriting decision, then re-run payment readiness.",
        ],
        "deep_link": "/proposals/{id}/underwriting",
    },
    {
        "key": "not_expired",
        "error_code": "PROPOSAL_EXPIRED",
        "message": "This proposal has expired.",
        "resolution_steps": [
            "Create a fresh proposal from a current quotation.",
            "Cancel this proposal to close it out.",
        ],
        "deep_link": "/proposals/{id}",
    },
    {
        "key": "quotation_version_current",
        "error_code": "PROPOSAL_QUOTATION_VERSION_STALE",
        "message": "The underlying quotation has been revised after conversion.",
        "resolution_steps": [
            "Open the quotation and review its latest version.",
            "Reconvert from the current quotation version so the proposal matches the quote.",
        ],
        "deep_link": "/proposals/{id}/quotation",
    },
)

_SPEC_MAP = {spec["key"]: spec for spec in _SPECS}


def _missing_enrichment_sections(proposal):
    """Enrichment gaps excluding beneficiaries and documents (own checklist items)."""
    sections = enrichment_service.missing_sections(proposal)
    return [
        section
        for section in sections.get("required_missing", [])
        if section not in ("beneficiaries", "documents")
    ]


def _beneficiaries_valid(proposal):
    beneficiaries = list(proposal.beneficiaries.all())
    if not beneficiaries:
        return False
    if not any(item.is_primary for item in beneficiaries):
        return False
    total = sum((item.share_percent or 0) for item in beneficiaries)
    if total != 100:
        return False
    return all((not item.is_minor or bool((item.guardian_name or "").strip())) for item in beneficiaries)


def _underwriting_cleared(proposal):
    if proposal.underwriting_status == UnderwritingStatus.CLEARED:
        return True
    return not proposal.medical_required and proposal.underwriting_status != UnderwritingStatus.DECLINED


def _check(proposal, key, as_of=None):
    if key == "partner_verified":
        passed = bool(proposal.partner_id) and bool(getattr(proposal.quotation, "partner_verified", False))
    elif key == "enrichment_complete":
        passed = not _missing_enrichment_sections(proposal)
    elif key == "beneficiaries_valid":
        passed = _beneficiaries_valid(proposal)
    elif key == "mandatory_documents_complete":
        passed = not document_service.missing_mandatory_documents(proposal)
    elif key == "underwriting_cleared_or_not_required":
        passed = _underwriting_cleared(proposal)
    elif key == "not_expired":
        passed = not parameter_resolver.is_expired(proposal, as_of=as_of)
    elif key == "quotation_version_current":
        version = proposal.quotation_version
        quoted_version = getattr(proposal.quotation, "current_version_number", None)
        passed = bool(version) and bool(quoted_version) and version.version_number == quoted_version
    else:  # pragma: no cover - guarded by CHECKLIST_ITEMS.
        passed = True
    return passed


def evaluate_payment_ready(proposal, as_of=None):
    """Return the current pass/fail checklist for UI rendering (no mutation)."""
    items = []
    for key in CHECKLIST_ITEMS:
        spec = _SPEC_MAP[key]
        passed = _check(proposal, key, as_of=as_of)
        items.append(
            {
                "key": key,
                "passed": bool(passed),
                "error_code": "" if passed else spec["error_code"],
                "message": "" if passed else spec["message"],
                "resolution_steps": [] if passed else spec["resolution_steps"],
                "deep_link": "" if passed else spec["deep_link"].format(id=proposal.pk),
            }
        )
    return {
        "passed": all(item["passed"] for item in items),
        "items": items,
        "proposal": str(proposal.pk),
        "status": proposal.status,
        "expiry_date": proposal.expiry_date.isoformat() if proposal.expiry_date else None,
    }


def mark_payment_ready(*, proposal, actor=None, request=None, source_channel="API", reason="", as_of=None):
    """Transition a fully-complete proposal to payment readiness.

    All-pass runs ENRICHMENT → PAYMENT_READY → AWAITING_FIRST_PREMIUM once,
    stamps ``payment_ready``/``payment_ready_at``, links the first-premium
    commitment (source_type=PROPOSAL, installment 1), emits a single
    ``ProposalPaymentReady`` event consumed by the receipts module, and audits
    the full checklist snapshot. Re-evaluation on an already-ready proposal is
    idempotent: it returns the current state without re-emitting the event.
    """
    if proposal.status in ("CONVERTED", "CANCELLED", "EXPIRED"):
        raise ProposalError(
            f"Cannot mark a '{proposal.status}' proposal payment-ready.",
            error_code="PROPOSAL_INVALID_TRANSITION",
            status_code=422,
            resolution_steps=["Only non-terminal proposals can become payment-ready."],
        )

    result = evaluate_payment_ready(proposal, as_of=as_of)
    if not result["passed"]:
        failed = [item for item in result["items"] if not item["passed"]]
        raise ProposalError(
            "This proposal is not payment-ready; resolve each failed checklist item.",
            error_code="PROPOSAL_NOT_PAYMENT_READY",
            status_code=409,
            details={"checklist": failed, "status": proposal.status},
            resolution_steps=["Open each failed item using its deep link.", "Resolve it, then re-run payment readiness."],
        )

    if proposal.status == "AWAITING_FIRST_PREMIUM" and proposal.payment_ready:
        return {**result, "already_ready": True}

    with transaction.atomic():
        before = AuditService.snapshot(proposal)
        proposal.payment_ready = True
        proposal.payment_ready_at = timezone.now()
        proposal.status = "AWAITING_FIRST_PREMIUM"
        proposal.save()

        from apps.ol_proposals.services.first_premium_service import link_first_premium_commitment

        link_first_premium_commitment(
            proposal=proposal, actor=actor, request=request, source_channel=source_channel
        )

        after = AuditService.snapshot(proposal)
        after["checklist"] = result
        AuditService.log_action(
            "MARK_PAYMENT_READY",
            proposal,
            actor=actor,
            request=request,
            before_state=before,
            after_state=after,
            changed_fields=["status", "payment_ready", "payment_ready_at"],
            reason=reason or "Payment readiness evaluation passed; proposal moved to awaiting first premium.",
            source_channel=source_channel,
        )
        proposal_events.emit_payment_ready(
            proposal,
            actor=actor,
            from_status=before.get("status") or proposal.status,
            reason=reason or "Payment readiness evaluation passed.",
            source_channel=source_channel,
            metadata={
                "checklist": [item["key"] for item in result["items"] if item["passed"]],
                "first_premium_commitment": proposal.first_premium_commitment.commitment_number
                if proposal.first_premium_commitment_id
                else None,
            },
        )
        from apps.ol_proposals.services.notification_service import notify_payment_ready

        notify_payment_ready(proposal=proposal, actor=actor, source_channel=source_channel)
    return {**result, "already_ready": False}