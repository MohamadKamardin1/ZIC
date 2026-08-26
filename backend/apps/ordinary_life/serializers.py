from decimal import Decimal

from rest_framework import serializers

from apps.ordinary_life.models import (
    OLAnticipatedEndowmentInstallmentRate,
    OLApplication,
    OLBeneficiary,
    OLBeneficiaryAllocation,
    OLBeneficiaryType,
    OLBenefit,
    OLClaim,
    OLClient,
    OLCommitment,
    OLCommitmentStatus,
    OLComputationApproach,
    OLDefaultSystemParameter,
    OLDocumentRecord,
    OLEndorsement,
    OLGracePeriod,
    OLGracePeriodNotificationSchedule,
    OLHealthDeclaration,
    OLHealthQuestion,
    OLHealthQuestionnaire,
    OLHealthResponse,
    OLLoan,
    OLLookupValue,
    OLMaturityClaimSetup,
    OLMaturityInstallment,
    OLMedicalRequirement,
    OLMedicalResult,
    OLMemberCoverConfiguration,
    OLNote,
    OLOverrideCommissionSetup,
    OLPaidUpRate,
    OLPaidUpSetup,
    OLPaymentAllocation,
    OLPaymentObligation,
    OLPlan,
    OLPolicy,
    OLPolicyParty,
    OLPolicyRenewal,
    OLPolicyRenewalStatus,
    OLPolicyStatus,
    OLPolicyStatusHistory,
    OLPolicyTransaction,
    OLPremiumInstallment,
    OLPremiumSchedule,
    OLProduct,
    OLProductBenefit,
    OLProductRider,
    OLProductVersion,
    OLProposal,
    OLQuotation,
    OLQuotationVersion,
    OLRateBand,
    OLReinstatementRequest,
    OLReinstatementWindow,
    OLRider,
    OLSurrenderSetup,
    OLSurrenderValueRate,
    OLUnderwritingCase,
    OLUnderwritingDecisionEvent,
    OLWithdrawal,
    OLWorkflowEvent,
)


def _read_only_fields(model):
    """Every model field, for response serializers whose Meta uses
    ``fields = "__all__"`` and wants every field read-only. Using ``fields``
    directly would make ``read_only_fields`` the string ``"__all__"``, which
    Django REST Framework rejects."""
    return [field.name for field in model._meta.fields]


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
        read_only_fields = ["status", "quotation_number", "premium_amount"]

    def validate(self, attrs):
        if attrs.get("sum_assured", 0) <= 0:
            raise serializers.ValidationError({"sum_assured": "Sum assured must be greater than zero."})
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


class OLProductVersionSerializer(serializers.ModelSerializer):
    product_code = serializers.CharField(source="product.code", read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = OLProductVersion
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at"]


class OLPlanSerializer(serializers.ModelSerializer):
    product_code = serializers.CharField(source="product_version.product.code", read_only=True)
    product_version_number = serializers.IntegerField(source="product_version.version_number", read_only=True)

    class Meta:
        model = OLPlan
        fields = "__all__"


class OLBenefitSerializer(serializers.ModelSerializer):
    class Meta:
        model = OLBenefit
        fields = "__all__"


class OLProductBenefitSerializer(serializers.ModelSerializer):
    benefit_code = serializers.CharField(source="benefit.code", read_only=True)
    benefit_name = serializers.CharField(source="benefit.name", read_only=True)

    class Meta:
        model = OLProductBenefit
        fields = "__all__"


class OLRiderSerializer(serializers.ModelSerializer):
    class Meta:
        model = OLRider
        fields = "__all__"


class OLProductRiderSerializer(serializers.ModelSerializer):
    rider_code = serializers.CharField(source="rider.code", read_only=True)
    rider_name = serializers.CharField(source="rider.name", read_only=True)

    class Meta:
        model = OLProductRider
        fields = "__all__"


class OLRateBandSerializer(serializers.ModelSerializer):
    product_code = serializers.CharField(source="product_version.product.code", read_only=True)
    plan_code = serializers.CharField(source="plan.code", read_only=True, allow_null=True)

    class Meta:
        model = OLRateBand
        fields = "__all__"


class OLApplicationSerializer(serializers.ModelSerializer):
    partner_name = serializers.CharField(source="partner.display_name", read_only=True)
    policyholder_name = serializers.CharField(source="policyholder.display_name", read_only=True)
    life_assured_name = serializers.CharField(source="life_assured.display_name", read_only=True)
    payer_name = serializers.CharField(source="payer.display_name", read_only=True)
    proposal_number = serializers.CharField(source="proposal.proposal_number", read_only=True, allow_null=True)

    class Meta:
        model = OLApplication
        fields = "__all__"
        read_only_fields = ["application_number", "proposal", "status", "submitted_at", "created_at", "updated_at"]


class OLApplicationCreateSerializer(serializers.Serializer):
    partner = serializers.UUIDField()
    policyholder = serializers.UUIDField()
    life_assured = serializers.UUIDField()
    payer = serializers.UUIDField(required=False, allow_null=True)
    declarations = serializers.JSONField(required=False)


class OLReasonSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True)


class OLQuotationVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = OLQuotationVersion
        fields = "__all__"
        read_only_fields = _read_only_fields(model)


class OLQuotationCreateSerializer(serializers.Serializer):
    application = serializers.UUIDField()
    product_version = serializers.UUIDField()
    sum_assured = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0.01"))
    term_years = serializers.IntegerField(min_value=1)
    payment_frequency = serializers.CharField(max_length=30)
    plan = serializers.UUIDField(required=False, allow_null=True)
    rider_codes = serializers.ListField(child=serializers.CharField(max_length=50), required=False, allow_empty=True)


class OLProposalConvertSerializer(serializers.Serializer):
    quotation = serializers.UUIDField()
    application = serializers.UUIDField(required=False, allow_null=True)
    reason = serializers.CharField(required=False, allow_blank=True)


class OLUnderwritingCaseSerializer(serializers.ModelSerializer):
    proposal_number = serializers.CharField(source="proposal.proposal_number", read_only=True)
    unresolved_requirement_count = serializers.SerializerMethodField()

    class Meta:
        model = OLUnderwritingCase
        fields = "__all__"
        read_only_fields = _read_only_fields(model)

    def get_unresolved_requirement_count(self, obj):
        return obj.medical_requirements.exclude(status__in=["VERIFIED", "WAIVED"]).count()


class OLUnderwritingDecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["APPROVED", "REFERRED", "DECLINED", "POSTPONED"])
    risk_class = serializers.CharField(required=False, default="STANDARD", allow_blank=True)
    reason = serializers.CharField()


class OLHealthDeclarationSerializer(serializers.ModelSerializer):
    response_count = serializers.IntegerField(source="responses.count", read_only=True)

    class Meta:
        model = OLHealthDeclaration
        fields = "__all__"
        read_only_fields = _read_only_fields(model)


class OLHealthResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = OLHealthResponse
        fields = "__all__"
        read_only_fields = _read_only_fields(model)


class OLHealthDeclarationCreateSerializer(serializers.Serializer):
    questionnaire = serializers.UUIDField(required=False, allow_null=True)
    responses = serializers.ListField(child=serializers.JSONField(), required=False, allow_empty=True)
    reason = serializers.CharField(required=False, allow_blank=True)


class OLMedicalRequirementSerializer(serializers.ModelSerializer):
    proposal_number = serializers.CharField(source="underwriting_case.proposal.proposal_number", read_only=True)
    result = serializers.SerializerMethodField()

    class Meta:
        model = OLMedicalRequirement
        fields = "__all__"
        read_only_fields = _read_only_fields(model)

    def get_result(self, obj):
        result = getattr(obj, "result", None)
        if not result:
            return None
        return OLMedicalResultSerializer(result).data


class OLMedicalResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = OLMedicalResult
        fields = "__all__"
        read_only_fields = _read_only_fields(model)


class OLMedicalResultCreateSerializer(serializers.Serializer):
    result = serializers.CharField()
    evidence_reference = serializers.CharField(required=False, allow_blank=True)
    result_data = serializers.JSONField(required=False)
    reason = serializers.CharField(required=False, allow_blank=True)


class OLPaymentObligationSerializer(serializers.ModelSerializer):
    policy_number = serializers.CharField(source="policy.policy_number", read_only=True, allow_null=True)
    proposal_number = serializers.CharField(source="proposal.proposal_number", read_only=True, allow_null=True)

    class Meta:
        model = OLPaymentObligation
        fields = "__all__"
        read_only_fields = _read_only_fields(model)


class OLPaymentAllocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = OLPaymentAllocation
        fields = "__all__"
        read_only_fields = _read_only_fields(model)


class OLPaymentAllocationCreateSerializer(serializers.Serializer):
    external_receipt_reference = serializers.CharField(max_length=120)
    amount = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0.01"))
    currency = serializers.CharField(max_length=3, required=False)
    metadata = serializers.JSONField(required=False)
    reason = serializers.CharField(required=False, allow_blank=True)


class OLPolicyPartySerializer(serializers.ModelSerializer):
    class Meta:
        model = OLPolicyParty
        fields = "__all__"
        read_only_fields = _read_only_fields(model)


class OLPremiumScheduleSerializer(serializers.ModelSerializer):
    policy_number = serializers.CharField(source="policy.policy_number", read_only=True)

    class Meta:
        model = OLPremiumSchedule
        fields = "__all__"
        read_only_fields = _read_only_fields(model)


class OLPremiumInstallmentSerializer(serializers.ModelSerializer):
    policy_number = serializers.CharField(source="schedule.policy.policy_number", read_only=True)

    class Meta:
        model = OLPremiumInstallment
        fields = "__all__"
        read_only_fields = _read_only_fields(model)


class OLPolicyTransactionSerializer(serializers.ModelSerializer):
    policy_number = serializers.CharField(source="policy.policy_number", read_only=True)
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = OLPolicyTransaction
        fields = "__all__"
        read_only_fields = _read_only_fields(model)

    def get_created_by_name(self, obj):
        if not obj.created_by:
            return "System"
        return obj.created_by.get_full_name() or obj.created_by.email or str(obj.created_by_id)


class OLEndorsementSerializer(serializers.ModelSerializer):
    policy_number = serializers.CharField(source="policy.policy_number", read_only=True)

    class Meta:
        model = OLEndorsement
        fields = "__all__"
        read_only_fields = [
            "endorsement_number", "status", "approved_by", "approved_at", "applied_at",
            "before_snapshot", "after_snapshot", "applied_transaction", "created_by",
            "created_at", "updated_at",
        ]


class OLEndorsementCreateSerializer(serializers.Serializer):
    endorsement_type = serializers.CharField(max_length=50)
    requested_effective_date = serializers.DateField()
    requested_changes = serializers.JSONField()
    reason = serializers.CharField(required=False, allow_blank=True)
    idempotency_key = serializers.CharField(required=False, allow_blank=True)


class OLPolicyRenewalSerializer(serializers.ModelSerializer):
    policy_number = serializers.CharField(source="policy.policy_number", read_only=True)

    class Meta:
        model = OLPolicyRenewal
        fields = "__all__"
        read_only_fields = [
            "renewal_number", "status", "before_snapshot", "after_snapshot", "approved_by",
            "approved_at", "applied_at", "applied_transaction", "payment_obligation", "created_by",
            "created_at", "updated_at",
        ]


class OLPolicyRenewalCreateSerializer(serializers.Serializer):
    requested_effective_date = serializers.DateField()
    new_end_date = serializers.DateField()
    reason = serializers.CharField(required=False, allow_blank=True)
    idempotency_key = serializers.CharField(required=False, allow_blank=True)


class OLReinstatementRequestSerializer(serializers.ModelSerializer):
    policy_number = serializers.CharField(source="policy.policy_number", read_only=True)

    class Meta:
        model = OLReinstatementRequest
        fields = "__all__"
        read_only_fields = [
            "request_number", "status", "before_snapshot", "after_snapshot", "approved_by",
            "approved_at", "applied_at", "applied_transaction", "payment_obligation", "created_by",
            "created_at", "updated_at",
        ]


class OLReinstatementCreateSerializer(serializers.Serializer):
    requested_effective_date = serializers.DateField()
    reason = serializers.CharField(required=False, allow_blank=True)
    idempotency_key = serializers.CharField(required=False, allow_blank=True)


class OLPolicyStatusHistorySerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()

    class Meta:
        model = OLPolicyStatusHistory
        fields = "__all__"
        read_only_fields = _read_only_fields(model)

    def get_actor_name(self, obj):
        if not obj.actor:
            return "System"
        return obj.actor.get_full_name() or obj.actor.email or str(obj.actor_id)


class OLDocumentRecordSerializer(serializers.ModelSerializer):
    policy_number = serializers.CharField(source="policy.policy_number", read_only=True, allow_null=True)
    proposal_number = serializers.CharField(source="proposal.proposal_number", read_only=True, allow_null=True)

    class Meta:
        model = OLDocumentRecord
        fields = "__all__"
        read_only_fields = [
            "status", "uploaded_by", "verified_by", "rejected_by", "uploaded_at", "verified_at",
            "rejected_at", "status_reason", "created_at",
        ]


class OLDocumentCreateSerializer(serializers.Serializer):
    proposal = serializers.UUIDField(required=False, allow_null=True)
    policy = serializers.UUIDField(required=False, allow_null=True)
    document_type = serializers.CharField(max_length=80)
    file_reference = serializers.CharField(max_length=255, required=False, allow_blank=True)
    metadata = serializers.JSONField(required=False)
    idempotency_key = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        if not attrs.get("proposal") and not attrs.get("policy"):
            raise serializers.ValidationError("Either proposal or policy is required.")
        if attrs.get("proposal") and attrs.get("policy"):
            raise serializers.ValidationError("A document must have exactly one parent.")
        return attrs


class OLNoteSerializer(serializers.ModelSerializer):
    policy_number = serializers.CharField(source="policy.policy_number", read_only=True, allow_null=True)
    proposal_number = serializers.CharField(source="proposal.proposal_number", read_only=True, allow_null=True)
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = OLNote
        fields = "__all__"
        read_only_fields = ["created_by", "created_at"]

    def get_created_by_name(self, obj):
        return obj.created_by.get_full_name() or obj.created_by.email or str(obj.created_by_id)


class OLNoteCreateSerializer(serializers.Serializer):
    proposal = serializers.UUIDField(required=False, allow_null=True)
    policy = serializers.UUIDField(required=False, allow_null=True)
    content = serializers.CharField()
    is_internal = serializers.BooleanField(required=False, default=True)
    idempotency_key = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        if not attrs.get("proposal") and not attrs.get("policy"):
            raise serializers.ValidationError("Either proposal or policy is required.")
        if attrs.get("proposal") and attrs.get("policy"):
            raise serializers.ValidationError("A note must have exactly one parent.")
        return attrs


class OLBeneficiaryAllocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = OLBeneficiaryAllocation
        fields = "__all__"
        read_only_fields = _read_only_fields(model)


class OLApprovalActionSerializer(serializers.Serializer):
    approval_id = serializers.UUIDField()
    comments = serializers.CharField(required=False, allow_blank=True)


class OLPolicyIssueSerializer(serializers.Serializer):
    proposal = serializers.UUIDField()
    effective_date = serializers.DateField(required=False)
    beneficiary_allocations = serializers.ListField(
        child=serializers.JSONField(),
        allow_empty=False,
    )
    reason = serializers.CharField(required=False, allow_blank=True)
    idempotency_key = serializers.CharField(required=False, allow_blank=True)


class OLWorkflowEventReadSerializer(OLWorkflowEventSerializer):
    pass


class OLUnderwritingDecisionEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = OLUnderwritingDecisionEvent
        fields = "__all__"
        read_only_fields = _read_only_fields(model)
