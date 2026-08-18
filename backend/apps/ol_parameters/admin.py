from django.contrib import admin, messages

from .models import (
    OLComputationApproach,
    OLDefaultSystemParameter,
    OLMaturityClaimSetup,
    OLOverrideCommissionSetup,
    OLParameterTableRegistry,
)
from .permissions import has_ol_parameter_permission
from .services.default_setup_service import OLDefaultSetupService
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


class OLDefaultSetupAdmin(admin.ModelAdmin):
    list_filter = ("is_active", "effective_from", "effective_to")
    search_fields = ("code", "name", "description")
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by")
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

    @admin.action(description="Deactivate selected OL Default Setup records")
    def deactivate_selected(self, request, queryset):
        if not has_ol_parameter_permission(request.user, "deactivate"):
            self.message_user(request, "You do not have permission to deactivate these records.", messages.ERROR)
            return
        count = 0
        for instance in queryset:
            OLDefaultSetupService.deactivate(actor=request.user, instance=instance, request=request)
            count += 1
        self.message_user(request, f"{count} OL Default Setup record(s) deactivated.")


@admin.register(OLDefaultSystemParameter)
class OLDefaultSystemParameterAdmin(OLDefaultSetupAdmin):
    list_display = (
        "parameter_key", "name", "parameter_category", "value_type", "is_active",
        "effective_from", "effective_to", "updated_by", "updated_at",
    )
    list_filter = ("is_active", "parameter_category", "value_type", "effective_from", "effective_to")
    search_fields = ("parameter_key", "code", "name", "parameter_category", "description")
    ordering = ("parameter_category", "name", "parameter_key")
    fieldsets = (
        ("Identity", {"fields": ("code", "parameter_key", "name", "parameter_category", "description", "is_active")}),
        ("Typed value", {"fields": ("value_type", "string_value", "integer_value", "decimal_value", "boolean_value", "date_value", "json_value")}),
        ("Effective dates", {"fields": ("effective_from", "effective_to")}),
        ("Audit", {"fields": ("created_by", "created_at", "updated_by", "updated_at")}),
    )


@admin.register(OLOverrideCommissionSetup)
class OLOverrideCommissionSetupAdmin(OLDefaultSetupAdmin):
    list_display = (
        "priority", "code", "name", "rate_type", "rate_value", "product", "plan",
        "partner", "channel", "effective_from", "effective_to", "is_active",
    )
    list_filter = ("is_active", "rate_type", "intermediary_type", "channel", "currency", "effective_from", "effective_to")
    search_fields = ("code", "name", "description", "reason", "intermediary_type", "channel", "currency", "product__code", "plan__code")
    ordering = ("priority", "-effective_from", "code")
    autocomplete_fields = ("partner", "product", "plan", "rider")
    fieldsets = (
        ("Identity", {"fields": ("code", "name", "description", "reason", "is_active", "priority")}),
        ("Scope", {"fields": ("partner", "intermediary_type", "product", "plan", "rider", "channel", "branch", "currency")}),
        ("Rate", {"fields": ("premium_year_from", "premium_year_to", "policy_year_from", "policy_year_to", "rate_type", "rate_value")}),
        ("Effective dates", {"fields": ("effective_from", "effective_to")}),
        ("Audit", {"fields": ("created_by", "created_at", "updated_by", "updated_at")}),
    )


@admin.register(OLComputationApproach)
class OLComputationApproachAdmin(OLDefaultSetupAdmin):
    list_display = (
        "calculation_area", "sequence", "code", "name", "calculation_basis", "formula_key",
        "effective_from", "effective_to", "is_active", "updated_at",
    )
    list_filter = ("is_active", "calculation_area", "calculation_basis", "effective_from", "effective_to")
    search_fields = ("code", "name", "description", "calculation_area", "calculation_basis", "formula_key")
    ordering = ("calculation_area", "sequence", "name", "code")
    fieldsets = (
        ("Identity", {"fields": ("code", "name", "description", "is_active")}),
        ("Calculation contract", {"fields": ("calculation_area", "calculation_basis", "formula_key", "sequence", "configuration")}),
        ("Effective dates", {"fields": ("effective_from", "effective_to")}),
        ("Audit", {"fields": ("created_by", "created_at", "updated_by", "updated_at")}),
    )


@admin.register(OLMaturityClaimSetup)
class OLMaturityClaimSetupAdmin(OLDefaultSetupAdmin):
    list_display = (
        "code", "name", "product", "plan", "auto_create_maturity_claim",
        "days_before_maturity_to_initiate", "notification_days", "default_payout_method",
        "require_approval", "effective_from", "effective_to", "is_active",
    )
    list_filter = ("is_active", "auto_create_maturity_claim", "require_documents", "require_approval", "default_payout_method", "effective_from", "effective_to")
    search_fields = ("code", "name", "description", "default_payout_method", "maturity_claim_status_to_create", "product__code", "plan__code")
    ordering = ("-effective_from", "name", "code")
    autocomplete_fields = ("product", "plan")
    fieldsets = (
        ("Identity", {"fields": ("code", "name", "description", "is_active")}),
        ("Scope", {"fields": ("product", "plan")}),
        ("Maturity behavior", {"fields": ("auto_create_maturity_claim", "days_before_maturity_to_initiate", "notification_days", "default_payout_method", "require_documents", "require_approval", "maturity_claim_status_to_create")}),
        ("Effective dates", {"fields": ("effective_from", "effective_to")}),
        ("Audit", {"fields": ("created_by", "created_at", "updated_by", "updated_at")}),
    )
