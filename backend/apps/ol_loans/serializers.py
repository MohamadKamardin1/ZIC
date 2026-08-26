from rest_framework import serializers

from decimal import Decimal

from .models import OLLoan, OLLoanDisbursement, OLLoanInterestAccrual, OLLoanOffset, OLLoanRepayment, OLLoanSchedule


def _display(instance, *attributes):
    for attribute in attributes:
        value = getattr(instance, attribute, None)
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

    class Meta:
        model = OLLoanRepayment
        fields = (
            "id",
            "receipt_ref",
            "receipt_number",
            "amount",
            "currency",
            "exchange_rate",
            "allocation_breakdown",
            "reason",
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
    partner_display = serializers.SerializerMethodField()
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = OLLoan
        fields = (
            "id",
            "loan_number",
            "policy_ref",
            "policy_display",
            "partner",
            "partner_display",
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
            "approval_request",
            "approved_by",
            "approved_at",
            "rejected_by",
            "rejected_at",
            "rejection_reason",
            "reason",
            "created_at",
            "updated_at",
        )

    def get_policy_display(self, obj):
        policy = obj.policy_ref
        return _display(policy, "policy_number", "proposal_ref_id")

    def get_partner_display(self, obj):
        return _display(obj.partner, "legal_name", "partner_number")


class OLLoanRequestSerializer(serializers.Serializer):
    requested_amount = serializers.DecimalField(max_digits=18, decimal_places=2, min_value=Decimal("0.01"))
    term_months = serializers.IntegerField(min_value=1)
    repayment_mode = serializers.CharField(max_length=40)
    reason = serializers.CharField(max_length=2000, allow_blank=False, trim_whitespace=True)
    as_of = serializers.DateField(required=False)


class OLLoanDisbursementRequestSerializer(serializers.Serializer):
    payment_mode = serializers.CharField(max_length=40, trim_whitespace=True)
    bank_account_code = serializers.CharField(max_length=50, required=False, allow_blank=True, trim_whitespace=True)
    as_of = serializers.DateField(required=False)
    reason = serializers.CharField(max_length=2000, required=False, allow_blank=True, trim_whitespace=True)


class OLLoanRepaymentRequestSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=18, decimal_places=2, min_value=Decimal("0.01"))
    currency = serializers.CharField(max_length=3)
    exchange_rate = serializers.DecimalField(max_digits=18, decimal_places=8, min_value=Decimal("0.00000001"), required=False)
    receipt_ref = serializers.CharField(max_length=120, required=False, allow_blank=True, trim_whitespace=True)
    reason = serializers.CharField(max_length=2000, required=False, allow_blank=True, trim_whitespace=True)
    payment_date = serializers.DateField(required=False)


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

    class Meta(OLLoanListSerializer.Meta):
        fields = OLLoanListSerializer.Meta.fields + (
            "disbursement",
            "schedules",
            "repayments",
            "interest_accruals",
            "offsets",
        )
