from django.db.models import Q
from rest_framework import serializers

from apps.ol_commitments.models import OLCommitment

from .models import (
    MaturityClaim,
    Policy,
    PolicyAuditLog,
    PolicyBenefit,
    PolicyEndorsement,
    PolicyLoan,
    PolicyLoanRepayment,
    PolicyMember,
    PolicyRider,
    SurrenderRequest,
    WithdrawalPayment,
    WithdrawalRequest,
)


def _partner_label(partner):
    if not partner:
        return ""
    number = getattr(partner, "partner_number", "") or ""
    name = getattr(partner, "legal_name", "") or ""
    if not name:
        name = " ".join(
            value
            for value in (
                getattr(partner, "first_name", ""),
                getattr(partner, "other_name", ""),
                getattr(partner, "surname", ""),
            )
            if value
        )
    return " — ".join(part for part in (number, name) if part) or "Unnamed partner"


def _policy_plan_snapshot(policy):
    snapshot = policy.contract_snapshot if isinstance(policy.contract_snapshot, dict) else {}
    plans = snapshot.get("plans", [])
    return [plan for plan in plans if isinstance(plan, dict)]


def _status_allowed_actions(status):
    actions = {
        "ACTIVE": ["view", "service", "endorse", "print", "cancel"],
        "LAPSED": ["view", "service", "reinstate", "print"],
        "PAID_UP": ["view", "service", "print"],
        "SURRENDER_PENDING": ["view", "print"],
        "SURRENDERED": ["view", "print"],
        "MATURED_PENDING_PAYMENT": ["view", "print"],
        "MATURED": ["view", "print"],
        "EXPIRED": ["view", "print"],
        "CANCELLED": ["view", "print"],
        "CLAIM_SETTLED": ["view", "print"],
        "TERMINATED": ["view", "print"],
    }
    return actions.get((status or "").upper(), ["view"])


class PolicyMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = PolicyMember
        fields = ("id", "member_relation", "name", "dob", "gender", "benefit_amount", "created_at", "updated_at")
        read_only_fields = fields


class PolicyRiderSerializer(serializers.ModelSerializer):
    class Meta:
        model = PolicyRider
        fields = ("id", "rider_code", "sum_assured", "amount", "premium", "created_at", "updated_at")
        read_only_fields = fields


class PolicyBenefitSerializer(serializers.ModelSerializer):
    class Meta:
        model = PolicyBenefit
        fields = ("id", "benefit_type", "calculation_basis", "amount", "created_at", "updated_at")
        read_only_fields = fields


class PolicyEndorsementSerializer(serializers.ModelSerializer):
    class Meta:
        model = PolicyEndorsement
        fields = (
            "id",
            "endorsement_number",
            "endorsement_type",
            "effective_date",
            "description",
            "status",
            "before_snapshot",
            "after_snapshot",
            "reason",
            "source_channel",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class MaturityClaimSerializer(serializers.ModelSerializer):
    policy_number = serializers.CharField(source="policy.policy_number", read_only=True)
    payment_requisition_number = serializers.SerializerMethodField()

    class Meta:
        model = MaturityClaim
        fields = (
            "id",
            "claim_number",
            "policy_number",
            "claim_date",
            "maturity_value",
            "loan_deduction",
            "net_payout",
            "payout_method",
            "status",
            "approval_required",
            "documents_required",
            "documents_verified",
            "payment_requisition_number",
            "payment_reference",
            "reason",
            "created_at",
        )
        read_only_fields = fields

    def get_payment_requisition_number(self, obj):
        return getattr(obj.payment_requisition, "requisition_number", "") if obj.payment_requisition else ""


class PolicyLoanRepaymentSerializer(serializers.ModelSerializer):
    loan_number = serializers.CharField(source="loan.loan_number", read_only=True)

    class Meta:
        model = PolicyLoanRepayment
        fields = (
            "id",
            "repayment_number",
            "loan_number",
            "payment_date",
            "amount",
            "interest_component",
            "principal_component",
            "reason",
            "created_at",
        )
        read_only_fields = fields


class PolicyLoanSerializer(serializers.ModelSerializer):
    policy_number = serializers.CharField(source="policy.policy_number", read_only=True)
    repayments = PolicyLoanRepaymentSerializer(many=True, read_only=True)
    payment_requisition_number = serializers.SerializerMethodField()

    class Meta:
        model = PolicyLoan
        fields = (
            "id",
            "loan_number",
            "policy_number",
            "requested_at",
            "approved_at",
            "disbursed_at",
            "principal_amount",
            "outstanding_principal",
            "accrued_interest",
            "outstanding_interest",
            "interest_rate",
            "currency",
            "status",
            "approval_required",
            "payment_requisition_number",
            "repayment_options",
            "reason",
            "repayments",
            "created_at",
        )
        read_only_fields = fields

    def get_payment_requisition_number(self, obj):
        return getattr(obj.payment_requisition, "requisition_number", "") if obj.payment_requisition else ""


def _policy_snapshot_value(policy, *keys):
    snapshot = policy.contract_snapshot if isinstance(policy.contract_snapshot, dict) else {}
    for key in keys:
        value = snapshot.get(key)
        if value not in (None, ""):
            return str(value)
    return ""


def _policy_label(policy):
    return " — ".join(part for part in (policy.policy_number, _partner_label(policy.partner)) if part) or "Unnamed policy"


class WithdrawalPaymentSerializer(serializers.ModelSerializer):
    payment_mode_display = serializers.CharField(source="payment_mode", read_only=True)

    class Meta:
        model = WithdrawalPayment
        fields = (
            "id",
            "payment_mode",
            "payment_mode_display",
            "receipt_reference",
            "amount",
            "currency",
            "payment_date",
            "status",
            "created_at",
        )
        read_only_fields = fields


class WithdrawalRequestSerializer(serializers.ModelSerializer):
    policy_number = serializers.CharField(source="policy.policy_number", read_only=True)
    policy_id = serializers.UUIDField(source="policy.id", read_only=True)
    policy_display = serializers.SerializerMethodField()
    policyholder_name = serializers.SerializerMethodField()
    policyholder_display = serializers.SerializerMethodField()
    product_display = serializers.SerializerMethodField()
    agent_display = serializers.SerializerMethodField()
    branch_display = serializers.SerializerMethodField()
    currency = serializers.CharField(source="policy.currency", read_only=True)
    gross_amount = serializers.DecimalField(source="amount", max_digits=18, decimal_places=2, read_only=True)
    fee_amount = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)
    net_payout = serializers.DecimalField(source="net_amount", max_digits=18, decimal_places=2, read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    payment_requisition_number = serializers.SerializerMethodField()
    allowed_actions = serializers.SerializerMethodField()
    payments = WithdrawalPaymentSerializer(many=True, read_only=True)

    class Meta:
        model = WithdrawalRequest
        fields = (
            "id",
            "request_number",
            "policy_id",
            "policy_number",
            "policy_display",
            "policyholder_name",
            "policyholder_display",
            "product_display",
            "agent_display",
            "branch_display",
            "currency",
            "request_date",
            "amount",
            "gross_amount",
            "cash_value_before",
            "loan_balance_before",
            "cash_value_after",
            "fee_amount",
            "fee_rate",
            "fee_basis",
            "net_amount",
            "net_payout",
            "status",
            "status_display",
            "approved_at",
            "processed_at",
            "paid_at",
            "cancelled_at",
            "reversed_at",
            "payment_mode",
            "receipt_reference",
            "payment_requisition_number",
            "reason",
            "approval_reason",
            "cancellation_reason",
            "reversal_reason",
            "allowed_actions",
            "payments",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_policy_display(self, obj):
        return _policy_label(obj.policy)

    def get_policyholder_name(self, obj):
        partner = obj.policy.partner
        return " ".join(value for value in (getattr(partner, "first_name", ""), getattr(partner, "other_name", ""), getattr(partner, "surname", "")) if value) or getattr(partner, "legal_name", "") or "Unnamed policyholder"

    def get_policyholder_display(self, obj):
        return _partner_label(obj.policy.partner)

    def get_product_display(self, obj):
        code = obj.policy.product_plan_ref or ""
        snapshot_name = _policy_snapshot_value(obj.policy, "product_display", "product_name")
        if snapshot_name:
            return " — ".join(part for part in (code, snapshot_name) if part)
        try:
            from apps.ol_parameters.models import OLProduct

            product = OLProduct.objects.filter(code=code, is_active=True).first()
        except Exception:
            product = None
        return " — ".join(part for part in (code, getattr(product, "name", "")) if part) or "Unspecified product/plan"

    def get_agent_display(self, obj):
        return _partner_label(obj.policy.agent) if obj.policy.agent else _policy_snapshot_value(obj.policy, "agent_display", "agent_name", "agent_code")

    def get_branch_display(self, obj):
        return _policy_snapshot_value(obj.policy, "branch_display", "branch_name", "branch_code", "location_display", "location_name")

    def get_payment_requisition_number(self, obj):
        return getattr(obj.payment_requisition, "requisition_number", "") if obj.payment_requisition else ""

    def get_allowed_actions(self, obj):
        return withdrawal_allowed_actions(obj.status)


def withdrawal_allowed_actions(status):
    actions = {
        "REQUESTED": ["view", "approve", "reject", "cancel", "print"],
        "APPROVED": ["view", "process_payout", "cancel", "print"],
        "PROCESSING": ["view", "print"],
        "PAID": ["view", "reverse", "print"],
        "REVERSED": ["view", "print"],
        "DECLINED": ["view", "print"],
        "CANCELLED": ["view", "print"],
    }
    return actions.get((status or "").upper(), ["view"])


class SurrenderRequestSerializer(serializers.ModelSerializer):
    payment_requisition_number = serializers.SerializerMethodField()

    class Meta:
        model = SurrenderRequest
        fields = (
            "id",
            "request_number",
            "request_date",
            "surrender_value",
            "outstanding_loan_amount",
            "charges",
            "net_surrender_value",
            "status",
            "payment_requisition_number",
            "reason",
            "created_at",
        )
        read_only_fields = fields

    def get_payment_requisition_number(self, obj):
        return getattr(obj.payment_requisition, "requisition_number", "") if obj.payment_requisition else ""


class PolicyAuditLogSerializer(serializers.ModelSerializer):
    actor_display = serializers.SerializerMethodField()

    class Meta:
        model = PolicyAuditLog
        fields = (
            "id",
            "event_type",
            "from_status",
            "to_status",
            "before_snapshot",
            "after_snapshot",
            "reason",
            "source_channel",
            "correlation_id",
            "actor_display",
            "created_at",
        )
        read_only_fields = fields

    def get_actor_display(self, obj):
        if not obj.actor:
            return "System"
        return getattr(obj.actor, "get_full_name", lambda: "")() or getattr(obj.actor, "email", "") or "User"


class PolicyListSerializer(serializers.ModelSerializer):
    proposal_ref_display = serializers.SerializerMethodField()
    policyholder_display = serializers.SerializerMethodField()
    policyholder_name = serializers.SerializerMethodField()
    product_plan_display = serializers.CharField(source="product_plan_ref", read_only=True)
    product_name = serializers.SerializerMethodField()
    plan_name = serializers.SerializerMethodField()
    agent_display = serializers.SerializerMethodField()
    agent_name = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()
    allowed_actions = serializers.SerializerMethodField()

    class Meta:
        model = Policy
        fields = (
            "id",
            "policy_number",
            "proposal_ref_display",
            "policyholder_display",
            "policyholder_name",
            "product_plan_display",
            "product_name",
            "plan_name",
            "agent_display",
            "agent_name",
            "currency",
            "sum_assured",
            "premium_amount",
            "premium_frequency",
            "term_years",
            "risk_commencement_date",
            "maturity_date",
            "status",
            "status_display",
            "allowed_actions",
            "version",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_proposal_ref_display(self, obj):
        proposal = obj.proposal_ref
        return getattr(proposal, "proposal_number", "") or "Unnumbered proposal"

    def get_policyholder_display(self, obj):
        return _partner_label(obj.partner)

    def get_policyholder_name(self, obj):
        if not obj.partner:
            return ""
        return getattr(obj.partner, "legal_name", "") or self.get_policyholder_display(obj)

    def get_product_name(self, obj):
        plans = _policy_plan_snapshot(obj)
        product_names = [plan.get("product_code") for plan in plans if plan.get("product_code")]
        return ", ".join(dict.fromkeys(product_names)) or obj.product_plan_ref

    def get_plan_name(self, obj):
        plans = _policy_plan_snapshot(obj)
        plan_names = [plan.get("plan_name") or plan.get("plan_code") for plan in plans]
        return ", ".join(dict.fromkeys(name for name in plan_names if name)) or obj.product_plan_ref

    def get_agent_display(self, obj):
        return _partner_label(obj.agent)

    def get_agent_name(self, obj):
        if not obj.agent:
            return ""
        return getattr(obj.agent, "legal_name", "") or self.get_agent_display(obj)

    def get_status_display(self, obj):
        return obj.get_status_display()

    def get_allowed_actions(self, obj):
        return _status_allowed_actions(obj.status)


class PolicyDetailSerializer(PolicyListSerializer):
    members = PolicyMemberSerializer(many=True, read_only=True)
    riders = PolicyRiderSerializer(many=True, read_only=True)
    benefits = PolicyBenefitSerializer(many=True, read_only=True)
    endorsements = PolicyEndorsementSerializer(many=True, read_only=True)
    surrender_requests = SurrenderRequestSerializer(many=True, read_only=True)
    loans = PolicyLoanSerializer(many=True, read_only=True)
    withdrawal_requests = WithdrawalRequestSerializer(many=True, read_only=True)
    maturity_claims = MaturityClaimSerializer(many=True, read_only=True)
    audit_logs = PolicyAuditLogSerializer(many=True, read_only=True)
    linked_proposal = serializers.SerializerMethodField()
    linked_commitments = serializers.SerializerMethodField()
    installments = serializers.SerializerMethodField()
    ol_loan_summary = serializers.SerializerMethodField()

    class Meta(PolicyListSerializer.Meta):
        fields = PolicyListSerializer.Meta.fields + (
            "first_premium_receipt_ref",
            "contract_snapshot",
            "members",
            "riders",
            "benefits",
            "endorsements",
            "surrender_requests",
            "loans",
            "withdrawal_requests",
            "maturity_claims",
            "audit_logs",
            "linked_proposal",
            "linked_commitments",
            "installments",
            "ol_loan_summary",
        )

    def get_linked_proposal(self, obj):
        proposal = obj.proposal_ref
        return {
            "proposal_number": getattr(proposal, "proposal_number", ""),
            "status": getattr(proposal, "status", ""),
            "quotation_number": getattr(getattr(proposal, "quotation", None), "quote_number", ""),
        }

    def get_linked_commitments(self, obj):
        commitments = (
            OLCommitment.objects.filter(
                Q(source_reference=obj.policy_number) | Q(source_object_id=str(obj.pk))
            )
            .exclude(status__in=["COMPLETED", "CANCELLED", "REVERSED", "WAIVED", "CLOSED"])
            .order_by("due_date", "created_at")
        )
        return [
            {
                "commitment_number": commitment.commitment_number,
                "status": commitment.status,
                "currency": commitment.currency,
                "premium_frequency": commitment.premium_frequency,
                "due_date": commitment.due_date,
                "premium_amount": commitment.premium_amount,
                "amount_paid": commitment.amount_paid,
                "balance": commitment.balance,
            }
            for commitment in commitments
        ]

    def get_installments(self, obj):
        snapshot = obj.contract_snapshot if isinstance(obj.contract_snapshot, dict) else {}
        installments = snapshot.get("installments", [])
        return installments if isinstance(installments, list) else []

    def get_ol_loan_summary(self, obj):
        from apps.ol_loans.services.integration_service import policy_loan_summary

        return policy_loan_summary(obj.pk)
