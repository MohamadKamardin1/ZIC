"""Quotation → proposal conversion service (BR-01, idempotent, audited)."""

from dataclasses import dataclass
from datetime import date, timedelta

from django.db import transaction

from apps.governance.services.audit_service import AuditService
from apps.ol_parameters.models import OLDefaultSystemParameter
from apps.ol_proposals import events as proposal_events
from apps.ol_proposals.errors import ProposalError, partner_not_verified
from apps.ol_proposals.models import (
    OLProposal,
    OLProposalBenefit,
    OLProposalFundAllocation,
    OLProposalInstallmentConfig,
    OLProposalInstallmentRateRow,
    OLProposalMember,
    OLProposalPlanConfig,
    OLProposalRider,
)
from apps.ol_quotations.models import OLQuotation, OLQuotationVersion, QuotationStatus
from apps.system_parameters.services.numbering_service import NumberingEngine

PARAM_VALIDITY_DAYS = "PROPOSAL_VALIDITY_DAYS"


@dataclass
class ConversionResult:
    proposal: OLProposal
    created: bool
    duplicate: bool = False


def _validity_days():
    row = OLDefaultSystemParameter.objects.filter(
        parameter_key=PARAM_VALIDITY_DAYS, is_active=True
    ).first()
    if row is None:
        return 60
    for value in (row.integer_value, row.decimal_value, getattr(row, "string_value", None)):
        if value is None:
            continue
        try:
            days = int(value)
            if days >= 1:
                return days
        except (TypeError, ValueError):
            continue
    return 60


def _prospect_snapshot(quotation):
    return {
        "quote_number": quotation.quote_number,
        "quote_name": quotation.quote_name,
        "quote_date": quotation.quote_date.isoformat() if quotation.quote_date else None,
        "identity_type": quotation.identity_type,
        "identity_number": quotation.identity_number,
        "date_of_birth": quotation.date_of_birth.isoformat() if quotation.date_of_birth else None,
        "age_at_quote": quotation.age_at_quote,
        "gender": quotation.gender,
        "smoker_status": quotation.smoker_status,
        "location": quotation.location,
        "address": quotation.address,
        "currency": quotation.currency,
        "partner_id": str(quotation.partner_id or quotation.linked_partner_id) if (quotation.partner_id or quotation.linked_partner_id) else None,
    }


def _version_children_snapshot(version, quotation):
    full_snapshot = version.snapshot or {}
    children = full_snapshot.get("children", {}) if isinstance(full_snapshot, dict) else {}
    plans = children.get("ol_quotations.olquotationplanconfiguration", [])
    if not plans:
        plans = children.get("ol_quotations.olquotationproduct", [])
    financial = full_snapshot.get("financial_summary") or {}
    return plans, financial


def _financial_summary(quotation):
    summary = getattr(quotation, "financial_summary", None)
    if not summary:
        return {}
    return {
        "total_sum_assured": str(summary.total_sum_assured),
        "total_premium": str(summary.total_premium),
        "total_rider_premium": str(summary.total_rider_premium),
        "total_benefit_premium": str(summary.total_benefit_premium),
        "base_premium": str(summary.base_premium),
        "total_loading": str(summary.total_loading),
        "total_discount": str(summary.total_discount),
        "total_tax": str(summary.total_tax),
        "installment_charge": str(summary.installment_charge),
        "estimated_maturity_value": str(summary.estimated_maturity_value),
        "currency": summary.currency,
    }


def _carry_over(proposal, quotation):
    """Carry config data from the quotation into the typed proposal children."""
    counts = {
        "plan_configs": 0,
        "members": 0,
        "installment_configs": 0,
        "installment_rate_rows": 0,
        "fund_allocations": 0,
        "riders": 0,
        "benefits": 0,
    }

    plan_map = {}
    for config in quotation.plan_configurations.filter(is_selected=True):
        plan_config = OLProposalPlanConfig.objects.create(
            proposal=proposal,
            product_version=config.product_version,
            plan=config.plan,
            plan_name_snapshot=getattr(config.plan, "name", "") or "",
            sub_product_code=config.sub_product_code,
            section_number=config.section_number,
            base_sum_assured=config.base_sum_assured,
            term_years=config.term_years,
            payment_period_years=config.payment_period_years,
            premium_frequency=config.premium_frequency,
            quote_basis=config.quote_basis,
            estimated_maturity_value=config.estimated_maturity_value,
            premium_factor=config.premium_factor,
            premium_amount=config.premium_amount,
            is_selected=config.is_selected,
        )
        plan_map[config.pk] = plan_config
        counts["plan_configs"] += 1

    for member in quotation.members.all():
        OLProposalMember.objects.create(
            proposal=proposal,
            member_type=member.member_type,
            partner=member.partner,
            first_name=member.first_name,
            last_name=member.last_name,
            identity_number=member.identity_number,
            date_of_birth=member.date_of_birth,
            age_at_quote=member.age_at_quote,
            gender=member.gender,
            smoker_status=member.smoker_status,
            relationship=member.relationship,
            contact_phone=member.contact_phone,
            contact_email=member.contact_email,
            member_sum_assured=member.member_sum_assured,
            coverage_basis=member.coverage_basis,
        )
        counts["members"] += 1

    for installment in quotation.installment_configurations.filter(is_selected=True):
        config_row = OLProposalInstallmentConfig.objects.create(
            proposal=proposal,
            plan_config=plan_map.get(installment.plan_configuration_id),
            frequency=installment.frequency,
            annuity_period_years=installment.annuity_period_years,
            number_of_installments=installment.number_of_installments,
            after_maturity_benefits=installment.after_maturity_benefits,
            before_maturity_benefits=installment.before_maturity_benefits,
            installment_amount=installment.installment_amount,
            first_due_date=installment.first_due_date,
            currency=installment.currency,
            is_selected=installment.is_selected,
        )
        counts["installment_configs"] += 1
        for row in installment.rate_rows.all():
            OLProposalInstallmentRateRow.objects.create(
                installment_config=config_row,
                sequence=row.sequence,
                period_from=row.period_from,
                period_to=row.period_to,
                description=row.description,
                rate_percent=row.rate_percent,
                rate=row.rate,
                charge=row.charge,
                notes=row.notes,
            )
            counts["installment_rate_rows"] += 1

    for allocation in quotation.fund_allocations.filter(is_selected=True):
        OLProposalFundAllocation.objects.create(
            proposal=proposal,
            plan_config=plan_map.get(allocation.plan_configuration_id),
            fund=allocation.fund,
            fund_name_snapshot=getattr(allocation.fund, "name", "") or "",
            allocation_percentage=allocation.allocation_percentage,
            allocation_amount=allocation.allocation_amount,
            is_selected=allocation.is_selected,
        )
        counts["fund_allocations"] += 1

    for rider in quotation.rider_selections.filter(is_selected=True):
        OLProposalRider.objects.create(
            proposal=proposal,
            rider=rider.rider,
            rider_name_snapshot=getattr(rider.rider, "name", "") or "",
            plan_config=plan_map.get(rider.plan_configuration_id),
            rider_sum_assured=rider.rider_sum_assured,
            rider_term_years=rider.rider_term_years,
            beneficial_type=rider.beneficial_type,
            benefit_basis=rider.benefit_basis,
            benefit_value=rider.benefit_value,
            loading=rider.loading,
            discount=rider.discount,
            premium_amount=rider.premium_amount,
            is_selected=rider.is_selected,
        )
        counts["riders"] += 1

    for benefit in quotation.benefits.filter(is_selected=True):
        OLProposalBenefit.objects.create(
            proposal=proposal,
            plan_config=plan_map.get(benefit.plan_configuration_id),
            code=benefit.code,
            name=benefit.name,
            benefit_type=benefit.benefit_type,
            basis=benefit.basis,
            value=benefit.value,
            loading=benefit.loading,
            discount=benefit.discount,
            maximum_cap=benefit.maximum_cap,
            sum_assured=benefit.sum_assured,
            premium_amount=benefit.premium_amount,
            is_selected=benefit.is_selected,
        )
        counts["benefits"] += 1

    return counts


def convert_quotation_to_proposal(*, quotation, actor=None, request=None, version_number=None, source_channel="API", notes=""):
    """Convert a FINALIZED, partner-verified quotation into a proposal.

    Idempotent on ``(quotation, quotation_version)``: a second call returns the
    existing proposal with ``created=False``.
    """
    locked = OLQuotation.objects.select_for_update().get(pk=quotation.pk)
    if locked.status != QuotationStatus.FINALIZED:
        raise ProposalError(
            "Only finalized quotations can be converted to proposals.",
            error_code="PROPOSAL_ERROR",
            status_code=422,
            resolution_steps=["Finalize the quotation.", "Re-run conversion after finalization."],
        )
    if not locked.partner_verified:
        partner_label = str(locked.partner) if locked.partner_id else "The quotation partner"
        raise partner_not_verified(partner_label)
    if locked.expiry_date and locked.expiry_date < date.today():
        raise ProposalError(
            "Expired quotations cannot be converted to proposals.",
            error_code="PROPOSAL_EXPIRED",
            status_code=422,
            resolution_steps=["Create a fresh quotation and convert it."],
        )
    if locked.approval_required:
        raise ProposalError(
            "Quotation approval must be resolved before conversion to proposal.",
            error_code="PROPOSAL_ERROR",
            status_code=422,
            resolution_steps=["Resolve the quotation approval requirement.", "Re-run conversion."],
        )

    version = OLQuotationVersion.objects.filter(
        quotation=locked,
        version_number=version_number or locked.current_version_number,
    ).first()
    if version is None:
        version = OLQuotationVersion.objects.filter(quotation=locked).order_by("-version_number").first()
    if version is None:
        raise ProposalError(
            "The quotation has no version snapshot to convert.",
            error_code="PROPOSAL_ERROR",
            status_code=422,
            resolution_steps=["Recalculate or re-finalize the quotation."],
        )

    existing = OLProposal.objects.filter(quotation=locked, quotation_version=version).first()
    if existing:
        return ConversionResult(existing, created=False, duplicate=True)

    with transaction.atomic():
        plans_snapshot, version_financial = _version_children_snapshot(version, locked)
        financial_snapshot = version_financial or _financial_summary(locked)
        partner = locked.partner or locked.linked_partner

        proposal = OLProposal(
            quotation=locked,
            quotation_version=version,
            proposal_number=NumberingEngine.generate_number("OL_PROPOSAL", OLProposal, field_name="proposal_number"),
            status="ENRICHMENT",
            partner=partner,
            partner_name_snapshot=str(partner) if partner else "",
            agent_partner=locked.agent_partner,
            agent_name_snapshot=str(locked.agent_partner) if locked.agent_partner_id else "",
            currency=locked.currency,
            expiry_date=date.today() + timedelta(days=_validity_days()),
            source_channel=source_channel,
            created_by=actor if actor and getattr(actor, "is_authenticated", False) else None,
            prospect_snapshot=_prospect_snapshot(locked),
            plans_snapshot=plans_snapshot,
            financial_summary_snapshot=financial_snapshot,
        )
        proposal.save()
        counts = _carry_over(proposal, locked)

        proposal_events.emit_created(proposal, actor=actor, reason=notes or "Quotation converted to proposal.", source_channel=source_channel)

        summary = ", ".join(f"{key}={value}" for key, value in counts.items())
        AuditService.log_action(
            "CONVERT_QUOTATION_TO_PROPOSAL",
            proposal,
            actor=actor,
            request=request,
            after_state=AuditService.snapshot(proposal),
            reason=f"Quotation {locked.quote_number} converted. Carried: {summary}.",
            source_channel=source_channel,
        )
        return ConversionResult(proposal, created=True, duplicate=False)