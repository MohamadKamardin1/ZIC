from django.contrib import admin

from .models import (
    GCHealthQuestion,
    GCHealthQuestionnaire,
    GCLookupValue,
    GCProduct,
    GCRider,
    GCRiderRate,
    GCSchemeMemberStatus,
    GCSchemePremiumRate,
    GCSchemeRenewalStatus,
    GCSchemeStatus,
    GCSchemeType,
    GCSubProduct,
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


@admin.register(GCSubProduct)
class GCSubProductAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "is_active", "updated_at", "updated_by")
    list_filter = ("is_active",)
    search_fields = ("code", "name", "description")
    ordering = ("name", "code")
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by")
    fieldsets = (
        ("Identity", {"fields": ("code", "name", "description")}),
        ("Status", {"fields": ("is_active",)}),
        ("Audit", {"fields": ("created_by", "updated_by", "created_at", "updated_at")}),
    )


@admin.register(GCProduct)
class GCProductAdmin(admin.ModelAdmin):
    list_display = (
        "code", "name", "scheme_type_ref", "sub_product", "insurance_class",
        "premium_basis", "requires_medical", "currency", "is_active", "updated_at",
    )
    list_filter = ("scheme_type_ref", "sub_product", "insurance_class", "premium_basis", "requires_medical", "is_active", "currency")
    search_fields = ("code", "name", "description", "scheme_type_ref__code", "scheme_type_ref__name", "sub_product__code", "sub_product__name")
    ordering = ("scheme_type_ref", "name")
    list_select_related = ("scheme_type_ref", "sub_product")
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by")
    fieldsets = (
        ("Identity", {"fields": ("code", "name", "description")}),
        ("Hierarchy", {"fields": ("scheme_type_ref", "sub_product")}),
        ("Class", {"fields": ("insurance_class", "currency", "premium_basis", "requires_medical", "is_active")}),
        ("Members & loan", {"fields": ("min_members", "max_members", "min_loan_amount", "max_loan_amount", "min_loan_term", "max_loan_term")}),
        ("Eligibility", {"fields": ("min_entry_age", "max_entry_age", "max_cover_age", "free_cover_limit")}),
        ("Audit", {"fields": ("created_by", "updated_by", "created_at", "updated_at")}),
    )


@admin.register(GCRider)
class GCRiderAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "rider_category", "benefit_type", "requires_underwriting", "rider_type", "is_mandatory", "is_active", "updated_at")
    list_filter = ("rider_category", "benefit_type", "requires_underwriting", "is_mandatory", "is_active")
    search_fields = ("code", "name", "description")
    ordering = ("rider_category", "name")
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by")
    fieldsets = (
        ("Identity", {"fields": ("code", "name", "description")}),
        ("Benefit", {"fields": ("rider_category", "benefit_type", "requires_underwriting")}),
        ("Legacy & status", {"fields": ("rider_type", "is_mandatory", "is_active")}),
        ("Audit", {"fields": ("created_by", "updated_by", "created_at", "updated_at")}),
    )


@admin.register(GCRiderRate)
class GCRiderRateAdmin(admin.ModelAdmin):
    list_display = ("rider", "product_ref", "rate_type", "rate_value", "currency", "age_band_start", "age_band_end", "effective_from", "effective_to", "is_active")
    list_filter = ("rate_type", "currency", "gender", "is_active", "rider")
    search_fields = ("rider__code", "rider__name", "product_ref__code", "product_ref__name")
    ordering = ("rider", "age_band_start")
    list_select_related = ("rider", "product_ref")
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by")
    fieldsets = (
        ("Scope", {"fields": ("rider", "product_ref")}),
        ("Rate", {"fields": ("rate_value", "rate_type", "currency")}),
        ("Dimensions", {"fields": ("age_band_start", "age_band_end", "gender")}),
        ("Effective dating", {"fields": ("effective_from", "effective_to", "is_active")}),
        ("Legacy values", {"fields": ("rate_per_mille", "flat_amount", "effective_date", "expiry_date")}),
        ("Audit", {"fields": ("created_by", "updated_by", "created_at", "updated_at")}),
    )
