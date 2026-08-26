import csv
import json

from django.http import HttpResponse
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.pagination import StandardPagination

from .models import (
    OLAgentCommissionSetup,
    OLAnticipatedEndowmentInstallmentRate,
    OLBeneficialType,
    OLBonusRate,
    OLCashSurrenderValue,
    OLClaimReason,
    OLClaimStatus,
    OLClaimType,
    OLCommitmentStatus,
    OLComputationApproach,
    OLCorrespondentType,
    OLDefaultSystemParameter,
    OLDischargeType,
    OLGracePeriod,
    OLGracePeriodNotificationSchedule,
    OLHealthQuestion,
    OLHealthQuestionnaire,
    OLHealthQuestionnaireItem,
    OLInstallmentChargeRate,
    OLInvestmentFund,
    OLInvestmentFundType,
    OLJointLifeSetup,
    OLLoanInterestControl,
    OLLoanSystemSetup,
    OLMaturityClaimSetup,
    OLMedicalCode,
    OLMedicalFacility,
    OLMedicalHistory,
    OLMedicalLimit,
    OLMedicalPractitioner,
    OLMemberCoverConfiguration,
    OLMortalityRateRow,
    OLMortalityRateTable,
    OLMortgageInterestFactor,
    OLOverrideCommissionSetup,
    OLPaidUpRate,
    OLPaidUpSetup,
    OLParameterTableRegistry,
    OLPersonalHabit,
    OLPlanOccupationRiskLimit,
    OLPlanRiskCategory,
    OLPlanTargetMarket,
    OLPlanTaxConfiguration,
    OLPlanType,
    OLPolicyRenewalStatus,
    OLPolicyStatus,
    OLPremiumRateRow,
    OLPremiumRateTable,
    OLProduct,
    OLReinstatementInterestRate,
    OLReinstatementWindow,
    OLReserveLoading,
    OLRiderRateRow,
    OLRiderRateTable,
    OLRiderSetup,
    OLSurrenderSetup,
    OLSurrenderValueRate,
)
from .permissions import HasOLParameterPermission, has_ol_parameter_permission
from .serializers import (
    OLAgentCommissionSetupSerializer,
    OLAnticipatedEndowmentInstallmentRateSerializer,
    OLBeneficialTypeSerializer,
    OLBonusRateSerializer,
    OLCashSurrenderValueSerializer,
    OLClaimReasonSerializer,
    OLClaimStatusSerializer,
    OLClaimTypeSerializer,
    OLCommitmentStatusSerializer,
    OLComputationApproachSerializer,
    OLCorrespondentTypeSerializer,
    OLDefaultSystemParameterSerializer,
    OLDischargeTypeSerializer,
    OLGracePeriodNotificationScheduleSerializer,
    OLGracePeriodSerializer,
    OLHealthQuestionnaireItemSerializer,
    OLHealthQuestionnaireSerializer,
    OLHealthQuestionSerializer,
    OLInstallmentChargeRateSerializer,
    OLInvestmentFundSerializer,
    OLInvestmentFundTypeSerializer,
    OLJointLifeSetupSerializer,
    OLLoanInterestControlSerializer,
    OLLoanSystemSetupSerializer,
    OLMaturityClaimSetupSerializer,
    OLMedicalCodeSerializer,
    OLMedicalFacilitySerializer,
    OLMedicalHistorySerializer,
    OLMedicalLimitSerializer,
    OLMedicalPractitionerSerializer,
    OLMemberCoverConfigurationSerializer,
    OLMortalityRateRowSerializer,
    OLMortalityRateTableSerializer,
    OLMortgageInterestFactorSerializer,
    OLOverrideCommissionSetupSerializer,
    OLPaidUpRateSerializer,
    OLPaidUpSetupSerializer,
    OLPersonalHabitSerializer,
    OLPlanOccupationRiskLimitSerializer,
    OLPlanRiskCategorySerializer,
    OLPlanTargetMarketSerializer,
    OLPlanTaxConfigurationSerializer,
    OLPlanTypeSerializer,
    OLPolicyRenewalStatusSerializer,
    OLPolicyStatusSerializer,
    OLPremiumRateRowSerializer,
    OLPremiumRateTableSerializer,
    OLProductSerializer,
    OLReinstatementInterestRateSerializer,
    OLReinstatementWindowSerializer,
    OLReserveLoadingSerializer,
    OLRiderRateRowSerializer,
    OLRiderRateTableSerializer,
    OLRiderSetupSerializer,
    OLSurrenderSetupSerializer,
    OLSurrenderValueRateSerializer,
    OLTableRegistrySerializer,
)
from .services.default_setup_service import OLDefaultSetupService
from .services.parameter_service import OLParameterService
from .services.policy_setup_service import OLPolicySetupService
from .services.rating_setup_service import OLRatingSetupService


class OLParameterTableRegistryViewSet(viewsets.ModelViewSet):
    """Declarative registry consumed by table-first OL parameter clients."""

    queryset = OLParameterTableRegistry.objects.select_related("created_by", "updated_by").all()
    serializer_class = OLTableRegistrySerializer
    pagination_class = StandardPagination
    permission_classes = [permissions.IsAuthenticated, HasOLParameterPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["slug", "label", "description", "parameter_group", "model_label"]
    filterset_fields = ["is_active", "parameter_group", "export_support", "model_label"]
    ordering_fields = ["slug", "label", "parameter_group", "created_at", "updated_at"]
    ordering = ["parameter_group", "label", "slug"]

    def get_queryset(self):
        queryset = super().get_queryset()
        if has_ol_parameter_permission(self.request.user, "configure"):
            return queryset
        return queryset.filter(is_active=True)

    def perform_create(self, serializer):
        instance = OLParameterService.create_registry(
            actor=self.request.user,
            data=serializer.validated_data,
            request=self.request,
        )
        serializer.instance = instance

    def perform_update(self, serializer):
        instance = OLParameterService.update_registry(
            actor=self.request.user,
            instance=self.get_object(),
            data=serializer.validated_data,
            request=self.request,
        )
        serializer.instance = instance

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        OLParameterService.deactivate_registry(actor=request.user, instance=instance, request=request)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], url_path="deactivate")
    def deactivate(self, request, *args, **kwargs):
        instance = self.get_object()
        OLParameterService.deactivate_registry(actor=request.user, instance=instance, request=request)
        return Response(self.get_serializer(instance).data, status=status.HTTP_200_OK)


class OLDefaultSetupViewSet(viewsets.ModelViewSet):
    """Shared table behavior for all OL Default Setup configuration entities."""

    model = None
    serializer_class = None
    pagination_class = StandardPagination
    permission_classes = [permissions.IsAuthenticated, HasOLParameterPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["code", "name", "description"]
    filterset_fields = ["is_active", "effective_from", "effective_to"]
    ordering_fields = ["code", "name", "is_active", "effective_from", "effective_to", "created_at", "updated_at"]
    ordering = ["name", "code"]
    table_slug = ""

    def get_queryset(self):
        queryset = self.model.objects.select_related("created_by", "updated_by").all()
        if not has_ol_parameter_permission(self.request.user, "configure"):
            queryset = queryset.filter(is_active=True)
        return queryset

    def perform_create(self, serializer):
        serializer.instance = OLDefaultSetupService.create(
            model=self.model,
            actor=self.request.user,
            data=serializer.validated_data,
            request=self.request,
        )

    def perform_update(self, serializer):
        serializer.instance = OLDefaultSetupService.update(
            model=self.model,
            actor=self.request.user,
            instance=self.get_object(),
            data=serializer.validated_data,
            request=self.request,
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        OLDefaultSetupService.deactivate(actor=request.user, instance=instance, request=request)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], url_path="deactivate")
    def deactivate(self, request, *args, **kwargs):
        instance = self.get_object()
        OLDefaultSetupService.deactivate(actor=request.user, instance=instance, request=request)
        return Response(self.get_serializer(instance).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="export")
    def export(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        payload = self.get_serializer(queryset, many=True).data
        fieldnames = list(payload[0].keys()) if payload else [field.name for field in self.model._meta.fields]
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{self.table_slug or self.model._meta.model_name}.csv"'
        writer = csv.DictWriter(response, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in payload:
            writer.writerow({
                key: json.dumps(value, default=str) if isinstance(value, (dict, list)) else value
                for key, value in row.items()
            })
        return response


class OLDefaultSystemParameterViewSet(OLDefaultSetupViewSet):
    model = OLDefaultSystemParameter
    serializer_class = OLDefaultSystemParameterSerializer
    table_slug = "default-system-parameters"
    search_fields = ["code", "parameter_key", "name", "parameter_category", "description"]
    filterset_fields = ["is_active", "parameter_category", "value_type", "effective_from", "effective_to"]
    ordering_fields = ["code", "parameter_key", "name", "parameter_category", "value_type", "is_active", "effective_from", "created_at", "updated_at"]
    ordering = ["parameter_category", "name", "parameter_key"]


class OLOverrideCommissionSetupViewSet(OLDefaultSetupViewSet):
    model = OLOverrideCommissionSetup
    serializer_class = OLOverrideCommissionSetupSerializer
    table_slug = "override-commission-setups"
    search_fields = ["code", "name", "description", "intermediary_type", "channel", "currency", "reason"]
    filterset_fields = [
        "is_active", "partner", "product", "plan", "rider", "branch", "intermediary_type", "channel", "currency",
        "rate_type", "priority", "effective_from", "effective_to",
    ]
    ordering_fields = ["priority", "code", "name", "rate_value", "rate_type", "effective_from", "effective_to", "created_at", "updated_at"]
    ordering = ["priority", "-effective_from", "code"]


class OLAgentCommissionSetupViewSet(OLDefaultSetupViewSet):
    model = OLAgentCommissionSetup
    serializer_class = OLAgentCommissionSetupSerializer
    table_slug = "agent-commission-setups"
    search_fields = [
        "code", "name", "description", "reason", "intermediary_type", "distribution_channel", "currency",
        "product__code", "plan__code", "rider__code", "partner__partner_number",
    ]
    filterset_fields = [
        "is_active", "partner", "product", "plan", "rider", "branch", "intermediary_type",
        "distribution_channel", "currency", "commission_type", "rate_type", "priority",
        "premium_year_from", "premium_year_to", "policy_year_from", "policy_year_to", "effective_from", "effective_to",
    ]
    ordering_fields = [
        "priority", "code", "name", "commission_type", "rate_value", "rate_type", "effective_from", "effective_to",
        "created_at", "updated_at",
    ]
    ordering = ["priority", "commission_type", "-effective_from", "code"]


class OLComputationApproachViewSet(OLDefaultSetupViewSet):
    model = OLComputationApproach
    serializer_class = OLComputationApproachSerializer
    table_slug = "computation-approaches"
    search_fields = ["code", "name", "description", "calculation_area", "calculation_basis", "formula_key"]
    filterset_fields = ["is_active", "calculation_area", "calculation_basis", "sequence", "effective_from", "effective_to"]
    ordering_fields = ["calculation_area", "sequence", "code", "name", "formula_key", "is_active", "effective_from", "created_at", "updated_at"]
    ordering = ["calculation_area", "sequence", "name", "code"]


class OLMaturityClaimSetupViewSet(OLDefaultSetupViewSet):
    model = OLMaturityClaimSetup
    serializer_class = OLMaturityClaimSetupSerializer
    table_slug = "maturity-claim-setups"
    search_fields = ["code", "name", "description", "default_payout_method", "maturity_claim_status_to_create"]
    filterset_fields = ["is_active", "product", "plan", "auto_create_maturity_claim", "require_documents", "require_approval", "effective_from", "effective_to"]
    ordering_fields = ["code", "name", "days_before_maturity_to_initiate", "notification_days", "is_active", "effective_from", "created_at", "updated_at"]
    ordering = ["-effective_from", "name", "code"]


class OLParameterHealthView(APIView):
    """Low-sensitivity readiness endpoint for the OL Parameters bounded context."""

    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response(
            {
                "status": "ok",
                "service": "ol_parameters",
                "timestamp": timezone.now(),
                "registry": {
                    "total": OLParameterTableRegistry.objects.count(),
                    "active": OLParameterTableRegistry.objects.filter(is_active=True).count(),
                },
                "default_setup": {
                    "default_system_parameters": OLDefaultSystemParameter.objects.filter(is_active=True).count(),
                    "override_commission_setups": OLOverrideCommissionSetup.objects.filter(is_active=True).count(),
                    "computation_approaches": OLComputationApproach.objects.filter(is_active=True).count(),
                    "maturity_claim_setups": OLMaturityClaimSetup.objects.filter(is_active=True).count(),
                },
                "policy_setup": {
                    "anticipated_endowment_rates": OLAnticipatedEndowmentInstallmentRate.objects.filter(is_active=True).count(),
                    "grace_periods": OLGracePeriod.objects.filter(is_active=True).count(),
                    "policy_statuses": OLPolicyStatus.objects.filter(is_active=True).count(),
                    "policy_renewal_statuses": OLPolicyRenewalStatus.objects.filter(is_active=True).count(),
                    "beneficial_types": OLBeneficialType.objects.filter(is_active=True).count(),
                    "member_cover_configurations": OLMemberCoverConfiguration.objects.filter(is_active=True).count(),
                },
                "policy_setup_part2": {
                    "surrender_setups": OLSurrenderSetup.objects.filter(is_active=True).count(),
                    "paid_up_setups": OLPaidUpSetup.objects.filter(is_active=True).count(),
                    "surrender_value_rates": OLSurrenderValueRate.objects.filter(is_active=True).count(),
                    "paid_up_rates": OLPaidUpRate.objects.filter(is_active=True).count(),
                    "commitment_statuses": OLCommitmentStatus.objects.filter(is_active=True).count(),
                },
                "policy_setup_part3": {
                    "health_questions": OLHealthQuestion.objects.filter(is_active=True).count(),
                    "health_questionnaires": OLHealthQuestionnaire.objects.filter(is_active=True).count(),
                    "health_questionnaire_items": OLHealthQuestionnaireItem.objects.filter(is_active=True).count(),
                    "grace_period_notification_schedules": OLGracePeriodNotificationSchedule.objects.filter(is_active=True).count(),
                    "reinstatement_windows": OLReinstatementWindow.objects.filter(is_active=True).count(),
                },
                "product_setup": {
                    "plan_types": OLPlanType.objects.filter(is_active=True).count(),
                    "products": OLProduct.objects.filter(is_active=True).count(),
                    "tax_configurations": OLPlanTaxConfiguration.objects.filter(is_active=True).count(),
                    "target_markets": OLPlanTargetMarket.objects.filter(is_active=True).count(),
                    "risk_categories": OLPlanRiskCategory.objects.filter(is_active=True).count(),
                    "occupation_risk_limits": OLPlanOccupationRiskLimit.objects.filter(is_active=True).count(),
                    "investment_fund_types": OLInvestmentFundType.objects.filter(is_active=True).count(),
                    "investment_funds": OLInvestmentFund.objects.filter(is_active=True).count(),
                },
                "product_rating_part1": {
                    "premium_rate_tables": OLPremiumRateTable.objects.filter(is_active=True).count(),
                    "premium_rate_rows": OLPremiumRateRow.objects.filter(is_active=True).count(),
                    "mortality_rate_tables": OLMortalityRateTable.objects.filter(is_active=True).count(),
                    "mortality_rate_rows": OLMortalityRateRow.objects.filter(is_active=True).count(),
                    "joint_life_setups": OLJointLifeSetup.objects.filter(is_active=True).count(),
                },
                "product_rating_part2": {
                    "reinstatement_interest_rates": OLReinstatementInterestRate.objects.filter(is_active=True).count(),
                    "bonus_rates": OLBonusRate.objects.filter(is_active=True).count(),
                    "mortgage_interest_factors": OLMortgageInterestFactor.objects.filter(is_active=True).count(),
                    "installment_charge_rates": OLInstallmentChargeRate.objects.filter(is_active=True).count(),
                    "cash_surrender_values": OLCashSurrenderValue.objects.filter(is_active=True).count(),
                    "reserve_loadings": OLReserveLoading.objects.filter(is_active=True).count(),
                },
                "rider_setup": {
                    "riders": OLRiderSetup.objects.filter(is_active=True).count(),
                    "rider_rate_tables": OLRiderRateTable.objects.filter(is_active=True).count(),
                    "rider_rate_rows": OLRiderRateRow.objects.filter(is_active=True).count(),
                },
                "agent_management": {
                    "agent_commission_setups": OLAgentCommissionSetup.objects.filter(is_active=True).count(),
                },
                "loan_setup": {
                    "loan_system_setups": OLLoanSystemSetup.objects.filter(is_active=True).count(),
                    "loan_interest_controls": OLLoanInterestControl.objects.filter(is_active=True).count(),
                },
                "medical_underwriting": {
                    "medical_codes": OLMedicalCode.objects.filter(is_active=True).count(),
                    "medical_limits": OLMedicalLimit.objects.filter(is_active=True).count(),
                    "personal_habits": OLPersonalHabit.objects.filter(is_active=True).count(),
                    "medical_history": OLMedicalHistory.objects.filter(is_active=True).count(),
                    "medical_facilities": OLMedicalFacility.objects.filter(is_active=True).count(),
                    "medical_practitioners": OLMedicalPractitioner.objects.filter(is_active=True).count(),
                },
                "claim_setup": {
                    "claim_types": OLClaimType.objects.filter(is_active=True).count(),
                    "claim_reasons": OLClaimReason.objects.filter(is_active=True).count(),
                    "claim_statuses": OLClaimStatus.objects.filter(is_active=True).count(),
                    "discharge_types": OLDischargeType.objects.filter(is_active=True).count(),
                    "correspondent_types": OLCorrespondentType.objects.filter(is_active=True).count(),
                },
            }
        )


class OLAnticipatedEndowmentInstallmentRateViewSet(OLDefaultSetupViewSet):
    model = OLAnticipatedEndowmentInstallmentRate
    serializer_class = OLAnticipatedEndowmentInstallmentRateSerializer
    table_slug = "anticipated-endowment-rates"
    search_fields = ["code", "name", "description", "installment_type", "frequency", "currency"]
    filterset_fields = [
        "is_active", "product", "plan", "installment_type", "frequency", "currency",
        "effective_from", "effective_to",
    ]
    ordering_fields = [
        "code", "name", "frequency", "rate_factor", "age_from", "term_from",
        "policy_year_from", "effective_from", "effective_to", "created_at", "updated_at",
    ]
    ordering = ["product", "plan", "frequency", "age_from", "term_from", "code"]


class OLGracePeriodViewSet(OLDefaultSetupViewSet):
    model = OLGracePeriod
    serializer_class = OLGracePeriodSerializer
    table_slug = "grace-periods"
    search_fields = ["code", "name", "description", "premium_frequency"]
    filterset_fields = [
        "is_active", "product", "plan", "premium_frequency", "grace_days", "warning_days",
        "pre_lapse_days", "lapse_days", "effective_from", "effective_to",
    ]
    ordering_fields = [
        "code", "name", "grace_days", "warning_days", "pre_lapse_days", "lapse_days",
        "effective_from", "effective_to", "created_at", "updated_at",
    ]
    ordering = ["product", "plan", "premium_frequency", "-effective_from", "code"]


class OLPolicyStatusViewSet(OLDefaultSetupViewSet):
    model = OLPolicyStatus
    serializer_class = OLPolicyStatusSerializer
    table_slug = "policy-statuses"
    search_fields = ["code", "name", "description", "badge_type"]
    filterset_fields = ["is_active", "is_terminal", "badge_type", "display_order"]
    ordering_fields = ["display_order", "code", "name", "badge_type", "is_terminal", "created_at", "updated_at"]
    ordering = ["display_order", "name", "code"]

    @action(detail=False, methods=["get"], url_path="validate-transitions")
    def validate_transitions(self, request, *args, **kwargs):
        return Response(OLPolicySetupService.validate_status_transitions())


class OLPolicyRenewalStatusViewSet(OLDefaultSetupViewSet):
    model = OLPolicyRenewalStatus
    serializer_class = OLPolicyRenewalStatusSerializer
    table_slug = "policy-renewal-statuses"
    search_fields = ["code", "name", "description", "renewal_action"]
    filterset_fields = ["is_active", "renewal_action", "display_order"]
    ordering_fields = ["display_order", "code", "name", "renewal_action", "created_at", "updated_at"]
    ordering = ["display_order", "name", "code"]


class OLBeneficialTypeViewSet(OLDefaultSetupViewSet):
    model = OLBeneficialType
    serializer_class = OLBeneficialTypeSerializer
    table_slug = "beneficial-types"
    search_fields = ["code", "name", "description", "category", "calculation_basis"]
    filterset_fields = ["is_active", "category", "calculation_basis", "allows_multiple"]
    ordering_fields = ["category", "code", "name", "default_ratio", "calculation_basis", "created_at", "updated_at"]
    ordering = ["category", "name", "code"]


class OLMemberCoverConfigurationViewSet(OLDefaultSetupViewSet):
    model = OLMemberCoverConfiguration
    serializer_class = OLMemberCoverConfigurationSerializer
    table_slug = "member-cover-configurations"
    search_fields = ["code", "name", "description", "cover_type", "member_relation", "premium_basis", "coverage_basis"]
    filterset_fields = [
        "is_active", "product", "plan", "cover_type", "member_relation", "min_age", "max_age",
        "waiting_period_days", "premium_basis", "coverage_basis", "effective_from", "effective_to",
    ]
    ordering_fields = [
        "code", "name", "cover_type", "member_relation", "min_age", "max_age",
        "waiting_period_days", "effective_from", "effective_to", "created_at", "updated_at",
    ]
    ordering = ["product", "plan", "cover_type", "member_relation", "min_age", "code"]


class OLSurrenderSetupViewSet(OLDefaultSetupViewSet):
    model = OLSurrenderSetup
    serializer_class = OLSurrenderSetupSerializer
    table_slug = "surrender-setups"
    search_fields = ["code", "name", "description", "surrender_charge_type"]
    filterset_fields = [
        "is_active", "product", "plan", "surrender_charge_type", "partial_surrender_allowed",
        "require_approval", "effective_from", "effective_to",
    ]
    ordering_fields = [
        "code", "name", "minimum_policy_months", "minimum_premiums_paid", "surrender_charge_value",
        "effective_from", "effective_to", "created_at", "updated_at",
    ]
    ordering = ["product", "plan", "-effective_from", "code"]


class OLPaidUpSetupViewSet(OLDefaultSetupViewSet):
    model = OLPaidUpSetup
    serializer_class = OLPaidUpSetupSerializer
    table_slug = "paid-up-setups"
    search_fields = ["code", "name", "description", "paidup_conversion_basis", "paidup_effective_rule"]
    filterset_fields = [
        "is_active", "product", "plan", "allow_paidup", "paidup_conversion_basis", "paidup_effective_rule",
        "effective_from", "effective_to",
    ]
    ordering_fields = [
        "code", "name", "minimum_policy_months", "minimum_premiums_paid", "allow_paidup",
        "effective_from", "effective_to", "created_at", "updated_at",
    ]
    ordering = ["product", "plan", "-effective_from", "code"]


class OLSurrenderValueRateViewSet(OLDefaultSetupViewSet):
    model = OLSurrenderValueRate
    serializer_class = OLSurrenderValueRateSerializer
    table_slug = "surrender-value-rates"
    search_fields = ["code", "name", "description", "table_code", "rate_table_version", "gender", "smoker_status"]
    filterset_fields = [
        "is_active", "product", "plan", "table_code", "rate_table_version", "gender", "smoker_status",
        "age_from", "age_to", "term_from", "term_to", "policy_year_from", "policy_year_to",
        "effective_from", "effective_to",
    ]
    ordering_fields = [
        "table_code", "rate_table_version", "code", "name", "rate_factor", "row_order", "age_from", "term_from",
        "policy_year_from", "effective_from", "effective_to", "created_at", "updated_at",
    ]
    ordering = ["table_code", "rate_table_version", "product", "plan", "row_order", "age_from", "term_from", "policy_year_from", "code"]


class OLPaidUpRateViewSet(OLDefaultSetupViewSet):
    model = OLPaidUpRate
    serializer_class = OLPaidUpRateSerializer
    table_slug = "paid-up-rates"
    search_fields = ["code", "name", "description", "table_code", "rate_table_version", "gender", "smoker_status"]
    filterset_fields = [
        "is_active", "product", "plan", "table_code", "rate_table_version", "gender", "smoker_status",
        "age_from", "age_to", "term_from", "term_to", "policy_year_from", "policy_year_to",
        "effective_from", "effective_to",
    ]
    ordering_fields = [
        "table_code", "rate_table_version", "code", "name", "rate_factor", "row_order", "age_from", "term_from",
        "policy_year_from", "effective_from", "effective_to", "created_at", "updated_at",
    ]
    ordering = ["table_code", "rate_table_version", "product", "plan", "row_order", "age_from", "term_from", "policy_year_from", "code"]


class OLCommitmentStatusViewSet(OLDefaultSetupViewSet):
    model = OLCommitmentStatus
    serializer_class = OLCommitmentStatusSerializer
    table_slug = "commitment-statuses"
    search_fields = ["code", "name", "description", "applies_to"]
    filterset_fields = ["is_active", "applies_to", "is_terminal", "display_order"]
    ordering_fields = ["applies_to", "display_order", "code", "name", "is_terminal", "created_at", "updated_at"]
    ordering = ["applies_to", "display_order", "name", "code"]


class OLHealthQuestionViewSet(OLDefaultSetupViewSet):
    model = OLHealthQuestion
    serializer_class = OLHealthQuestionSerializer
    table_slug = "health-questions"
    search_fields = ["code", "name", "description", "question_text", "category", "answer_type", "underwriting_impact"]
    filterset_fields = ["is_active", "category", "answer_type", "underwriting_impact", "requires_medical_followup"]
    ordering_fields = ["category", "code", "name", "answer_type", "underwriting_impact", "requires_medical_followup", "created_at", "updated_at"]
    ordering = ["category", "name", "code"]


class OLHealthQuestionnaireViewSet(OLDefaultSetupViewSet):
    model = OLHealthQuestionnaire
    serializer_class = OLHealthQuestionnaireSerializer
    table_slug = "health-questionnaires"
    search_fields = ["code", "name", "description", "applies_to_scope", "scheme_code", "version"]
    filterset_fields = [
        "is_active", "applies_to_scope", "product", "plan", "scheme_code", "version",
        "age_threshold", "effective_from", "effective_to",
    ]
    ordering_fields = [
        "code", "name", "applies_to_scope", "version", "sum_assured_threshold", "age_threshold",
        "effective_from", "effective_to", "created_at", "updated_at",
    ]
    ordering = ["code", "-effective_from", "version"]


class OLHealthQuestionnaireItemViewSet(OLDefaultSetupViewSet):
    model = OLHealthQuestionnaireItem
    serializer_class = OLHealthQuestionnaireItemSerializer
    table_slug = "health-questionnaire-items"
    search_fields = ["code", "name", "description", "questionnaire__code", "questionnaire__name", "health_question__code", "health_question__question_text"]
    filterset_fields = ["is_active", "questionnaire", "health_question", "sequence", "mandatory", "trigger_medical_requirement"]
    ordering_fields = ["questionnaire", "sequence", "code", "name", "mandatory", "trigger_medical_requirement", "score", "created_at", "updated_at"]
    ordering = ["questionnaire", "sequence", "code"]


class OLGracePeriodNotificationScheduleViewSet(OLDefaultSetupViewSet):
    model = OLGracePeriodNotificationSchedule
    serializer_class = OLGracePeriodNotificationScheduleSerializer
    table_slug = "grace-period-notification-schedules"
    search_fields = ["code", "name", "description", "event_type", "notification_channel", "recipient_type", "template_code"]
    filterset_fields = [
        "is_active", "event_type", "days_offset", "notification_channel", "recipient_type",
        "template_code", "effective_from", "effective_to",
    ]
    ordering_fields = [
        "event_type", "days_offset", "code", "name", "notification_channel", "recipient_type",
        "effective_from", "effective_to", "created_at", "updated_at",
    ]
    ordering = ["event_type", "days_offset", "code"]


class OLReinstatementWindowViewSet(OLDefaultSetupViewSet):
    model = OLReinstatementWindow
    serializer_class = OLReinstatementWindowSerializer
    table_slug = "reinstatement-windows"
    search_fields = ["code", "name", "description"]
    filterset_fields = [
        "is_active", "product", "plan", "days_after_lapse", "maximum_reinstatements",
        "require_medical_underwriting", "require_outstanding_premium_payment", "effective_from", "effective_to",
    ]
    ordering_fields = [
        "code", "name", "days_after_lapse", "maximum_reinstatements", "interest_rate", "penalty_rate",
        "effective_from", "effective_to", "created_at", "updated_at",
    ]
    ordering = ["product", "plan", "-effective_from", "code"]



class OLPlanTypeViewSet(OLDefaultSetupViewSet):
    model = OLPlanType
    serializer_class = OLPlanTypeSerializer
    table_slug = "plan-types"
    search_fields = ["code", "name", "description", "plan_category"]
    filterset_fields = ["is_active", "plan_category"]
    ordering_fields = ["code", "name", "plan_category", "is_active", "created_at", "updated_at"]
    ordering = ["name", "code"]


class OLProductViewSet(OLDefaultSetupViewSet):
    model = OLProduct
    serializer_class = OLProductSerializer
    table_slug = "products"
    search_fields = ["code", "name", "description", "currency", "insurance_class"]
    filterset_fields = ["is_active", "plan_type", "insurance_class", "currency", "investment_linked", "effective_from", "effective_to"]
    ordering_fields = ["code", "name", "plan_type", "insurance_class", "currency", "is_active", "effective_from", "effective_to", "created_at", "updated_at"]
    ordering = ["name", "code"]


class OLPlanTaxConfigurationViewSet(OLDefaultSetupViewSet):
    model = OLPlanTaxConfiguration
    serializer_class = OLPlanTaxConfigurationSerializer
    table_slug = "plan-tax-configurations"
    search_fields = ["code", "name", "description", "tax_type", "tax_basis", "apply_on", "country_or_branch"]
    filterset_fields = ["is_active", "product", "plan", "tax_type", "tax_basis", "rate_type", "sequence", "country_or_branch", "effective_from", "effective_to"]
    ordering_fields = ["code", "name", "sequence", "rate_value", "effective_from", "effective_to", "created_at", "updated_at"]
    ordering = ["product", "plan", "sequence", "code"]


class OLPlanTargetMarketViewSet(OLDefaultSetupViewSet):
    model = OLPlanTargetMarket
    serializer_class = OLPlanTargetMarketSerializer
    table_slug = "plan-target-markets"
    search_fields = ["code", "name", "description", "target_market_type", "residency_requirement"]
    filterset_fields = ["is_active", "product", "plan", "target_market_type", "residency_requirement", "effective_from", "effective_to"]
    ordering_fields = ["code", "name", "target_market_type", "min_age", "max_age", "effective_from", "effective_to", "created_at", "updated_at"]
    ordering = ["product", "plan", "target_market_type", "code"]


class OLPlanRiskCategoryViewSet(OLDefaultSetupViewSet):
    model = OLPlanRiskCategory
    serializer_class = OLPlanRiskCategorySerializer
    table_slug = "plan-risk-categories"
    search_fields = ["code", "name", "description", "underwriting_class", "loading_basis"]
    filterset_fields = ["is_active", "product", "plan", "underwriting_class", "loading_basis", "effective_from", "effective_to"]
    ordering_fields = ["code", "name", "underwriting_class", "loading_basis", "effective_from", "effective_to", "created_at", "updated_at"]
    ordering = ["product", "plan", "underwriting_class", "code"]


class OLPlanOccupationRiskLimitViewSet(OLDefaultSetupViewSet):
    model = OLPlanOccupationRiskLimit
    serializer_class = OLPlanOccupationRiskLimitSerializer
    table_slug = "plan-occupation-risk-limits"
    search_fields = ["code", "name", "description", "occupation_risk_category"]
    filterset_fields = ["is_active", "product", "plan", "occupation_risk_category", "exclusion_flag", "effective_from", "effective_to"]
    ordering_fields = ["code", "name", "occupation_risk_category", "max_sum_assured", "loading_rate", "effective_from", "effective_to", "created_at", "updated_at"]
    ordering = ["product", "plan", "occupation_risk_category", "code"]


class OLInvestmentFundTypeViewSet(OLDefaultSetupViewSet):
    model = OLInvestmentFundType
    serializer_class = OLInvestmentFundTypeSerializer
    table_slug = "investment-fund-types"
    search_fields = ["code", "name", "description", "risk_profile"]
    filterset_fields = ["is_active", "risk_profile"]
    ordering_fields = ["code", "name", "risk_profile", "is_active", "created_at", "updated_at"]
    ordering = ["name", "code"]


class OLInvestmentFundViewSet(OLDefaultSetupViewSet):
    model = OLInvestmentFund
    serializer_class = OLInvestmentFundSerializer
    table_slug = "investment-funds"
    search_fields = ["code", "name", "description", "currency", "valuation_frequency"]
    filterset_fields = ["is_active", "fund_type", "currency", "valuation_frequency", "effective_from", "effective_to"]
    ordering_fields = ["code", "name", "fund_type", "currency", "valuation_frequency", "unit_price", "effective_from", "effective_to", "created_at", "updated_at"]
    ordering = ["name", "code"]


class OLPremiumRateTableViewSet(OLDefaultSetupViewSet):
    model = OLPremiumRateTable
    serializer_class = OLPremiumRateTableSerializer
    table_slug = "premium-rate-tables"
    search_fields = ["table_code", "name", "description", "rating_basis", "currency", "version", "product__code", "plan__code"]
    filterset_fields = ["is_active", "product", "plan", "rating_basis", "currency", "version", "effective_from", "effective_to"]
    ordering_fields = ["table_code", "name", "version", "rating_basis", "effective_from", "effective_to", "created_at", "updated_at"]
    ordering = ["table_code", "-effective_from", "version"]


class OLPremiumRateRowViewSet(OLDefaultSetupViewSet):
    model = OLPremiumRateRow
    serializer_class = OLPremiumRateRowSerializer
    table_slug = "premium-rate-rows"
    search_fields = ["code", "name", "description", "table__table_code", "table__version", "gender", "smoker_status", "frequency", "rate_unit"]
    filterset_fields = [
        "is_active", "table", "gender", "smoker_status", "age_from", "age_to", "term_from", "term_to",
        "frequency", "rate_unit", "effective_from", "effective_to",
    ]
    ordering_fields = [
        "code", "name", "table", "gender", "smoker_status", "frequency", "age_from", "term_from",
        "sum_assured_band_from", "rate", "effective_from", "effective_to", "created_at", "updated_at",
    ]
    ordering = ["table", "gender", "smoker_status", "frequency", "age_from", "term_from", "code"]


class OLMortalityRateTableViewSet(OLDefaultSetupViewSet):
    model = OLMortalityRateTable
    serializer_class = OLMortalityRateTableSerializer
    table_slug = "mortality-rate-tables"
    search_fields = ["table_code", "name", "description", "version"]
    filterset_fields = ["is_active", "version", "effective_from", "effective_to"]
    ordering_fields = ["table_code", "name", "version", "effective_from", "effective_to", "created_at", "updated_at"]
    ordering = ["table_code", "-effective_from", "version"]


class OLMortalityRateRowViewSet(OLDefaultSetupViewSet):
    model = OLMortalityRateRow
    serializer_class = OLMortalityRateRowSerializer
    table_slug = "mortality-rate-rows"
    search_fields = ["code", "name", "description", "table__table_code", "table__version", "gender", "smoker_status"]
    filterset_fields = ["is_active", "table", "age", "gender", "smoker_status", "policy_year", "effective_from", "effective_to"]
    ordering_fields = ["table", "age", "gender", "smoker_status", "policy_year", "mortality_rate", "created_at", "updated_at"]
    ordering = ["table", "age", "gender", "smoker_status", "policy_year", "code"]

    @action(detail=False, methods=["post"], url_path="bulk-import")
    def bulk_import(self, request, *args, **kwargs):
        payload = request.data.get("rows") if isinstance(request.data, dict) else None
        if not isinstance(payload, list) or not payload:
            return Response({"detail": "Request body must contain a non-empty rows list."}, status=status.HTTP_400_BAD_REQUEST)
        validated_rows = []
        for row in payload:
            serializer = self.get_serializer(data=row)
            serializer.is_valid(raise_exception=True)
            validated_rows.append(serializer.validated_data)
        instances = OLRatingSetupService.bulk_create_rows(
            model=self.model,
            actor=request.user,
            rows=validated_rows,
            request=request,
        )
        return Response(self.get_serializer(instances, many=True).data, status=status.HTTP_201_CREATED)


class OLJointLifeSetupViewSet(OLDefaultSetupViewSet):
    model = OLJointLifeSetup
    serializer_class = OLJointLifeSetupSerializer
    table_slug = "joint-life-setups"
    search_fields = ["code", "name", "description", "joint_life_type", "age_basis", "survivor_benefit_rule", "underwriting_rule"]
    filterset_fields = ["is_active", "product", "plan", "joint_life_type", "age_basis", "effective_from", "effective_to"]
    ordering_fields = ["code", "name", "joint_life_type", "age_basis", "premium_adjustment_factor", "effective_from", "effective_to", "created_at", "updated_at"]
    ordering = ["product", "plan", "joint_life_type", "-effective_from", "code"]


class OLReinstatementInterestRateViewSet(OLDefaultSetupViewSet):
    model = OLReinstatementInterestRate
    serializer_class = OLReinstatementInterestRateSerializer
    table_slug = "reinstatement-interest-rates"
    search_fields = ["code", "name", "description", "calculation_basis"]
    filterset_fields = ["is_active", "product", "plan", "calculation_basis", "effective_from", "effective_to"]
    ordering_fields = ["code", "name", "rate", "calculation_basis", "effective_from", "effective_to", "created_at", "updated_at"]
    ordering = ["product", "plan", "calculation_basis", "-effective_from", "code"]


class OLBonusRateViewSet(OLDefaultSetupViewSet):
    model = OLBonusRate
    serializer_class = OLBonusRateSerializer
    table_slug = "bonus-rates"
    search_fields = ["code", "name", "description", "bonus_type", "declaration_frequency"]
    filterset_fields = ["is_active", "product", "plan", "bonus_type", "valuation_year", "declaration_frequency", "effective_from", "effective_to"]
    ordering_fields = ["code", "name", "bonus_type", "rate", "valuation_year", "declaration_frequency", "effective_from", "effective_to", "created_at", "updated_at"]
    ordering = ["product", "plan", "bonus_type", "valuation_year", "-effective_from", "code"]


class OLMortgageInterestFactorViewSet(OLDefaultSetupViewSet):
    model = OLMortgageInterestFactor
    serializer_class = OLMortgageInterestFactorSerializer
    table_slug = "mortgage-interest-factors"
    search_fields = ["code", "name", "description", "calculation_basis", "product__code", "plan__code"]
    filterset_fields = ["is_active", "product", "plan", "calculation_basis", "effective_from", "effective_to"]
    ordering_fields = ["code", "name", "factor", "calculation_basis", "effective_from", "effective_to", "created_at", "updated_at"]
    ordering = ["product", "plan", "calculation_basis", "-effective_from", "code"]


class OLInstallmentChargeRateViewSet(OLDefaultSetupViewSet):
    model = OLInstallmentChargeRate
    serializer_class = OLInstallmentChargeRateSerializer
    table_slug = "installment-charge-rates"
    search_fields = ["code", "name", "description", "frequency", "charge_type", "apply_on"]
    filterset_fields = ["is_active", "product", "plan", "frequency", "charge_type", "apply_on", "effective_from", "effective_to"]
    ordering_fields = ["code", "name", "frequency", "charge_type", "apply_on", "rate_value", "effective_from", "effective_to", "created_at", "updated_at"]
    ordering = ["product", "plan", "frequency", "charge_type", "apply_on", "-effective_from", "code"]


class OLCashSurrenderValueViewSet(OLDefaultSetupViewSet):
    model = OLCashSurrenderValue
    serializer_class = OLCashSurrenderValueSerializer
    table_slug = "cash-surrender-values"
    search_fields = ["code", "name", "description", "gender", "smoker_status", "product__code", "plan__code"]
    filterset_fields = [
        "is_active", "product", "plan", "policy_year_from", "policy_year_to", "age_from", "age_to",
        "term_from", "term_to", "gender", "smoker_status", "effective_from", "effective_to",
    ]
    ordering_fields = [
        "code", "name", "policy_year_from", "policy_year_to", "age_from", "age_to", "term_from", "term_to",
        "surrender_value_factor", "rate", "effective_from", "effective_to", "created_at", "updated_at",
    ]
    ordering = ["product", "plan", "policy_year_from", "age_from", "term_from", "code"]


class OLReserveLoadingViewSet(OLDefaultSetupViewSet):
    model = OLReserveLoading
    serializer_class = OLReserveLoadingSerializer
    table_slug = "reserve-loadings"
    search_fields = ["code", "name", "description", "loading_type", "loading_basis"]
    filterset_fields = ["is_active", "product", "plan", "loading_type", "loading_basis", "effective_from", "effective_to"]
    ordering_fields = ["code", "name", "loading_type", "loading_basis", "rate_value", "effective_from", "effective_to", "created_at", "updated_at"]
    ordering = ["product", "plan", "loading_type", "loading_basis", "-effective_from", "code"]


class OLRiderSetupViewSet(OLDefaultSetupViewSet):
    model = OLRiderSetup
    serializer_class = OLRiderSetupSerializer
    table_slug = "rider-setups"
    search_fields = [
        "code", "name", "description", "rider_category", "benefit_type", "calculation_basis",
        "product__code", "plan__code",
    ]
    filterset_fields = [
        "is_active", "rider_category", "benefit_type", "calculation_basis", "product", "plan",
        "allows_standalone", "requires_underwriting", "effective_from", "effective_to",
    ]
    ordering_fields = [
        "code", "name", "rider_category", "benefit_type", "calculation_basis", "min_age", "max_age",
        "min_term", "max_term", "min_sum_assured", "max_sum_assured", "waiting_period_days",
        "effective_from", "effective_to", "created_at", "updated_at",
    ]
    ordering = ["rider_category", "benefit_type", "name", "code"]


class OLRiderRateTableViewSet(OLDefaultSetupViewSet):
    model = OLRiderRateTable
    serializer_class = OLRiderRateTableSerializer
    table_slug = "rider-rate-tables"
    search_fields = [
        "table_code", "name", "description", "rating_basis", "version", "rider__code", "rider__name",
        "product__code", "plan__code",
    ]
    filterset_fields = ["is_active", "rider", "product", "plan", "rating_basis", "version", "effective_from", "effective_to"]
    ordering_fields = ["table_code", "name", "rider", "version", "rating_basis", "effective_from", "effective_to", "created_at", "updated_at"]
    ordering = ["table_code", "rider", "-effective_from", "version"]


class OLRiderRateRowViewSet(OLDefaultSetupViewSet):
    model = OLRiderRateRow
    serializer_class = OLRiderRateRowSerializer
    table_slug = "rider-rate-rows"
    search_fields = [
        "code", "name", "description", "table__table_code", "table__version", "table__rider__code",
        "gender", "smoker_status", "frequency", "rate_unit",
    ]
    filterset_fields = [
        "is_active", "table", "table__rider", "gender", "smoker_status", "age_from", "age_to",
        "term_from", "term_to", "frequency", "rate_unit", "effective_from", "effective_to",
    ]
    ordering_fields = [
        "code", "name", "table", "gender", "smoker_status", "frequency", "age_from", "term_from",
        "sum_assured_band_from", "rate", "effective_from", "effective_to", "created_at", "updated_at",
    ]
    ordering = ["table", "gender", "smoker_status", "frequency", "age_from", "term_from", "code"]


class OLLoanSystemSetupViewSet(OLDefaultSetupViewSet):
    model = OLLoanSystemSetup
    serializer_class = OLLoanSystemSetupSerializer
    table_slug = "loan-system-setups"
    search_fields = [
        "code", "name", "description", "loan_basis", "loan_currency",
        "effect_on_claim", "effect_on_surrender", "effect_on_maturity",
        "product__code", "plan__code",
    ]
    filterset_fields = [
        "is_active", "product", "plan", "allow_policy_loans", "loan_basis", "loan_currency",
        "auto_deduct_from_benefits", "require_approval", "effect_on_claim", "effect_on_surrender",
        "effect_on_maturity", "effective_from", "effective_to",
    ]
    ordering_fields = [
        "code", "name", "loan_basis", "max_loan_percentage_of_cash_value", "min_loan_amount",
        "max_loan_amount", "loan_currency", "effective_from", "effective_to", "created_at", "updated_at",
    ]
    ordering = ["product", "plan", "-effective_from", "code"]


class OLLoanInterestControlViewSet(OLDefaultSetupViewSet):
    model = OLLoanInterestControl
    serializer_class = OLLoanInterestControlSerializer
    table_slug = "loan-interest-controls"
    search_fields = [
        "code", "name", "description", "compounding_frequency", "interest_calculation_basis",
        "interest_suspension_rule", "product__code", "plan__code",
    ]
    filterset_fields = [
        "is_active", "product", "plan", "compounding_frequency", "interest_calculation_basis",
        "capitalize_interest", "effective_from", "effective_to",
    ]
    ordering_fields = [
        "code", "name", "interest_rate", "compounding_frequency", "interest_calculation_basis",
        "grace_period_days", "penalty_interest_rate", "effective_from", "effective_to", "created_at", "updated_at",
    ]
    ordering = ["product", "plan", "-effective_from", "code"]


class OLMedicalCodeViewSet(OLDefaultSetupViewSet):
    model = OLMedicalCode
    serializer_class = OLMedicalCodeSerializer
    table_slug = "medical-codes"
    search_fields = ["code", "name", "description", "medical_category"]
    filterset_fields = ["is_active", "medical_category", "effective_from", "effective_to"]
    ordering_fields = ["code", "name", "medical_category", "is_active", "effective_from", "effective_to", "created_at", "updated_at"]
    ordering = ["medical_category", "name", "code"]


class OLMedicalLimitViewSet(OLDefaultSetupViewSet):
    model = OLMedicalLimit
    serializer_class = OLMedicalLimitSerializer
    table_slug = "medical-limits"
    search_fields = [
        "code", "name", "description", "medical_code__code", "medical_code__name",
        "limit_type", "required_frequency", "product__code", "plan__code",
    ]
    filterset_fields = [
        "is_active", "medical_code", "product", "plan", "limit_type", "required_frequency",
        "mandatory_flag", "age_from", "age_to", "effective_from", "effective_to",
    ]
    ordering_fields = [
        "code", "name", "medical_code", "product", "plan", "age_from", "age_to",
        "sum_assured_from", "sum_assured_to", "limit_type", "required_frequency", "limit_amount",
        "effective_from", "effective_to", "created_at", "updated_at",
    ]
    ordering = ["medical_code", "product", "plan", "age_from", "sum_assured_from", "-effective_from", "code"]


class OLPersonalHabitViewSet(OLDefaultSetupViewSet):
    model = OLPersonalHabit
    serializer_class = OLPersonalHabitSerializer
    table_slug = "personal-habits"
    search_fields = ["code", "name", "description", "habit_category", "question_text", "underwriting_impact"]
    filterset_fields = ["is_active", "habit_category", "underwriting_impact", "requires_evidence", "effective_from", "effective_to"]
    ordering_fields = ["code", "name", "habit_category", "underwriting_impact", "requires_evidence", "effective_from", "effective_to", "created_at", "updated_at"]
    ordering = ["habit_category", "name", "code"]


class OLMedicalHistoryViewSet(OLDefaultSetupViewSet):
    model = OLMedicalHistory
    serializer_class = OLMedicalHistorySerializer
    table_slug = "medical-history"
    search_fields = ["code", "name", "description", "condition_category", "severity", "underwriting_note"]
    filterset_fields = ["is_active", "condition_category", "severity", "waiting_period_days", "exclusion_flag", "loading_flag", "effective_from", "effective_to"]
    ordering_fields = ["code", "name", "condition_category", "severity", "waiting_period_days", "exclusion_flag", "loading_flag", "effective_from", "effective_to", "created_at", "updated_at"]
    ordering = ["condition_category", "severity", "name", "code"]


class OLMedicalFacilityViewSet(OLDefaultSetupViewSet):
    model = OLMedicalFacility
    serializer_class = OLMedicalFacilitySerializer
    table_slug = "medical-facilities"
    search_fields = [
        "code", "name", "description", "facility_code", "facility_type", "registration_number",
        "address", "city", "country", "contact_email", "contact_phone", "partner__partner_number", "partner__legal_name",
    ]
    filterset_fields = ["is_active", "partner", "facility_type", "approval_status", "city", "country", "effective_from", "effective_to"]
    ordering_fields = ["code", "name", "facility_code", "facility_type", "city", "country", "approval_status", "effective_from", "effective_to", "created_at", "updated_at"]
    ordering = ["name", "facility_code"]


class OLMedicalPractitionerViewSet(OLDefaultSetupViewSet):
    model = OLMedicalPractitioner
    serializer_class = OLMedicalPractitionerSerializer
    table_slug = "medical-practitioners"
    search_fields = [
        "code", "name", "description", "practitioner_code", "first_name", "last_name", "specialty",
        "license_number", "email", "phone", "partner__partner_number", "partner__legal_name", "medical_facility__facility_code",
    ]
    filterset_fields = ["is_active", "partner", "medical_facility", "specialty", "approval_status", "effective_from", "effective_to"]
    ordering_fields = ["code", "name", "practitioner_code", "first_name", "last_name", "specialty", "license_number", "approval_status", "effective_from", "effective_to", "created_at", "updated_at"]
    ordering = ["last_name", "first_name", "practitioner_code"]


# End of OL Medical Underwriting viewsets


class OLClaimTypeViewSet(OLDefaultSetupViewSet):
    model = OLClaimType
    serializer_class = OLClaimTypeSerializer
    table_slug = "claim-types"
    search_fields = [
        "code", "name", "description", "claim_category", "calculation_basis", "duplicate_check_rule",
    ]
    filterset_fields = [
        "is_active", "claim_category", "calculation_basis", "duplicate_check_rule",
        "allow_waiver_of_premium", "require_approval", "effective_from", "effective_to",
    ]
    ordering_fields = [
        "code", "name", "claim_category", "calculation_basis", "duplicate_check_rule",
        "waiting_period_days", "effective_from", "effective_to", "created_at", "updated_at",
    ]
    ordering = ["claim_category", "name", "code"]


class OLClaimReasonViewSet(OLDefaultSetupViewSet):
    model = OLClaimReason
    serializer_class = OLClaimReasonSerializer
    table_slug = "claim-reasons"
    search_fields = ["code", "name", "description", "reason_category", "claim_type__code", "claim_type__name"]
    filterset_fields = ["is_active", "claim_type", "reason_category", "effective_from", "effective_to"]
    ordering_fields = ["code", "name", "claim_type", "reason_category", "effective_from", "effective_to", "created_at", "updated_at"]
    ordering = ["reason_category", "claim_type", "name", "code"]


class OLClaimStatusViewSet(OLDefaultSetupViewSet):
    model = OLClaimStatus
    serializer_class = OLClaimStatusSerializer
    table_slug = "claim-statuses"
    search_fields = ["code", "name", "description", "badge_type"]
    filterset_fields = ["is_active", "badge_type", "is_terminal", "is_payable", "effective_from", "effective_to"]
    ordering_fields = ["code", "name", "display_order", "badge_type", "is_terminal", "is_payable", "effective_from", "effective_to", "created_at", "updated_at"]
    ordering = ["display_order", "name", "code"]


class OLDischargeTypeViewSet(OLDefaultSetupViewSet):
    model = OLDischargeType
    serializer_class = OLDischargeTypeSerializer
    table_slug = "discharge-types"
    search_fields = ["code", "name", "description", "discharge_category", "template_code"]
    filterset_fields = ["is_active", "discharge_category", "template_code", "effective_from", "effective_to"]
    ordering_fields = ["code", "name", "discharge_category", "template_code", "effective_from", "effective_to", "created_at", "updated_at"]
    ordering = ["discharge_category", "name", "code"]


class OLCorrespondentTypeViewSet(OLDefaultSetupViewSet):
    model = OLCorrespondentType
    serializer_class = OLCorrespondentTypeSerializer
    table_slug = "correspondent-types"
    search_fields = ["code", "name", "description", "correspondence_category", "communication_channel", "purpose"]
    filterset_fields = ["is_active", "correspondence_category", "communication_channel", "effective_from", "effective_to"]
    ordering_fields = ["code", "name", "correspondence_category", "communication_channel", "purpose", "effective_from", "effective_to", "created_at", "updated_at"]
    ordering = ["correspondence_category", "name", "code"]
