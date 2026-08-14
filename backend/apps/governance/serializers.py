from rest_framework import serializers

from apps.governance.models import ApprovalRequest, AuditLog, ConfigurationVersion
from apps.partners.models import (
    DocumentVersion,
    KYCReviewHistory,
    PartnerTypeAssignmentHistory,
)


class AuditLogSerializer(serializers.ModelSerializer):
    user_email = serializers.ReadOnlyField(source="user.email")
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = [
            "id", "user", "user_email", "user_name",
            "action_type", "action", "actor_type",
            "entity_type", "entity_id", "entity_repr", "app_label", "model_name",
            "object_id", "object_repr", "before_state", "after_state", "changed_fields",
            "description", "reason", "source_channel", "ip_address", "user_agent",
            "request_id", "correlation_id", "timestamp", "created_at",
        ]
        read_only_fields = fields

    def get_user_name(self, obj):
        if obj.user:
            return obj.user.full_name or obj.user.email
        return "System"


class AuditLogFilterSerializer(serializers.Serializer):
    entity_type = serializers.CharField(required=False)
    model_name = serializers.CharField(required=False)
    app_label = serializers.CharField(required=False)
    entity_id = serializers.UUIDField(required=False)
    object_id = serializers.CharField(required=False)
    action_type = serializers.CharField(required=False)
    action = serializers.CharField(required=False)
    actor_type = serializers.CharField(required=False)
    source_channel = serializers.CharField(required=False)
    user_id = serializers.UUIDField(required=False)
    correlation_id = serializers.CharField(required=False)
    date_from = serializers.DateTimeField(required=False)
    date_to = serializers.DateTimeField(required=False)


class ApprovalRequestSerializer(serializers.ModelSerializer):
    submitted_by_email = serializers.ReadOnlyField(source="submitted_by.email")
    submitted_by_name = serializers.SerializerMethodField()
    reviewed_by_email = serializers.ReadOnlyField(source="reviewed_by.email")
    reviewed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = ApprovalRequest
        fields = [
            "id", "module", "entity_type", "entity_id", "entity_repr",
            "action", "requested_data", "current_data",
            "status", "submitted_by", "submitted_by_email", "submitted_by_name",
            "submitted_at", "reviewed_by", "reviewed_by_email", "reviewed_by_name",
            "reviewed_at", "comments", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "status", "submitted_by", "submitted_at",
            "reviewed_by", "reviewed_at", "created_at", "updated_at",
        ]

    def get_submitted_by_name(self, obj):
        if obj.submitted_by:
            return obj.submitted_by.full_name or obj.submitted_by.email
        return "System"

    def get_reviewed_by_name(self, obj):
        if obj.reviewed_by:
            return obj.reviewed_by.full_name or obj.reviewed_by.email
        return None


class ApprovalActionSerializer(serializers.Serializer):
    comments = serializers.CharField(required=False, allow_blank=True)


class ConfigurationVersionSerializer(serializers.ModelSerializer):
    created_by_email = serializers.ReadOnlyField(source="created_by.email")
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = ConfigurationVersion
        fields = [
            "id", "module", "version_number",
            "effective_from", "effective_to", "status",
            "configuration_data", "change_summary",
            "created_by", "created_by_email", "created_by_name",
            "created_at", "notes",
        ]
        read_only_fields = ["id", "version_number", "created_at"]

    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.full_name or obj.created_by.email
        return None


class DocumentVersionSerializer(serializers.ModelSerializer):
    uploaded_by_email = serializers.ReadOnlyField(source="uploaded_by.email")
    verified_by_email = serializers.ReadOnlyField(source="verified_by.email")

    class Meta:
        model = DocumentVersion
        fields = [
            "id", "document", "version_number",
            "file", "file_name", "file_size", "mime_type",
            "status", "notes",
            "uploaded_by", "uploaded_by_email", "uploaded_at",
            "verification_status", "verified_by", "verified_by_email",
            "verified_at", "verification_notes",
        ]
        read_only_fields = ["id", "version_number", "uploaded_by", "uploaded_at"]


class KYCReviewHistorySerializer(serializers.ModelSerializer):
    reviewed_by_email = serializers.ReadOnlyField(source="reviewed_by.email")
    reviewed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = KYCReviewHistory
        fields = [
            "id", "kyc_profile", "review_type",
            "previous_kyc_status", "new_kyc_status",
            "previous_risk_score", "new_risk_score",
            "previous_risk_level", "new_risk_level",
            "reviewed_by", "reviewed_by_email", "reviewed_by_name",
            "decision_date", "comments", "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def get_reviewed_by_name(self, obj):
        if obj.reviewed_by:
            return obj.reviewed_by.full_name or obj.reviewed_by.email
        return None


class PartnerTypeAssignmentHistorySerializer(serializers.ModelSerializer):
    changed_by_email = serializers.ReadOnlyField(source="changed_by.email")
    changed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = PartnerTypeAssignmentHistory
        fields = [
            "id", "assignment", "previous_status", "new_status",
            "reason", "changed_by", "changed_by_email", "changed_by_name",
            "changed_at",
        ]
        read_only_fields = ["id", "changed_at"]

    def get_changed_by_name(self, obj):
        if obj.changed_by:
            return obj.changed_by.full_name or obj.changed_by.email
        return None
