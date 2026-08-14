import logging
from datetime import date

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.governance.services.audit_service import AuditService
from apps.partner_onboarding.exceptions import (
    ApplicationTransitionError,
    ApplicationValidationError,
    PartnerConversionError,
)
from apps.partner_onboarding.models import (
    PartnerApplication,
    PartnerApplicationEvent,
    PartnerApplicationTask,
)
from apps.partner_onboarding.services.compliance_service import ComplianceService
from apps.system_parameters.services.config_service import (
    ConfigurationError,
    ConfigurationService,
)
from apps.system_parameters.services.numbering_service import NumberingEngine
from apps.system_parameters.services.validation_config_service import (
    ValidationConfigService,
)
from apps.system_parameters.services.workflow_service import WorkflowEngine

logger = logging.getLogger(__name__)


class ApplicationService:
    """Application workflow orchestration.

    All state changes go through this service so that transition validation,
    authorization at the view layer, audit history, timestamps, and side
    effects remain consistent across API clients.
    """

    @staticmethod
    def _validate_transition(application, target_status):
        try:
            WorkflowEngine.validate_transition(application.status, target_status)
        except ConfigurationError as exc:
            raise ApplicationTransitionError(
                message=str(exc),
                details={
                    "current_status": application.status,
                    "requested_status": target_status,
                    "allowed_transitions": WorkflowEngine.get_allowed_transitions(
                        application.status
                    ),
                },
            ) from exc

    @staticmethod
    def generate_application_number(partner_type="INDIVIDUAL"):
        return NumberingEngine.generate_application_number(partner_type)

    @staticmethod
    def _actor(user):
        return user if user and not getattr(user, "is_anonymous", False) else None

    @staticmethod
    def _event_type(target_status, source="status"):
        return {
            "SUBMITTED": "SUBMITTED",
            "UNDER_REVIEW": "REVIEW_STARTED",
            "PENDING_DOCUMENTS": "DOCUMENTS_REQUESTED",
            "COMPLIANCE_CHECK": "SENT_TO_COMPLIANCE",
            "APPROVED": "APPROVED",
            "REJECTED": "REJECTED",
            "SUSPENDED": "SUSPENDED",
            "CONVERTED": "CONVERTED",
        }.get(target_status, "UPDATED" if source == "status" else source)

    @staticmethod
    def _snapshot(application):
        return {
            "id": str(application.pk),
            "application_number": application.application_number,
            "status": application.status,
            "partner_type": application.partner_type,
            "email": application.email,
            "display_name": application.display_name,
            "submitted_at": application.submitted_at.isoformat()
            if application.submitted_at
            else None,
            "reviewed_at": application.reviewed_at.isoformat()
            if application.reviewed_at
            else None,
            "approved_at": application.approved_at.isoformat()
            if application.approved_at
            else None,
            "converted_at": application.converted_at.isoformat()
            if application.converted_at
            else None,
        }

    @staticmethod
    def _record_event(
        application,
        event_type,
        actor=None,
        from_status="",
        to_status="",
        notes="",
        metadata=None,
        before_state=None,
        after_state=None,
    ):
        event = PartnerApplicationEvent.objects.create(
            application=application,
            event_type=event_type,
            from_status=from_status or "",
            to_status=to_status or "",
            actor=ApplicationService._actor(actor),
            notes=notes or "",
            metadata=metadata or {},
        )
        # Governance audit is intentionally written in the same transaction as
        # the state change. This makes the history complete and queryable by
        # administrators without a second asynchronous dependency.
        AuditService.log(
            action_type={
                "SUBMITTED": "SUBMIT",
                "REVIEW_STARTED": "UPDATE",
                "DOCUMENTS_REQUESTED": "UPDATE",
                "SENT_TO_COMPLIANCE": "UPDATE",
                "APPROVED": "APPROVE",
                "REJECTED": "REJECT",
                "SUSPENDED": "DEACTIVATE",
                "CONVERTED": "ACTIVATE",
                "CREATED": "CREATE",
                "UPDATED": "UPDATE",
            }.get(event_type, "UPDATE"),
            entity_type="PartnerApplication",
            entity_id=application.pk,
            entity_repr=application.application_number,
            before_state=before_state,
            after_state=after_state,
            description=notes or event_type.replace("_", " ").title(),
            user=actor,
        )
        return event

    @staticmethod
    def _required_scalar_fields(application):
        if application.partner_type == "INDIVIDUAL":
            return ValidationConfigService.get_individual_required_fields()
        return ValidationConfigService.get_corporate_required_fields()

    @staticmethod
    def _required_nested_data(application):
        missing = {}
        assignments = list(
            application.partner_types.select_related("partner_type").all()
        )
        if not assignments:
            missing["partner_types"] = "At least one active partner type is required."
            return missing

        required_doc_codes = set()
        required_contacts = set()
        required_banks = set()
        required_fields = []
        for assignment in assignments:
            partner_type = assignment.partner_type
            required_doc_codes.update(
                partner_type.document_requirements.filter(
                    is_active=True, is_required=True
                ).values_list("code", flat=True)
            )
            required_contacts.update(
                partner_type.contact_requirements.filter(
                    is_active=True, is_required=True
                ).values_list("contact_type", flat=True)
            )
            required_banks.update(
                partner_type.bank_requirements.filter(
                    is_active=True, is_required=True
                ).values_list("bank_type", flat=True)
            )
            required_fields.extend(
                partner_type.field_configurations.filter(
                    is_active=True, is_required=True
                ).values_list("field_code", flat=True)
            )

        document_codes = set(
            application.documents.values_list("document_type", flat=True)
        )
        missing_docs = sorted(required_doc_codes - document_codes)
        if missing_docs:
            missing["documents"] = missing_docs

        verified_codes = set(
            application.documents.filter(is_verified=True).values_list(
                "document_type", flat=True
            )
        )
        unverified_required = sorted(required_doc_codes - verified_codes)
        if unverified_required:
            missing["verified_documents"] = unverified_required

        contact_types = set(
            application.contacts.values_list("contact_type", flat=True)
        )
        missing_contacts = sorted(required_contacts - contact_types)
        if missing_contacts:
            missing["contacts"] = missing_contacts

        bank_types = set(
            application.bank_accounts.values_list("currency", flat=True)
        )
        # Bank requirements use a configurable bank_type while the legacy
        # onboarding account has no bank_type column. Any bank account satisfies
        # the requirement until the dedicated bank_type field is introduced.
        if required_banks and not bank_types and not application.bank_accounts.exists():
            missing["bank_accounts"] = sorted(required_banks)

        present_fields = set(
            application.field_values.values_list(
                "field_config__field_code", flat=True
            )
        )
        missing_fields = sorted(set(required_fields) - present_fields)
        if missing_fields:
            missing["dynamic_fields"] = missing_fields

        return missing

    @staticmethod
    def validate_for_submission(application):
        errors = {}
        for field in ApplicationService._required_scalar_fields(application):
            value = getattr(application, field, None)
            if value is None or value == "":
                errors[field] = f"Field '{field}' is required for submission."

        # Common consistency checks are enforced at the service boundary even
        # when an application was created by an import or an older client.
        if application.partner_type == "INDIVIDUAL" and application.company_name:
            errors["company_name"] = "Individual applications cannot contain company data."
        if application.partner_type == "CORPORATE" and not application.company_name:
            errors["company_name"] = "Company name is required for corporate applications."
        if application.date_of_birth and application.date_of_birth > date.today():
            errors["date_of_birth"] = "Date of birth cannot be in the future."

        errors.update(ApplicationService._required_nested_data(application))
        if errors:
            raise ApplicationValidationError(
                message="Application is incomplete and cannot be submitted.",
                details=errors,
            )
        return True

    @staticmethod
    def deduplicate_drafts(email):
        """Return the newest draft without deleting user data.

        Previous behavior deleted older drafts, which made auditability and
        recovery impossible. Callers may explicitly abandon duplicates instead.
        """
        if not email:
            return None
        return (
            PartnerApplication.objects.filter(email=email, status="DRAFT")
            .order_by("-created_at")
            .first()
        )

    @staticmethod
    @transaction.atomic
    def create_draft(user, data):
        payload = dict(data)
        payload.pop("application_number", None)
        payload.pop("submitted_by", None)
        payload["application_number"] = ApplicationService.generate_application_number(
            payload.get("partner_type", "INDIVIDUAL")
        )
        payload["submitted_by"] = user
        payload["status"] = "ACTIVE"
        try:
            application = PartnerApplication.objects.create(**payload)
        except IntegrityError as exc:
            raise ApplicationValidationError(
                message="An application with these unique details already exists.",
                details={"email": payload.get("email")},
            ) from exc
        ApplicationService._record_event(
            application,
            "CREATED",
            actor=user,
            to_status="ACTIVE",
            notes="Onboarding application draft created.",
            after_state=ApplicationService._snapshot(application),
        )
        logger.info("Draft application created: %s", application.application_number)
        return application

    @staticmethod
    @transaction.atomic
    def update_draft(application, user, validated_data):
        locked = PartnerApplication.objects.select_for_update().get(pk=application.pk)
        if locked.status not in ("DRAFT", "ACTIVE"):
            raise ApplicationValidationError(
                message="Only draft applications can be updated.",
                details={"status": locked.status},
            )
        before = ApplicationService._snapshot(locked)
        for field, value in validated_data.items():
            setattr(locked, field, value)
        locked.status = "ACTIVE"
        locked.save()
        ApplicationService._record_event(
            locked,
            "UPDATED",
            actor=user,
            from_status=before["status"],
            to_status=locked.status,
            notes="Onboarding application draft updated.",
            before_state=before,
            after_state=ApplicationService._snapshot(locked),
        )
        return locked

    @staticmethod
    def _transition(application, target_status, user, *, notes="", update=None, metadata=None):
        with transaction.atomic():
            locked = PartnerApplication.objects.select_for_update().get(pk=application.pk)
            ApplicationService._validate_transition(locked, target_status)
            before = ApplicationService._snapshot(locked)
            for field, value in (update or {}).items():
                setattr(locked, field, value)
            locked.status = target_status
            locked.save()
            event_type = ApplicationService._event_type(target_status)
            ApplicationService._record_event(
                locked,
                event_type,
                actor=user,
                from_status=before["status"],
                to_status=target_status,
                notes=notes,
                metadata=metadata,
                before_state=before,
                after_state=ApplicationService._snapshot(locked),
            )
            return locked

    @staticmethod
    def submit(application, user):
        if application.status not in ("DRAFT", "ACTIVE"):
            raise ApplicationTransitionError(
                message="Only draft applications can be submitted.",
                details={"status": application.status, "allowed_statuses": ["DRAFT", "ACTIVE"]},
            )
        ApplicationService.validate_for_submission(application)
        return ApplicationService._transition(
            application,
            "SUBMITTED",
            user,
            notes="Application submitted for review.",
            update={"submitted_at": timezone.now()},
        )

    @staticmethod
    def start_review(application, user, notes=""):
        return ApplicationService._transition(
            application,
            "UNDER_REVIEW",
            user,
            notes=notes or "Application review started.",
            update={"reviewed_by": user, "reviewed_at": timezone.now()},
        )

    @staticmethod
    def request_documents(application, user, requested_documents=None, notes=""):
        requested_documents = requested_documents or []
        locked = ApplicationService._transition(
            application,
            "PENDING_DOCUMENTS",
            user,
            notes=notes or "Additional documents requested.",
            update={"reviewed_by": user},
            metadata={"requested_documents": requested_documents},
        )
        requested_documents = [str(item).strip() for item in requested_documents if str(item).strip()]
        if not requested_documents:
            requested_documents = ["Additional onboarding documents"]
        for document_name in requested_documents:
            task_title = f"Provide onboarding document: {document_name}"
            if PartnerApplicationTask.objects.filter(
                application=locked,
                task_type="DOCUMENT_REQUEST",
                title=task_title,
                status__in=("PENDING", "IN_PROGRESS"),
            ).exists():
                continue
            PartnerApplicationTask.objects.create(
                application=locked,
                task_type="DOCUMENT_REQUEST",
                title=task_title,
                description=notes or f"Upload and provide the requested document: {document_name}.",
                priority="HIGH",
            )
            ApplicationService._record_event(
                locked,
                "TASK_CREATED",
                actor=user,
                to_status=locked.status,
                notes=task_title,
                metadata={"requested_document": document_name},
            )
        return locked

    @staticmethod
    def send_to_compliance(application, user, notes=""):
        # Compliance is only meaningful once a reviewer has verified the
        # evidence package. This prevents premature approval decisions.
        missing = ApplicationService._required_nested_data(application)
        if missing.get("verified_documents"):
            raise ApplicationValidationError(
                message="All required documents must be verified before compliance review.",
                details=missing,
            )
        return ApplicationService._transition(
            application,
            "COMPLIANCE_CHECK",
            user,
            notes=notes or "Application sent for compliance review.",
            update={"compliance_notes": notes, "reviewed_by": user},
        )

    @staticmethod
    def approve(application, user, notes=""):
        result = ComplianceService.flag_high_risk(application)
        compliance_note = notes.strip()
        if result["is_high_risk"] and not compliance_note:
            raise ApplicationValidationError(
                message="A compliance decision note is required for high-risk applications.",
                details={"risk_score": result["risk_score"], "threshold": result["threshold"]},
            )
        return ApplicationService._transition(
            application,
            "APPROVED",
            user,
            notes=compliance_note or "Application approved.",
            update={
                "approved_by": user,
                "approved_at": timezone.now(),
                "compliance_notes": compliance_note or application.compliance_notes,
            },
            metadata=result,
        )

    @staticmethod
    def reject(application, user, reason="", notes=""):
        reason = (reason or "").strip()
        if not reason:
            raise ApplicationValidationError(
                message="A rejection reason is required.",
                details={"rejection_reason": "This field is required."},
            )
        return ApplicationService._transition(
            application,
            "REJECTED",
            user,
            notes=notes or reason,
            update={
                "rejection_reason": reason,
                "compliance_notes": notes,
                "approved_by": user,
            },
        )

    @staticmethod
    def suspend(application, user, notes=""):
        return ApplicationService._transition(
            application,
            "SUSPENDED",
            user,
            notes=notes or "Application suspended.",
            update={"compliance_notes": notes, "approved_by": user},
        )

    @staticmethod
    def resume(application, user, notes=""):
        return ApplicationService._transition(
            application,
            "COMPLIANCE_CHECK",
            user,
            notes=notes or "Suspended application resumed for compliance review.",
            update={"reviewed_by": user},
        )

    @staticmethod
    def _check_conversion_duplicates(application):
        from apps.partners.models import Partner

        if Partner.objects.filter(email__iexact=application.email).exists():
            return {"email": application.email}
        if application.identification_number and Partner.objects.filter(
            identification_type=application.identification_type,
            identification_number=application.identification_number,
        ).exists():
            return {
                "identification_type": application.identification_type,
                "identification_number": application.identification_number,
            }
        if application.tin_number and Partner.objects.filter(
            tin_number=application.tin_number
        ).exists():
            return {"tin_number": application.tin_number}
        return None

    @staticmethod
    @transaction.atomic
    def convert_to_partner(application, user):
        locked = PartnerApplication.objects.select_for_update().get(pk=application.pk)
        ApplicationService._validate_transition(locked, "CONVERTED")
        ApplicationService.validate_for_submission(locked)
        if locked.converted_at:
            from apps.partners.models import Partner
            return Partner.objects.get(created_from_application=locked)

        duplicate = ApplicationService._check_conversion_duplicates(locked)
        if duplicate:
            raise PartnerConversionError(
                message="A partner already exists with matching identity details.",
                details=duplicate,
            )

        from apps.partners.models import (
            CorporateProfile,
            IndividualProfile,
            Partner,
            PartnerAssignmentBankAccount,
            PartnerAssignmentContact,
            PartnerDocument,
            PartnerDynamicFieldValue,
            PartnerKYCProfile,
            PartnerTypeAssignment,
        )

        try:
            partner = Partner.objects.create(
                partner_number=NumberingEngine.generate_partner_number(),
                partner_type=locked.partner_type,
                partner_category=locked.partner_type,
                status="ACTIVE",
                identification_type=locked.identification_type,
                identification_number=locked.identification_number,
                title=locked.title,
                first_name=locked.first_name,
                other_name=locked.other_name,
                surname=locked.surname,
                gender=locked.gender,
                date_of_birth=locked.date_of_birth,
                marital_status=locked.marital_status,
                occupation=locked.occupation,
                nationality=locked.nationality,
                company_name=locked.company_name,
                tin_number=locked.tin_number,
                incorporation_date=locked.incorporation_date,
                industry=locked.industry,
                contact_person=locked.contact_person,
                contact_person_phone=locked.contact_person_phone,
                contact_person_email=locked.contact_person_email,
                physical_address=locked.physical_address,
                postal_address=locked.postal_address,
                email=locked.email,
                telephone_number=locked.telephone_number,
                mobile_number=locked.mobile_number,
                political_risk=locked.political_risk,
                aml_risk=locked.aml_risk,
                created_from_application=locked,
                activated_at=timezone.now(),
            )
            if locked.partner_type == "INDIVIDUAL":
                IndividualProfile.objects.create(
                    partner=partner,
                    identification_type=locked.identification_type,
                    identification_number=locked.identification_number,
                    title=locked.title,
                    first_name=locked.first_name,
                    other_name=locked.other_name,
                    surname=locked.surname,
                    gender=locked.gender,
                    date_of_birth=locked.date_of_birth,
                    marital_status=locked.marital_status,
                    occupation=locked.occupation,
                    nationality=locked.nationality,
                )
            else:
                CorporateProfile.objects.create(
                    partner=partner,
                    company_name=locked.company_name,
                    tin_number=locked.tin_number,
                    incorporation_date=locked.incorporation_date,
                    industry=locked.industry,
                    contact_person=locked.contact_person,
                    contact_person_phone=locked.contact_person_phone,
                    contact_person_email=locked.contact_person_email,
                )

            risk = ComplianceService.calculate_risk_score(locked)
            for app_assignment in locked.partner_types.select_related("partner_type").all():
                assignment = PartnerTypeAssignment.objects.create(
                    partner=partner,
                    partner_type=app_assignment.partner_type,
                    branch=app_assignment.branch,
                    location=app_assignment.location,
                    share_data_externally=app_assignment.share_data_externally,
                    status="ACTIVE",
                    effective_date=timezone.now().date(),
                )
                PartnerKYCProfile.objects.create(
                    assignment=assignment,
                    kyc_status="VERIFIED",
                    risk_score=risk,
                    risk_level=("HIGH" if risk >= 70 else "MEDIUM" if risk >= 40 else "LOW"),
                    last_review_date=timezone.now(),
                    reviewed_by=user,
                    notes=locked.compliance_notes,
                )

                for value in locked.field_values.filter(
                    application_partner_type__isnull=True
                ) | locked.field_values.filter(
                    application_partner_type=app_assignment
                ):
                    PartnerDynamicFieldValue.objects.update_or_create(
                        assignment=assignment,
                        field_config=value.field_config,
                        defaults={"value_json": value.value_json},
                    )
                for contact in locked.contacts.filter(
                    application_partner_type__isnull=True
                ) | locked.contacts.filter(
                    application_partner_type=app_assignment
                ):
                    PartnerAssignmentContact.objects.create(
                        assignment=assignment,
                        contact_type=contact.contact_type,
                        first_name=contact.first_name,
                        last_name=contact.last_name,
                        email=contact.email,
                        phone=contact.phone,
                        mobile=contact.mobile,
                        designation=contact.designation,
                        is_primary=contact.is_primary,
                        notes=contact.notes,
                    )
                for bank in locked.bank_accounts.filter(
                    application_partner_type__isnull=True
                ) | locked.bank_accounts.filter(
                    application_partner_type=app_assignment
                ):
                    PartnerAssignmentBankAccount.objects.create(
                        assignment=assignment,
                        bank_type="OTHER",
                        bank_name=bank.bank_name,
                        branch_name=bank.branch_name,
                        account_name=bank.account_name,
                        account_number=bank.account_number,
                        swift_code=bank.swift_code,
                        currency=bank.currency,
                        is_primary=bank.is_primary,
                        notes=bank.notes,
                    )
                for document in locked.documents.filter(
                    application_partner_type__isnull=True
                ) | locked.documents.filter(
                    application_partner_type=app_assignment
                ):
                    PartnerDocument.objects.create(
                        assignment=assignment,
                        document_requirement=app_assignment.partner_type.document_requirements.filter(
                            code=document.document_type,
                            is_active=True,
                        ).first(),
                        file=document.file,
                        uploaded_by=document.uploaded_by,
                        uploaded_at=document.created_at,
                        status="APPROVED" if document.is_verified else "UPLOADED",
                        verification_notes=document.verification_notes,
                    )

            before = ApplicationService._snapshot(locked)
            locked.status = "CONVERTED"
            locked.converted_at = timezone.now()
            locked.save(update_fields=["status", "converted_at", "updated_at"])
            ApplicationService._record_event(
                locked,
                "CONVERTED",
                actor=user,
                from_status=before["status"],
                to_status="CONVERTED",
                notes=f"Application converted to partner {partner.partner_number}.",
                metadata={"partner_id": str(partner.pk), "partner_number": partner.partner_number},
                before_state=before,
                after_state=ApplicationService._snapshot(locked),
            )
            return partner
        except IntegrityError as exc:
            raise PartnerConversionError(
                message="Partner conversion could not be completed because of a data conflict.",
                details={"application": locked.application_number},
            ) from exc
