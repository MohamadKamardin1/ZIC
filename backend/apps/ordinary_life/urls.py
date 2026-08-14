from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.ordinary_life.api_views import (
    OLApplicationApiViewSet,
    OLApprovalApiViewSet,
    OLAuditHistoryApiViewSet,
    OLBeneficiaryAllocationApiViewSet,
    OLClaimApiViewSet,
    OLClientApiViewSet,
    OLCommitmentApiViewSet,
    OLDocumentApiViewSet,
    OLEndorsementApiViewSet,
    OLHealthDeclarationApiViewSet,
    OLHealthResponseApiViewSet,
    OLLoanApiViewSet,
    OLMedicalRequirementApiViewSet,
    OLNoteApiViewSet,
    OLPaymentAllocationApiViewSet,
    OLPaymentObligationApiViewSet,
    OLPolicyApiViewSet,
    OLPolicyPartyApiViewSet,
    OLPolicyRenewalApiViewSet,
    OLPolicyStatusHistoryApiViewSet,
    OLPolicyTransactionApiViewSet,
    OLPremiumInstallmentApiViewSet,
    OLPremiumScheduleApiViewSet,
    OLProductApiViewSet,
    OLProposalApiViewSet,
    OLQuotationApiViewSet,
    OLQuotationVersionApiViewSet,
    OLReinstatementRequestApiViewSet,
    OLUnderwritingCaseApiViewSet,
    OLUnderwritingDecisionEventApiViewSet,
    OLWithdrawalApiViewSet,
    OLWorkflowEventApiViewSet,
)
from apps.ordinary_life.views import (
    OLAnticipatedEndowmentInstallmentRateViewSet,
    OLBeneficiaryTypeViewSet,
    OLCommitmentStatusViewSet,
    OLComputationApproachViewSet,
    OLDefaultSystemParameterViewSet,
    OLGracePeriodNotificationScheduleViewSet,
    OLGracePeriodViewSet,
    OLHealthQuestionnaireViewSet,
    OLHealthQuestionViewSet,
    OLLookupValueViewSet,
    OLMaturityClaimSetupViewSet,
    OLMaturityInstallmentViewSet,
    OLMemberCoverConfigurationViewSet,
    OLOverrideCommissionSetupViewSet,
    OLPaidUpRateViewSet,
    OLPaidUpSetupViewSet,
    OLPolicyRenewalStatusViewSet,
    OLPolicyStatusViewSet,
    OLReinstatementWindowViewSet,
    OLSurrenderSetupViewSet,
    OLSurrenderValueRateViewSet,
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
core_router.register(r"products", OLProductApiViewSet, basename="ol-product")
core_router.register(r"clients", OLClientApiViewSet, basename="ol-client")
core_router.register(r"applications", OLApplicationApiViewSet, basename="ol-application")
core_router.register(r"quotations", OLQuotationApiViewSet, basename="ol-quotation")
core_router.register(r"quotation-versions", OLQuotationVersionApiViewSet, basename="ol-quotation-version")
core_router.register(r"proposals", OLProposalApiViewSet, basename="ol-proposal")
core_router.register(r"underwriting-cases", OLUnderwritingCaseApiViewSet, basename="ol-underwriting-case")
core_router.register(r"underwriting-decision-events", OLUnderwritingDecisionEventApiViewSet, basename="ol-underwriting-decision-event")
core_router.register(r"medical-requirements", OLMedicalRequirementApiViewSet, basename="ol-medical-requirement")
core_router.register(r"health-declarations", OLHealthDeclarationApiViewSet, basename="ol-health-declaration")
core_router.register(r"health-responses", OLHealthResponseApiViewSet, basename="ol-health-response")
core_router.register(r"payment-obligations", OLPaymentObligationApiViewSet, basename="ol-payment-obligation")
core_router.register(r"payment-allocations", OLPaymentAllocationApiViewSet, basename="ol-payment-allocation")
core_router.register(r"policies", OLPolicyApiViewSet, basename="ol-policy")
core_router.register(r"endorsements", OLEndorsementApiViewSet, basename="ol-endorsement")
core_router.register(r"renewals", OLPolicyRenewalApiViewSet, basename="ol-policy-renewal")
core_router.register(r"reinstatements", OLReinstatementRequestApiViewSet, basename="ol-reinstatement-request")
core_router.register(r"premium-schedules", OLPremiumScheduleApiViewSet, basename="ol-premium-schedule")
core_router.register(r"premium-installments", OLPremiumInstallmentApiViewSet, basename="ol-premium-installment")
core_router.register(r"policy-parties", OLPolicyPartyApiViewSet, basename="ol-policy-party")
core_router.register(r"beneficiary-allocations", OLBeneficiaryAllocationApiViewSet, basename="ol-beneficiary-allocation")
core_router.register(r"documents", OLDocumentApiViewSet, basename="ol-document")
core_router.register(r"notes", OLNoteApiViewSet, basename="ol-note")
core_router.register(r"workflow-events", OLWorkflowEventApiViewSet, basename="ol-workflow-event")
core_router.register(r"policy-transactions", OLPolicyTransactionApiViewSet, basename="ol-policy-transaction")
core_router.register(r"policy-status-history", OLPolicyStatusHistoryApiViewSet, basename="ol-policy-status-history")
core_router.register(r"approvals", OLApprovalApiViewSet, basename="ol-approval")
core_router.register(r"audit-history", OLAuditHistoryApiViewSet, basename="ol-audit-history")
core_router.register(r"commitments", OLCommitmentApiViewSet, basename="ol-commitment")
core_router.register(r"loans", OLLoanApiViewSet, basename="ol-loan")
core_router.register(r"withdrawals", OLWithdrawalApiViewSet, basename="ol-withdrawal")
core_router.register(r"claims", OLClaimApiViewSet, basename="ol-claim")
core_router.register(r"maturity-installments", OLMaturityInstallmentViewSet, basename="ol-maturity-installment")

urlpatterns = [
    path("setup/", include(setup_router.urls)),
    path("core/", include(core_router.urls)),
]
