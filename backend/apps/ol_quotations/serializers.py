from rest_framework import serializers
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone

from apps.partners.models import Partner, PartnerKYCProfile, PartnerTypeAssignment
from apps.partner_onboarding.models import Location
from apps.system_parameters.services.config_service import ConfigurationService

from .permissions import OLQuotationPermission, has_quotation_permission

from .models import (
    OLQuotation,
    OLQuotationBeneficiary,
    OLQuotationBenefit,
    OLQuotationDocument,
    OLQuotationEvent,
    OLQuotationFinancialSummary,
    OLQuotationFundAllocation,
    OLQuotationInstallmentConfiguration,
    OLQuotationInstallmentRateRow,
    OLQuotationMember,
    OLQuotationPaymentDetail,
    OLQuotationPlanConfiguration,
    OLQuotationProduct,
    OLQuotationRiderSelection,
    OLQuotationUnderwriting,
    OLQuotationVersion,
)


class QuotationValidatedModelSerializer(serializers.ModelSerializer):
    def validate(self, attrs):
        instance = self.instance or self.Meta.model(**attrs)
        for key, value in attrs.items():
            setattr(instance, key, value)
        try:
            instance.full_clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict)
        return attrs


class QuotationNestedReadMixin:
    id = serializers.UUIDField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    created_by = serializers.PrimaryKeyRelatedField(read_only=True)
    updated_by = serializers.PrimaryKeyRelatedField(read_only=True)


class OLQuotationProductSerializer(QuotationNestedReadMixin, QuotationValidatedModelSerializer):
    class Meta:
        model = OLQuotationProduct
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "created_by", "updated_by"]


class OLQuotationPlanConfigurationSerializer(QuotationNestedReadMixin, QuotationValidatedModelSerializer):
    class Meta:
        model = OLQuotationPlanConfiguration
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "created_by", "updated_by"]


class OLQuotationPlanSelectionSerializer(serializers.Serializer):
    plans = serializers.ListField(
        child=serializers.DictField(),
        allow_empty=False,
        required=True,
    )

    def validate_plans(self, value):
        if not value:
            raise serializers.ValidationError("At least one plan must be selected.")
        for index, item in enumerate(value):
            if not isinstance(item, dict):
                raise serializers.ValidationError({index: "Each selection must be an object."})
            if not item.get("plan_id"):
                raise serializers.ValidationError({index: "plan_id is required for every selected plan."})
        return value


class OLQuotationPlanConfigurationPatchSerializer(serializers.Serializer):
    term_years = serializers.IntegerField(required=False, min_value=1)
    payment_period_years = serializers.IntegerField(required=False, min_value=1, allow_null=True)
    premium_frequency = serializers.CharField(required=False, allow_blank=False)
    quote_basis = serializers.CharField(required=False, allow_blank=False)
    estimated_maturity_value = serializers.DecimalField(required=False, max_digits=18, decimal_places=2, min_value=0, allow_null=True)
    premium_factor = serializers.CharField(required=False, allow_blank=False)
    joint_life = serializers.BooleanField(required=False)
    mortgage = serializers.BooleanField(required=False)
    personal_accident = serializers.BooleanField(required=False)
    premium_waiver = serializers.BooleanField(required=False)
    estimated_bonus_rate = serializers.DecimalField(required=False, max_digits=12, decimal_places=6, min_value=0)
    base_sum_assured = serializers.DecimalField(required=False, max_digits=18, decimal_places=2, min_value=0)
    is_selected = serializers.BooleanField(required=False)
    sub_product_code = serializers.CharField(required=False, allow_blank=True)
    coverage_rules = serializers.DictField(required=False)


class OLQuotationMemberSerializer(QuotationNestedReadMixin, QuotationValidatedModelSerializer):
    class Meta:
        model = OLQuotationMember
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "created_by", "updated_by", "age_at_quote"]

    def validate(self, attrs):
        instance = self.instance or OLQuotationMember(**attrs)
        for key, value in attrs.items():
            setattr(instance, key, value)
        try:
            instance.full_clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict)
        return attrs


class OLQuotationMemberStepSerializer(serializers.Serializer):
    """Request contract for additional Member Coverage rows."""

    full_name = serializers.CharField(required=True, max_length=301, trim_whitespace=True)
    relation = serializers.CharField(required=True, max_length=80, trim_whitespace=True)
    date_of_birth = serializers.DateField(required=True)
    gender = serializers.CharField(required=True, max_length=40, trim_whitespace=True)
    sum_assured = serializers.DecimalField(
        required=False,
        allow_null=True,
        max_digits=18,
        decimal_places=2,
        min_value=0,
    )
    coverage_basis = serializers.CharField(required=False, allow_blank=True, max_length=50)


class OLQuotationMemberStepResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField(allow_null=True)
    member_type = serializers.CharField()
    full_name = serializers.CharField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    relation = serializers.CharField()
    date_of_birth = serializers.DateField()
    age_at_quote = serializers.IntegerField(allow_null=True)
    gender = serializers.CharField()
    sum_assured = serializers.DecimalField(max_digits=18, decimal_places=2, allow_null=True)
    coverage_basis = serializers.CharField(allow_blank=True)
    waiting_period_days = serializers.IntegerField()
    is_principal = serializers.BooleanField()


class OLQuotationInstallmentRateRowSerializer(QuotationNestedReadMixin, QuotationValidatedModelSerializer):
    class Meta:
        model = OLQuotationInstallmentRateRow
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "created_by", "updated_by"]


class OLQuotationInstallmentConfigurationSerializer(QuotationNestedReadMixin, QuotationValidatedModelSerializer):
    rate_rows = OLQuotationInstallmentRateRowSerializer(many=True, read_only=True)

    class Meta:
        model = OLQuotationInstallmentConfiguration
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "created_by", "updated_by"]


class OLQuotationFundAllocationSerializer(QuotationNestedReadMixin, QuotationValidatedModelSerializer):
    class Meta:
        model = OLQuotationFundAllocation
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "created_by", "updated_by"]


class OLQuotationRiderSelectionSerializer(QuotationNestedReadMixin, QuotationValidatedModelSerializer):
    class Meta:
        model = OLQuotationRiderSelection
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "created_by", "updated_by"]


class OLQuotationBenefitSerializer(QuotationNestedReadMixin, QuotationValidatedModelSerializer):
    class Meta:
        model = OLQuotationBenefit
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "created_by", "updated_by"]


class OLQuotationDocumentSerializer(QuotationNestedReadMixin, QuotationValidatedModelSerializer):
    class Meta:
        model = OLQuotationDocument
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "created_by", "updated_by"]


class OLQuotationVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = OLQuotationVersion
        fields = "__all__"
        read_only_fields = [field.name for field in OLQuotationVersion._meta.fields]


class OLQuotationFinancialSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = OLQuotationFinancialSummary
        fields = "__all__"
        read_only_fields = [field.name for field in OLQuotationFinancialSummary._meta.fields]


class OLQuotationPaymentDetailSerializer(QuotationNestedReadMixin, QuotationValidatedModelSerializer):
    class Meta:
        model = OLQuotationPaymentDetail
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "created_by", "updated_by"]


class OLQuotationUnderwritingSerializer(QuotationNestedReadMixin, QuotationValidatedModelSerializer):
    class Meta:
        model = OLQuotationUnderwriting
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "created_by", "updated_by"]


class OLQuotationBeneficiarySerializer(QuotationNestedReadMixin, QuotationValidatedModelSerializer):
    class Meta:
        model = OLQuotationBeneficiary
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "created_by", "updated_by"]


class OLQuotationEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = OLQuotationEvent
        fields = "__all__"
        read_only_fields = [field.name for field in OLQuotationEvent._meta.fields]


class OLQuotationPersonalDetailsSerializer(serializers.Serializer):
    quote_name = serializers.CharField(required=True, max_length=255)
    quote_date = serializers.DateField(required=False, default=timezone.localdate)
    identity_type = serializers.CharField(required=True, max_length=40)
    identity_number = serializers.CharField(required=True, max_length=100, trim_whitespace=True)
    date_of_birth = serializers.DateField(required=True)
    age_at_quote = serializers.IntegerField(read_only=True)
    gender = serializers.CharField(required=True, max_length=40)
    smoker_status = serializers.CharField(required=True, max_length=40)
    location = serializers.CharField(required=False, allow_blank=True, max_length=255)
    location_id = serializers.UUIDField(required=False, write_only=True)
    agent_id = serializers.UUIDField(required=False, write_only=True)
    address = serializers.CharField(required=True, allow_blank=False)
    partner_exists = serializers.BooleanField(read_only=True)
    partner_id = serializers.UUIDField(read_only=True, allow_null=True)
    compliant = serializers.BooleanField(read_only=True)
    duplicate_active_quotation_warning = serializers.BooleanField(read_only=True)

    def _choice_codes(self, code):
        try:
            return {item["value"] for item in ConfigurationService.get_choice_list(code)}
        except Exception:
            return set()

    def validate(self, attrs):
        quote_date = attrs.get("quote_date") or timezone.localdate()
        dob = attrs.get("date_of_birth")
        if dob and dob > quote_date:
            raise serializers.ValidationError({"date_of_birth": "Date of birth cannot be after the quote date."})
        if dob and dob > timezone.localdate():
            raise serializers.ValidationError({"date_of_birth": "Date of birth cannot be in the future."})
        if dob:
            age = quote_date.year - dob.year - ((quote_date.month, quote_date.day) < (dob.month, dob.day))
            maximum_age = ConfigurationService.get_int_parameter("OL_MAX_QUOTATION_AGE", 120)
            minimum_age = ConfigurationService.get_int_parameter("OL_MIN_QUOTATION_AGE", 0)
            if age < minimum_age or age > maximum_age:
                raise serializers.ValidationError({"date_of_birth": f"Computed age must be between {minimum_age} and {maximum_age} years."})
            attrs["age_at_quote"] = age

        choices = {
            "identity_type": "IDENTIFICATION_TYPE_CHOICES",
            "gender": "GENDER_CHOICES",
            "smoker_status": "SMOKER_STATUS_CHOICES",
        }
        for field, choice_code in choices.items():
            value = attrs.get(field)
            allowed = self._choice_codes(choice_code)
            if allowed and value not in allowed:
                raise serializers.ValidationError({field: "Select a configured active option."})
            if not allowed:
                raise serializers.ValidationError({field: f"{choice_code} is not configured."})

        identity_rules = ConfigurationService.get_json_parameter("OL_IDENTITY_FORMAT_RULES", {}) or {}
        rule = identity_rules.get(attrs.get("identity_type"), {}) if isinstance(identity_rules, dict) else {}
        if isinstance(rule, dict):
            pattern = rule.get("regex")
            if pattern:
                import re
                if not re.fullmatch(pattern, attrs["identity_number"]):
                    raise serializers.ValidationError({"identity_number": "Identity number does not match the configured format."})
            if rule.get("min_length") is not None and len(attrs["identity_number"]) < int(rule["min_length"]):
                raise serializers.ValidationError({"identity_number": "Identity number is shorter than the configured minimum length."})
            if rule.get("max_length") is not None and len(attrs["identity_number"]) > int(rule["max_length"]):
                raise serializers.ValidationError({"identity_number": "Identity number exceeds the configured maximum length."})

        location_id = attrs.pop("location_id", None)
        if location_id:
            try:
                location = Location.objects.get(pk=location_id, is_active=True)
            except Location.DoesNotExist:
                raise serializers.ValidationError({"location_id": "Select an active configured location."})
            attrs["location_master"] = location
            attrs["location"] = str(location)
        elif not attrs.get("location"):
            raise serializers.ValidationError({"location": "This field is required."})

        agent_id = attrs.pop("agent_id", None)
        if agent_id:
            try:
                agent = Partner.objects.get(pk=agent_id, is_active=True, status="ACTIVE")
            except Partner.DoesNotExist:
                raise serializers.ValidationError({"agent_id": "Select an active eligible agent."})
            eligible = PartnerTypeAssignment.objects.filter(
                partner=agent,
                status="ACTIVE",
                partner_type__is_active=True,
            ).filter(
                partner_type__code__iexact=ConfigurationService.get_str_parameter("OL_AGENT_PARTNER_TYPE_CODE", "AGENT")
            ).exists()
            if not eligible:
                raise serializers.ValidationError({"agent_id": "Selected partner is not configured as an active agent."})
            attrs["agent_partner"] = agent
        else:
            raise serializers.ValidationError({"agent_id": "This field is required."})

        from .models import OLQuotation, QuotationStatus
        quotation = self.context.get("quotation")
        duplicate_query = OLQuotation.objects.filter(
            identity_type=attrs.get("identity_type"),
            identity_number__iexact=attrs.get("identity_number", ""),
            date_of_birth=attrs.get("date_of_birth"),
            status__in=[QuotationStatus.DRAFT, QuotationStatus.FINALIZED],
        )
        if quotation and quotation.pk:
            duplicate_query = duplicate_query.exclude(pk=quotation.pk)
        attrs["_duplicate_active_quotation_warning"] = duplicate_query.exists()

        # Partner type and verified KYC are evaluated through active assignments.
        partner_query = Partner.objects.filter(
            identification_type=attrs.get("identity_type"),
            identification_number__iexact=attrs.get("identity_number", ""),
            date_of_birth=attrs.get("date_of_birth"),
            is_active=True,
            status="ACTIVE",
            type_assignments__status="ACTIVE",
            type_assignments__kyc_profiles__kyc_status="VERIFIED",
        ).distinct()
        partner = partner_query.first()
        attrs["_partner_exists"] = bool(partner)
        attrs["_partner_id"] = partner.pk if partner else None
        attrs["_partner_compliant"] = bool(partner)
        return attrs

    def to_representation(self, instance):
        quotation = instance
        data = {
            "quote_name": quotation.quote_name,
            "quote_date": quotation.quote_date,
            "identity_type": quotation.identity_type,
            "identity_number": quotation.identity_number,
            "date_of_birth": quotation.date_of_birth,
            "age_at_quote": quotation.age_at_quote,
            "gender": quotation.gender,
            "smoker_status": quotation.smoker_status,
            "location": quotation.location,
            "location_id": str(quotation.location_master_id) if quotation.location_master_id else None,
            "agent_id": str(quotation.agent_partner_id) if quotation.agent_partner_id else None,
            "agent": {
                "id": str(quotation.agent_partner_id),
                "name": str(quotation.agent_partner),
                "partner_number": quotation.agent_partner.partner_number,
            } if quotation.agent_partner_id else None,
            "address": quotation.address,
            "partner_exists": bool(quotation.linked_partner_id or quotation.partner_id),
            "partner_id": str(quotation.linked_partner_id or quotation.partner_id) if (quotation.linked_partner_id or quotation.partner_id) else None,
            "compliant": bool(quotation.partner_verified),
        }
        return data


class OLQuotationListSerializer(serializers.ModelSerializer):
    prospect_name = serializers.SerializerMethodField()
    plans_summary = serializers.SerializerMethodField()
    plan_count = serializers.SerializerMethodField()
    status_badge = serializers.SerializerMethodField()
    version = serializers.IntegerField(source="current_version_number", read_only=True)
    agent = serializers.SerializerMethodField()
    created_by = serializers.SerializerMethodField()
    row_actions = serializers.SerializerMethodField()

    class Meta:
        model = OLQuotation
        fields = [
            "id",
            "quote_number",
            "quote_name",
            "prospect_name",
            "plans_summary",
            "plan_count",
            "total_premium",
            "currency",
            "status",
            "status_badge",
            "version",
            "quote_date",
            "agent",
            "created_by",
            "row_actions",
        ]
        read_only_fields = fields

    @staticmethod
    def _user_payload(user):
        if not user:
            return None
        name = " ".join(
            part for part in [
                getattr(user, "first_name", ""),
                getattr(user, "last_name", ""),
            ] if part
        ).strip() or getattr(user, "username", "")
        return {"id": str(user.pk), "name": name, "username": getattr(user, "username", "")}

    def get_prospect_name(self, obj):
        members = list(obj.members.all())
        prospect = next((member for member in members if member.member_type == "LIFE_ASSURED"), None)
        if prospect is None and members:
            prospect = members[0]
        if prospect:
            name = " ".join(
                part for part in [
                    getattr(prospect, "first_name", ""),
                    getattr(prospect, "middle_name", ""),
                    getattr(prospect, "last_name", ""),
                ] if part
            ).strip()
            if name:
                return name
        return obj.quote_name or ""

    def get_plans_summary(self, obj):
        plans = []
        for configuration in obj.plan_configurations.all():
            if not configuration.is_selected:
                continue
            if configuration.plan:
                label = f"{configuration.plan.code} - {configuration.plan.name}"
            else:
                label = configuration.sub_product_code or str(configuration.product_version)
            if label and label not in plans:
                plans.append(label)
        return ", ".join(plans)

    def get_plan_count(self, obj):
        annotated = getattr(obj, "work_queue_plan_count", None)
        if annotated is not None:
            return annotated
        return sum(1 for configuration in obj.plan_configurations.all() if configuration.is_selected)

    def get_status_badge(self, obj):
        label = obj.get_status_display()
        return {"code": obj.status, "label": label, "tone": obj.status.lower()}

    def get_agent(self, obj):
        return self._user_payload(obj.agent)

    def get_created_by(self, obj):
        return self._user_payload(obj.created_by)

    def _action(self, obj, *, key, permission, state_allowed, method, suffix, reason=None):
        request = self.context.get("request")
        permission_code = OLQuotationPermission.code_for(permission)
        has_permission = has_quotation_permission(request.user if request else None, permission)
        visible = bool(has_permission and state_allowed)
        if reason is None:
            if not has_permission:
                reason = "Insufficient permission."
            elif not state_allowed:
                reason = "Action is not available for this quotation status."
        path = f"/api/v1/ol/quotations/quotations/{obj.pk}{suffix}"
        return {
            "key": key,
            "visible": visible,
            "enabled": visible,
            "method": method,
            "url": path,
            "permission": permission_code,
            "state_allowed": bool(state_allowed),
            "reason": reason,
        }

    def get_row_actions(self, obj):
        status = obj.status
        partner_verified = bool(obj.partner_verified)
        return {
            "view": self._action(
                obj, key="view", permission="view", state_allowed=True, method="GET", suffix="/"
            ),
            "edit": self._action(
                obj, key="edit", permission="update", state_allowed=status == "DRAFT", method="PATCH", suffix="/"
            ),
            "revise": self._action(
                obj, key="revise", permission="update", state_allowed=status == "FINALIZED", method="POST", suffix="/revise/"
            ),
            "finalize": self._action(
                obj, key="finalize", permission="finalize", state_allowed=status == "DRAFT", method="POST", suffix="/finalize/"
            ),
            "print": self._action(
                obj, key="print", permission="print", state_allowed=status in {"FINALIZED", "CONVERTED"}, method="GET", suffix="/print/"
            ),
            "convert_to_proposal": self._action(
                obj, key="convert_to_proposal", permission="convert", state_allowed=status == "FINALIZED" and partner_verified, method="POST", suffix="/convert/"
            ),
            "delete": self._action(
                obj, key="delete", permission="destroy", state_allowed=status == "DRAFT", method="DELETE", suffix="/"
            ),
        }


class OLQuotationSerializer(serializers.ModelSerializer):
    products = OLQuotationProductSerializer(many=True, read_only=True)
    plan_configurations = OLQuotationPlanConfigurationSerializer(many=True, read_only=True)
    members = OLQuotationMemberSerializer(many=True, read_only=True)
    installment_configurations = OLQuotationInstallmentConfigurationSerializer(many=True, read_only=True)
    fund_allocations = OLQuotationFundAllocationSerializer(many=True, read_only=True)
    rider_selections = OLQuotationRiderSelectionSerializer(many=True, read_only=True)
    payment_detail = OLQuotationPaymentDetailSerializer(read_only=True)
    underwriting_detail = OLQuotationUnderwritingSerializer(read_only=True)
    beneficiaries = OLQuotationBeneficiarySerializer(many=True, read_only=True)
    benefits = OLQuotationBenefitSerializer(many=True, read_only=True)
    documents = OLQuotationDocumentSerializer(many=True, read_only=True)
    versions = OLQuotationVersionSerializer(many=True, read_only=True)
    financial_summary = OLQuotationFinancialSummarySerializer(read_only=True)
    events = OLQuotationEventSerializer(many=True, read_only=True)

    class Meta:
        model = OLQuotation
        fields = [
            "id",
            "quote_number",
            "quote_name",
            "quote_date",
            "status",
            "partner",
            "product",
            "product_version",
            "linked_partner",
            "currency",
            "current_version_number",
            "wizard_step_completion",
            "identity_type",
            "identity_number",
            "date_of_birth",
            "age_at_quote",
            "gender",
            "smoker_status",
            "location",
            "agent",
            "address",
            "partner_verified",
            "approval_required",
            "expiry_date",
            "total_sum_assured",
            "total_premium",
            "calculation_snapshot",
            "metadata",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
            "products",
            "plan_configurations",
            "members",
            "installment_configurations",
            "fund_allocations",
            "rider_selections",
            "payment_detail",
            "underwriting_detail",
            "beneficiaries",
            "benefits",
            "documents",
            "versions",
            "financial_summary",
            "events",
        ]
        read_only_fields = [
            "id",
            "quote_number",
            "status",
            "age_at_quote",
            "current_version_number",
            "wizard_step_completion",
            "partner_verified",
            "approval_required",
            "total_sum_assured",
            "total_premium",
            "calculation_snapshot",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
            "products",
            "plan_configurations",
            "members",
            "installment_configurations",
            "fund_allocations",
            "rider_selections",
            "payment_detail",
            "underwriting_detail",
            "beneficiaries",
            "benefits",
            "documents",
            "versions",
            "financial_summary",
            "events",
        ]

    def validate(self, attrs):
        instance = self.instance or OLQuotation(**attrs)
        for key, value in attrs.items():
            setattr(instance, key, value)
        try:
            instance.full_clean(exclude=["quote_number"] if not instance.quote_number else [])
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict)
        return attrs
