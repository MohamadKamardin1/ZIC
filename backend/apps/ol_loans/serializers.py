from decimal import Decimal

from rest_framework import serializers

from .models import OLLoan, OLLoanDisbursement, OLLoanInterestAccrual, OLLoanOffset, OLLoanRepayment, OLLoanSchedule
from .services.loan_actions import allowed_actions


def _display(instance, *attributes):
    for attribute in attributes:
        value = getattr(instance, attribute, None)
        if value:
            return str(value)
    return ""


def _snapshot_dict(policy):
    snapshot = getattr(policy, "contract_snapshot", None)
    return snapshot if isinstance(snapshot, dict) else {}


def _snapshot_display(snapshot, *keys):
    for key in keys:
        value = snapshot.get(key)
        if isinstance(value, dict):
            value = value.get("label") or value.get("name") or value.get("code")
        if value:
            return str(value)
    return ""


class OLLoanDisbursementSerializer(serializers.ModelSerializer):
    requisition_number = serializers.CharField(source="requisition.requisition_number", read_only=True)

    class Meta:
        model = OLLoanDisbursement
        fields = (
            "id",
            "amount",
            "currency",
            "payment_mode",
            "bank_account_code",
            "disbursement_date",
            "status",
            "idempotency_key",
            "requisition_number",
            "reason",
            "created_at",
        )


class OLLoanScheduleSerializer(serializers.ModelSerializer):
    balance = serializers.DecimalField(max_digits=18, decimal_places=2, coerce_to_string=True)

    class Meta:
        model = OLLoanSchedule
        fields = (
            "id",
            "installment_number",
            "due_date",
            "principal_due",
            "interest_due",
            "penalty_due",
            "principal_paid",
            "interest_paid",
            "penalty_paid",
            "amount_paid",
            "balance",
            "status",
        )


class OLLoanRepaymentSerializer(serializers.ModelSerializer):
    receipt_number = serializers.CharField(source="receipt_allocation.receipt.receipt_number", read_only=True)
    receipt_id = serializers.CharField(source="receipt_allocation.receipt.id", read_only=True)

    class Meta:
        model = OLLoanRepayment
        fields = (
            "id",
            "receipt_ref",
            "receipt_number",
            "receipt_id",
            "amount",
            "currency",
            "exchange_rate",
            "allocation_breakdown",
            "reason",
            "source_channel",
            "created_at",
        )


class OLLoanInterestAccrualSerializer(serializers.ModelSerializer):
    class Meta:
        model = OLLoanInterestAccrual
        fields = (
            "id",
            "period_start",
            "period_end",
            "principal_base",
            "interest_amount",
            "penalty_amount",
            "cumulative_interest",
            "created_at",
        )


class OLLoanOffsetSerializer(serializers.ModelSerializer):
    class Meta:
        model = OLLoanOffset
        fields = (
            "id",
            "source_type",
            "source_id",
            "offset_amount",
            "remaining_payout",
            "reason",
            "created_at",
        )


class OLLoanListSerializer(serializers.ModelSerializer):
    policy_display = serializers.SerializerMethodField()
    policy_number = serializers.SerializerMethodField()
    policyholder_name = serializers.SerializerMethodField()
    partner_display = serializers.SerializerMethodField()
    product_display = serializers.SerializerMethodField()
    agent_display = serializers.SerializerMethodField()
    branch_display = serializers.SerializerMethodField()
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    allowed_actions = serializers.SerializerMethodField()

    class Meta:
        model = OLLoan
        fields = (
            "id",
            "loan_number",
            "policy_number",
            "policy_display",
            "policyholder_name",
            "partner_display",
            "product_display",
            "agent_display",
            "branch_display",
            "currency",
            "principal_amount",
            "cash_value_snapshot",
            "disbursed_amount",
            "repayment_mode",
            "interest_rate",
            "compounding_frequency",
            "term_months",
            "disbursement_date",
            "maturity_date",
            "status",
            "status_display",
            "total_repaid",
            "outstanding_balance",
            "approval_required",
            "approved_at",
            "rejected_at",
            "rejection_reason",
            "reason",
            "allowed_actions",
            "created_at",
            "updated_at",
        )

    def get_policy_display(self, obj):
        policy = obj.policy_ref
        return _display(policy, "policy_number", "proposal_ref_id")

    def get_policy_number(self, obj):
        return self.get_policy_display(obj)

    def get_policyholder_name(self, obj):
        return _display(obj.partner, "legal_name", "partner_number")

    def get_partner_display(self, obj):
        return self.get_policyholder_name(obj)

    def get_product_display(self, obj):
        policy = obj.policy_ref
        snapshot = _snapshot_dict(policy)
        return (
            _snapshot_display(snapshot, "product_display", "product_name", "plan_display", "plan_name")
            or getattr(policy, "product_plan_ref", "")
            or "Not configured"
        )

    def get_agent_display(self, obj):
        agent = getattr(obj.policy_ref, "agent", None)
        return _display(agent, "legal_name", "partner_number") or "Not assigned"

    def get_branch_display(self, obj):
        snapshot = _snapshot_dict(obj.policy_ref)
        return _snapshot_display(snapshot, "branch_display", "branch_name", "branch", "location_display", "location_name") or "Not recorded"

    def get_allowed_actions(self, obj):
        request = self.context.get("request")
        return allowed_actions(obj, getattr(request, "user", None))


class OLLoanRequestSerializer(serializers.Serializer):
    requested_amount = serializers.DecimalField(max_digits=18, decimal_places=2, min_value=Decimal("0.01"))
    term_months = serializers.IntegerField(min_value=1)
    repayment_mode = serializers.CharField(max_length=40)
    reason = serializers.CharField(max_length=2000, allow_blank=False, trim_whitespace=True)
    as_of = serializers.DateField(required=False)


class OLLoanPortalRequestSerializer(OLLoanRequestSerializer):
    policy_number = serializers.CharField(max_length=100, trim_whitespace=True)


class OLLoanDisbursementRequestSerializer(serializers.Serializer):
    payment_mode = serializers.CharField(max_length=40, trim_whitespace=True)
    bank_account_code = serializers.CharField(max_length=50, required=False, allow_blank=True, trim_whitespace=True)
    as_of = serializers.DateField(required=False)
    reason = serializers.CharField(max_length=2000, required=False, allow_blank=True, trim_whitespace=True)


class OLLoanRepaymentRequestSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=18, decimal_places=2, min_value=Decimal("0.01"))
    currency = serializers.CharField(max_length=3)
    payment_mode = serializers.CharField(max_length=40, required=False, allow_blank=True, trim_whitespace=True)
    exchange_rate = serializers.DecimalField(max_digits=18, decimal_places=8, min_value=Decimal("0.00000001"), required=False)
    receipt_ref = serializers.CharField(max_length=120, required=False, allow_blank=True, trim_whitespace=True)
    reason = serializers.CharField(max_length=2000, required=False, allow_blank=True, trim_whitespace=True)
    payment_date = serializers.DateField(required=False)


class OLLoanOffsetRequestSerializer(serializers.Serializer):
    source_type = serializers.ChoiceField(choices=("SURRENDER", "MATURITY", "CLAIM"))
    source_id = serializers.CharField(max_length=120, trim_whitespace=True)
    payout_amount = serializers.DecimalField(max_digits=18, decimal_places=2, min_value=Decimal("0.01"))
    reason = serializers.CharField(max_length=2000, required=False, allow_blank=True, trim_whitespace=True)


class OLLoanApprovalSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=2000, required=False, allow_blank=True, trim_whitespace=True)


class OLLoanRejectionSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=2000, required=False, allow_blank=True, trim_whitespace=True)


class OLLoanBulkActionSerializer(serializers.Serializer):
    loan_ids = serializers.ListField(child=serializers.UUIDField(), allow_empty=False)
    reason = serializers.CharField(max_length=2000, required=False, allow_blank=True, trim_whitespace=True)


class OLLoanDetailSerializer(OLLoanListSerializer):
    disbursement = OLLoanDisbursementSerializer(read_only=True)
    schedules = OLLoanScheduleSerializer(many=True, read_only=True)
    repayments = OLLoanRepaymentSerializer(many=True, read_only=True)
    interest_accruals = OLLoanInterestAccrualSerializer(many=True, read_only=True)
    offsets = OLLoanOffsetSerializer(many=True, read_only=True)
    header = serializers.SerializerMethodField()
    audit_timeline = serializers.SerializerMethodField()

    class Meta(OLLoanListSerializer.Meta):
        fields = OLLoanListSerializer.Meta.fields + (
            "header",
            "disbursement",
            "schedules",
            "repayments",
            "interest_accruals",
            "offsets",
            "audit_timeline",
        )

    def get_header(self, obj):
        return {
            "loan_number": obj.loan_number,
            "policy_number": self.get_policy_number(obj),
            "policyholder_name": self.get_policyholder_name(obj),
            "product": self.get_product_display(obj),
            "agent": self.get_agent_display(obj),
            "branch": self.get_branch_display(obj),
            "principal": str(obj.principal_amount),
            "outstanding_balance": str(obj.outstanding_balance),
            "currency": obj.currency,
            "status": obj.status,
            "status_display": obj.get_status_display(),
        }

    def get_audit_timeline(self, obj):
        from apps.governance.models import AuditLog

        logs = (
            AuditLog.objects.filter(app_label="ol_loans", object_id=str(obj.pk))
            .select_related("user")
            .order_by("created_at", "timestamp")[:100]
        )
        entries = []
        for log in logs:
            before = log.before_state or {}
            after = log.after_state or {}
            actor = log.user
            entries.append(
                {
                    "action": log.action or log.action_type,
                    "from_status": before.get("status", ""),
                    "to_status": after.get("status", "") or before.get("status", ""),
                    "actor_name": (actor.get_full_name() or actor.username) if actor else "System",
                    "created_at": log.created_at,
                    "reason": log.reason or log.description or "",
                    "source_channel": log.source_channel,
                    "correlation_id": log.correlation_id or log.request_id or "",
                }
            )
        return entries
