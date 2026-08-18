from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    OLAnticipatedEndowmentInstallmentRateViewSet,
    OLBeneficialTypeViewSet,
    OLComputationApproachViewSet,
    OLDefaultSystemParameterViewSet,
    OLGracePeriodViewSet,
    OLMaturityClaimSetupViewSet,
    OLMemberCoverConfigurationViewSet,
    OLOverrideCommissionSetupViewSet,
    OLPaidUpRateViewSet,
    OLPaidUpSetupViewSet,
    OLCommitmentStatusViewSet,
    OLSurrenderSetupViewSet,
    OLSurrenderValueRateViewSet,
    OLParameterHealthView,
    OLParameterTableRegistryViewSet,
    OLPolicyRenewalStatusViewSet,
    OLPolicyStatusViewSet,
    OLHealthQuestionViewSet,
    OLHealthQuestionnaireViewSet,
    OLHealthQuestionnaireItemViewSet,
    OLGracePeriodNotificationScheduleViewSet,
    OLReinstatementWindowViewSet,
)


router = DefaultRouter()
router.register("tables", OLParameterTableRegistryViewSet, basename="ol-parameter-table")
router.register("default-system-parameters", OLDefaultSystemParameterViewSet, basename="ol-default-system-parameter")
router.register("override-commission-setups", OLOverrideCommissionSetupViewSet, basename="ol-override-commission-setup")
router.register("computation-approaches", OLComputationApproachViewSet, basename="ol-computation-approach")
router.register("maturity-claim-setups", OLMaturityClaimSetupViewSet, basename="ol-maturity-claim-setup")
router.register("anticipated-endowment-rates", OLAnticipatedEndowmentInstallmentRateViewSet, basename="ol-anticipated-endowment-rate")
router.register("grace-periods", OLGracePeriodViewSet, basename="ol-grace-period")
router.register("policy-statuses", OLPolicyStatusViewSet, basename="ol-policy-status")
router.register("policy-renewal-statuses", OLPolicyRenewalStatusViewSet, basename="ol-policy-renewal-status")
router.register("beneficial-types", OLBeneficialTypeViewSet, basename="ol-beneficial-type")
router.register("member-cover-configurations", OLMemberCoverConfigurationViewSet, basename="ol-member-cover-configuration")
router.register("surrender-setups", OLSurrenderSetupViewSet, basename="ol-surrender-setup")
router.register("paid-up-setups", OLPaidUpSetupViewSet, basename="ol-paid-up-setup")
router.register("surrender-value-rates", OLSurrenderValueRateViewSet, basename="ol-surrender-value-rate")
router.register("paid-up-rates", OLPaidUpRateViewSet, basename="ol-paid-up-rate")
router.register("commitment-statuses", OLCommitmentStatusViewSet, basename="ol-commitment-status")
router.register("health-questions", OLHealthQuestionViewSet, basename="ol-health-question")
router.register("health-questionnaires", OLHealthQuestionnaireViewSet, basename="ol-health-questionnaire")
router.register("health-questionnaire-items", OLHealthQuestionnaireItemViewSet, basename="ol-health-questionnaire-item")
router.register("grace-period-notification-schedules", OLGracePeriodNotificationScheduleViewSet, basename="ol-grace-period-notification-schedule")
router.register("reinstatement-windows", OLReinstatementWindowViewSet, basename="ol-reinstatement-window")

urlpatterns = [
    path("health/", OLParameterHealthView.as_view(), name="ol-parameters-health"),
    path("", include(router.urls)),
]
