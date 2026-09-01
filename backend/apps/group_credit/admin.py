from django.contrib import admin

from .models import (
    GCHealthQuestion,
    GCHealthQuestionnaire,
    GCLookupValue,
    GCSchemeMemberStatus,
    GCSchemePremiumRate,
    GCSchemeRenewalStatus,
    GCSchemeStatus,
    GCSchemeType,
)


@admin.register(GCSchemeType)
class GCSchemeTypeAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "partner_type_restriction", "is_active", "updated_at", "updated_by")
    list_filter = ("is_active", "partner_type_restriction")
    search_fields = ("code", "name", "description")
    ordering = ("name", "code")
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by")
    fieldsets = (
        ("Identity", {"fields": ("code", "name", "description")}),
        ("Restriction", {"fields": ("partner_type_restriction", "is_active")}),
        ("Audit", {"fields": ("created_by", "updated_by", "created_at", "updated_at")}),
    )


@admin.register(GCSchemePremiumRate)
class GCSchemePremiumRateAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "scheme_type",
        "rate_type",
        "rate_value",
        "currency",
        "effective_from",
        "effective_to",
        "is_active",
        "updated_at",
    )
    list_filter = ("rate_type", "currency", "is_active", "scheme_type")
    search_fields = ("name", "scheme_type__code", "scheme_type__name", "product_ref__code", "product_ref__name")
    ordering = ("scheme_type", "rate_type", "age_band_start")
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by")
    fieldsets = (
        ("Rate identity", {"fields": ("name", "scheme_type", "product_ref", "rate_type", "rate_value", "currency")}),
        ("Dimensions", {"fields": ("age_band_start", "age_band_end", "gender", "occupation_class")}),
        ("Legacy values", {"fields": ("rate_per_mille", "flat_rate", "effective_date", "expiry_date")}),
        ("Effective dating", {"fields": ("effective_from", "effective_to", "is_active")}),
        ("Audit", {"fields": ("created_by", "updated_by", "created_at", "updated_at")}),
    )


@admin.register(GCSchemeStatus)
class GCSchemeStatusAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "display_order", "is_terminal", "is_active", "updated_at")
    list_filter = ("is_active", "is_terminal")
    search_fields = ("code", "name", "description")
    ordering = ("display_order", "name")
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by")
    fieldsets = (
        ("Identity", {"fields": ("code", "name", "description")}),
        ("Behaviour", {"fields": ("display_order", "sort_order", "is_terminal", "is_active")}),
        ("Audit", {"fields": ("created_by", "updated_by", "created_at", "updated_at")}),
    )


@admin.register(GCSchemeMemberStatus)
class GCSchemeMemberStatusAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "display_order", "is_terminal", "allows_claims", "is_active", "updated_at")
    list_filter = ("is_active", "is_terminal", "allows_claims")
    search_fields = ("code", "name", "description")
    ordering = ("display_order", "name")
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by")
    fieldsets = (
        ("Identity", {"fields": ("code", "name", "description")}),
        ("Behaviour", {"fields": ("display_order", "is_terminal", "allows_claims", "is_active")}),
        ("Audit", {"fields": ("created_by", "updated_by", "created_at", "updated_at")}),
    )


@admin.register(GCSchemeRenewalStatus)
class GCSchemeRenewalStatusAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "display_order", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("code", "name", "description")
    ordering = ("display_order", "name")
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by")
    fieldsets = (
        ("Identity", {"fields": ("code", "name", "description")}),
        ("Behaviour", {"fields": ("display_order", "is_active")}),
        ("Audit", {"fields": ("created_by", "updated_by", "created_at", "updated_at")}),
    )


@admin.register(GCHealthQuestion)
class GCHealthQuestionAdmin(admin.ModelAdmin):
    list_display = ("code", "question_text", "answer_type", "category", "required", "sort_order", "is_active", "updated_at")
    list_filter = ("answer_type", "category", "required", "is_active")
    search_fields = ("code", "question_text", "category")
    ordering = ("category", "sort_order", "code")
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by")
    fieldsets = (
        ("Question", {"fields": ("code", "question_text", "category")}),
        ("Answer handling", {"fields": ("answer_type", "question_type", "options", "required", "is_required", "sort_order", "is_active")}),
        ("Audit", {"fields": ("created_by", "updated_by", "created_at", "updated_at")}),
    )


@admin.register(GCHealthQuestionnaire)
class GCHealthQuestionnaireAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "version", "scheme_type_ref", "threshold_trigger_amount", "is_active", "updated_at")
    list_filter = ("is_active", "scheme_type_ref")
    search_fields = ("code", "name", "description", "scheme_type_ref__code", "scheme_type_ref__name")
    ordering = ("-effective_date", "name")
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by")
    filter_horizontal = ("questions",)
    fieldsets = (
        ("Questionnaire", {"fields": ("code", "name", "description", "version")}),
        ("Scoping", {"fields": ("scheme_type_ref", "threshold_trigger_amount")}),
        ("Questions", {"fields": ("questions",)}),
        ("Effective dating", {"fields": ("effective_date", "effective_from", "is_active")}),
        ("Audit", {"fields": ("created_by", "updated_by", "created_at", "updated_at")}),
    )


@admin.register(GCLookupValue)
class GCLookupValueAdmin(admin.ModelAdmin):
    list_display = ("category", "value", "label", "sort_order", "is_active", "updated_at")
    list_filter = ("category", "is_active")
    search_fields = ("category", "value", "label")
    ordering = ("category", "sort_order", "label")
    readonly_fields = ("created_at", "updated_at")
