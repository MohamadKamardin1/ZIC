"""Enrichment service: section updates, beneficiary CRUD, completeness."""

from decimal import Decimal

from django.db import transaction

from apps.governance.services.audit_service import AuditService
from apps.ol_proposals import events as proposal_events
from apps.ol_proposals.errors import (
    ProposalError,
    beneficiary_shares_invalid,
)
from apps.ol_proposals.models import OLProposalBeneficiary


def mask_account_number(value):
    """Mask a bank account number, keeping the last 4 digits."""
    value = (value or "").strip()
    if not value:
        return ""
    if len(value) <= 4:
        return "*" * len(value)
    return "*" * (len(value) - 4) + value[-4:]


def apply_section(*, proposal, section, data, actor=None, request=None, source_channel="API", suppress_errors=False):
    """Apply one enrichment section (employer/intermediary/declarations/bank) with audit + event."""
    allowed = {"employer", "intermediary", "declarations", "bank_details"}
    if section not in allowed:
        raise ProposalError(
            f"Unknown enrichment section '{section}'.",
            error_code="VALIDATION_ERROR",
            status_code=422,
            field_errors={"section": [f"Choose one of: {', '.join(sorted(allowed))}."]},
        )

    with transaction.atomic():
        before = AuditService.snapshot(proposal)
        if section == "employer":
            _apply_employer(proposal, data)
        elif section == "intermediary":
            _apply_intermediary(proposal, data)
        elif section == "declarations":
            _apply_declarations(proposal, data)
        elif section == "bank_details":
            _apply_bank(proposal, data)

        if not suppress_errors:
            proposal.full_clean()

        proposal.save()

        after = AuditService.snapshot(proposal)
        changed = AuditService.changed_fields(before, after)
        AuditService.log_action(
            f"ENRICH_{section.upper()}",
            proposal,
            actor=actor,
            request=request,
            before_state=before,
            after_state=after,
            changed_fields=changed,
            reason=f"Proposal enrichment section '{section}' updated.",
            source_channel=source_channel,
        )
        proposal_events.emit_enriched(
            proposal,
            actor=actor,
            from_status=before.get("status") or proposal.status,
            to_status=proposal.status,
            reason=f"Enriched {section.replace('_', ' ')}.",
            source_channel=source_channel,
        )
        return proposal


def _apply_employer(proposal, data):
    if "employer_partner" in data:
        proposal.employer_partner_id = data.get("employer_partner") or None
    if "employment_reference" in data:
        proposal.employment_reference = str(data.get("employment_reference") or "")[:120]
    if "payroll_deduction" in data:
        proposal.payroll_deduction = bool(data.get("payroll_deduction"))
    if proposal.employer_partner_id:
        proposal.employer_name_snapshot = str(proposal.employer_partner)


def _apply_intermediary(proposal, data):
    if "agent_partner" in data:
        proposal.agent_partner_id = data.get("agent_partner") or None
    if "intermediary_channel" in data:
        proposal.intermediary_channel = (data.get("intermediary_channel") or "").strip().upper()
    if proposal.agent_partner_id:
        proposal.agent_name_snapshot = str(proposal.agent_partner)


def _apply_declarations(proposal, data):
    for field in ("declaration_pep_flag", "declaration_aml_flag", "existing_policies_count", "occupation_risk_note"):
        if field in data:
            setattr(proposal, field, data.get(field))
    if "declarations_free_text" in data:
        value = data.get("declarations_free_text")
        if value is not None and not isinstance(value, dict):
            raise ProposalError(
                "Declarations must be a JSON object.",
                error_code="VALIDATION_ERROR",
                status_code=422,
                field_errors={"declarations_free_text": ["Must be a JSON object."]},
            )
        proposal.declarations_free_text = value or {}


def _apply_bank(proposal, data):
    for field in ("bank_name", "bank_account_name", "bank_account_number"):
        if field in data:
            setattr(proposal, field, str(data.get(field) or "")[:160 if field == "bank_name" else 200 if field == "bank_account_name" else 80])


# ---------------------------------------------------------------------------
# Beneficiaries
# ---------------------------------------------------------------------------


def validate_beneficiaries(proposal):
    """Enforce shares = 100, at least one primary, and minor-guardian rules."""
    beneficiaries = list(proposal.beneficiaries.all())
    if not beneficiaries:
        return
    if not any(item.is_primary for item in beneficiaries):
        raise ProposalError(
            "At least one beneficiary must be marked as primary.",
            error_code="PROPOSAL_BENEFICIARY_SHARES_INVALID",
            status_code=422,
            resolution_steps=["Mark one beneficiary as primary.", "Confirm the share percentages total 100%."],
        )
    total = sum((Decimal(str(item.share_percent or 0)) for item in beneficiaries), Decimal("0.00"))
    if total != Decimal("100.00"):
        raise beneficiary_shares_invalid(total)
    for item in beneficiaries:
        if item.is_minor and not (item.guardian_name or "").strip():
            raise ProposalError(
                f"A guardian is required for minor beneficiary '{item.person_name}'.",
                error_code="PROPOSAL_BENEFICIARY_GUARDIAN_REQUIRED",
                status_code=422,
                resolution_steps=["Record the guardian name and relationship.", "Retry the beneficiary update."],
            )


def replace_beneficiaries(*, proposal, items, actor=None, request=None, source_channel="API"):
    """Atomically replace the beneficiary set with a validated batch."""
    if not items:
        raise ProposalError(
            "At least one beneficiary is required.",
            error_code="PROPOSAL_BENEFICIARY_SHARES_INVALID",
            status_code=422,
            resolution_steps=["Add at least one beneficiary with a primary flag."],
        )
    total = sum((Decimal(str(item.get("share_percent") or 0)) for item in items), Decimal("0.00"))
    if total != Decimal("100.00"):
        raise beneficiary_shares_invalid(total)
    if not any(item.get("is_primary") for item in items):
        raise ProposalError(
            "At least one beneficiary must be marked as primary.",
            error_code="PROPOSAL_BENEFICIARY_SHARES_INVALID",
            status_code=422,
            resolution_steps=["Mark one beneficiary as primary."],
        )
    for item in items:
        if item.get("is_minor") and not (item.get("guardian_name") or "").strip():
            raise ProposalError(
                "A guardian is required for a minor beneficiary.",
                error_code="PROPOSAL_BENEFICIARY_GUARDIAN_REQUIRED",
                status_code=422,
                resolution_steps=["Record the guardian name and relationship."],
            )
    seen = set()
    for item in items:
        identity_type = (item.get("identity_type") or "").strip().upper()
        identity_number = (item.get("identity_number") or "").strip()
        if identity_type and identity_number:
            key = (identity_type, identity_number)
            if key in seen:
                raise ProposalError(
                    f"A beneficiary with {identity_type} '{identity_number}' is duplicated.",
                    error_code="PROPOSAL_DUPLICATE_BENEFICIARY",
                    status_code=422,
                    resolution_steps=["Review the beneficiary identities in the batch."],
                )
            seen.add(key)

    with transaction.atomic():
        before = list(proposal.beneficiaries.all())
        proposal.beneficiaries.all().delete()
        fields = ("person_name", "identity_type", "identity_number", "share_percent", "is_primary", "is_minor", "guardian_name", "guardian_identity_type", "guardian_identity_number", "guardian_relationship")
        created = []
        for item in items:
            beneficiary = OLProposalBeneficiary(proposal=proposal)
            for field in fields:
                if field in item:
                    setattr(beneficiary, field, item.get(field))
            if beneficiary.identity_type:
                beneficiary.identity_type = beneficiary.identity_type.upper()
            if item.get("beneficial_type"):
                from apps.ol_parameters.models import OLBeneficialType

                beneficial = OLBeneficialType.objects.filter(pk=item["beneficial_type"]).first()
                if beneficial:
                    beneficiary.beneficial_type = beneficial
                    beneficiary.beneficial_type_name_snapshot = beneficial.name or str(beneficial)
            beneficiary.full_clean()
            beneficiary.save()
            created.append(beneficiary)
        AuditService.log_action(
            "ENRICH_BENEFICIARY_REPLACE",
            proposal,
            actor=actor,
            request=request,
            before_state={"beneficiaries": [item.person_name for item in before]},
            after_state={"beneficiaries": [item.person_name for item in created]},
            changed_fields=["beneficiaries"],
            reason=f"Beneficiary set replaced with {len(created)} beneficiary(ies).",
            source_channel=source_channel,
        )
        proposal_events.emit_enriched(proposal, actor=actor, reason="Beneficiaries replaced.", source_channel=source_channel)
    return created


def _duplicate_identity(proposal, identity_type, identity_number, exclude=None):
    identity_type = (identity_type or "").strip().upper()
    identity_number = (identity_number or "").strip()
    if not identity_type or not identity_number:
        return False
    queryset = proposal.beneficiaries.filter(
        identity_type__iexact=identity_type,
        identity_number__iexact=identity_number,
    )
    if exclude:
        queryset = queryset.exclude(pk=exclude)
    return queryset.exists()


def add_beneficiary(*, proposal, data, actor=None, request=None, source_channel="API"):
    beneficiary = OLProposalBeneficiary(proposal=proposal)
    with transaction.atomic():
        _populate_beneficiary(beneficiary, data, proposal)
        validate_beneficiaries(proposal)
        AuditService.log_action(
            "ENRICH_BENEFICIARY_CREATE",
            proposal,
            actor=actor,
            request=request,
            after_state=AuditService.snapshot(proposal),
            changed_fields=["beneficiaries"],
            reason=f"Beneficiary '{beneficiary.person_name}' added.",
            source_channel=source_channel,
        )
        proposal_events.emit_enriched(proposal, actor=actor, reason="Beneficiary added.", source_channel=source_channel)
    return beneficiary


def update_beneficiary(*, proposal, beneficiary_id, data, actor=None, request=None, source_channel="API"):
    beneficiary = proposal.beneficiaries.filter(pk=beneficiary_id).first()
    if not beneficiary:
        raise ProposalError(
            "The beneficiary could not be found.",
            error_code="PROPOSAL_BENEFICIARY_NOT_FOUND",
            status_code=404,
            resolution_steps=["Verify the beneficiary reference."],
        )
    with transaction.atomic():
        _populate_beneficiary(beneficiary, data, proposal, exclude=beneficiary_id)
        validate_beneficiaries(proposal)
        AuditService.log_action(
            "ENRICH_BENEFICIARY_UPDATE",
            proposal,
            actor=actor,
            request=request,
            before_state=AuditService.snapshot(beneficiary),
            after_state=AuditService.snapshot(beneficiary),
            changed_fields=["beneficiaries"],
            reason=f"Beneficiary '{beneficiary.person_name}' updated.",
            source_channel=source_channel,
        )
        proposal_events.emit_enriched(proposal, actor=actor, reason="Beneficiary updated.", source_channel=source_channel)
    return beneficiary


def remove_beneficiary(*, proposal, beneficiary_id, actor=None, request=None, source_channel="API"):
    beneficiary = proposal.beneficiaries.filter(pk=beneficiary_id).first()
    if not beneficiary:
        raise ProposalError(
            "The beneficiary could not be found.",
            error_code="PROPOSAL_BENEFICIARY_NOT_FOUND",
            status_code=404,
            resolution_steps=["Verify the beneficiary reference."],
        )
    with transaction.atomic():
        name = beneficiary.person_name
        beneficiary.delete()
        validate_beneficiaries(proposal)
        AuditService.log_action(
            "ENRICH_BENEFICIARY_DELETE",
            proposal,
            actor=actor,
            request=request,
            before_state={"beneficiaries": [name]},
            changed_fields=["beneficiaries"],
            reason=f"Beneficiary '{name}' removed.",
            source_channel=source_channel,
        )
        proposal_events.emit_enriched(proposal, actor=actor, reason="Beneficiary removed.", source_channel=source_channel)
    return proposal


def _populate_beneficiary(beneficiary, data, proposal, exclude=None):
    for field in ("person_name", "identity_type", "identity_number", "share_percent", "is_primary", "is_minor", "guardian_name", "guardian_identity_type", "guardian_identity_number", "guardian_relationship"):
        if field in data:
            setattr(beneficiary, field, data.get(field))
    if beneficiary.identity_type:
        beneficiary.identity_type = beneficiary.identity_type.upper()
    if "beneficial_type" in data and data.get("beneficial_type"):
        from apps.ol_parameters.models import OLBeneficialType

        beneficial = OLBeneficialType.objects.filter(pk=data["beneficial_type"]).first()
        if beneficial:
            beneficiary.beneficial_type = beneficial
            beneficiary.beneficial_type_name_snapshot = beneficial.name or str(beneficial)
    if _duplicate_identity(proposal, beneficiary.identity_type, beneficiary.identity_number, exclude=exclude or beneficiary.pk):
        raise ProposalError(
            f"A beneficiary with {beneficiary.identity_type} '{beneficiary.identity_number}' already exists.",
            error_code="PROPOSAL_DUPLICATE_BENEFICIARY",
            status_code=422,
            resolution_steps=["Review the existing beneficiaries.", "Remove the duplicate or use a different identity document."],
        )
    beneficiary.full_clean()
    beneficiary.save()


# ---------------------------------------------------------------------------
# Completeness
# ---------------------------------------------------------------------------

REQUIRED_SECTIONS = ["beneficiaries", "declarations", "bank_details", "documents"]
OPTIONAL_SECTIONS = ["employer", "intermediary"]
ALL_SECTIONS = REQUIRED_SECTIONS + OPTIONAL_SECTIONS


def missing_sections(proposal):
    """Return which required/optional sections are incomplete for payment-readiness."""
    missing = []

    def mark(section, complete):
        if not complete:
            missing.append(section)

    beneficiaries = list(proposal.beneficiaries.all())
    mark("beneficiaries", bool(beneficiaries) and any(item.is_primary for item in beneficiaries) and sum(map(lambda item: Decimal(str(item.share_percent or 0)), beneficiaries), Decimal("0.00")) == Decimal("100.00") and all((not item.is_minor or bool((item.guardian_name or "").strip())) for item in beneficiaries))
    mark("declarations", proposal.declaration_pep_flag is not None and proposal.declaration_aml_flag is not None)
    mark("bank_details", bool((proposal.bank_name or "").strip()) and bool((proposal.bank_account_name or "").strip()) and bool((proposal.bank_account_number or "").strip()))
    from apps.ol_proposals.services.document_service import missing_mandatory_documents

    mark("documents", missing_mandatory_documents(proposal) == [])
    mark("employer", bool(proposal.employer_partner_id))
    mark("intermediary", bool(proposal.agent_partner_id))

    complete = all(section not in missing for section in REQUIRED_SECTIONS)
    return {"missing": missing, "required_missing": [section for section in REQUIRED_SECTIONS if section in missing], "complete": complete}