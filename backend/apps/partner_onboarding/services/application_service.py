import logging
from datetime import date

from django.db import transaction
from django.utils import timezone

from apps.partner_onboarding.exceptions import (
    ApplicationTransitionError,
    ApplicationValidationError,
    PartnerConversionError,
)
from apps.partner_onboarding.models import PartnerApplication
from apps.system_parameters.services.workflow_service import WorkflowEngine
from apps.system_parameters.services.numbering_service import NumberingEngine
from apps.system_parameters.services.validation_config_service import ValidationConfigService
from apps.system_parameters.services.config_service import (
    ConfigurationService,
    ConfigurationError,
)

logger = logging.getLogger(__name__)


class ApplicationService:

    @staticmethod
    def _validate_transition(application, target_status):
        try:
            WorkflowEngine.validate_transition(application.status, target_status)
        except ConfigurationError as e:
            raise ApplicationTransitionError(
                message=str(e),
                details={
                    "current_status": application.status,
                    "requested_status": target_status,
                    "allowed_transitions": WorkflowEngine.get_allowed_transitions(application.status),
                },
            )

    @staticmethod
    def generate_application_number(partner_type="INDIVIDUAL"):
        return NumberingEngine.generate_application_number(partner_type)

    @staticmethod
    def deduplicate_drafts(email):
        if not email:
            return
        duplicates = PartnerApplication.objects.filter(
            email=email, status="DRAFT",
        ).order_by("-created_at")
        if duplicates.count() > 0:
            duplicates.exclude(pk=duplicates.first().pk).delete()

    @staticmethod
    def create_draft(user, data):
        ApplicationService.deduplicate_drafts(data.get("email"))
        data["application_number"] = (
            ApplicationService.generate_application_number(data.get("partner_type"))
        )
        data["submitted_by"] = user
        application = PartnerApplication.objects.create(**data)
        logger.info(
            "Draft application created: %s by %s",
            application.application_number,
            user.email,
        )
        return application

    @staticmethod
    def submit(application, user):
        ApplicationService._validate_transition(application, "SUBMITTED")
        partner_type = application.partner_type
        if partner_type == "INDIVIDUAL":
            required = ValidationConfigService.get_individual_required_fields()
            for field in required:
                if not getattr(application, field, None):
                    raise ApplicationValidationError(
                        message=f"Field '{field}' is required for submission.",
                        details={"missing_field": field},
                    )
        elif partner_type == "CORPORATE":
            required = ValidationConfigService.get_corporate_required_fields()
            for field in required:
                if not getattr(application, field, None):
                    raise ApplicationValidationError(
                        message=f"Field '{field}' is required for submission.",
                        details={"missing_field": field},
                    )
        application.status = "SUBMITTED"
        application.submitted_at = timezone.now()
        application.save(update_fields=["status", "submitted_at", "updated_at"])
        logger.info("Application submitted: %s", application.application_number)
        return application

    @staticmethod
    def start_review(application, user):
        ApplicationService._validate_transition(application, "UNDER_REVIEW")
        application.status = "UNDER_REVIEW"
        application.reviewed_by = user
        application.reviewed_at = timezone.now()
        application.save(
            update_fields=[
                "status", "reviewed_by", "reviewed_at", "updated_at",
            ]
        )
        logger.info(
            "Review started: %s by %s",
            application.application_number,
            user.email,
        )
        return application

    @staticmethod
    def request_documents(application, user):
        ApplicationService._validate_transition(
            application, "PENDING_DOCUMENTS"
        )
        application.status = "PENDING_DOCUMENTS"
        application.reviewed_by = user
        application.save(update_fields=["status", "reviewed_by", "updated_at"])
        logger.info(
            "Documents requested: %s by %s",
            application.application_number,
            user.email,
        )
        return application

    @staticmethod
    def send_to_compliance(application, user, notes=""):
        ApplicationService._validate_transition(
            application, "COMPLIANCE_CHECK"
        )
        application.status = "COMPLIANCE_CHECK"
        application.compliance_notes = notes
        application.reviewed_by = user
        application.save(
            update_fields=[
                "status", "compliance_notes",
                "reviewed_by", "updated_at",
            ]
        )
        logger.info(
            "Sent to compliance: %s by %s",
            application.application_number,
            user.email,
        )
        return application

    @staticmethod
    def approve(application, user, notes=""):
        ApplicationService._validate_transition(application, "APPROVED")
        application.status = "APPROVED"
        application.approved_by = user
        application.approved_at = timezone.now()
        application.compliance_notes = notes
        application.save(
            update_fields=[
                "status", "approved_by", "approved_at",
                "compliance_notes", "updated_at",
            ]
        )
        logger.info(
            "Application approved: %s by %s",
            application.application_number,
            user.email,
        )
        return application

    @staticmethod
    def reject(application, user, reason="", notes=""):
        ApplicationService._validate_transition(application, "REJECTED")
        application.status = "REJECTED"
        application.rejection_reason = reason
        application.compliance_notes = notes
        application.approved_by = user
        application.save(
            update_fields=[
                "status", "rejection_reason",
                "compliance_notes", "approved_by", "updated_at",
            ]
        )
        logger.info(
            "Application rejected: %s by %s",
            application.application_number,
            user.email,
        )
        return application

    @staticmethod
    def suspend(application, user, notes=""):
        ApplicationService._validate_transition(application, "SUSPENDED")
        application.status = "SUSPENDED"
        application.compliance_notes = notes
        application.approved_by = user
        application.save(
            update_fields=[
                "status", "compliance_notes",
                "approved_by", "updated_at",
            ]
        )
        logger.info(
            "Application suspended: %s by %s",
            application.application_number,
            user.email,
        )
        return application

    @staticmethod
    def convert_to_partner(application, user):
        ApplicationService._validate_transition(application, "CONVERTED")

        from apps.partners.models import (
            Partner, IndividualProfile, CorporateProfile,
            PartnerTypeAssignment, PartnerDynamicFieldValue,
            PartnerAssignmentContact, PartnerAssignmentBankAccount,
            PartnerDocument, PartnerKYCProfile
        )
        from apps.partner_onboarding.services.compliance_service import ComplianceService

        if Partner.objects.filter(email=application.email).exists():
            raise PartnerConversionError(
                message="A partner with this email already exists.",
                details={"email": application.email},
            )

        with transaction.atomic():
            partner_number = NumberingEngine.generate_partner_number()

            partner = Partner.objects.create(
                partner_number=partner_number,
                partner_type=application.partner_type,
                partner_category=application.partner_type,
                status="ACTIVE",
                identification_type=application.identification_type,
                identification_number=application.identification_number,
                title=application.title,
                first_name=application.first_name,
                other_name=application.other_name,
                surname=application.surname,
                gender=application.gender,
                date_of_birth=application.date_of_birth,
                marital_status=application.marital_status,
                occupation=application.occupation,
                nationality=application.nationality,
                company_name=application.company_name,
                tin_number=application.tin_number,
                incorporation_date=application.incorporation_date,
                industry=application.industry,
                contact_person=application.contact_person,
                contact_person_phone=application.contact_person_phone,
                contact_person_email=application.contact_person_email,
                physical_address=application.physical_address,
                postal_address=application.postal_address,
                email=application.email,
                telephone_number=application.telephone_number,
                mobile_number=application.mobile_number,
                political_risk=application.political_risk,
                aml_risk=application.aml_risk,
                created_from_application=application,
                activated_at=timezone.now(),
            )

            if application.partner_type == "INDIVIDUAL":
                IndividualProfile.objects.create(
                    partner=partner,
                    identification_type=application.identification_type,
                    identification_number=application.identification_number,
                    title=application.title,
                    first_name=application.first_name,
                    other_name=application.other_name,
                    surname=application.surname,
                    gender=application.gender,
                    date_of_birth=application.date_of_birth,
                    marital_status=application.marital_status,
                    occupation=application.occupation,
                    nationality=application.nationality,
                )
            elif application.partner_type == "CORPORATE":
                CorporateProfile.objects.create(
                    partner=partner,
                    company_name=application.company_name,
                    tin_number=application.tin_number,
                    incorporation_date=application.incorporation_date,
                    industry=application.industry,
                    contact_person=application.contact_person,
                    contact_person_phone=application.contact_person_phone,
                    contact_person_email=application.contact_person_email,
                )

            # Migrate ApplicationPartnerTypes to PartnerTypeAssignments
            risk_score = ComplianceService.calculate_risk_score(application)
            kyc_status = "VERIFIED" if application.status in ("APPROVED", "CONVERTED") else "PENDING_REVIEW"

            for app_pt in application.partner_types.all():
                assignment = PartnerTypeAssignment.objects.create(
                    partner=partner,
                    partner_type=app_pt.partner_type,
                    branch=app_pt.branch,
                    location=app_pt.location,
                    share_data_externally=app_pt.share_data_externally,
                    status="ACTIVE",
                    effective_date=timezone.now().date(),
                )

                # Create KYC Profile for this assignment
                PartnerKYCProfile.objects.create(
                    assignment=assignment,
                    kyc_status=kyc_status,
                    risk_score=risk_score,
                    notes=application.compliance_notes,
                )

                # Migrate Dynamic Fields
                for app_field in application.field_values.all():
                    PartnerDynamicFieldValue.objects.create(
                        assignment=assignment,
                        field_config=app_field.field_config,
                        value_json=app_field.value_json,
                    )

                # Migrate Contacts
                for app_contact in application.contacts.all():
                    PartnerAssignmentContact.objects.create(
                        assignment=assignment,
                        contact_type=app_contact.contact_type,
                        first_name=app_contact.first_name,
                        last_name=app_contact.last_name,
                        email=app_contact.email,
                        phone=app_contact.phone,
                        mobile=app_contact.mobile,
                        designation=app_contact.designation,
                        is_primary=app_contact.is_primary,
                        notes=app_contact.notes,
                    )

                # Migrate Bank Accounts
                for app_bank in application.bank_accounts.all():
                    PartnerAssignmentBankAccount.objects.create(
                        assignment=assignment,
                        bank_type="OTHER",  # Fallback if unknown
                        bank_name=app_bank.bank_name,
                        branch_name=app_bank.branch_name,
                        account_name=app_bank.account_name,
                        account_number=app_bank.account_number,
                        swift_code=app_bank.swift_code,
                        currency=app_bank.currency,
                        is_primary=app_bank.is_primary,
                        notes=app_bank.notes,
                    )

                # Migrate Documents
                for app_doc in application.documents.all():
                    PartnerDocument.objects.create(
                        assignment=assignment,
                        file=app_doc.file,
                        uploaded_by=app_doc.uploaded_by,
                        uploaded_at=app_doc.created_at,
                        status="APPROVED" if app_doc.is_verified else "UPLOADED",
                        verification_notes=app_doc.verification_notes,
                    )

            application.status = "CONVERTED"
            application.converted_at = timezone.now()
            application.save(
                update_fields=["status", "converted_at", "updated_at"]
            )

            logger.info(
                "Application %s converted to partner %s",
                application.application_number,
                partner.partner_number,
            )
            return partner
