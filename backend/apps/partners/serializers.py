from rest_framework import serializers

from apps.partner_onboarding.models import Branch, Location
from apps.partners.models import (
    CorporateProfile,
    IndividualProfile,
    Partner,
    PartnerAssignmentBankAccount,
    PartnerAssignmentContact,
    PartnerBankAccount,
    PartnerContact,
    PartnerDocument,
    PartnerDynamicFieldValue,
    PartnerKYCProfile,
    PartnerType,
    PartnerTypeAssignment,
    PartnerTypeAssignmentHistory,
    PartnerTypeBankRequirement,
    PartnerTypeContactRequirement,
    PartnerTypeDocumentRequirement,
    PartnerTypeFieldConfiguration,
    UserPartnerLink,
)


class IndividualProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = IndividualProfile
        fields = [
            "id", "identification_type", "identification_number",
            "title", "first_name", "other_name", "surname",
            "gender", "date_of_birth", "marital_status",
            "occupation", "nationality",
        ]
        read_only_fields = ["id"]


class CorporateProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CorporateProfile
        fields = [
            "id", "company_name", "tin_number", "incorporation_date",
            "industry", "contact_person", "contact_person_phone",
            "contact_person_email",
        ]
        read_only_fields = ["id"]


class PartnerContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = PartnerContact
        fields = "__all__"
        read_only_fields = ["id", "partner", "created_at", "updated_at"]


class PartnerBankAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = PartnerBankAccount
        fields = "__all__"
        read_only_fields = ["id", "partner", "created_at", "updated_at"]


class PartnerTypeAssignmentSerializer(serializers.ModelSerializer):
    partner_type_name = serializers.ReadOnlyField(source="partner_type.name")
    partner_type_code = serializers.ReadOnlyField(source="partner_type.code")
    branch_name = serializers.ReadOnlyField(source="branch.name")
    location_name = serializers.ReadOnlyField(source="location.name")

    class Meta:
        model = PartnerTypeAssignment
        fields = [
            "id", "partner", "partner_type", "partner_type_name",
            "partner_type_code", "branch", "branch_name",
            "location", "location_name",
            "share_data_externally", "status", "effective_date",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class PartnerTypeAssignmentHistorySerializer(serializers.ModelSerializer):
    changed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = PartnerTypeAssignmentHistory
        fields = [
            "id", "assignment", "previous_status", "new_status", "reason",
            "changed_by", "changed_by_name", "changed_at",
        ]
        read_only_fields = fields

    def get_changed_by_name(self, obj):
        return obj.changed_by.full_name if obj.changed_by else None


class PartnerTypeAssignmentCreateSerializer(serializers.Serializer):
    partner_type = serializers.UUIDField()
    branch = serializers.UUIDField(required=False, allow_null=True)
    branches = serializers.ListField(child=serializers.UUIDField(), required=False, default=list)
    location = serializers.UUIDField(required=False, allow_null=True)
    share_data_externally = serializers.BooleanField(default=False)
    effective_date = serializers.DateField(required=False, allow_null=True)

    def validate_partner_type(self, value):
        try:
            return PartnerType.objects.get(id=value, is_active=True)
        except PartnerType.DoesNotExist:
            raise serializers.ValidationError("Invalid or inactive partner type.") from None

    def validate_branch(self, value):
        if not value:
            return None
        try:
            return Branch.objects.get(id=value, is_active=True)
        except Branch.DoesNotExist:
            raise serializers.ValidationError("Invalid branch.") from None

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
            raise serializers.ValidationError("Invalid location.") from None

    def validate(self, attrs):
        # Accept the legacy singular field, but never silently discard additional branches.
        branch = attrs.get("branch")
        branches = attrs.get("branches", [])
        if branch and branches and branch not in branches:
            raise serializers.ValidationError({"branches": "Use either branch or branches, not both with different values."})
        if len(branches) > 1:
            raise serializers.ValidationError({"branches": "A partner type may have only one branch assignment."})
        if branch and not branches:
            attrs["branches"] = [branch]
        attrs.pop("branch", None)
        return attrs

    def create(self, validated_data):
        partner = self.context["partner"]
        from apps.partners.services.partner_type_service import PartnerTypeAssignmentService
        branches = validated_data.get("branches", [])
        location = validated_data.get("location")

        if not branches:
            return PartnerTypeAssignmentService.assign(
                partner=partner,
                partner_type=validated_data["partner_type"],
                branch=None,
                location=location,
                share_data_externally=validated_data.get("share_data_externally", False),
                effective_date=validated_data.get("effective_date"),
            )

        # Use the first branch (the model only supports one assignment per partner_type)
        return PartnerTypeAssignmentService.assign(
            partner=partner,
            partner_type=validated_data["partner_type"],
            branch=branches[0],
            location=location,
            share_data_externally=validated_data.get("share_data_externally", False),
            effective_date=validated_data.get("effective_date"),
        )


class PartnerListSerializer(serializers.ModelSerializer):
    display_name = serializers.ReadOnlyField()
    partner_category = serializers.ReadOnlyField()

    class Meta:
        model = Partner
        fields = [
            "id", "partner_number", "partner_type", "partner_category",
            "party_type", "legal_name", "display_name",
            "email", "phone", "mobile_number", "status", "is_active",
            "political_risk", "aml_risk", "created_at",
        ]
        read_only_fields = fields


class PartnerDetailSerializer(serializers.ModelSerializer):
    display_name = serializers.ReadOnlyField()
    partner_category = serializers.ReadOnlyField()
    individual_profile = IndividualProfileSerializer(read_only=True, allow_null=True)
    corporate_profile = CorporateProfileSerializer(read_only=True, allow_null=True)
    type_assignments = PartnerTypeAssignmentSerializer(many=True, read_only=True)
    contacts = PartnerContactSerializer(many=True, read_only=True)
    bank_accounts = PartnerBankAccountSerializer(many=True, read_only=True)

    class Meta:
        model = Partner
        fields = [
            "id", "partner_number", "partner_type", "partner_category",
            "party_type", "legal_name", "status", "is_active", "display_name",
            "identification_type", "identification_number", "national_id", "registration_number",
            "title", "first_name", "other_name", "surname",
            "gender", "date_of_birth", "marital_status",
            "occupation", "nationality",
            "company_name", "tin_number", "incorporation_date",
            "industry", "contact_person", "contact_person_phone",
            "contact_person_email",
            "physical_address", "postal_address",
            "email", "phone", "telephone_number", "mobile_number",
            "political_risk", "aml_risk",
            "created_from_application",
            "individual_profile", "corporate_profile",
            "type_assignments",
            "contacts", "bank_accounts",
            "activated_at", "deactivated_at", "deactivation_reason",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "partner_number", "created_from_application",
            "individual_profile", "corporate_profile", "type_assignments",
            "contacts", "bank_accounts",
            "activated_at", "deactivated_at", "created_at", "updated_at",
        ]


class PartnerUpdateSerializer(serializers.ModelSerializer):
    partner_category = serializers.ChoiceField(
        choices=["INDIVIDUAL", "CORPORATE"], required=False,
    )

    class Meta:
        model = Partner
        fields = [
            "partner_category",
            "title", "first_name", "other_name", "surname",
            "gender", "date_of_birth", "marital_status", "occupation",
            "nationality", "telephone_number", "mobile_number",
            "physical_address", "postal_address",
            "company_name", "tin_number", "incorporation_date", "industry",
            "contact_person", "contact_person_phone", "contact_person_email",
            "identification_type", "identification_number",
            "political_risk", "aml_risk",
        ]


class PartnerTypeDocumentRequirementSerializer(serializers.ModelSerializer):
    partner_type_name = serializers.ReadOnlyField(source="partner_type.name")
    created_by_name = serializers.SerializerMethodField()
    updated_by_name = serializers.SerializerMethodField()

    class Meta:
        model = PartnerTypeDocumentRequirement
        fields = [
            "id", "partner_type", "partner_type_name",
            "code", "description", "is_required", "is_mandatory",
            "sort_order", "is_active",
            "created_by", "created_by_name",
            "updated_by", "updated_by_name",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "partner_type", "created_at", "updated_at", "created_by", "updated_by"]

    def get_created_by_name(self, obj):
        return obj.created_by.full_name if obj.created_by else None

    def get_updated_by_name(self, obj):
        return obj.updated_by.full_name if obj.updated_by else None


class PartnerTypeSerializer(serializers.ModelSerializer):
    branch_id = serializers.PrimaryKeyRelatedField(
        queryset=Branch.objects.all(), source="branch", allow_null=True, required=False,
    )
    location_id = serializers.PrimaryKeyRelatedField(
        queryset=Location.objects.all(), source="location", allow_null=True, required=False,
    )
    branch_name = serializers.SerializerMethodField()
    location_name = serializers.SerializerMethodField()

    class Meta:
        model = PartnerType
        fields = [
            "id", "code", "name", "description",
            "branch_id", "branch_name",
            "location_id", "location_name",
            "is_active", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_branch_name(self, obj):
        return obj.branch.name if obj.branch else None

    def get_location_name(self, obj):
        return obj.location.name if obj.location else None


class PartnerTypeFieldConfigurationSerializer(serializers.ModelSerializer):
    partner_type_name = serializers.ReadOnlyField(source="partner_type.name")

    class Meta:
        model = PartnerTypeFieldConfiguration
        fields = [
            "id", "partner_type", "partner_type_name",
            "field_name", "field_code", "field_type",
            "default_value", "is_required",
            "validation_rules", "display_order",
            "visibility_rules", "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "partner_type", "created_at", "updated_at"]


class PartnerTypeContactRequirementSerializer(serializers.ModelSerializer):
    partner_type_name = serializers.ReadOnlyField(source="partner_type.name")

    class Meta:
        model = PartnerTypeContactRequirement
        fields = [
            "id", "partner_type", "partner_type_name",
            "contact_type",
            "is_required", "multiple_allowed", "display_order",
            "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "partner_type", "created_at", "updated_at"]


class PartnerTypeBankRequirementSerializer(serializers.ModelSerializer):
    partner_type_name = serializers.ReadOnlyField(source="partner_type.name")

    class Meta:
        model = PartnerTypeBankRequirement
        fields = [
            "id", "partner_type", "partner_type_name",
            "bank_type",
            "is_required", "multiple_allowed",
            "validation_rules", "display_order",
            "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "partner_type", "created_at", "updated_at"]


class PartnerDocumentSerializer(serializers.ModelSerializer):
    document_requirement_code = serializers.ReadOnlyField(
        source="document_requirement.code"
    )
    document_requirement_name = serializers.SerializerMethodField()
    allow_multiple_uploads = serializers.ReadOnlyField(
        source="document_requirement.allow_multiple_uploads"
    )

    class Meta:
        model = PartnerDocument
        fields = [
            "id", "assignment", "document_requirement",
            "document_requirement_code", "document_requirement_name",
            "allow_multiple_uploads",
            "file", "document_number",
            "issue_date", "expiry_date",
            "uploaded_by", "uploaded_at",
            "status", "verification_notes",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "assignment", "uploaded_by", "uploaded_at",
            "created_at", "updated_at",
        ]

    def get_document_requirement_name(self, obj):
        return obj.document_requirement.description or obj.document_requirement.code


class PartnerDynamicFieldValueSerializer(serializers.ModelSerializer):
    field_code = serializers.ReadOnlyField(source="field_config.field_code")
    field_name = serializers.ReadOnlyField(source="field_config.field_name")
    field_type = serializers.ReadOnlyField(source="field_config.field_type")

    class Meta:
        model = PartnerDynamicFieldValue
        fields = [
            "id", "assignment", "field_config",
            "field_code", "field_name", "field_type",
            "value_json",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "assignment", "created_at", "updated_at"]


class PartnerAssignmentContactSerializer(serializers.ModelSerializer):
    config_contact_type = serializers.ReadOnlyField(
        source="contact_requirement.contact_type"
    )

    class Meta:
        model = PartnerAssignmentContact
        fields = [
            "id", "assignment", "contact_requirement",
            "config_contact_type",
            "contact_type", "first_name", "last_name",
            "email", "phone", "mobile",
            "designation",
            "is_primary", "notes",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "assignment", "created_at", "updated_at"]


class PartnerAssignmentBankAccountSerializer(serializers.ModelSerializer):
    config_bank_type = serializers.ReadOnlyField(
        source="bank_requirement.bank_type"
    )

    class Meta:
        model = PartnerAssignmentBankAccount
        fields = [
            "id", "assignment", "bank_requirement",
            "config_bank_type",
            "bank_type", "bank_name", "branch_name",
            "account_name", "account_number",
            "swift_code", "currency",
            "is_primary", "notes",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "assignment", "created_at", "updated_at"]


class PartnerKYCProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = PartnerKYCProfile
        fields = [
            "id", "assignment",
            "kyc_status",
            "risk_score", "risk_level",
            "last_review_date", "reviewed_by",
            "notes",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "assignment", "risk_score", "risk_level",
            "created_at", "updated_at",
        ]


class PartnerTypeAssignmentSetupSerializer(serializers.ModelSerializer):
    setup_summary = serializers.SerializerMethodField()
    documents = PartnerDocumentSerializer(many=True, read_only=True)
    field_values = PartnerDynamicFieldValueSerializer(many=True, read_only=True)
    assignment_contacts = PartnerAssignmentContactSerializer(many=True, read_only=True)
    assignment_bank_accounts = PartnerAssignmentBankAccountSerializer(
        many=True, read_only=True
    )
    kyc_profile = serializers.SerializerMethodField()

    class Meta:
        model = PartnerTypeAssignment
        fields = [
            "id", "partner", "partner_type",
            "setup_summary",
            "documents", "field_values",
            "assignment_contacts", "assignment_bank_accounts",
            "kyc_profile",
        ]
        read_only_fields = fields

    def get_setup_summary(self, obj):
        from apps.partners.services.setup_service import PartnerSetupService
        return PartnerSetupService.get_setup_summary(obj)

    def get_kyc_profile(self, obj):
        try:
            kyc = obj.kyc_profiles.first()
            if kyc:
                return PartnerKYCProfileSerializer(kyc).data
        except PartnerKYCProfile.DoesNotExist:
            pass
        return None


class UserPartnerLinkSerializer(serializers.ModelSerializer):
    user_name = serializers.ReadOnlyField(source="user.full_name")
    user_type = serializers.ReadOnlyField(source="user.user_type")
    partner_number = serializers.ReadOnlyField(source="partner.partner_number")
    partner_name = serializers.ReadOnlyField(source="partner.display_name")
    is_current = serializers.ReadOnlyField()

    class Meta:
        model = UserPartnerLink
        fields = [
            "id", "user", "user_name", "user_type", "partner", "partner_number",
            "partner_name", "link_status", "is_primary", "valid_from", "valid_to",
            "is_current", "created_by", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "user_name", "user_type", "partner_number", "partner_name",
            "is_current", "created_by", "created_at", "updated_at",
        ]


class UserPartnerLinkCreateSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    partner_id = serializers.UUIDField()
    is_primary = serializers.BooleanField(required=False, default=False)
    valid_from = serializers.DateTimeField(required=False)
    valid_to = serializers.DateTimeField(required=False, allow_null=True)

    def validate(self, attrs):
        from apps.users.models import User

        try:
            attrs["user"] = User.objects.get(pk=attrs.pop("user_id"))
        except User.DoesNotExist as exc:
            raise serializers.ValidationError({"user_id": "User not found."}) from exc
        try:
            attrs["partner"] = Partner.objects.get(pk=attrs.pop("partner_id"))
        except Partner.DoesNotExist as exc:
            raise serializers.ValidationError({"partner_id": "Partner not found."}) from exc
        if attrs.get("valid_to") and attrs.get("valid_from") and attrs["valid_to"] < attrs["valid_from"]:
            raise serializers.ValidationError({"valid_to": "valid_to must be on or after valid_from."})
        return attrs


class UserPartnerLinkRemoveSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class PartnerContextSerializer(serializers.ModelSerializer):
    display_name = serializers.ReadOnlyField()
    partner_category = serializers.ReadOnlyField()

    class Meta:
        model = Partner
        fields = [
            "id", "partner_number", "partner_type", "partner_category", "party_type",
            "legal_name", "display_name", "status", "is_active",
        ]
        read_only_fields = fields
