from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.ordinary_life.views import (
    OLLookupValueViewSet,
    OLDefaultSystemParameterViewSet,
    OLOverrideCommissionSetupViewSet,
    OLComputationApproachViewSet,
    OLMaturityClaimSetupViewSet,
    OLAnticipatedEndowmentInstallmentRateViewSet,
    OLGracePeriodViewSet,
    OLPolicyStatusViewSet,
    OLPolicyRenewalStatusViewSet,
    OLBeneficiaryTypeViewSet,
    OLMemberCoverConfigurationViewSet,
    OLSurrenderSetupViewSet,
    OLPaidUpSetupViewSet,
    OLSurrenderValueRateViewSet,
    OLPaidUpRateViewSet,
    OLCommitmentStatusViewSet,
    OLHealthQuestionViewSet,
    OLHealthQuestionnaireViewSet,
    OLGracePeriodNotificationScheduleViewSet,
    OLGracePeriodNotificationScheduleViewSet,
    OLReinstatementWindowViewSet,
    OLProductViewSet,
    OLClientViewSet,
    OLQuotationViewSet,
    OLProposalViewSet,
    OLCommitmentViewSet,
    OLPolicyViewSet,
    OLLoanViewSet,
    OLWithdrawalViewSet,
    OLClaimViewSet,
    OLMaturityInstallmentViewSet,
)

setup_router = DefaultRouter()
setup_router.register(r"lookup-values", OLLookupValueViewSet, basename="ol-lookup-values")
setup_router.register(r"default-system-parameters", OLDefaultSystemParameterViewSet, basename="ol-default-system-parameters")
setup_router.register(r"override-commission-setup", OLOverrideCommissionSetupViewSet, basename="ol-override-commission-setup")
setup_router.register(r"computation-approaches", OLComputationApproachViewSet, basename="ol-computation-approaches")
setup_router.register(r"maturity-claim-setup", OLMaturityClaimSetupViewSet, basename="ol-maturity-claim-setup")
setup_router.register(r"anticipated-endowment-rates", OLAnticipatedEndowmentInstallmentRateViewSet, basename="ol-anticipated-endowment-rates")
setup_router.register(r"grace-periods", OLGracePeriodViewSet, basename="ol-grace-periods")
setup_router.register(r"policy-statuses", OLPolicyStatusViewSet, basename="ol-policy-statuses")
setup_router.register(r"policy-renewal-statuses", OLPolicyRenewalStatusViewSet, basename="ol-policy-renewal-statuses")
setup_router.register(r"beneficiary-types", OLBeneficiaryTypeViewSet, basename="ol-beneficiary-types")
setup_router.register(r"member-cover-configurations", OLMemberCoverConfigurationViewSet, basename="ol-member-cover-configurations")
setup_router.register(r"surrender-setup", OLSurrenderSetupViewSet, basename="ol-surrender-setup")
setup_router.register(r"paid-up-setup", OLPaidUpSetupViewSet, basename="ol-paid-up-setup")
setup_router.register(r"surrender-value-rates", OLSurrenderValueRateViewSet, basename="ol-surrender-value-rates")
setup_router.register(r"paid-up-rates", OLPaidUpRateViewSet, basename="ol-paid-up-rates")
setup_router.register(r"commitment-statuses", OLCommitmentStatusViewSet, basename="ol-commitment-statuses")
setup_router.register(r"health-questions", OLHealthQuestionViewSet, basename="ol-health-questions")
setup_router.register(r"health-questionnaires", OLHealthQuestionnaireViewSet, basename="ol-health-questionnaires")
setup_router.register(r"grace-period-notification-schedules", OLGracePeriodNotificationScheduleViewSet, basename="ol-grace-period-notification-schedules")
setup_router.register(r"reinstatement-windows", OLReinstatementWindowViewSet, basename="ol-reinstatement-windows")

core_router = DefaultRouter()
core_router.register(r"products", OLProductViewSet, basename="ol-product")
core_router.register(r"clients", OLClientViewSet, basename="ol-client")
core_router.register(r"quotations", OLQuotationViewSet, basename="ol-quotation")
core_router.register(r"proposals", OLProposalViewSet, basename="ol-proposal")
core_router.register(r"commitments", OLCommitmentViewSet, basename="ol-commitment")
core_router.register(r"policies", OLPolicyViewSet, basename="ol-policy")
core_router.register(r"loans", OLLoanViewSet, basename="ol-loan")
core_router.register(r"withdrawals", OLWithdrawalViewSet, basename="ol-withdrawal")
core_router.register(r"claims", OLClaimViewSet, basename="ol-claim")
core_router.register(r"maturity-installments", OLMaturityInstallmentViewSet, basename="ol-maturity-installment")

urlpatterns = [
    path("setup/", include(setup_router.urls)),
    path("core/", include(core_router.urls)),
]
