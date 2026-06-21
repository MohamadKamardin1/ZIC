import logging
from datetime import date

from rest_framework import serializers

from apps.partner_onboarding.models import (
    PartnerApplication,
    PartnerApplicationDocument,
    PartnerApplicationTask,
    APPLICATION_STATUS_CHOICES,
    DOCUMENT_TYPE_CHOICES,
    TASK_TYPE_CHOICES,
    TASK_STATUS_CHOICES,
    TASK_PRIORITY_CHOICES,
)
from apps.partners.models import (
    IDENTIFICATION_TYPE_CHOICES,
    TITLE_CHOICES,
    GENDER_CHOICES,
    MARITAL_STATUS_CHOICES,
    POLITICAL_RISK_CHOICES,
    AML_RISK_CHOICES,
    INDUSTRY_CHOICES,
    NATIONALITY_CHOICES,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Document Serializers
# ---------------------------------------------------------------------------

class PartnerApplicationDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = PartnerApplicationDocument
        fields = [
            "id", "application", "document_type", "document_name",
            "file", "file_size", "mime_type", "is_verified",
            "verified_by", "verified_at", "verification_notes",
            "uploaded_by", "created_at",
        ]
        read_only_fields = [
            "id", "file_size", "mime_type", "is_verified",
            "verified_by", "verified_at", "uploaded_by", "created_at",
        ]


class PartnerApplicationDocumentUploadSerializer(serializers.ModelSerializer):
    ALLOWED_MIME_TYPES = [
        "application/pdf",
        "image/jpeg",
        "image/png",
        "image/jpg",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ]
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

    class Meta:
        model = PartnerApplicationDocument
        fields = ["id", "document_type", "document_name", "file"]

    def validate_file(self, value):
        if value.size > self.MAX_FILE_SIZE:
            raise serializers.ValidationError(
                "File size must not exceed 10 MB."
            )
        if value.content_type not in self.ALLOWED_MIME_TYPES:
            raise serializers.ValidationError(
                f"File type '{value.content_type}' is not allowed. "
                f"Accepted types: PDF, JPEG, PNG, DOC, DOCX."
            )
        return value


# ---------------------------------------------------------------------------
# Task Serializer
# ---------------------------------------------------------------------------

class PartnerApplicationTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = PartnerApplicationTask
        fields = [
            "id", "application", "task_type", "title", "description",
            "assigned_to", "status", "priority", "due_date",
            "completed_at", "completed_by", "notes",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "application", "completed_at", "completed_by",
            "created_at", "updated_at",
        ]

    def validate_due_date(self, value):
        if value and value < date.today():
            raise serializers.ValidationError(
                "Due date must be today or in the future."
            )
        return value


# ---------------------------------------------------------------------------
# Application List Serializer (read-only, flat)
# ---------------------------------------------------------------------------

class PartnerApplicationListSerializer(serializers.ModelSerializer):
    display_name = serializers.ReadOnlyField()
    created_by_name = serializers.SerializerMethodField()
    updated_by_name = serializers.SerializerMethodField()

    class Meta:
        model = PartnerApplication
        fields = [
            "id", "application_number", "partner_type", "display_name",
            "title", "surname", "mobile_number", "nationality",
            "identification_type", "email", "status", "political_risk", "aml_risk",
            "submitted_at", "created_at", "updated_at",
            "created_by_name", "updated_by_name",
        ]
        read_only_fields = fields

    def get_created_by_name(self, obj):
        if obj.submitted_by:
            first = getattr(obj.submitted_by, "first_name", "") or ""
            last = getattr(obj.submitted_by, "last_name", "") or ""
            full = f"{first} {last}".strip()
            return full or obj.submitted_by.username
        return None

    def get_updated_by_name(self, obj):
        user = obj.approved_by or obj.reviewed_by
        if user:
            first = getattr(user, "first_name", "") or ""
            last = getattr(user, "last_name", "") or ""
            full = f"{first} {last}".strip()
            return full or user.username
        return None


# ---------------------------------------------------------------------------
# Application Detail Serializer (read-only, nested)
# ---------------------------------------------------------------------------

class PartnerApplicationDetailSerializer(serializers.ModelSerializer):
    display_name = serializers.ReadOnlyField()
    documents = PartnerApplicationDocumentSerializer(many=True, read_only=True)
    tasks = PartnerApplicationTaskSerializer(many=True, read_only=True)

    class Meta:
        model = PartnerApplication
        fields = [
            "id", "application_number", "partner_type", "status",
            "display_name",
            # Individual
            "identification_type", "identification_number",
            "title", "first_name", "other_name", "surname",
            "gender", "date_of_birth", "marital_status",
            "occupation", "nationality",
            # Corporate
            "company_name", "tin_number", "incorporation_date",
            "industry", "contact_person", "contact_person_phone",
            "contact_person_email", "physical_address", "postal_address",
            # Common
            "email", "telephone_number", "mobile_number",
            "political_risk", "aml_risk",
            # Audit
            "submitted_by", "reviewed_by", "approved_by",
            "rejection_reason", "compliance_notes",
            "submitted_at", "reviewed_at", "approved_at", "converted_at",
            "created_at", "updated_at",
            # Nested
            "documents", "tasks",
        ]
        read_only_fields = fields


# ---------------------------------------------------------------------------
# Application Create Serializer (write — partner-type routing + validation)
# ---------------------------------------------------------------------------

INDIVIDUAL_REQUIRED_FIELDS = [
    "identification_type", "identification_number",
    "first_name", "surname", "email", "mobile_number",
    "date_of_birth", "nationality", "gender",
]

CORPORATE_REQUIRED_FIELDS = [
    "company_name", "tin_number", "incorporation_date",
    "industry", "email", "mobile_number",
    "contact_person", "contact_person_phone",
    "contact_person_email", "physical_address",
]


class PartnerApplicationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PartnerApplication
        fields = [
            "id", "partner_type",
            # Individual
            "identification_type", "identification_number",
            "title", "first_name", "other_name", "surname",
            "gender", "date_of_birth", "marital_status",
            "occupation", "nationality",
            # Corporate
            "company_name", "tin_number", "incorporation_date",
            "industry", "contact_person", "contact_person_phone",
            "contact_person_email", "physical_address", "postal_address",
            # Common
            "email", "telephone_number", "mobile_number",
            "political_risk", "aml_risk",
        ]

    def validate_email(self, value):
        from apps.partners.models import Partner
        if Partner.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                "A partner with this email already exists."
            )
        qs = PartnerApplication.objects.filter(email=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.filter(
            status__in=[
                "SUBMITTED", "UNDER_REVIEW",
                "COMPLIANCE_CHECK", "APPROVED",
            ]
        ).exists():
            raise serializers.ValidationError(
                "An active application with this email already exists."
            )
        return value

    def validate(self, attrs):
        partner_type = attrs.get("partner_type")
        if self.partial:
            partner_type = partner_type or getattr(self.instance, "partner_type", None)
        if not partner_type:
            raise serializers.ValidationError(
                {"partner_type": "partner_type is required."}
            )
        dob = attrs.get("date_of_birth")
        if dob:
            today = date.today()
            try:
                eighteenth_birthday = dob.replace(year=dob.year + 18)
            except ValueError:
                eighteenth_birthday = dob.replace(year=dob.year + 18, day=28)
            if today < eighteenth_birthday:
                raise serializers.ValidationError(
                    {"date_of_birth": "Partner must be 18 years or older."}
                )
        return attrs


# ---------------------------------------------------------------------------
# Application Update Serializer (DRAFT-only)
# ---------------------------------------------------------------------------

class PartnerApplicationUpdateSerializer(PartnerApplicationCreateSerializer):

    class Meta(PartnerApplicationCreateSerializer.Meta):
        pass

    def validate(self, attrs):
        instance = self.instance
        if instance and instance.status not in ("DRAFT", "ACTIVE"):
            raise serializers.ValidationError(
                "Only DRAFT or ACTIVE applications can be updated."
            )
        return super().validate(attrs)


# ---------------------------------------------------------------------------
# Application Submit Serializer (DRAFT → SUBMITTED validation)
# ---------------------------------------------------------------------------

class PartnerApplicationSubmitSerializer(serializers.Serializer):
    def validate(self, attrs):
        application = self.instance
        if application.status not in ("DRAFT", "ACTIVE"):
            raise serializers.ValidationError(
                "Only DRAFT or ACTIVE applications can be submitted."
            )
        partner_type = application.partner_type
        if partner_type == "INDIVIDUAL":
            for field in INDIVIDUAL_REQUIRED_FIELDS:
                if not getattr(application, field, None):
                    raise serializers.ValidationError(
                        {field: f"{field} is required before submission."}
                    )
        elif partner_type == "CORPORATE":
            for field in CORPORATE_REQUIRED_FIELDS:
                if not getattr(application, field, None):
                    raise serializers.ValidationError(
                        {field: f"{field} is required before submission."}
                    )
        return attrs


# ---------------------------------------------------------------------------
# Application Review Serializer (reviewer actions)
# ---------------------------------------------------------------------------

class PartnerApplicationReviewSerializer(serializers.Serializer):
    notes = serializers.CharField(required=False, allow_blank=True)
    requested_documents = serializers.ListField(
        child=serializers.CharField(),
        required=False,
    )

    def validate(self, attrs):
        application = self.instance
        if application.status not in ("SUBMITTED", "UNDER_REVIEW", "PENDING_DOCUMENTS"):
            raise serializers.ValidationError(
                f"Cannot review application in '{application.status}' status."
            )
        return attrs


# ---------------------------------------------------------------------------
# Application Compliance Serializer (approve / reject / suspend)
# ---------------------------------------------------------------------------

class PartnerApplicationComplianceSerializer(serializers.Serializer):
    notes = serializers.CharField(required=False, allow_blank=True)
    rejection_reason = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        application = self.instance
        # Allow rejection from review stages, compliance actions from COMPLIANCE_CHECK,
        # and resume from SUSPENDED
        allowed_statuses = ("UNDER_REVIEW", "PENDING_DOCUMENTS", "COMPLIANCE_CHECK", "SUSPENDED")
        if application.status not in allowed_statuses:
            raise serializers.ValidationError(
                f"Cannot perform compliance action on application "
                f"in '{application.status}' status."
            )
        return attrs


# ---------------------------------------------------------------------------
# Partner Convert Serializer (APPROVED → partner record)
# ---------------------------------------------------------------------------

class PartnerConvertSerializer(serializers.Serializer):
    def validate(self, attrs):
        application = self.instance
        if application.status != "APPROVED":
            raise serializers.ValidationError(
                "Only APPROVED applications can be converted to partners."
            )
        from apps.partners.models import Partner
        if Partner.objects.filter(email=application.email).exists():
            raise serializers.ValidationError(
                "A partner with this email already exists."
            )
        return attrs


# ---------------------------------------------------------------------------
# Choices Serializer (all dropdowns for the frontend)
# ---------------------------------------------------------------------------

class ChoicesSerializer(serializers.Serializer):
    partner_types = serializers.SerializerMethodField()
    identification_types = serializers.SerializerMethodField()
    titles = serializers.SerializerMethodField()
    genders = serializers.SerializerMethodField()
    marital_statuses = serializers.SerializerMethodField()
    political_risks = serializers.SerializerMethodField()
    aml_risks = serializers.SerializerMethodField()
    industries = serializers.SerializerMethodField()
    nationalities = serializers.SerializerMethodField()
    application_statuses = serializers.SerializerMethodField()
    document_types = serializers.SerializerMethodField()
    task_types = serializers.SerializerMethodField()
    task_statuses = serializers.SerializerMethodField()
    task_priorities = serializers.SerializerMethodField()

    def _format(self, choices):
        return [{"value": c[0], "label": c[1]} for c in choices]

    def get_partner_types(self, obj):
        from apps.partners.models import PARTNER_TYPE_CHOICES
        return self._format(PARTNER_TYPE_CHOICES)

    def get_identification_types(self, obj):
        return self._format(IDENTIFICATION_TYPE_CHOICES)

    def get_titles(self, obj):
        return self._format(TITLE_CHOICES)

    def get_genders(self, obj):
        return self._format(GENDER_CHOICES)

    def get_marital_statuses(self, obj):
        return self._format(MARITAL_STATUS_CHOICES)

    def get_political_risks(self, obj):
        return self._format(POLITICAL_RISK_CHOICES)

    def get_aml_risks(self, obj):
        return self._format(AML_RISK_CHOICES)

    def get_industries(self, obj):
        return self._format(INDUSTRY_CHOICES)

    def get_nationalities(self, obj):
        return self._format(NATIONALITY_CHOICES)

    def get_application_statuses(self, obj):
        return self._format(APPLICATION_STATUS_CHOICES)

    def get_document_types(self, obj):
        return self._format(DOCUMENT_TYPE_CHOICES)

    def get_task_types(self, obj):
        return self._format(TASK_TYPE_CHOICES)

    def get_task_statuses(self, obj):
        return self._format(TASK_STATUS_CHOICES)

    def get_task_priorities(self, obj):
        return self._format(TASK_PRIORITY_CHOICES)
