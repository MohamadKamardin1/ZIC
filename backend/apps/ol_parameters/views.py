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
    OLAnticipatedEndowmentInstallmentRate,
    OLBeneficialType,
    OLComputationApproach,
    OLDefaultSystemParameter,
    OLGracePeriod,
    OLGracePeriodNotificationSchedule,
    OLHealthQuestion,
    OLHealthQuestionnaire,
    OLHealthQuestionnaireItem,
    OLMaturityClaimSetup,
    OLMemberCoverConfiguration,
    OLOverrideCommissionSetup,
    OLPaidUpRate,
    OLPaidUpSetup,
    OLCommitmentStatus,
    OLReinstatementWindow,
    OLSurrenderSetup,
    OLSurrenderValueRate,
    OLParameterTableRegistry,
    OLPolicyRenewalStatus,
    OLPolicyStatus,
)
from .permissions import HasOLParameterPermission, has_ol_parameter_permission
from .serializers import (
    OLAnticipatedEndowmentInstallmentRateSerializer,
    OLBeneficialTypeSerializer,
    OLComputationApproachSerializer,
    OLDefaultSystemParameterSerializer,
    OLGracePeriodSerializer,
    OLMaturityClaimSetupSerializer,
    OLMemberCoverConfigurationSerializer,
    OLOverrideCommissionSetupSerializer,
    OLPaidUpRateSerializer,
    OLPaidUpSetupSerializer,
    OLCommitmentStatusSerializer,
    OLSurrenderSetupSerializer,
    OLSurrenderValueRateSerializer,
    OLPolicyRenewalStatusSerializer,
    OLPolicyStatusSerializer,
    OLHealthQuestionSerializer,
    OLHealthQuestionnaireSerializer,
    OLHealthQuestionnaireItemSerializer,
    OLGracePeriodNotificationScheduleSerializer,
    OLReinstatementWindowSerializer,
    OLTableRegistrySerializer,
)
from .services.default_setup_service import OLDefaultSetupService
from .services.parameter_service import OLParameterService
from .services.policy_setup_service import OLPolicySetupService


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
