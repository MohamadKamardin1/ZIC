from django.contrib import admin

from .models import AuditLog, ApprovalRequest, ConfigurationVersion


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ["action_type", "entity_type", "entity_repr", "user", "timestamp"]
    list_filter = ["action_type", "entity_type", "timestamp"]
    search_fields = ["entity_type", "entity_repr", "description", "user__email"]
    date_hierarchy = "timestamp"
    readonly_fields = [
        "user", "action_type", "entity_type", "entity_id", "entity_repr",
        "before_state", "after_state", "description",
        "ip_address", "user_agent", "request_id", "timestamp",
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
