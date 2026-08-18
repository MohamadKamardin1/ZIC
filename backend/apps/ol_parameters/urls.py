from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    OLAnticipatedEndowmentInstallmentRateViewSet,
    OLAgentCommissionSetupViewSet,
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
    OLPlanTypeViewSet,
    OLProductViewSet,
    OLPlanTaxConfigurationViewSet,
    OLPlanTargetMarketViewSet,
    OLPlanRiskCategoryViewSet,
    OLPlanOccupationRiskLimitViewSet,
    OLInvestmentFundTypeViewSet,
    OLInvestmentFundViewSet,
    OLPremiumRateTableViewSet,
    OLPremiumRateRowViewSet,
    OLMortalityRateTableViewSet,
    OLMortalityRateRowViewSet,
    OLJointLifeSetupViewSet,
    OLReinstatementInterestRateViewSet,
    OLBonusRateViewSet,
    OLMortgageInterestFactorViewSet,
    OLInstallmentChargeRateViewSet,
    OLCashSurrenderValueViewSet,
    OLReserveLoadingViewSet,
    OLRiderSetupViewSet,
    OLRiderRateTableViewSet,
    OLRiderRateRowViewSet,
)


router = DefaultRouter()
router.register("tables", OLParameterTableRegistryViewSet, basename="ol-parameter-table")
router.register("default-system-parameters", OLDefaultSystemParameterViewSet, basename="ol-default-system-parameter")
router.register("override-commission-setups", OLOverrideCommissionSetupViewSet, basename="ol-override-commission-setup")
router.register("agent-commission-setups", OLAgentCommissionSetupViewSet, basename="ol-agent-commission-setup")
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
router.register("plan-types", OLPlanTypeViewSet, basename="ol-plan-type")
router.register("products", OLProductViewSet, basename="ol-product")
router.register("plan-tax-configurations", OLPlanTaxConfigurationViewSet, basename="ol-plan-tax-configuration")
router.register("plan-target-markets", OLPlanTargetMarketViewSet, basename="ol-plan-target-market")
router.register("plan-risk-categories", OLPlanRiskCategoryViewSet, basename="ol-plan-risk-category")
router.register("plan-occupation-risk-limits", OLPlanOccupationRiskLimitViewSet, basename="ol-plan-occupation-risk-limit")
router.register("investment-fund-types", OLInvestmentFundTypeViewSet, basename="ol-investment-fund-type")
router.register("investment-funds", OLInvestmentFundViewSet, basename="ol-investment-fund")
router.register("premium-rate-tables", OLPremiumRateTableViewSet, basename="ol-premium-rate-table")
router.register("premium-rate-rows", OLPremiumRateRowViewSet, basename="ol-premium-rate-row")
router.register("mortality-rate-tables", OLMortalityRateTableViewSet, basename="ol-mortality-rate-table")
router.register("mortality-rate-rows", OLMortalityRateRowViewSet, basename="ol-mortality-rate-row")
router.register("joint-life-setups", OLJointLifeSetupViewSet, basename="ol-joint-life-setup")
router.register("reinstatement-interest-rates", OLReinstatementInterestRateViewSet, basename="ol-reinstatement-interest-rate")
router.register("bonus-rates", OLBonusRateViewSet, basename="ol-bonus-rate")
router.register("mortgage-interest-factors", OLMortgageInterestFactorViewSet, basename="ol-mortgage-interest-factor")
router.register("installment-charge-rates", OLInstallmentChargeRateViewSet, basename="ol-installment-charge-rate")
router.register("cash-surrender-values", OLCashSurrenderValueViewSet, basename="ol-cash-surrender-value")
router.register("reserve-loadings", OLReserveLoadingViewSet, basename="ol-reserve-loading")
router.register("rider-setups", OLRiderSetupViewSet, basename="ol-rider-setup")
router.register("rider-rate-tables", OLRiderRateTableViewSet, basename="ol-rider-rate-table")
router.register("rider-rate-rows", OLRiderRateRowViewSet, basename="ol-rider-rate-row")

urlpatterns = [
    path("health/", OLParameterHealthView.as_view(), name="ol-parameters-health"),
    path("", include(router.urls)),
]
