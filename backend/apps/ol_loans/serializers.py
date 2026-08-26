from rest_framework import serializers

from decimal import Decimal

from .models import OLLoan, OLLoanInterestAccrual, OLLoanOffset, OLLoanRepayment, OLLoanSchedule


def _display(instance, *attributes):
    for attribute in attributes:
        value = getattr(instance, attribute, None)
        if value:
            return str(value)
    return ""


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
            "amount_paid",
            "balance",
            "status",
        )


class OLLoanRepaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = OLLoanRepayment
        fields = (
            "id",
            "receipt_ref",
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


class OLLoanDetailSerializer(OLLoanListSerializer):
    schedules = OLLoanScheduleSerializer(many=True, read_only=True)
    repayments = OLLoanRepaymentSerializer(many=True, read_only=True)
    interest_accruals = OLLoanInterestAccrualSerializer(many=True, read_only=True)
    offsets = OLLoanOffsetSerializer(many=True, read_only=True)

    class Meta(OLLoanListSerializer.Meta):
        fields = OLLoanListSerializer.Meta.fields + (
            "schedules",
            "repayments",
            "interest_accruals",
            "offsets",
        )
