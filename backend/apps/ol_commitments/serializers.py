from rest_framework import serializers

from apps.ol_commitments.models import (
    OLCommitment,
    OLCommitmentAllocation,
    OLCommitmentNotificationLog,
)
from apps.ol_commitments.services.commitment_actions import allowed_actions
from apps.ol_commitments.services.parameter_resolver import compute_grace_envelope


def grace_days_for(commitment):
    envelope = compute_grace_envelope(
        commitment.due_date,
        product=commitment.product,
        plan=commitment.plan,
        premium_frequency=commitment.premium_frequency,
    )
    return envelope.grace_days if envelope.grace_date else None


class CommitmentAllocationSerializer(serializers.ModelSerializer):
    reversal_of = serializers.UUIDField(source="reversal_of_id", allow_null=True, required=False)

    class Meta:
        model = OLCommitmentAllocation
        fields = (
            "id",
            "receipt_reference",
            "amount",
            "payment_mode",
            "currency",
            "exchange_rate",
            "reason",
            "reversal_of",
            "allocated_at",
            "allocated_by",
            "source_channel",
        )


class CommitmentNotificationLogSerializer(serializers.ModelSerializer):
    notification_channel = serializers.CharField(source="notification_channel")
    recipient_type = serializers.CharField(source="recipient_type")

    class Meta:
        model = OLCommitmentNotificationLog
        fields = (
            "id",
            "event_type",
            "dispatch_on",
            "notification_channel",
            "recipient_type",
            "recipient_identifier",
            "template_code",
            "status",
        )


class CommitmentBaseSerializer(serializers.ModelSerializer):
    grace_days = serializers.SerializerMethodField()
    allowed_actions = serializers.SerializerMethodField()

    class Meta:
        model = OLCommitment
        fields = (
            "id",
            "commitment_number",
            "source_type",
            "source_reference",
            "partner",
            "partner_name_snapshot",
            "product",
            "product_name_snapshot",
            "plan",
            "plan_name_snapshot",
            "currency",
            "premium_frequency",
            "installment_number",
            "installment_count",
            "due_date",
            "premium_amount",
            "amount_paid",
            "amount_waived",
            "balance",
            "status",
            "grace_date",
            "warning_date",
            "pre_lapse_date",
            "lapse_date",
            "approval_required",
            "reason_code",
            "reason_text",
            "source_channel",
            "grace_days",
            "allowed_actions",
        )

    def get_grace_days(self, obj):
        return grace_days_for(obj)

    def get_allowed_actions(self, obj):
        return allowed_actions(obj)


class CommitmentDetailSerializer(CommitmentBaseSerializer):
    allocations = CommitmentAllocationSerializer(many=True, read_only=True)
    notification_logs = CommitmentNotificationLogSerializer(many=True, read_only=True)
    status_history = serializers.SerializerMethodField()

    class Meta(CommitmentBaseSerializer.Meta):
        fields = CommitmentBaseSerializer.Meta.fields + (
            "allocations",
            "notification_logs",
            "status_history",
        )

    def get_status_history(self, obj):
        from apps.governance.models import AuditLog

        logs = (
            AuditLog.objects.filter(app_label="ol_commitments", object_id=str(obj.pk))
            .order_by("-created_at")[:50]
        )
        entries = []
        for log in logs:
            after = log.after_state or {}
            before = log.before_state or {}
            entries.append(
                {
                    "fromStatus": before.get("status", ""),
                    "toStatus": after.get("status", "") or log.action,
                    "actorName": (log.user.get_full_name() or log.user.username) if log.user else "System",
                    "createdAt": log.created_at,
                    "reason": log.reason or "",
                    "sourceChannel": log.source_channel,
                }
            )
        return entries


class ManualCommitmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = OLCommitment
        fields = (
            "partner",
            "product",
            "plan",
            "currency",
            "premium_frequency",
            "installment_number",
            "installment_count",
            "due_date",
            "premium_amount",
            "payment_mode",
            "reason",
        )
        extra_kwargs = {
            "partner": {"required": False, "allow_null": True},
            "product": {"required": False, "allow_null": True},
            "plan": {"required": False, "allow_null": True},
            "currency": {"required": False},
        }

    def validate_premium_amount(self, value):
        if value is None or value <= 0:
            raise serializers.ValidationError("Premium amount must be greater than zero.")
        return value

    def validate_due_date(self, value):
        if not value:
            raise serializers.ValidationError("Due date is required.")
        return value

    def create(self, validated_data):
        from apps.ol_commitments.models import CommitmentSourceChannel
        from apps.system_parameters.services.numbering_service import NumberingEngine

        reason = validated_data.pop("reason", "")
        validated_data.pop("payment_mode", None)
        commitment = OLCommitment(
            source_type="MANUAL",
            source_channel=CommitmentSourceChannel.MANUAL,
            commitment_number=NumberingEngine.generate_number(
                "OL_COMMITMENT", OLCommitment, field_name="commitment_number"
            ),
            **validated_data,
        )
        commitment.save()
        if reason:
            commitment.reason_text = reason
            commitment.save(update_fields=["reason_text"])
        return commitment