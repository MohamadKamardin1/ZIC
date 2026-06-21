import logging
from datetime import date

from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from apps.partner_onboarding.exceptions import (
    ApplicationTransitionError,
    ApplicationValidationError,
    PartnerConversionError,
)
from apps.partner_onboarding.models import PartnerApplication

logger = logging.getLogger(__name__)


class ApplicationService:

    STATE_MACHINE = {
        "ACTIVE": ["DRAFT", "SUBMITTED"],
        "DRAFT": ["SUBMITTED"],
        "SUBMITTED": ["UNDER_REVIEW", "DRAFT"],
        "UNDER_REVIEW": ["PENDING_DOCUMENTS", "COMPLIANCE_CHECK", "REJECTED"],
        "PENDING_DOCUMENTS": ["UNDER_REVIEW", "COMPLIANCE_CHECK", "REJECTED"],
        "COMPLIANCE_CHECK": ["APPROVED", "REJECTED", "SUSPENDED"],
        "APPROVED": ["CONVERTED"],
        "SUSPENDED": ["COMPLIANCE_CHECK", "REJECTED"],
        "REJECTED": [],
        "CONVERTED": [],
    }

    @staticmethod
    def _validate_transition(application, target_status):
        allowed = ApplicationService.STATE_MACHINE.get(
            application.status, []
        )
        if target_status not in allowed:
            raise ApplicationTransitionError(
                message=(
                    f"Cannot transition from '{application.status}' "
                    f"to '{target_status}'."
                ),
                details={
                    "current_status": application.status,
                    "requested_status": target_status,
                    "allowed_transitions": allowed,
                },
            )

    @staticmethod
    def generate_application_number(partner_type="INDIVIDUAL"):
        today = date.today()
        year = today.year
        code = "PA" if partner_type == "INDIVIDUAL" else "CO"
        prefix = f"{code}-{year}-"
        last = (
            PartnerApplication.objects
            .filter(application_number__startswith=prefix)
            .aggregate(last_num=Max("application_number"))
        )["last_num"]
        if last:
            try:
                num = int(last.split("-")[-1]) + 1
            except (ValueError, IndexError):
                num = 1
        else:
            num = 1
        return f"{prefix}{num:06d}"

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
            required = [
                "identification_type", "identification_number",
                "first_name", "surname", "email",
                "mobile_number", "date_of_birth",
                "nationality", "gender",
            ]
            for field in required:
                if not getattr(application, field, None):
                    raise ApplicationValidationError(
                        message=f"Field '{field}' is required for submission.",
                        details={"missing_field": field},
                    )
        elif partner_type == "CORPORATE":
            required = [
                "company_name", "tin_number", "incorporation_date",
                "industry", "email", "mobile_number",
                "contact_person", "contact_person_phone",
                "contact_person_email", "physical_address",
            ]
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

        from apps.partners.models import Partner

        if Partner.objects.filter(email=application.email).exists():
            raise PartnerConversionError(
                message="A partner with this email already exists.",
                details={"email": application.email},
            )

        with transaction.atomic():
            today = date.today()
            year = today.year
            prefix = f"PN-{year}-"
            last = (
                Partner.objects
                .filter(partner_number__startswith=prefix)
                .aggregate(last_num=Max("partner_number"))
            )["last_num"]
            if last:
                try:
                    num = int(last.split("-")[-1]) + 1
                except (ValueError, IndexError):
                    num = 1
            else:
                num = 1
            partner_number = f"{prefix}{num:06d}"

            partner = Partner.objects.create(
                partner_number=partner_number,
                partner_type=application.partner_type,
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
