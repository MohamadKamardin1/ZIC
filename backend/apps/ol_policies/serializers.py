from rest_framework import serializers

from .models import (
    Policy,
    PolicyAuditLog,
    PolicyBenefit,
    PolicyEndorsement,
    PolicyMember,
    PolicyRider,
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
    agent_display = serializers.SerializerMethodField()
    product_plan_display = serializers.CharField(source="product_plan_ref", read_only=True)
    status_display = serializers.SerializerMethodField()

    class Meta:
        model = Policy
        fields = (
            "id",
            "policy_number",
            "proposal_ref_display",
            "policyholder_display",
            "agent_display",
            "product_plan_display",
            "currency",
            "sum_assured",
            "premium_amount",
            "premium_frequency",
            "term_years",
            "risk_commencement_date",
            "maturity_date",
            "status",
            "status_display",
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

    def get_agent_display(self, obj):
        return _partner_label(obj.agent)

    def get_status_display(self, obj):
        return obj.get_status_display()


class PolicyDetailSerializer(PolicyListSerializer):
    members = PolicyMemberSerializer(many=True, read_only=True)
    riders = PolicyRiderSerializer(many=True, read_only=True)
    benefits = PolicyBenefitSerializer(many=True, read_only=True)
    endorsements = PolicyEndorsementSerializer(many=True, read_only=True)
    audit_logs = PolicyAuditLogSerializer(many=True, read_only=True)

    class Meta(PolicyListSerializer.Meta):
        fields = PolicyListSerializer.Meta.fields + (
            "first_premium_receipt_ref",
            "contract_snapshot",
            "members",
            "riders",
            "benefits",
            "endorsements",
            "audit_logs",
        )
