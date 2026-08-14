from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend

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
)

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
    queryset = OLQuotation.objects.all()
    serializer_class = OLQuotationSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["quotation_number", "client__first_name", "client__last_name"]
    filterset_fields = ["status", "product"]
    ordering_fields = ["created_at"]

class OLProposalViewSet(viewsets.ModelViewSet):
    queryset = OLProposal.objects.all()
    serializer_class = OLProposalSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["proposal_number", "quotation__quotation_number"]
    filterset_fields = ["status", "underwriting_status"]
    ordering_fields = ["created_at"]

class OLCommitmentViewSet(viewsets.ModelViewSet):
    queryset = OLCommitment.objects.all()
    serializer_class = OLCommitmentSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["commitment_number", "proposal__proposal_number"]
    filterset_fields = ["status"]
    ordering_fields = ["created_at"]

class OLPolicyViewSet(viewsets.ModelViewSet):
    queryset = OLPolicy.objects.all()
    serializer_class = OLPolicySerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["policy_number", "proposal__proposal_number"]
    filterset_fields = ["status"]
    ordering_fields = ["created_at"]

class OLLoanViewSet(viewsets.ModelViewSet):
    queryset = OLLoan.objects.all()
    serializer_class = OLLoanSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["loan_number", "policy__policy_number"]
    filterset_fields = ["status"]
    ordering_fields = ["created_at"]

class OLWithdrawalViewSet(viewsets.ModelViewSet):
    queryset = OLWithdrawal.objects.all()
    serializer_class = OLWithdrawalSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["withdrawal_number", "policy__policy_number"]
    filterset_fields = ["status", "withdrawal_type"]
    ordering_fields = ["created_at"]

class OLClaimViewSet(viewsets.ModelViewSet):
    queryset = OLClaim.objects.all()
    serializer_class = OLClaimSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["claim_number", "policy__policy_number"]
    filterset_fields = ["status"]
    ordering_fields = ["created_at"]

class OLMaturityInstallmentViewSet(viewsets.ModelViewSet):
    queryset = OLMaturityInstallment.objects.all()
    serializer_class = OLMaturityInstallmentSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["installment_number", "policy__policy_number"]
    filterset_fields = ["status"]
    ordering_fields = ["created_at"]

