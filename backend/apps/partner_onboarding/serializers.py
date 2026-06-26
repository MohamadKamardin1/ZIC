import logging
from datetime import date

from rest_framework import serializers

from apps.partner_onboarding.models import (
    PartnerApplication,
    PartnerApplicationDocument,
    PartnerApplicationTask,
    ApplicationPartnerType,
    ApplicationContact,
    ApplicationBankAccount,
    ApplicationFieldValue,
    Branch,
    Location,
)
from apps.system_parameters.services.config_service import ConfigurationService, ConfigurationError
from apps.system_parameters.services.validation_config_service import ValidationConfigService

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Branch / Location / Application Partner Type / Contact / Bank Serializers
# ---------------------------------------------------------------------------


class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = ["id", "code", "name", "is_active"]


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ["id", "branch_id", "code", "name", "is_active"]


class ApplicationPartnerTypeSerializer(serializers.ModelSerializer):
    partner_type_name = serializers.ReadOnlyField(source="partner_type.name")
    branch_name = serializers.ReadOnlyField(source="branch.name")
    location_name = serializers.ReadOnlyField(source="location.name")

    class Meta:
        model = ApplicationPartnerType
        fields = [
            "id", "application", "partner_type", "partner_type_name",
            "branch", "branch_name", "location", "location_name",
            "share_data_externally", "created_at",
        ]


class ApplicationPartnerTypeCreateSerializer(serializers.Serializer):
    partner_type = serializers.UUIDField()
    branches = serializers.ListField(child=serializers.UUIDField(), required=False, default=list)
    location = serializers.UUIDField(required=False, allow_null=True, default=None)
    share_data_externally = serializers.BooleanField(default=False)

    def validate_partner_type(self, value):
        from apps.partners.models import PartnerType
        try:
            return PartnerType.objects.get(id=value, is_active=True)
        except PartnerType.DoesNotExist:
            raise serializers.ValidationError("Invalid or inactive partner type.")

    def validate_branches(self, value):
        if not value:
            return []
        existing = Branch.objects.filter(id__in=value, is_active=True)
        if len(existing) != len(value):
            raise serializers.ValidationError("One or more branches are invalid.")
        return list(existing)

    def validate_location(self, value):
        if not value:
            return None
        try:
            return Location.objects.get(id=value, is_active=True)
        except Location.DoesNotExist:
            raise serializers.ValidationError("Invalid location.")

    def create(self, validated_data):
        application = self.context["application"]
        partner_type = validated_data["partner_type"]
        branches = validated_data.get("branches", [])
        location = validated_data.get("location")
        share = validated_data.get("share_data_externally", False)

        instances = []
        if branches:
            for branch in branches:
                apt = ApplicationPartnerType.objects.create(
                    application=application,
                    partner_type=partner_type,
                    branch=branch,
                    location=location if branch == branches[-1] else None,
                    share_data_externally=share,
                )
                instances.append(apt)
        else:
            apt = ApplicationPartnerType.objects.create(
                application=application,
                partner_type=partner_type,
                location=location,
                share_data_externally=share,
            )
            instances.append(apt)
        return instances

    def to_representation(self, instance):
        if isinstance(instance, list):
            return ApplicationPartnerTypeSerializer(instance, many=True).data
        return ApplicationPartnerTypeSerializer(instance).data


class ApplicationContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApplicationContact
        exclude = ["application"]
        read_only_fields = ["id", "created_at", "updated_at"]


class ApplicationBankAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApplicationBankAccount
        exclude = ["application"]
        read_only_fields = ["id", "is_verified", "created_at", "updated_at"]


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
    document_type = serializers.CharField(max_length=50)

    class Meta:
        model = PartnerApplicationDocument
        fields = ["id", "document_type", "document_name", "file"]

    def validate_file(self, value):
        from apps.system_parameters.services.document_config_service import DocumentConfigService

        max_bytes = DocumentConfigService.get_max_file_size_bytes()
        if value.size > max_bytes:
            max_mb = DocumentConfigService.get_max_file_size_mb()
            raise serializers.ValidationError(
                f"File size must not exceed {max_mb} MB."
            )

        allowed_mimes = DocumentConfigService.get_allowed_mime_types()
        if value.content_type not in allowed_mimes:
            raise serializers.ValidationError(
                f"File type '{value.content_type}' is not allowed. "
                f"Accepted types: {', '.join(allowed_mimes)}."
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

INDIVIDUAL_REQUIRED_FIELDS = ValidationConfigService.get_individual_required_fields()
CORPORATE_REQUIRED_FIELDS = ValidationConfigService.get_corporate_required_fields()


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
    partner_categories = serializers.SerializerMethodField()
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
    system_partner_types = serializers.SerializerMethodField()
    branches = serializers.SerializerMethodField()
    locations = serializers.SerializerMethodField()

    CHOICE_LIST_MAP = {
        "partner_types": "PARTNER_TYPE_CHOICES",
        "identification_types": "IDENTIFICATION_TYPE_CHOICES",
        "titles": "TITLE_CHOICES",
        "genders": "GENDER_CHOICES",
        "marital_statuses": "MARITAL_STATUS_CHOICES",
        "political_risks": "POLITICAL_RISK_CHOICES",
        "aml_risks": "AML_RISK_CHOICES",
        "industries": "INDUSTRY_CHOICES",
        "nationalities": "NATIONALITY_CHOICES",
        "application_statuses": "APPLICATION_STATUS_CHOICES",
        "document_types": "DOCUMENT_TYPE_CHOICES",
        "task_types": "TASK_TYPE_CHOICES",
        "task_statuses": "TASK_STATUS_CHOICES",
        "task_priorities": "TASK_PRIORITY_CHOICES",
    }

    def _get_choice_list(self, code):
        try:
            return ConfigurationService.get_choice_list(code)
        except ConfigurationError:
            return []

    def get_partner_types(self, obj):
        return self._get_choice_list("PARTNER_TYPE_CHOICES")

    def get_partner_categories(self, obj):
        return self._get_choice_list("PARTNER_CATEGORY_CHOICES")

    def get_identification_types(self, obj):
        return self._get_choice_list("IDENTIFICATION_TYPE_CHOICES")

    def get_titles(self, obj):
        return self._get_choice_list("TITLE_CHOICES")

    def get_genders(self, obj):
        return self._get_choice_list("GENDER_CHOICES")

    def get_marital_statuses(self, obj):
        return self._get_choice_list("MARITAL_STATUS_CHOICES")

    def get_political_risks(self, obj):
        return self._get_choice_list("POLITICAL_RISK_CHOICES")

    def get_aml_risks(self, obj):
        return self._get_choice_list("AML_RISK_CHOICES")

    def get_industries(self, obj):
        return self._get_choice_list("INDUSTRY_CHOICES")

    def get_nationalities(self, obj):
        return self._get_choice_list("NATIONALITY_CHOICES")

    def get_application_statuses(self, obj):
        return self._get_choice_list("APPLICATION_STATUS_CHOICES")

    def get_document_types(self, obj):
        return self._get_choice_list("DOCUMENT_TYPE_CHOICES")

    def get_task_types(self, obj):
        return self._get_choice_list("TASK_TYPE_CHOICES")

    def get_task_statuses(self, obj):
        return self._get_choice_list("TASK_STATUS_CHOICES")

    def get_task_priorities(self, obj):
        return self._get_choice_list("TASK_PRIORITY_CHOICES")

    def get_system_partner_types(self, obj):
        from apps.partners.models import PartnerType
        return [
            {"value": str(pt.id), "label": pt.name}
            for pt in PartnerType.objects.filter(is_active=True).order_by("name")
        ]

    def get_branches(self, obj):
        from apps.partner_onboarding.models import Branch
        return [
            {"value": str(b.id), "label": b.name}
            for b in Branch.objects.filter(is_active=True).order_by("name")
        ]

    def get_locations(self, obj):
        from apps.partner_onboarding.models import Location
        return [
            {"value": str(l.id), "label": l.name, "branch_id": str(l.branch_id)}
            for l in Location.objects.filter(is_active=True).order_by("name")
        ]


# ---------------------------------------------------------------------------
# Field Value Serializers
# ---------------------------------------------------------------------------


class ApplicationFieldValueSerializer(serializers.ModelSerializer):
    field_code = serializers.ReadOnlyField(source="field_config.field_code")
    field_name = serializers.ReadOnlyField(source="field_config.field_name")
    field_type = serializers.ReadOnlyField(source="field_config.field_type")

    class Meta:
        model = ApplicationFieldValue
        exclude = ["application"]
        read_only_fields = ["id", "created_at", "updated_at"]


class ApplicationFieldValueBatchSerializer(serializers.Serializer):
    field_config = serializers.UUIDField()
    value_json = serializers.JSONField(allow_null=True, default=dict)

    def validate_field_config(self, value):
        from apps.partners.models import PartnerTypeFieldConfiguration
        if not PartnerTypeFieldConfiguration.objects.filter(id=value).exists():
            raise serializers.ValidationError("Invalid field_config ID")
        return value
