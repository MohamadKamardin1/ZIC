import logging
from rest_framework import serializers

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

class OLLookupValueSerializer(serializers.ModelSerializer):
    class Meta:
        model = OLLookupValue
        fields = "__all__"

class OLDefaultSystemParameterSerializer(serializers.ModelSerializer):
    class Meta:
        model = OLDefaultSystemParameter
        fields = "__all__"

class OLOverrideCommissionSetupSerializer(serializers.ModelSerializer):
    class Meta:
        model = OLOverrideCommissionSetup
        fields = "__all__"

class OLComputationApproachSerializer(serializers.ModelSerializer):
    class Meta:
        model = OLComputationApproach
        fields = "__all__"

class OLMaturityClaimSetupSerializer(serializers.ModelSerializer):
    class Meta:
        model = OLMaturityClaimSetup
        fields = "__all__"

class OLAnticipatedEndowmentInstallmentRateSerializer(serializers.ModelSerializer):
    class Meta:
        model = OLAnticipatedEndowmentInstallmentRate
        fields = "__all__"

class OLGracePeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = OLGracePeriod
        fields = "__all__"

class OLPolicyStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = OLPolicyStatus
        fields = "__all__"

class OLPolicyRenewalStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = OLPolicyRenewalStatus
        fields = "__all__"

class OLBeneficiaryTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = OLBeneficiaryType
        fields = "__all__"

class OLMemberCoverConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = OLMemberCoverConfiguration
        fields = "__all__"

class OLSurrenderSetupSerializer(serializers.ModelSerializer):
    class Meta:
        model = OLSurrenderSetup
        fields = "__all__"

class OLPaidUpSetupSerializer(serializers.ModelSerializer):
    class Meta:
        model = OLPaidUpSetup
        fields = "__all__"

class OLSurrenderValueRateSerializer(serializers.ModelSerializer):
    class Meta:
        model = OLSurrenderValueRate
        fields = "__all__"

class OLPaidUpRateSerializer(serializers.ModelSerializer):
    class Meta:
        model = OLPaidUpRate
        fields = "__all__"

class OLCommitmentStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = OLCommitmentStatus
        fields = "__all__"

class OLHealthQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = OLHealthQuestion
        fields = "__all__"

class OLHealthQuestionnaireSerializer(serializers.ModelSerializer):
    class Meta:
        model = OLHealthQuestionnaire
        fields = "__all__"

class OLGracePeriodNotificationScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = OLGracePeriodNotificationSchedule
        fields = "__all__"

class OLReinstatementWindowSerializer(serializers.ModelSerializer):
    class Meta:
        model = OLReinstatementWindow
        fields = "__all__"

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

class OLProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = OLProduct
        fields = "__all__"

    def validate(self, attrs):
        minimum, maximum = attrs.get("min_age"), attrs.get("max_age")
        if minimum is not None and maximum is not None and minimum > maximum:
            raise serializers.ValidationError({"max_age": "Maximum age must be greater than or equal to minimum age."})
        if attrs.get("term_length_years") is not None and attrs["term_length_years"] <= 0:
            raise serializers.ValidationError({"term_length_years": "Term length must be greater than zero."})
        return attrs

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
        read_only_fields = ["status", "quotation_number"]

    def validate(self, attrs):
        if attrs.get("sum_assured", 0) <= 0:
            raise serializers.ValidationError({"sum_assured": "Sum assured must be greater than zero."})
        if attrs.get("premium_amount", 0) <= 0:
            raise serializers.ValidationError({"premium_amount": "Premium amount must be greater than zero."})
        product = attrs.get("product")
        if product is not None and not product.is_active:
            raise serializers.ValidationError({"product": "The selected product is inactive."})
        return attrs

class OLProposalSerializer(serializers.ModelSerializer):
    quotation_number = serializers.CharField(source="quotation.quotation_number", read_only=True)

    class Meta:
        model = OLProposal
        fields = "__all__"
        read_only_fields = ["status", "underwriting_status", "proposal_number"]

class OLCommitmentSerializer(serializers.ModelSerializer):
    proposal_number = serializers.CharField(source="proposal.proposal_number", read_only=True)

    class Meta:
        model = OLCommitment
        fields = "__all__"

class OLPolicySerializer(serializers.ModelSerializer):
    proposal_number = serializers.CharField(source="proposal.proposal_number", read_only=True)
    beneficiary_count = serializers.IntegerField(source="beneficiaries.count", read_only=True)

    class Meta:
        model = OLPolicy
        fields = "__all__"
        read_only_fields = ["status", "policy_number"]

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
        read_only_fields = ["status", "claim_number"]

    def validate(self, attrs):
        if attrs.get("claim_amount", 0) <= 0:
            raise serializers.ValidationError({"claim_amount": "Claim amount must be greater than zero."})
        return attrs

class OLMaturityInstallmentSerializer(serializers.ModelSerializer):
    policy_number = serializers.CharField(source="policy.policy_number", read_only=True)

    class Meta:
        model = OLMaturityInstallment
        fields = "__all__"
        read_only_fields = ["status", "installment_number"]


class OLBeneficiarySerializer(serializers.ModelSerializer):
    class Meta:
        model = OLBeneficiary
        fields = "__all__"

    def validate_percentage(self, value):
        if value <= 0 or value > 100:
            raise serializers.ValidationError("Percentage must be greater than zero and no more than 100.")
        return value


class OLWorkflowEventSerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()

    class Meta:
        model = OLWorkflowEvent
        fields = [
            "id", "entity_type", "entity_id", "action", "previous_status",
            "new_status", "reason", "actor", "actor_name", "metadata", "created_at",
        ]
        read_only_fields = fields

    def get_actor_name(self, obj):
        if not obj.actor:
            return "System"
        return obj.actor.get_full_name() or obj.actor.email or str(obj.actor_id)
