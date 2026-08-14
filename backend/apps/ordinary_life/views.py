from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from rest_framework import filters, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from apps.system_parameters.services.numbering_service import NumberingEngine
from apps.ordinary_life.services.lifecycle_service import OrdinaryLifeWorkflowService

from apps.ordinary_life.models import (
    OLLookupValue,
    OLDefaultSystemParameter,
    OLOverrideCommissionSetup,
    OLComputationApproach,
    OLMaturityClaimSetup,
    OLAnticipatedEndowmentInstallmentRate,
    OLGracePeriod,
    OLPolicyStatus,
    OLPolicyRenewalStatus,
    OLBeneficiaryType,
    OLMemberCoverConfiguration,
    OLSurrenderSetup,
    OLPaidUpSetup,
    OLSurrenderValueRate,
    OLPaidUpRate,
    OLCommitmentStatus,
    OLHealthQuestion,
    OLHealthQuestionnaire,
    OLGracePeriodNotificationSchedule,
    OLReinstatementWindow,
)
from apps.ordinary_life.serializers import (
    OLLookupValueSerializer,
    OLDefaultSystemParameterSerializer,
    OLOverrideCommissionSetupSerializer,
    OLComputationApproachSerializer,
    OLMaturityClaimSetupSerializer,
    OLAnticipatedEndowmentInstallmentRateSerializer,
    OLGracePeriodSerializer,
    OLPolicyStatusSerializer,
    OLPolicyRenewalStatusSerializer,
    OLBeneficiaryTypeSerializer,
    OLMemberCoverConfigurationSerializer,
    OLSurrenderSetupSerializer,
    OLPaidUpSetupSerializer,
    OLSurrenderValueRateSerializer,
    OLPaidUpRateSerializer,
    OLCommitmentStatusSerializer,
    OLHealthQuestionSerializer,
    OLHealthQuestionnaireSerializer,
    OLGracePeriodNotificationScheduleSerializer,
    OLReinstatementWindowSerializer,
)

class OLLookupValueViewSet(viewsets.ModelViewSet):
    queryset = OLLookupValue.objects.all()
    serializer_class = OLLookupValueSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["category", "is_active"]
    search_fields = ["category", "value", "label"]
    ordering_fields = ["category", "sort_order", "label", "created_at"]
    ordering = ["category", "sort_order", "label"]


class OLDefaultSystemParameterViewSet(viewsets.ModelViewSet):
    queryset = OLDefaultSystemParameter.objects.all()
    serializer_class = OLDefaultSystemParameterSerializer


class OLOverrideCommissionSetupViewSet(viewsets.ModelViewSet):
    queryset = OLOverrideCommissionSetup.objects.all()
    serializer_class = OLOverrideCommissionSetupSerializer


class OLComputationApproachViewSet(viewsets.ModelViewSet):
    queryset = OLComputationApproach.objects.all()
    serializer_class = OLComputationApproachSerializer


class OLMaturityClaimSetupViewSet(viewsets.ModelViewSet):
    queryset = OLMaturityClaimSetup.objects.all()
    serializer_class = OLMaturityClaimSetupSerializer


class OLAnticipatedEndowmentInstallmentRateViewSet(viewsets.ModelViewSet):
    queryset = OLAnticipatedEndowmentInstallmentRate.objects.all()
    serializer_class = OLAnticipatedEndowmentInstallmentRateSerializer


class OLGracePeriodViewSet(viewsets.ModelViewSet):
    queryset = OLGracePeriod.objects.all()
    serializer_class = OLGracePeriodSerializer


class OLPolicyStatusViewSet(viewsets.ModelViewSet):
    queryset = OLPolicyStatus.objects.all()
    serializer_class = OLPolicyStatusSerializer


class OLPolicyRenewalStatusViewSet(viewsets.ModelViewSet):
    queryset = OLPolicyRenewalStatus.objects.all()
    serializer_class = OLPolicyRenewalStatusSerializer


class OLBeneficiaryTypeViewSet(viewsets.ModelViewSet):
    queryset = OLBeneficiaryType.objects.all()
    serializer_class = OLBeneficiaryTypeSerializer


class OLMemberCoverConfigurationViewSet(viewsets.ModelViewSet):
    queryset = OLMemberCoverConfiguration.objects.all()
    serializer_class = OLMemberCoverConfigurationSerializer


class OLSurrenderSetupViewSet(viewsets.ModelViewSet):
    queryset = OLSurrenderSetup.objects.all()
    serializer_class = OLSurrenderSetupSerializer


class OLPaidUpSetupViewSet(viewsets.ModelViewSet):
    queryset = OLPaidUpSetup.objects.all()
    serializer_class = OLPaidUpSetupSerializer


class OLSurrenderValueRateViewSet(viewsets.ModelViewSet):
    queryset = OLSurrenderValueRate.objects.all()
    serializer_class = OLSurrenderValueRateSerializer


class OLPaidUpRateViewSet(viewsets.ModelViewSet):
    queryset = OLPaidUpRate.objects.all()
    serializer_class = OLPaidUpRateSerializer


class OLCommitmentStatusViewSet(viewsets.ModelViewSet):
    queryset = OLCommitmentStatus.objects.all()
    serializer_class = OLCommitmentStatusSerializer


class OLHealthQuestionViewSet(viewsets.ModelViewSet):
    queryset = OLHealthQuestion.objects.all()
    serializer_class = OLHealthQuestionSerializer


class OLHealthQuestionnaireViewSet(viewsets.ModelViewSet):
    queryset = OLHealthQuestionnaire.objects.all()
    serializer_class = OLHealthQuestionnaireSerializer


class OLGracePeriodNotificationScheduleViewSet(viewsets.ModelViewSet):
    queryset = OLGracePeriodNotificationSchedule.objects.all()
    serializer_class = OLGracePeriodNotificationScheduleSerializer


class OLReinstatementWindowViewSet(viewsets.ModelViewSet):
    queryset = OLReinstatementWindow.objects.all()
    serializer_class = OLReinstatementWindowSerializer

from apps.ordinary_life.models import (
    OLProduct,
    OLClient,
    OLQuotation,
    OLProposal,
    OLCommitment,
    OLPolicy,
    OLLoan,
    OLWithdrawal,
    OLClaim,
    OLMaturityInstallment,
    OLBeneficiary,
    OLWorkflowEvent,
)

from apps.ordinary_life.serializers import (
    OLProductSerializer,
    OLClientSerializer,
    OLQuotationSerializer,
    OLProposalSerializer,
    OLCommitmentSerializer,
    OLPolicySerializer,
    OLLoanSerializer,
    OLWithdrawalSerializer,
    OLClaimSerializer,
    OLMaturityInstallmentSerializer,
    OLBeneficiarySerializer,
    OLWorkflowEventSerializer,
)

def _service_validation_error(exc):
    detail = getattr(exc, "message_dict", None)
    if detail is None:
        detail = {"detail": exc.messages}
    return serializers.ValidationError(detail)


def _action_response(request, instance, serializer_class):
    return Response(serializer_class(instance, context={"request": request}).data)


class OLProductViewSet(viewsets.ModelViewSet):
    queryset = OLProduct.objects.all()
    serializer_class = OLProductSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["code", "name"]
    filterset_fields = ["is_active"]
    ordering_fields = ["name", "created_at"]


class OLClientViewSet(viewsets.ModelViewSet):
    queryset = OLClient.objects.all()
    serializer_class = OLClientSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["first_name", "last_name", "id_number", "phone", "email"]
    ordering_fields = ["first_name", "created_at"]


class OLQuotationViewSet(viewsets.ModelViewSet):
    queryset = OLQuotation.objects.select_related("client", "product").all()
    serializer_class = OLQuotationSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["quotation_number", "client__first_name", "client__last_name"]
    filterset_fields = ["status", "product"]
    ordering_fields = ["created_at"]

    def perform_create(self, serializer):
        serializer.save(quotation_number=NumberingEngine.generate_number("OL_QUOTATION", OLQuotation, field_name="quotation_number"))

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        try:
            result = OrdinaryLifeWorkflowService.submit_quotation(self.get_object(), request.data.get("reason", ""))
        except DjangoValidationError as exc:
            raise _service_validation_error(exc)
        return _action_response(request, result, self.get_serializer_class())

    @action(detail=True, methods=["post"], url_path="convert-to-proposal")
    def convert_to_proposal(self, request, pk=None):
        try:
            result = OrdinaryLifeWorkflowService.convert_quotation_to_proposal(
                self.get_object(), request.data.get("medical_required"), request.data.get("reason", "")
            )
        except DjangoValidationError as exc:
            raise _service_validation_error(exc)
        return _action_response(request, result, OLProposalSerializer)


class OLProposalViewSet(viewsets.ModelViewSet):
    queryset = OLProposal.objects.select_related("quotation").all()
    serializer_class = OLProposalSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["proposal_number", "quotation__quotation_number"]
    filterset_fields = ["status", "underwriting_status"]
    ordering_fields = ["created_at"]

    def perform_create(self, serializer):
        serializer.save(proposal_number=NumberingEngine.generate_number("OL_PROPOSAL", OLProposal, field_name="proposal_number"))

    @action(detail=True, methods=["post"])
    def underwriting(self, request, pk=None):
        try:
            result = OrdinaryLifeWorkflowService.complete_underwriting(
                self.get_object(), request.data.get("decision", ""), request.data.get("reason", "")
            )
        except DjangoValidationError as exc:
            raise _service_validation_error(exc)
        return _action_response(request, result, self.get_serializer_class())

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        try:
            result = OrdinaryLifeWorkflowService.approve_proposal(self.get_object(), request.data.get("reason", ""))
        except DjangoValidationError as exc:
            raise _service_validation_error(exc)
        return _action_response(request, result, self.get_serializer_class())

    @action(detail=True, methods=["post"])
    def decline(self, request, pk=None):
        try:
            result = OrdinaryLifeWorkflowService.decline_proposal(self.get_object(), request.data.get("reason", ""))
        except DjangoValidationError as exc:
            raise _service_validation_error(exc)
        return _action_response(request, result, self.get_serializer_class())


class OLCommitmentViewSet(viewsets.ModelViewSet):
    queryset = OLCommitment.objects.select_related("proposal").all()
    serializer_class = OLCommitmentSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["commitment_number", "proposal__proposal_number"]
    filterset_fields = ["status"]
    ordering_fields = ["created_at"]

    def perform_create(self, serializer):
        serializer.save(commitment_number=NumberingEngine.generate_number("OL_COMMITMENT", OLCommitment, field_name="commitment_number"))

    @action(detail=True, methods=["post"])
    def settle(self, request, pk=None):
        try:
            result = OrdinaryLifeWorkflowService.settle_commitment(
                self.get_object(), request.data.get("amount_paid"), request.data.get("reason", "")
            )
        except DjangoValidationError as exc:
            raise _service_validation_error(exc)
        return _action_response(request, result, self.get_serializer_class())


class OLPolicyViewSet(viewsets.ModelViewSet):
    queryset = OLPolicy.objects.select_related("proposal", "policyholder", "life_assured", "agent").all()
    serializer_class = OLPolicySerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["policy_number", "proposal__proposal_number"]
    filterset_fields = ["status"]
    ordering_fields = ["created_at"]

    @action(detail=False, methods=["post"])
    def issue(self, request):
        proposal = get_object_or_404(OLProposal, pk=request.data.get("proposal"))
        try:
            result = OrdinaryLifeWorkflowService.issue_policy(
                proposal,
                request.data.get("start_date"),
                request.data.get("end_date"),
                request.data.get("agent"),
                request.data.get("reason", ""),
            )
        except DjangoValidationError as exc:
            raise _service_validation_error(exc)
        return _action_response(request, result, self.get_serializer_class())


class OLLoanViewSet(viewsets.ModelViewSet):
    queryset = OLLoan.objects.select_related("policy").all()
    serializer_class = OLLoanSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["loan_number", "policy__policy_number"]
    filterset_fields = ["status"]
    ordering_fields = ["created_at"]

    def perform_create(self, serializer):
        serializer.save(loan_number=NumberingEngine.generate_number("OL_LOAN", OLLoan, field_name="loan_number"))

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        try:
            result = OrdinaryLifeWorkflowService.approve_loan(self.get_object(), request.data.get("reason", ""))
        except DjangoValidationError as exc:
            raise _service_validation_error(exc)
        return _action_response(request, result, self.get_serializer_class())


class OLWithdrawalViewSet(viewsets.ModelViewSet):
    queryset = OLWithdrawal.objects.select_related("policy").all()
    serializer_class = OLWithdrawalSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["withdrawal_number", "policy__policy_number"]
    filterset_fields = ["status", "withdrawal_type"]
    ordering_fields = ["created_at"]

    def perform_create(self, serializer):
        serializer.save(withdrawal_number=NumberingEngine.generate_number("OL_WITHDRAWAL", OLWithdrawal, field_name="withdrawal_number"))

    @action(detail=True, methods=["post"])
    def pay(self, request, pk=None):
        try:
            result = OrdinaryLifeWorkflowService.pay_withdrawal(self.get_object(), request.data.get("reason", ""))
        except DjangoValidationError as exc:
            raise _service_validation_error(exc)
        return _action_response(request, result, self.get_serializer_class())


class OLClaimViewSet(viewsets.ModelViewSet):
    queryset = OLClaim.objects.select_related("policy").all()
    serializer_class = OLClaimSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["claim_number", "policy__policy_number"]
    filterset_fields = ["status"]
    ordering_fields = ["created_at"]

    def perform_create(self, serializer):
        serializer.save(claim_number=NumberingEngine.generate_number("OL_CLAIM", OLClaim, field_name="claim_number"))

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        try:
            result = OrdinaryLifeWorkflowService.submit_claim(self.get_object(), request.data.get("reason", ""))
        except DjangoValidationError as exc:
            raise _service_validation_error(exc)
        return _action_response(request, result, self.get_serializer_class())

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        try:
            result = OrdinaryLifeWorkflowService.approve_claim(
                self.get_object(), request.data.get("approved_amount"), request.data.get("reason", "")
            )
        except DjangoValidationError as exc:
            raise _service_validation_error(exc)
        return _action_response(request, result, self.get_serializer_class())

    @action(detail=True, methods=["post"])
    def pay(self, request, pk=None):
        try:
            result = OrdinaryLifeWorkflowService.pay_claim(self.get_object(), request.data.get("reason", ""))
        except DjangoValidationError as exc:
            raise _service_validation_error(exc)
        return _action_response(request, result, self.get_serializer_class())


class OLMaturityInstallmentViewSet(viewsets.ModelViewSet):
    queryset = OLMaturityInstallment.objects.select_related("policy").all()
    serializer_class = OLMaturityInstallmentSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["installment_number", "policy__policy_number"]
    filterset_fields = ["status"]
    ordering_fields = ["created_at"]

    def perform_create(self, serializer):
        serializer.save(installment_number=NumberingEngine.generate_number("OL_INSTALLMENT", OLMaturityInstallment, field_name="installment_number"))

    @action(detail=True, methods=["post"])
    def pay(self, request, pk=None):
        try:
            result = OrdinaryLifeWorkflowService.pay_maturity_installment(self.get_object(), request.data.get("reason", ""))
        except DjangoValidationError as exc:
            raise _service_validation_error(exc)
        return _action_response(request, result, self.get_serializer_class())


class OLBeneficiaryViewSet(viewsets.ModelViewSet):
    queryset = OLBeneficiary.objects.select_related("policy", "beneficiary_type").all()
    serializer_class = OLBeneficiarySerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "relationship", "id_number"]
    filterset_fields = ["policy", "beneficiary_type"]
    ordering_fields = ["name", "created_at"]


class OLWorkflowEventViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = OLWorkflowEvent.objects.select_related("actor").all()
    serializer_class = OLWorkflowEventSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["entity_type", "entity_id", "action"]
    ordering_fields = ["created_at"]
