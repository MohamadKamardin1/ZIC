import os

views_code = """
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
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["code", "name"]
    filterset_fields = ["is_active"]
    ordering_fields = ["name", "created_at"]

class OLClientViewSet(viewsets.ModelViewSet):
    queryset = OLClient.objects.all()
    serializer_class = OLClientSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["first_name", "last_name", "id_number", "phone", "email"]
    ordering_fields = ["first_name", "created_at"]

class OLQuotationViewSet(viewsets.ModelViewSet):
    queryset = OLQuotation.objects.all()
    serializer_class = OLQuotationSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["quotation_number", "client__first_name", "client__last_name"]
    filterset_fields = ["status", "product"]
    ordering_fields = ["created_at"]

class OLProposalViewSet(viewsets.ModelViewSet):
    queryset = OLProposal.objects.all()
    serializer_class = OLProposalSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["proposal_number", "quotation__quotation_number"]
    filterset_fields = ["status", "underwriting_status"]
    ordering_fields = ["created_at"]

class OLCommitmentViewSet(viewsets.ModelViewSet):
    queryset = OLCommitment.objects.all()
    serializer_class = OLCommitmentSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["commitment_number", "proposal__proposal_number"]
    filterset_fields = ["status"]
    ordering_fields = ["created_at"]

class OLPolicyViewSet(viewsets.ModelViewSet):
    queryset = OLPolicy.objects.all()
    serializer_class = OLPolicySerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["policy_number", "proposal__proposal_number"]
    filterset_fields = ["status"]
    ordering_fields = ["created_at"]

class OLLoanViewSet(viewsets.ModelViewSet):
    queryset = OLLoan.objects.all()
    serializer_class = OLLoanSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["loan_number", "policy__policy_number"]
    filterset_fields = ["status"]
    ordering_fields = ["created_at"]

class OLWithdrawalViewSet(viewsets.ModelViewSet):
    queryset = OLWithdrawal.objects.all()
    serializer_class = OLWithdrawalSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["withdrawal_number", "policy__policy_number"]
    filterset_fields = ["status", "withdrawal_type"]
    ordering_fields = ["created_at"]

class OLClaimViewSet(viewsets.ModelViewSet):
    queryset = OLClaim.objects.all()
    serializer_class = OLClaimSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["claim_number", "policy__policy_number"]
    filterset_fields = ["status"]
    ordering_fields = ["created_at"]

class OLMaturityInstallmentViewSet(viewsets.ModelViewSet):
    queryset = OLMaturityInstallment.objects.all()
    serializer_class = OLMaturityInstallmentSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["installment_number", "policy__policy_number"]
    filterset_fields = ["status"]
    ordering_fields = ["created_at"]

"""

with open("backend/apps/ordinary_life/views.py", "a") as f:
    f.write(views_code)
