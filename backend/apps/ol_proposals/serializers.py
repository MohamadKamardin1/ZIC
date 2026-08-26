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


class OLHealthQuestionnaireItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    sequence = serializers.IntegerField()
    mandatory = serializers.BooleanField()
    trigger_medical_requirement = serializers.BooleanField()
    scoring_threshold = serializers.SerializerMethodField()
    question_id = serializers.UUIDField(source="health_question_id")
    question_code = serializers.CharField(source="health_question.code", read_only=True)
    question_text = serializers.CharField(source="health_question.question_text", read_only=True)
    answer_type = serializers.CharField(source="health_question.answer_type", read_only=True)
    category = serializers.CharField(source="health_question.category", read_only=True)
    underwriting_impact = serializers.CharField(source="health_question.underwriting_impact", read_only=True)

    def get_scoring_threshold(self, item):
        return str(item.score) if item.score is not None else None


class OLProposalBaseSerializer(serializers.ModelSerializer):
    quotation_number = serializers.CharField(source="quotation.quote_number", read_only=True)
    bank_account_number = serializers.SerializerMethodField()

    def get_bank_account_number(self, obj):
        from apps.ol_proposals.services.enrichment_service import mask_account_number

        return mask_account_number(obj.bank_account_number)

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
            "employment_reference",
            "payroll_deduction",
            "intermediary_channel",
            "declaration_pep_flag",
            "declaration_aml_flag",
            "existing_policies_count",
            "occupation_risk_note",
            "declarations_free_text",
            "bank_name",
            "bank_account_name",
            "bank_account_number",
            "created_at",
            "updated_at",
        )


class OLProposalListSerializer(serializers.ModelSerializer):
    policyholder = serializers.SerializerMethodField()
    agent = serializers.SerializerMethodField()
    employer = serializers.SerializerMethodField()
    product = serializers.SerializerMethodField()
    plan = serializers.SerializerMethodField()
    total_premium = serializers.SerializerMethodField()
    status_badge = serializers.SerializerMethodField()
    first_premium_posted = serializers.SerializerMethodField()
    allowed_actions = serializers.SerializerMethodField()

    def _selected_config(self, obj):
        configs = list(obj.plan_configs.all())
        return configs[0] if configs else None

    def get_policyholder(self, obj):
        return obj.partner_name_snapshot or "-"

    def get_agent(self, obj):
        return obj.agent_name_snapshot or "-"

    def get_employer(self, obj):
        return obj.employer_name_snapshot or "-"

    def get_product(self, obj):
        config = self._selected_config(obj)
        product = getattr(getattr(config, "product_version", None), "product", None) if config else None
        if product is None:
            return "-"
        code = (getattr(product, "code", "") or "").strip()
        name = (getattr(product, "name", "") or "").strip()
        return f"{code} - {name}".strip() or "-"

    def get_plan(self, obj):
        config = self._selected_config(obj)
        plan = getattr(config, "plan", None) if config else None
        if plan is None:
            return "-"
        return (config.plan_name_snapshot or getattr(plan, "name", "") or getattr(plan, "code", "") or "-").strip()

    def get_total_premium(self, obj):
        snapshot = obj.financial_summary_snapshot or {}
        value = snapshot.get("total_premium")
        if value is None:
            config = self._selected_config(obj)
            value = config.premium_amount if config and config.premium_amount is not None else None
        return str(value) if value is not None else ""

    def get_status_badge(self, obj):
        names = self.context.setdefault("_status_names", {})
        if not names:
            from apps.ol_parameters.models import OLProposalStatus

            names.update(
                {
                    row.code.upper(): row.name
                    for row in OLProposalStatus.objects.filter(applies_to__iexact="PROPOSAL", is_active=True)
                }
            )
        return {"code": obj.status, "name": names.get((obj.status or "").upper(), obj.status)}

    def get_first_premium_posted(self, obj):
        commitment = obj.first_premium_commitment
        if commitment is None:
            return False
        posted = (commitment.status or "").strip().upper() == "COMPLETED"
        paid = (commitment.amount_paid or 0) + (commitment.amount_waived or 0)
        return bool(posted and paid >= (commitment.premium_amount or 0))

    def get_allowed_actions(self, obj):
        from apps.ol_proposals.services.lifecycle_service import allowed_actions

        request = self.context.get("request")
        actor = request.user if request else None
        return allowed_actions(obj, actor=actor)

    class Meta:
        model = OLProposal
        fields = (
            "id",
            "proposal_number",
            "policyholder",
            "agent",
            "employer",
            "product",
            "plan",
            "total_premium",
            "currency",
            "status",
            "status_badge",
            "payment_ready",
            "first_premium_posted",
            "expiry_date",
            "created_at",
            "allowed_actions",
        )


class PartnerPortalProposalListSerializer(serializers.ModelSerializer):
    policyholder = serializers.SerializerMethodField()
    agent = serializers.SerializerMethodField()
    employer = serializers.SerializerMethodField()
    product = serializers.SerializerMethodField()
    plan = serializers.SerializerMethodField()
    total_premium = serializers.SerializerMethodField()
    status_badge = serializers.SerializerMethodField()

    def _selected_config(self, obj):
        configs = list(obj.plan_configs.all())
        return configs[0] if configs else None

    def get_policyholder(self, obj):
        return obj.partner_name_snapshot or "-"

    def get_agent(self, obj):
        return obj.agent_name_snapshot or "-"

    def get_employer(self, obj):
        return obj.employer_name_snapshot or "-"

    def get_product(self, obj):
        config = self._selected_config(obj)
        product = getattr(getattr(config, "product_version", None), "product", None) if config else None
        if product is None:
            return "-"
        return f"{getattr(product, 'code', '') or ''} - {getattr(product, 'name', '') or ''}".strip() or "-"

    def get_plan(self, obj):
        config = self._selected_config(obj)
        plan = getattr(config, "plan", None) if config else None
        if plan is None:
            return "-"
        return (config.plan_name_snapshot or getattr(plan, "name", "") or getattr(plan, "code", "") or "-").strip()

    def get_total_premium(self, obj):
        snapshot = obj.financial_summary_snapshot or {}
        value = snapshot.get("total_premium")
        return str(value) if value is not None else ""

    def get_status_badge(self, obj):
        names = self.context.setdefault("_status_names", {})
        if not names:
            from apps.ol_parameters.models import OLProposalStatus

            names.update(
                {row.code.upper(): row.name for row in OLProposalStatus.objects.filter(applies_to__iexact="PROPOSAL", is_active=True)}
            )
        return {"code": obj.status, "name": names.get((obj.status or "").upper(), obj.status)}

    class Meta:
        model = OLProposal
        fields = (
            "id",
            "proposal_number",
            "policyholder",
            "agent",
            "employer",
            "product",
            "plan",
            "total_premium",
            "currency",
            "status_badge",
            "expiry_date",
            "created_at",
        )


class PartnerPortalProposalDetailSerializer(PartnerPortalProposalListSerializer):
    quotation_number = serializers.CharField(source="quotation.quote_number", read_only=True)
    beneficiaries = OLProposalBeneficiarySerializer(many=True, read_only=True)
    documents = OLProposalDocumentSerializer(many=True, read_only=True)
    first_premium = serializers.SerializerMethodField()

    def get_first_premium(self, obj):
        from apps.ol_proposals.services.first_premium_service import first_premium_status

        status = first_premium_status(obj)
        if not status["linked"]:
            return {"linked": False, "first_premium_posted": False}
        commitment = status["commitment"]
        return {
            "linked": True,
            "commitment_number": commitment["commitment_number"],
            "status": commitment["status"],
            "amount_due": commitment["amount_due"],
            "amount_paid": commitment["amount_paid"],
            "balance": commitment["balance"],
            "first_premium_posted": status["first_premium_posted"],
        }

    class Meta(PartnerPortalProposalListSerializer.Meta):
        fields = PartnerPortalProposalListSerializer.Meta.fields + (
            "quotation_number",
            "beneficiaries",
            "documents",
            "first_premium",
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
    first_premium = serializers.SerializerMethodField()
    receipts = serializers.SerializerMethodField()

    def get_first_premium(self, obj):
        from apps.ol_proposals.services.first_premium_service import first_premium_status

        return first_premium_status(obj)

    def get_receipts(self, obj):
        from apps.ol_proposals.services.first_premium_service import proposal_receipt_references

        return proposal_receipt_references(obj)

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
            "first_premium",
            "receipts",
        )