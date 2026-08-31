from decimal import Decimal

from django.db.models import Q, Sum
from rest_framework import serializers

from apps.governance.models import AuditLog

from .models import (
    InstallmentItemStatus,
    InstallmentPlanStatus,
    OLInstallmentItem,
    OLMaturityInstallmentConfig,
    OLMaturityInstallmentPlan,
)
from .permissions import has_ol_maturity_installment_permission


def _partner_name(partner):
    if not partner:
        return "Unassigned"
    legal_name = getattr(partner, "legal_name", "") or ""
    if legal_name:
        return legal_name
    return (
        " ".join(
            part
            for part in (
                getattr(partner, "first_name", ""),
                getattr(partner, "other_name", ""),
                getattr(partner, "surname", ""),
            )
            if part
        )
        or getattr(partner, "partner_number", "")
        or "Unassigned"
    )


def _partner_display(partner):
    if not partner:
        return "Unassigned"
    number = getattr(partner, "partner_number", "") or ""
    return " — ".join(part for part in (number, _partner_name(partner)) if part)


def _money(value):
    return str((value or Decimal("0.00")).quantize(Decimal("0.01")))


class OLInstallmentItemSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    payment_requisition_number = serializers.CharField(
        source="payment_requisition_ref.requisition_number", read_only=True, default=None
    )
    paid_by_display = serializers.SerializerMethodField()
    allowed_actions = serializers.SerializerMethodField()

    class Meta:
        model = OLInstallmentItem
        fields = (
            "id",
            "installment_number",
            "due_date",
            "amount",
            "status",
            "status_display",
            "payment_requisition_number",
            "payment_reference",
            "payment_bank_details",
            "paid_date",
            "paid_by_display",
            "narration",
            "allowed_actions",
        )
        read_only_fields = fields

    def get_paid_by_display(self, obj):
        user = obj.paid_by
        return user.get_full_name() or user.email if user else "System"

    def get_allowed_actions(self, obj):
        actions = _item_allowed_actions(obj.status)
        request = self.context.get("request")
        user = getattr(request, "user", None) if request else None
        if user and not getattr(user, "is_superuser", False):
            actions = [action for action in actions if has_ol_maturity_installment_permission(user, action)]
        return actions


class OLMaturityInstallmentConfigSerializer(serializers.ModelSerializer):
    configured_by_display = serializers.SerializerMethodField()

    class Meta:
        model = OLMaturityInstallmentConfig
        fields = (
            "calculation_basis",
            "installment_rate_snapshot",
            "paid_up_rate_snapshot",
            "installment_charge_snapshot",
            "parameters_used",
            "assumptions",
            "configured_by_display",
            "configured_at",
        )
        read_only_fields = fields

    def get_configured_by_display(self, obj):
        user = obj.configured_by
        return user.get_full_name() or user.email if user else "System"


class OLMaturityInstallmentPlanListSerializer(serializers.ModelSerializer):
    policy_number = serializers.CharField(source="policy_ref.policy_number", read_only=True)
    policyholder_name = serializers.SerializerMethodField()
    policyholder_display = serializers.SerializerMethodField()
    maturity_claim_number = serializers.CharField(
        source="maturity_claim_ref.claim_number", read_only=True, default=None
    )
    frequency_display = serializers.CharField(source="get_frequency_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    paid_count = serializers.SerializerMethodField()
    paid_amount = serializers.SerializerMethodField()
    remaining_amount = serializers.SerializerMethodField()
    allowed_actions = serializers.SerializerMethodField()

    class Meta:
        model = OLMaturityInstallmentPlan
        fields = (
            "id",
            "plan_number",
            "policy_number",
            "policyholder_name",
            "policyholder_display",
            "maturity_claim_number",
            "currency",
            "total_maturity_value",
            "total_payable_amount",
            "installment_count",
            "frequency",
            "frequency_display",
            "start_date",
            "end_date",
            "status",
            "status_display",
            "paid_count",
            "paid_amount",
            "remaining_amount",
            "allowed_actions",
        )
        read_only_fields = fields

    def get_policyholder_name(self, obj):
        return _partner_name(obj.partner)

    def get_policyholder_display(self, obj):
        return _partner_display(obj.partner)

    def get_paid_count(self, obj):
        return obj.items.filter(status=InstallmentItemStatus.PAID).count()

    def get_paid_amount(self, obj):
        return _money(obj.items.filter(status=InstallmentItemStatus.PAID).aggregate(total=Sum("amount"))["total"])

    def get_remaining_amount(self, obj):
        paid = self.get_paid_amount(obj)
        return _money(Decimal(obj.total_payable_amount) - Decimal(paid))

    def get_allowed_actions(self, obj):
        actions = _plan_allowed_actions(obj.status)
        request = self.context.get("request")
        user = getattr(request, "user", None) if request else None
        if user and not getattr(user, "is_superuser", False):
            actions = [action for action in actions if has_ol_maturity_installment_permission(user, action)]
        return actions


class OLMaturityInstallmentPlanDetailSerializer(OLMaturityInstallmentPlanListSerializer):
    items = OLInstallmentItemSerializer(many=True, read_only=True)
    config = OLMaturityInstallmentConfigSerializer(read_only=True)
    source_channel_display = serializers.CharField(source="get_source_channel_display", read_only=True)
    created_by_display = serializers.SerializerMethodField()
    activated_by_display = serializers.SerializerMethodField()
    completed_by_display = serializers.SerializerMethodField()
    terminated_by_display = serializers.SerializerMethodField()
    policy_context = serializers.SerializerMethodField()
    maturity_claim_context = serializers.SerializerMethodField()
    audit_timeline = serializers.SerializerMethodField()

    class Meta(OLMaturityInstallmentPlanListSerializer.Meta):
        fields = OLMaturityInstallmentPlanListSerializer.Meta.fields + (
            "parameter_snapshot",
            "source_channel",
            "source_channel_display",
            "created_by_display",
            "activated_at",
            "activated_by_display",
            "completed_at",
            "completed_by_display",
            "terminated_at",
            "terminated_by_display",
            "items",
            "config",
            "policy_context",
            "maturity_claim_context",
            "audit_timeline",
            "created_at",
            "updated_at",
        )

    def get_created_by_display(self, obj):
        user = obj.created_by
        return user.get_full_name() or user.email if user else "System"

    def get_activated_by_display(self, obj):
        user = obj.activated_by
        return user.get_full_name() or user.email if user else "System"

    def get_completed_by_display(self, obj):
        user = obj.completed_by
        return user.get_full_name() or user.email if user else "System"

    def get_terminated_by_display(self, obj):
        user = obj.terminated_by
        return user.get_full_name() or user.email if user else "System"

    def get_policy_context(self, obj):
        policy = obj.policy_ref
        return {
            "policy_number": policy.policy_number,
            "policyholder_display": _partner_display(policy.partner),
            "currency": policy.currency,
            "policy_status": policy.status,
            "maturity_date": policy.maturity_date,
            "product_display": policy.product_plan_ref,
        }

    def get_maturity_claim_context(self, obj):
        claim = obj.maturity_claim_ref
        if not claim:
            return None
        return {
            "claim_number": claim.claim_number,
            "maturity_value": _money(claim.maturity_value),
            "loan_deduction": _money(claim.loan_deduction),
            "net_payout": _money(claim.net_payout),
            "claim_status": claim.status,
        }

    def get_audit_timeline(self, obj):
        logs = (
            AuditLog.objects.filter(app_label="ol_maturity_installments")
            .filter(Q(object_id=str(obj.pk)) | Q(entity_id=obj.pk) | Q(entity_repr__startswith=f"{obj.plan_number} —"))
            .select_related("user")
            .order_by("timestamp", "created_at")
        )
        return [
            {
                "action": log.action or log.action_type,
                "action_display": log.get_action_type_display()
                if hasattr(log, "get_action_type_display")
                else log.action_type,
                "timestamp": log.timestamp,
                "actor_display": (log.user.get_full_name() or log.user.email) if log.user else "System",
                "reason": log.reason or log.description,
                "source_channel": log.source_channel,
                "before_state": log.before_state or {},
                "after_state": log.after_state or {},
            }
            for log in logs
        ]


def _plan_allowed_actions(status):
    return {
        InstallmentPlanStatus.CREATED: ["view", "print", "cancel"],
        InstallmentPlanStatus.ACTIVE: ["view", "print", "cancel"],
        InstallmentPlanStatus.COMPLETED: ["view", "print"],
        InstallmentPlanStatus.TERMINATED: ["view", "print"],
    }.get((status or "").upper(), ["view"])


def _item_allowed_actions(status):
    return {
        InstallmentItemStatus.SCHEDULED: ["view", "process_payment"],
        InstallmentItemStatus.PAYMENT_PENDING: ["view", "process_payment"],
        InstallmentItemStatus.PAID: ["view"],
        InstallmentItemStatus.MISSED: ["view", "process_payment"],
        InstallmentItemStatus.WAIVED: ["view"],
    }.get((status or "").upper(), ["view"])
