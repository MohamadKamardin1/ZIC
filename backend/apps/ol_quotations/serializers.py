from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

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
