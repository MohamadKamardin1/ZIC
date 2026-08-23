from rest_framework import serializers

from .models import (
    OLProposal,
    OLProposalBeneficiary,
    OLProposalBenefit,
    OLProposalDocument,
    OLProposalFundAllocation,
    OLProposalHealthAnswer,
    OLProposalInstallmentConfig,
    OLProposalInstallmentRateRow,
    OLProposalMember,
    OLProposalPlanConfig,
    OLProposalRider,
)


class OLProposalPlanConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = OLProposalPlanConfig
        fields = (
            "id",
            "product_version",
            "plan",
            "plan_name_snapshot",
            "sub_product_code",
            "section_number",
            "base_sum_assured",
            "term_years",
            "payment_period_years",
            "premium_frequency",
            "quote_basis",
            "estimated_maturity_value",
            "premium_factor",
            "premium_amount",
            "is_selected",
        )


class OLProposalMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = OLProposalMember
        fields = ("id", "member_type", "partner", "full_name_snapshot", "first_name", "last_name", "identity_number", "date_of_birth", "age_at_quote", "gender", "smoker_status", "relationship", "contact_phone", "contact_email", "member_sum_assured", "coverage_basis")


class OLProposalInstallmentRateRowSerializer(serializers.ModelSerializer):
    class Meta:
        model = OLProposalInstallmentRateRow
        fields = ("id", "sequence", "period_from", "period_to", "description", "rate_percent", "rate", "charge", "notes")


class OLProposalInstallmentConfigSerializer(serializers.ModelSerializer):
    rate_rows = OLProposalInstallmentRateRowSerializer(many=True, read_only=True)

    class Meta:
        model = OLProposalInstallmentConfig
        fields = ("id", "plan_config", "frequency", "annuity_period_years", "number_of_installments", "after_maturity_benefits", "before_maturity_benefits", "installment_amount", "first_due_date", "currency", "is_selected", "rate_rows")


class OLProposalFundAllocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = OLProposalFundAllocation
        fields = ("id", "plan_config", "fund", "fund_name_snapshot", "allocation_percentage", "allocation_amount", "is_selected")


class OLProposalRiderSerializer(serializers.ModelSerializer):
    class Meta:
        model = OLProposalRider
        fields = ("id", "rider", "rider_name_snapshot", "plan_config", "rider_sum_assured", "rider_term_years", "beneficial_type", "benefit_basis", "benefit_value", "loading", "discount", "premium_amount", "is_selected")


class OLProposalBenefitSerializer(serializers.ModelSerializer):
    class Meta:
        model = OLProposalBenefit
        fields = ("id", "plan_config", "code", "name", "benefit_type", "basis", "value", "loading", "discount", "maximum_cap", "sum_assured", "premium_amount", "is_selected")


class OLProposalBeneficiarySerializer(serializers.ModelSerializer):
    class Meta:
        model = OLProposalBeneficiary
        fields = ("id", "person_name", "identity_type", "identity_number", "beneficial_type", "beneficial_type_name_snapshot", "share_percent", "is_primary", "is_minor", "guardian_name", "guardian_identity_type", "guardian_identity_number", "guardian_relationship")


class OLProposalDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = OLProposalDocument
        fields = ("id", "document_type", "file_reference", "mandatory", "status", "rejection_reason", "uploaded_by", "uploaded_at")


class OLProposalHealthAnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = OLProposalHealthAnswer
        fields = ("id", "questionnaire_item", "health_question", "answer", "score", "triggers_medical", "answered_at")


class OLProposalBaseSerializer(serializers.ModelSerializer):
    quotation_number = serializers.CharField(source="quotation.quote_number", read_only=True)

    class Meta:
        model = OLProposal
        fields = (
            "id",
            "proposal_number",
            "quotation",
            "quotation_number",
            "quotation_version",
            "status",
            "partner",
            "partner_name_snapshot",
            "agent_partner",
            "agent_name_snapshot",
            "employer_partner",
            "employer_name_snapshot",
            "currency",
            "expiry_date",
            "payment_ready",
            "payment_ready_at",
            "underwriting_status",
            "medical_required",
            "converted_policy",
            "reason_code",
            "reason_text",
            "source_channel",
            "created_at",
            "updated_at",
        )


class OLProposalDetailSerializer(OLProposalBaseSerializer):
    plan_configs = OLProposalPlanConfigSerializer(many=True, read_only=True)
    members = OLProposalMemberSerializer(many=True, read_only=True)
    installment_configs = OLProposalInstallmentConfigSerializer(many=True, read_only=True)
    fund_allocations = OLProposalFundAllocationSerializer(many=True, read_only=True)
    riders = OLProposalRiderSerializer(many=True, read_only=True)
    benefits = OLProposalBenefitSerializer(many=True, read_only=True)
    beneficiaries = OLProposalBeneficiarySerializer(many=True, read_only=True)
    documents = OLProposalDocumentSerializer(many=True, read_only=True)
    health_answers = OLProposalHealthAnswerSerializer(many=True, read_only=True)

    class Meta(OLProposalBaseSerializer.Meta):
        fields = OLProposalBaseSerializer.Meta.fields + (
            "plan_configs",
            "members",
            "installment_configs",
            "fund_allocations",
            "riders",
            "benefits",
            "beneficiaries",
            "documents",
            "health_answers",
        )