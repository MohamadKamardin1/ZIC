from decimal import Decimal

from rest_framework import serializers
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone

from apps.partners.models import Partner, PartnerKYCProfile, PartnerTypeAssignment
from apps.partner_onboarding.models import Location
from apps.system_parameters.services.config_service import ConfigurationService
from apps.ol_proposals.models import OLProposal

from .permissions import OLQuotationPermission, has_quotation_permission
from .services.quotation_service import QuotationService

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


class OLQuotationPartnerVerificationSerializer(serializers.Serializer):
    partner_exists = serializers.BooleanField(read_only=True)
    partner_id = serializers.UUIDField(read_only=True, allow_null=True)
    compliant = serializers.BooleanField(read_only=True)
    missing_fields = serializers.ListField(child=serializers.CharField(), read_only=True)
    partner_number = serializers.CharField(read_only=True, allow_null=True)
    partner_display_name = serializers.CharField(read_only=True, allow_null=True)


class OLQuotationPartnerCompletionSerializer(serializers.Serializer):
    first_name = serializers.CharField(required=False, allow_blank=True, max_length=100)
    surname = serializers.CharField(required=False, allow_blank=True, max_length=100)
    other_name = serializers.CharField(required=False, allow_blank=True, max_length=100)
    email = serializers.EmailField(required=False, allow_blank=True)
    mobile_number = serializers.CharField(required=False, allow_blank=True, max_length=20)
    telephone_number = serializers.CharField(required=False, allow_blank=True, max_length=20)
    gender = serializers.CharField(required=False, allow_blank=True, max_length=10)
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    identification_type = serializers.CharField(required=False, allow_blank=True, max_length=50)
    identification_number = serializers.CharField(required=False, allow_blank=True, max_length=120)
    nationality = serializers.CharField(required=False, allow_blank=True, max_length=100)
    occupation = serializers.CharField(required=False, allow_blank=True, max_length=200)

    def validate(self, attrs):
        quotation = self.context.get("quotation")
        if quotation is not None:
            for field, quotation_field in {
                "identification_type": "identity_type",
                "identification_number": "identity_number",
                "date_of_birth": "date_of_birth",
                "gender": "gender",
            }.items():
                if field not in attrs or attrs[field] in (None, ""):
                    value = getattr(quotation, quotation_field, None)
                    if value not in (None, ""):
                        attrs[field] = value
        if attrs.get("date_of_birth") and attrs["date_of_birth"] > timezone.localdate():
            raise serializers.ValidationError({"date_of_birth": "Date of birth cannot be in the future."})
        return attrs


def _display_value(value):
    if value is None:
        return None
    number = next(
        (getattr(value, field, None) for field in ("partner_number", "quote_number", "quotation_number", "code") if getattr(value, field, None)),
        None,
    )
    name = getattr(value, "name", None) or getattr(value, "legal_name", None)
    if not name:
        parts = [
            getattr(value, field, None)
            for field in ("title", "first_name", "other_name", "surname", "last_name")
        ]
        name = " ".join(str(part) for part in parts if part).strip() or None
    if number:
        return f"{number} — {name}" if name and str(name) != str(number) else str(number)
    if name:
        return str(name)
    return str(value)


class _ForeignKeyDisplayField(serializers.Field):
    def __init__(self, relation_name, **kwargs):
        self.relation_name = relation_name
        super().__init__(read_only=True, **kwargs)

    def get_attribute(self, instance):
        return getattr(instance, self.relation_name, None)

    def to_representation(self, value):
        return _display_value(value)


class ForeignKeyDisplayMixin:
    """Append a display label beside each direct FK in model-backed responses."""

    def get_fields(self):
        fields = super().get_fields()
        model = getattr(getattr(self, "Meta", None), "model", None)
        if model is None:
            return fields
        for model_field in model._meta.get_fields():
            if not getattr(model_field, "many_to_one", False) or not getattr(model_field, "concrete", False):
                continue
            display_name = f"{model_field.name}_display"
            if display_name not in fields:
                fields[display_name] = _ForeignKeyDisplayField(model_field.name)
        return fields


class OLProposalSerializer(ForeignKeyDisplayMixin, serializers.ModelSerializer):
    quotation_id = serializers.UUIDField(source="quotation.pk", read_only=True)
    quotation_version_id = serializers.UUIDField(source="quotation_version.pk", read_only=True, allow_null=True)

    class Meta:
        model = OLProposal
        fields = [
            "id",
            "proposal_number",
            "status",
            "quotation_id",
            "quotation_version_id",
            "created_at",
        ]
        read_only_fields = fields


class QuotationValidatedModelSerializer(ForeignKeyDisplayMixin, serializers.ModelSerializer):
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
        error_messages={
            "required": "Select at least one plan before continuing.",
            "empty": "Select at least one plan before continuing.",
            "invalid": "Each selected plan must be sent as a configuration object.",
        },
    )

    def validate_plans(self, value):
        if not value:
            raise serializers.ValidationError("At least one plan must be selected.")
        for index, item in enumerate(value):
            if not isinstance(item, dict):
                raise serializers.ValidationError({index: "Each selection must be an object."})
            if not item.get("plan_id"):
                raise serializers.ValidationError({f"plan_{index}.plan_id": "Choose a plan for this section before continuing."})
        return value


class OLQuotationPlanConfigurationPatchSerializer(serializers.Serializer):
    term_years = serializers.IntegerField(required=False, min_value=1, error_messages={"invalid": "Enter a whole number of years for the policy term.", "min_value": "Enter a policy term of at least 1 year, then use the plan range shown on screen."})
    payment_period_years = serializers.IntegerField(required=False, min_value=1, allow_null=True, error_messages={"invalid": "Enter a whole number of years for the payment period.", "min_value": "Enter a payment period of at least 1 year and no longer than the policy term."})
    premium_frequency = serializers.CharField(required=False, allow_blank=False, error_messages={"blank": "Choose a payment frequency from the available options."})
    quote_basis = serializers.CharField(required=False, allow_blank=False, error_messages={"blank": "Choose a quote basis from the available options."})
    estimated_maturity_value = serializers.DecimalField(required=False, max_digits=18, decimal_places=2, min_value=0, allow_null=True, error_messages={"invalid": "Enter a valid estimated maturity amount.", "min_value": "Enter a positive estimated maturity amount greater than TZS 0.00."})
    premium_factor = serializers.CharField(required=False, allow_blank=False, error_messages={"blank": "Choose a premium factor from the available options, or leave it unset when the plan permits that."})
    joint_life = serializers.BooleanField(required=False)
    mortgage = serializers.BooleanField(required=False)
    personal_accident = serializers.BooleanField(required=False)
    premium_waiver = serializers.BooleanField(required=False)
    estimated_bonus_rate = serializers.DecimalField(required=False, max_digits=12, decimal_places=6, min_value=0, error_messages={"invalid": "Enter a valid bonus rate per mille.", "min_value": "Enter zero or a positive bonus rate per mille."})
    base_sum_assured = serializers.DecimalField(required=False, max_digits=18, decimal_places=2, min_value=0, error_messages={"invalid": "Enter a valid base sum assured amount.", "min_value": "Enter a positive base sum assured greater than TZS 0.00; the configured plan range is shown on screen."})
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


class OLQuotationInstallmentTemplateRateRowSerializer(serializers.Serializer):
    sequence = serializers.IntegerField(min_value=1)
    description = serializers.CharField(max_length=255)
    rate_percent = serializers.DecimalField(max_digits=7, decimal_places=4, min_value=Decimal("0"), max_value=Decimal("100"))
    paid_up_rate = serializers.DecimalField(max_digits=18, decimal_places=8, min_value=Decimal("0"), allow_null=True, required=False)


class OLQuotationInstallmentConfigureSerializer(serializers.Serializer):
    annuity_period_years = serializers.IntegerField(min_value=1)
    payment_mode = serializers.CharField(max_length=40)
    after_maturity_benefits = serializers.BooleanField(required=False, default=False)
    before_maturity_benefits = serializers.BooleanField(required=False, default=False)
    rate_rows = OLQuotationInstallmentTemplateRateRowSerializer(many=True, allow_empty=False)

    def validate_rate_rows(self, value):
        sequences = [row["sequence"] for row in value]
        if len(sequences) != len(set(sequences)):
            raise serializers.ValidationError("Installment row sequences must be unique.")
        total = sum((row["rate_percent"] for row in value), Decimal("0"))
        if total != Decimal("100"):
            raise serializers.ValidationError("Installment rates must sum exactly to 100.")
        return value


class OLQuotationInstallmentPlanRowSerializer(serializers.Serializer):
    plan_configuration_id = serializers.UUIDField()
    plan_code = serializers.CharField(allow_blank=True)
    plan_name = serializers.CharField(allow_blank=True)
    policy_term_years = serializers.IntegerField()
    payment_mode = serializers.CharField(allow_blank=True)
    total_number_of_installments = serializers.IntegerField(min_value=0)
    status = serializers.ChoiceField(choices=["READY_TO_CONFIGURE", "CONFIGURED"])
    can_configure = serializers.BooleanField()


class OLQuotationInstallmentTemplateSerializer(serializers.Serializer):
    plan_configuration_id = serializers.UUIDField()
    has_template = serializers.BooleanField()
    banner = serializers.CharField(allow_blank=True)
    policy_term_years = serializers.IntegerField()
    payment_mode = serializers.CharField(allow_blank=True)
    available_payment_modes = serializers.ListField(child=serializers.CharField())
    rate_rows = OLQuotationInstallmentTemplateRateRowSerializer(many=True)


class OLQuotationInstallmentStateSerializer(serializers.Serializer):
    rows = OLQuotationInstallmentPlanRowSerializer(many=True)
    requires_configuration = serializers.BooleanField()
    wizard_complete = serializers.BooleanField()


class OLQuotationFundAllocationSerializer(QuotationNestedReadMixin, QuotationValidatedModelSerializer):
    class Meta:
        model = OLQuotationFundAllocation
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "created_by", "updated_by"]


class OLQuotationInvestmentFundOptionSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    code = serializers.CharField()
    name = serializers.CharField()
    description = serializers.CharField(allow_blank=True)
    fund_type_id = serializers.UUIDField()
    fund_type_code = serializers.CharField()
    fund_type_name = serializers.CharField()
    risk_profile = serializers.CharField()
    currency = serializers.CharField()
    valuation_frequency = serializers.CharField()
    unit_price = serializers.DecimalField(max_digits=18, decimal_places=6, allow_null=True)
    currency_compatible = serializers.BooleanField()
    currency_conversion_allowed = serializers.BooleanField()
    selectable = serializers.BooleanField()


class OLQuotationInvestmentFundAllocationInputSerializer(serializers.Serializer):
    plan_config_id = serializers.UUIDField(
        error_messages={
            "required": "Select the selected plan configuration that this fund allocation belongs to.",
            "invalid": "The fund allocation must reference a valid selected plan configuration.",
        },
    )
    fund_id = serializers.UUIDField(
        error_messages={
            "required": "Select an investment fund for this allocation.",
            "invalid": "Select a valid investment fund from the available options.",
        },
    )
    allocation_percent = serializers.DecimalField(
        max_digits=7,
        decimal_places=4,
        min_value=Decimal("0"),
        max_value=Decimal("100"),
    )
    allocated_amount = serializers.DecimalField(
        max_digits=18,
        decimal_places=2,
        min_value=Decimal("0"),
        required=False,
        allow_null=True,
    )


class OLQuotationInvestmentFundConfigureSerializer(serializers.Serializer):
    allocations = OLQuotationInvestmentFundAllocationInputSerializer(many=True, allow_empty=False)


class OLQuotationInvestmentFundStateSerializer(serializers.Serializer):
    plan_rows = serializers.ListField(child=serializers.DictField())
    requires_allocation = serializers.BooleanField()
    not_applicable = serializers.BooleanField()
    wizard_complete = serializers.BooleanField()


class OLQuotationInvestmentFundOptionsSerializer(serializers.Serializer):
    plan_configuration_id = serializers.UUIDField(allow_null=True)
    not_applicable = serializers.BooleanField()
    quotation_currency = serializers.CharField()
    funds = OLQuotationInvestmentFundOptionSerializer(many=True)


class OLQuotationRiderOptionSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    code = serializers.CharField()
    name = serializers.CharField()
    rider_category = serializers.CharField()
    benefit_type = serializers.CharField()
    calculation_basis = serializers.CharField()
    min_age = serializers.IntegerField()
    max_age = serializers.IntegerField()
    min_term = serializers.IntegerField()
    max_term = serializers.IntegerField()
    min_sum_assured = serializers.DecimalField(max_digits=18, decimal_places=2, allow_null=True)
    max_sum_assured = serializers.DecimalField(max_digits=18, decimal_places=2, allow_null=True)
    waiting_period_days = serializers.IntegerField()
    allows_standalone = serializers.BooleanField()
    requires_underwriting = serializers.BooleanField()
    product_id = serializers.UUIDField(allow_null=True)
    plan_id = serializers.UUIDField(allow_null=True)
    selectable = serializers.BooleanField()
    synchronized_option = serializers.CharField(allow_blank=True)


class OLQuotationBenefitInputSerializer(serializers.Serializer):
    beneficial_type_id = serializers.UUIDField(
        required=False,
        allow_null=True,
        error_messages={
            "invalid": "Select a configured Benefit Type from the list. Do not submit the benefit name or code.",
        },
    )
    benefit_type = serializers.CharField(required=False, allow_blank=True, max_length=80)
    basis = serializers.ChoiceField(choices=["FIXED", "RATIO", "LOADED", "DISCOUNTED", "CAPPED"])
    value = serializers.DecimalField(max_digits=18, decimal_places=2, min_value=Decimal("0"), required=False, allow_null=True)
    loading = serializers.DecimalField(max_digits=9, decimal_places=4, min_value=Decimal("0"), max_value=Decimal("100"), required=False)
    discount = serializers.DecimalField(max_digits=9, decimal_places=4, min_value=Decimal("0"), max_value=Decimal("100"), required=False)
    maximum_cap = serializers.DecimalField(max_digits=18, decimal_places=2, min_value=Decimal("0"), required=False, allow_null=True)
    code = serializers.CharField(required=False, allow_blank=True, max_length=80)
    name = serializers.CharField(required=False, allow_blank=True, max_length=255)

    def validate(self, attrs):
        basis = attrs.get("basis")
        value = attrs.get("value")
        if basis == "RATIO" and (value is None or not 0 < value <= Decimal("100")):
            raise serializers.ValidationError({"value": "Ratio benefit value must be greater than 0 and no greater than 100 percent."})
        if basis == "CAPPED" and attrs.get("maximum_cap") is None:
            raise serializers.ValidationError({"maximum_cap": "A maximum cap is required for a capped benefit."})
        if attrs.get("maximum_cap") is not None and value is not None and basis != "RATIO" and attrs["maximum_cap"] < value:
            raise serializers.ValidationError({"maximum_cap": "Maximum cap cannot be less than the benefit value."})
        return attrs


class OLQuotationRiderSelectionInputSerializer(serializers.Serializer):
    rider_id = serializers.UUIDField()
    plan_config_id = serializers.UUIDField(required=False, allow_null=True)
    rider_sum_assured = serializers.DecimalField(max_digits=18, decimal_places=2, min_value=Decimal("0.01"))
    rider_term_years = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    beneficial_type_id = serializers.UUIDField(
        required=False,
        allow_null=True,
        error_messages={
            "invalid": "Select a configured Benefit Type from the list. Do not submit the benefit name or code.",
        },
    )
    benefit_basis = serializers.ChoiceField(choices=["FIXED", "RATIO", "LOADED", "DISCOUNTED", "CAPPED"], required=False, default="FIXED")
    benefit_value = serializers.DecimalField(max_digits=18, decimal_places=2, min_value=Decimal("0"), required=False, allow_null=True)
    loading = serializers.DecimalField(max_digits=9, decimal_places=4, min_value=Decimal("0"), max_value=Decimal("100"), required=False, default=Decimal("0"))
    discount = serializers.DecimalField(max_digits=9, decimal_places=4, min_value=Decimal("0"), max_value=Decimal("100"), required=False, default=Decimal("0"))
    maximum_cap = serializers.DecimalField(max_digits=18, decimal_places=2, min_value=Decimal("0"), required=False, allow_null=True)
    benefits = OLQuotationBenefitInputSerializer(many=True, required=False, default=list)

    def validate(self, attrs):
        basis = attrs.get("benefit_basis", "FIXED")
        value = attrs.get("benefit_value")
        if basis == "RATIO" and (value is None or not 0 < value <= Decimal("100")):
            raise serializers.ValidationError({"benefit_value": "Ratio benefit value must be greater than 0 and no greater than 100 percent."})
        if basis == "CAPPED" and attrs.get("maximum_cap") is None:
            raise serializers.ValidationError({"maximum_cap": "A maximum cap is required for a capped benefit."})
        if attrs.get("maximum_cap") is not None and value is not None and basis != "RATIO" and attrs["maximum_cap"] < value:
            raise serializers.ValidationError({"maximum_cap": "Maximum cap cannot be less than the benefit value."})
        return attrs


class OLQuotationRidersConfigureSerializer(serializers.Serializer):
    selections = OLQuotationRiderSelectionInputSerializer(many=True, allow_empty=True, default=list)


class OLQuotationRiderStateSerializer(serializers.Serializer):
    plan_rows = serializers.ListField(child=serializers.DictField())
    available_benefit_types = serializers.ListField(child=serializers.DictField())
    requires_configuration = serializers.BooleanField()
    wizard_complete = serializers.BooleanField()


class OLQuotationRiderOptionsSerializer(serializers.Serializer):
    plan_configuration_id = serializers.UUIDField(allow_null=True)
    quotation_age = serializers.IntegerField(allow_null=True)
    quotation_currency = serializers.CharField()
    riders = OLQuotationRiderOptionSerializer(many=True)
    benefit_types = serializers.ListField(child=serializers.DictField())


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
    source_version_number = serializers.SerializerMethodField()
    template_code = serializers.SerializerMethodField()
    pdf_url = serializers.SerializerMethodField()
    html_url = serializers.SerializerMethodField()

    def get_source_version_number(self, obj):
        return obj.source_version.version_number if obj.source_version_id else None

    def get_template_code(self, obj):
        return obj.template.code if obj.template_id else None

    def get_pdf_url(self, obj):
        from django.core.files.storage import default_storage
        return default_storage.url(obj.file_reference) if obj.file_reference else None

    def get_html_url(self, obj):
        from django.core.files.storage import default_storage
        return default_storage.url(obj.html_reference) if obj.html_reference else None

    class Meta:
        model = OLQuotationDocument
        fields = [
            "id", "quotation", "source_version", "source_version_number", "template", "template_code",
            "template_version", "document_type", "file_reference", "html_reference", "pdf_url", "html_url",
            "mime_type", "status", "generated_by", "generated_at", "metadata", "created_at", "updated_at",
            "created_by", "updated_by",
        ]
        read_only_fields = fields


class OLQuotationVersionSerializer(ForeignKeyDisplayMixin, serializers.ModelSerializer):
    class Meta:
        model = OLQuotationVersion
        fields = "__all__"
        read_only_fields = [field.name for field in OLQuotationVersion._meta.fields]


class OLQuotationVersionListSerializer(ForeignKeyDisplayMixin, serializers.ModelSerializer):
    class Meta:
        model = OLQuotationVersion
        fields = ["id", "version_number", "status", "created_by", "created_at", "change_reason"]
        read_only_fields = fields


class OLQuotationProjectionRowSerializer(serializers.Serializer):
    plan_configuration_id = serializers.CharField(required=False, allow_null=True)
    policy_year = serializers.IntegerField()
    premiums_paid = serializers.DecimalField(max_digits=18, decimal_places=2)
    estimated_bonus = serializers.DecimalField(max_digits=18, decimal_places=2)
    surrender_value = serializers.DecimalField(max_digits=18, decimal_places=2)
    paid_up_value = serializers.DecimalField(max_digits=18, decimal_places=2)
    estimated_maturity_value = serializers.DecimalField(max_digits=18, decimal_places=2)


class OLQuotationInstallmentPayoutSerializer(serializers.Serializer):
    plan_configuration_id = serializers.CharField(required=False, allow_null=True)
    installment_configuration_id = serializers.CharField(required=False, allow_null=True)
    sequence = serializers.IntegerField()
    description = serializers.CharField(allow_blank=True, required=False)
    payout_amount = serializers.DecimalField(max_digits=18, decimal_places=2)
    payout_date = serializers.DateField()
    rate_percent = serializers.DecimalField(max_digits=9, decimal_places=4)
    paid_up_rate = serializers.DecimalField(max_digits=18, decimal_places=8, required=False)


class OLQuotationFinancialSummarySerializer(ForeignKeyDisplayMixin, serializers.ModelSerializer):
    quotation_id = serializers.UUIDField(read_only=True)

    class Meta:
        model = OLQuotationFinancialSummary
        fields = "__all__"
        read_only_fields = [field.name for field in OLQuotationFinancialSummary._meta.fields]


class OLQuotationFinancialDetailsSerializer(ForeignKeyDisplayMixin, serializers.ModelSerializer):
    quotation_id = serializers.UUIDField(read_only=True)
    projections = OLQuotationProjectionRowSerializer(many=True, read_only=True)
    installment_payouts = OLQuotationInstallmentPayoutSerializer(many=True, read_only=True)
    plan_breakdowns = serializers.SerializerMethodField()
    rider_breakdowns = serializers.SerializerMethodField()
    tax_breakdown = serializers.SerializerMethodField()

    class Meta:
        model = OLQuotationFinancialSummary
        fields = "__all__"
        read_only_fields = [field.name for field in OLQuotationFinancialSummary._meta.fields] + [
            "plan_breakdowns", "rider_breakdowns", "tax_breakdown",
        ]

    def _snapshot_section(self, obj, key):
        return (obj.calculation_snapshot or {}).get(key, [])

    def get_plan_breakdowns(self, obj):
        return self._snapshot_section(obj, "plan_breakdowns")

    def get_rider_breakdowns(self, obj):
        return self._snapshot_section(obj, "rider_breakdowns")

    def get_tax_breakdown(self, obj):
        return self._snapshot_section(obj, "tax_breakdown")


class OLQuotationCalculateSerializer(serializers.Serializer):
    """Calculation is derived entirely from the persisted quotation wizard state."""

    pass


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


class OLQuotationEventSerializer(ForeignKeyDisplayMixin, serializers.ModelSerializer):
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
            "location_display": (
                f"{quotation.location_master.code} — {quotation.location_master.name}"
                if quotation.location_master_id and quotation.location_master
                else quotation.location or None
            ),
            "agent_id": str(quotation.agent_partner_id) if quotation.agent_partner_id else None,
            "agent": {
                "id": str(quotation.agent_partner_id),
                "name": str(quotation.agent_partner),
                "partner_number": quotation.agent_partner.partner_number,
            } if quotation.agent_partner_id else None,
            "agent_display": _display_value(quotation.agent_partner or quotation.agent),
            "address": quotation.address,
            "partner_exists": bool(quotation.linked_partner_id or quotation.partner_id),
            "partner_id": str(quotation.linked_partner_id or quotation.partner_id) if (quotation.linked_partner_id or quotation.partner_id) else None,
            "compliant": bool(quotation.partner_verified),
        }
        return data


class OLQuotationListSerializer(ForeignKeyDisplayMixin, serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    agent_display = serializers.SerializerMethodField()
    location_display = serializers.SerializerMethodField()
    currency_display = serializers.SerializerMethodField()
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
            "agent_display",
            "location_display",
            "currency_display",
            "created_by",
            "row_actions",
        ]
        read_only_fields = fields

    @staticmethod
    def _user_payload(user):
        if not user:
            return None
        name = _display_value(user) or " ".join(
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

    def get_status(self, obj):
        return QuotationService.effective_status(obj)

    def get_status_badge(self, obj):
        effective_status = self.get_status(obj)
        label = dict(obj._meta.get_field("status").choices).get(effective_status, effective_status)
        return {"code": effective_status, "label": label, "tone": effective_status.lower()}

    def get_agent(self, obj):
        return self._user_payload(obj.agent_partner or obj.agent)

    def get_agent_display(self, obj):
        agent = obj.agent_partner or obj.agent
        return _display_value(agent)

    def get_location_display(self, obj):
        if obj.location_master_id and obj.location_master:
            return f"{obj.location_master.code} — {obj.location_master.name}"
        return obj.location or None

    def get_currency_display(self, obj):
        options = ConfigurationService.get_choice_list("CURRENCY_CHOICES", active_only=True)
        match = next((item for item in options if item.get("value") == obj.currency), None)
        return match.get("label") if match else obj.currency

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
        status = self.get_status(obj)
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


class OLQuotationSerializer(ForeignKeyDisplayMixin, serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    agent_display = serializers.SerializerMethodField()
    location_display = serializers.SerializerMethodField()
    currency_display = serializers.SerializerMethodField()
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
            "agent_display",
            "location_display",
            "currency_display",
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

    def get_status(self, obj):
        return QuotationService.effective_status(obj)

    def get_agent_display(self, obj):
        return _display_value(obj.agent_partner or obj.agent)

    def get_location_display(self, obj):
        if obj.location_master_id and obj.location_master:
            return f"{obj.location_master.code} — {obj.location_master.name}"
        return obj.location or None

    def get_currency_display(self, obj):
        options = ConfigurationService.get_choice_list("CURRENCY_CHOICES", active_only=True)
        match = next((item for item in options if item.get("value") == obj.currency), None)
        return match.get("label") if match else obj.currency

    def validate(self, attrs):
        instance = self.instance or OLQuotation(**attrs)
        for key, value in attrs.items():
            setattr(instance, key, value)
        try:
            instance.full_clean(exclude=["quote_number"] if not instance.quote_number else [])
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict)
        return attrs
