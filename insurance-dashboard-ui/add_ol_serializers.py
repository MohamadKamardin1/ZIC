import os

serializers_code = """
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

class OLProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = OLProduct
        fields = "__all__"

class OLClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = OLClient
        fields = "__all__"

class OLQuotationSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source="client.__str__", read_only=True)
    product_name = serializers.CharField(source="product.__str__", read_only=True)

    class Meta:
        model = OLQuotation
        fields = "__all__"

class OLProposalSerializer(serializers.ModelSerializer):
    quotation_number = serializers.CharField(source="quotation.quotation_number", read_only=True)
    
    class Meta:
        model = OLProposal
        fields = "__all__"

class OLCommitmentSerializer(serializers.ModelSerializer):
    proposal_number = serializers.CharField(source="proposal.proposal_number", read_only=True)

    class Meta:
        model = OLCommitment
        fields = "__all__"

class OLPolicySerializer(serializers.ModelSerializer):
    proposal_number = serializers.CharField(source="proposal.proposal_number", read_only=True)

    class Meta:
        model = OLPolicy
        fields = "__all__"

class OLLoanSerializer(serializers.ModelSerializer):
    policy_number = serializers.CharField(source="policy.policy_number", read_only=True)

    class Meta:
        model = OLLoan
        fields = "__all__"

class OLWithdrawalSerializer(serializers.ModelSerializer):
    policy_number = serializers.CharField(source="policy.policy_number", read_only=True)

    class Meta:
        model = OLWithdrawal
        fields = "__all__"

class OLClaimSerializer(serializers.ModelSerializer):
    policy_number = serializers.CharField(source="policy.policy_number", read_only=True)

    class Meta:
        model = OLClaim
        fields = "__all__"

class OLMaturityInstallmentSerializer(serializers.ModelSerializer):
    policy_number = serializers.CharField(source="policy.policy_number", read_only=True)

    class Meta:
        model = OLMaturityInstallment
        fields = "__all__"
"""

with open("backend/apps/ordinary_life/serializers.py", "a") as f:
    f.write(serializers_code)
