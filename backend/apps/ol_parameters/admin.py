from django.contrib import admin, messages

from .models import OLParameterTableRegistry
from .permissions import has_ol_parameter_permission
from .services.parameter_service import OLParameterService


@admin.register(OLParameterTableRegistry)
class OLParameterTableRegistryAdmin(admin.ModelAdmin):
    list_display = (
        "label",
        "slug",
        "parameter_group",
        "model_label",
        "is_active",
        "export_support",
        "updated_at",
        "updated_by",
    )
    list_filter = ("is_active", "export_support", "parameter_group")
    search_fields = ("slug", "label", "description", "model_label", "parameter_group")
    ordering = ("parameter_group", "label", "slug")
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by")
    fieldsets = (
        (
            "Table identity",
            {"fields": ("slug", "label", "description", "parameter_group", "model_label", "is_active")},
        ),
        (
            "Table contract",
            {
                "fields": (
                    "visible_columns",
                    "searchable_fields",
                    "filter_fields",
                    "default_ordering",
                    "allowed_actions",
                    "export_support",
                )
            },
        ),
        (
            "Permission contract",
            {"fields": ("permission_code", "permission_requirements")},
        ),
        (
            "Audit",
            {"fields": ("created_by", "created_at", "updated_by", "updated_at")},
        ),
    )
    actions = ("deactivate_selected",)

    def has_module_permission(self, request):
        return has_ol_parameter_permission(request.user, "view")

    def has_view_permission(self, request, obj=None):
        return has_ol_parameter_permission(request.user, "view")

    def has_add_permission(self, request):
        return has_ol_parameter_permission(request.user, "create")

    def has_change_permission(self, request, obj=None):
        return has_ol_parameter_permission(request.user, "update")

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        if not change and not obj.created_by_id:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)

    @admin.action(description="Deactivate selected OL parameter tables")
    def deactivate_selected(self, request, queryset):
        if not has_ol_parameter_permission(request.user, "deactivate"):
            self.message_user(request, "You do not have permission to deactivate OL parameter tables.", messages.ERROR)
            return
        count = 0
        for instance in queryset:
            OLParameterService.deactivate_registry(actor=request.user, instance=instance, request=request)
            count += 1
        self.message_user(request, f"{count} table registry record(s) deactivated.")
