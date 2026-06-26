import logging

from django.db import transaction

from apps.partners.models import (
    PartnerTypeAssignment,
    PartnerDocument,
    PartnerDynamicFieldValue,
    PartnerAssignmentContact,
    PartnerAssignmentBankAccount,
    PartnerKYCProfile,
)

logger = logging.getLogger(__name__)


class PartnerSetupService:

    @staticmethod
    @transaction.atomic
    def generate_setup(assignment):
        partner_type = assignment.partner_type
        created = {"documents": 0, "fields": 0, "kyc": 0}

        active_doc_reqs = partner_type.document_requirements.filter(is_active=True)
        for req in active_doc_reqs:
            existing = assignment.documents.filter(document_requirement=req).count()
            if existing == 0:
                PartnerDocument.objects.create(
                    assignment=assignment,
                    document_requirement=req,
                    status="NOT_SUBMITTED",
                )
                created["documents"] += 1

        active_fields = partner_type.field_configurations.filter(is_active=True)
        for field in active_fields:
            PartnerDynamicFieldValue.objects.get_or_create(
                assignment=assignment,
                field_config=field,
            )
            created["fields"] += 1

        kyc, kyc_created = PartnerKYCProfile.objects.get_or_create(
            assignment=assignment,
            defaults={"kyc_status": "NOT_SET"},
        )
        if kyc_created:
            created["kyc"] = 1

        logger.info(
            "Setup generated for %s — %s: %s",
            assignment.partner.partner_number,
            partner_type.name,
            created,
        )
        return created

    @staticmethod
    def get_setup_summary(assignment):
        partner_type = assignment.partner_type

        doc_configs = partner_type.document_requirements.filter(is_active=True).order_by("sort_order")
        total_docs = doc_configs.count()
        submitted_docs = assignment.documents.exclude(status="NOT_SUBMITTED").count()
        required_docs = doc_configs.filter(is_required=True).count()
        required_submitted = assignment.documents.filter(
            document_requirement__is_required=True,
        ).exclude(status="NOT_SUBMITTED").count()

        field_configs = partner_type.field_configurations.filter(is_active=True).order_by("display_order")
        total_fields = field_configs.count()
        filled_fields = assignment.field_values.exclude(value_json__isnull=True).exclude(
            value_json={}
        ).count()
        required_fields = field_configs.filter(is_required=True).count()
        required_filled = assignment.field_values.filter(
            field_config__is_required=True,
        ).exclude(value_json__isnull=True).exclude(value_json={}).count()

        contact_configs = partner_type.contact_requirements.filter(is_active=True).order_by("display_order")
        total_contacts = contact_configs.count()
        submitted_contacts = assignment.assignment_contacts.count()

        bank_configs = partner_type.bank_requirements.filter(is_active=True).order_by("display_order")
        total_banks = bank_configs.count()
        submitted_banks = assignment.assignment_bank_accounts.count()

        kyc = None
        try:
            kyc = assignment.kyc_profiles.first()
        except PartnerKYCProfile.DoesNotExist:
            pass

        doc_pct = int((submitted_docs / total_docs * 100)) if total_docs else 100
        field_pct = int((filled_fields / total_fields * 100)) if total_fields else 100
        contact_pct = int((submitted_contacts / total_contacts * 100)) if total_contacts else 100
        bank_pct = int((submitted_banks / total_banks * 100)) if total_banks else 100

        return {
            "documents": {
                "total": total_docs,
                "submitted": submitted_docs,
                "required": required_docs,
                "required_submitted": required_submitted,
                "progress_pct": doc_pct,
            },
            "fields": {
                "total": total_fields,
                "filled": filled_fields,
                "required": required_fields,
                "required_filled": required_filled,
                "progress_pct": field_pct,
            },
            "contacts": {
                "total": total_contacts,
                "submitted": submitted_contacts,
                "progress_pct": contact_pct,
            },
            "banks": {
                "total": total_banks,
                "submitted": submitted_banks,
                "progress_pct": bank_pct,
            },
            "kyc": {
                "status": kyc.kyc_status if kyc else "NOT_SET",
                "risk_score": float(kyc.risk_score) if kyc and kyc.risk_score else None,
                "risk_level": kyc.risk_level if kyc else "",
            },
        }
