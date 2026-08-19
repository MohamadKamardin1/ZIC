from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

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
