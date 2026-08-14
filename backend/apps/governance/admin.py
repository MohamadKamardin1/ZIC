from django.contrib import admin

from .models import ApprovalRequest, AuditLog, ConfigurationVersion


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = [
        "action", "model_name", "object_repr", "user", "actor_type",
        "source_channel", "correlation_id", "created_at",
    ]
    list_filter = ["action", "action_type", "actor_type", "source_channel", "app_label", "model_name", "created_at"]
    search_fields = [
        "entity_type", "model_name", "object_id", "object_repr", "description",
        "reason", "correlation_id", "user__email",
    ]
    date_hierarchy = "created_at"
    readonly_fields = [
        "user", "action_type", "action", "actor_type", "entity_type", "entity_id",
        "entity_repr", "app_label", "model_name", "object_id", "object_repr",
        "before_state", "after_state", "changed_fields", "description", "reason",
        "source_channel", "ip_address", "user_agent", "request_id",
        "correlation_id", "timestamp", "created_at",
    ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ApprovalRequest)
class ApprovalRequestAdmin(admin.ModelAdmin):
    list_display = ["module", "entity_type", "action", "status", "submitted_by", "submitted_at"]
    list_filter = ["module", "status", "action"]
    search_fields = ["module", "entity_type", "entity_repr", "submitted_by__email"]
    readonly_fields = ["created_at", "updated_at"]

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ConfigurationVersion)
class ConfigurationVersionAdmin(admin.ModelAdmin):
    list_display = ["module", "version_number", "status", "effective_from", "effective_to", "created_at"]
    list_filter = ["module", "status"]
    search_fields = ["module", "change_summary", "notes"]
    readonly_fields = ["created_at"]
