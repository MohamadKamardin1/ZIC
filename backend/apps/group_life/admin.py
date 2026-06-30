"""
Django Admin configuration for the Group Life Insurance module.
Registers all GL models with rich admin interfaces including
search, filtering, list display, and inline editing.
"""

from django.contrib import admin

from .models import (
    # Layer 1 — Parameters
    GLSchemeType, GLSchemeStatus, GLSchemeMemberStatus, GLSchemeRenewalStatus,
    GLSchemePremiumRate, GLHealthQuestion, GLHealthQuestionnaire,
    # Layer 2 — Products & Riders
    GLSubProduct, GLProduct, GLRider, GLRiderRate,
    # Layer 3 — Quotations
    GLQuotation, GLQuotationCategory, GLQuotationRider,
    # Layer 4 — Schemes & Members
    GLScheme, GLSchemeCategory, GLSchemeRider, GLSchemeMember,
    GLSchemeMemberDependent,
    # Layer 5 — Medical UW
    GLMedicalCode, GLMedicalLimit, GLUnderwritingDecision,
    GLPersonalHabit, GLMedicalHistory, GLMedicalFacility,
    GLMedicalPractitioner, GLMedicalCase,
    # Layer 6 — Claims
    GLClaimType, GLClaimReason, GLClaimStatus, GLDischargeType,
    GLCorrespondentType, GLClaim, GLClaimInstallment, GLMedicalInvoice,
    # Layer 7 — Renewals
    GLSchemeRenewal,
)


# =============================================================================
# INLINES
# =============================================================================


class GLRiderRateInline(admin.TabularInline):
    model = GLRiderRate
    extra = 1
    fields = [
        "age_band_start", "age_band_end", "gender",
        "rate_per_mille", "flat_amount",
        "effective_date", "expiry_date", "is_active",
    ]


class GLQuotationCategoryInline(admin.TabularInline):
    model = GLQuotationCategory
    extra = 1
    fields = [
        "category_name", "salary_multiple", "flat_sum_assured",
        "member_count", "total_sum_assured", "annual_premium",
        "premium_rate_per_mille", "sort_order",
    ]


class GLQuotationRiderInline(admin.TabularInline):
    model = GLQuotationRider
    extra = 1
    fields = ["rider", "rate_per_mille", "total_premium"]


class GLSchemeCategoryInline(admin.TabularInline):
    model = GLSchemeCategory
    extra = 1
    fields = [
        "category_name", "salary_multiple", "flat_sum_assured",
        "premium_rate_per_mille", "min_entry_age", "max_entry_age",
        "max_cover_age", "sort_order", "is_active",
    ]


class GLSchemeRiderInline(admin.TabularInline):
    model = GLSchemeRider
    extra = 1
    fields = ["rider", "rate_per_mille", "flat_amount", "is_active"]


class GLSchemeMemberDependentInline(admin.TabularInline):
    model = GLSchemeMemberDependent
    extra = 0
    fields = [
        "relationship", "first_name", "surname", "gender",
        "date_of_birth", "sum_assured", "premium_amount", "is_active",
    ]


class GLClaimInstallmentInline(admin.TabularInline):
    model = GLClaimInstallment
    extra = 0
    fields = [
        "installment_number", "due_date", "amount", "paid_amount",
        "status", "payment_reference", "payment_date",
    ]
    readonly_fields = ["installment_number"]


class GLClaimReasonInline(admin.TabularInline):
    model = GLClaimReason
    extra = 1
    fields = ["code", "name", "description", "is_active"]


# =============================================================================
# LAYER 1 — PARAMETER ADMINS
# =============================================================================


@admin.register(GLSchemeType)
class GLSchemeTypeAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "is_active", "created_at"]
    list_filter = ["is_active"]
    search_fields = ["code", "name"]
    ordering = ["name"]


@admin.register(GLSchemeStatus)
class GLSchemeStatusAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "sort_order", "is_terminal", "is_active"]
    list_filter = ["is_terminal", "is_active"]
    search_fields = ["code", "name"]
    ordering = ["sort_order"]


@admin.register(GLSchemeMemberStatus)
class GLSchemeMemberStatusAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["code", "name"]


@admin.register(GLSchemeRenewalStatus)
class GLSchemeRenewalStatusAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["code", "name"]


@admin.register(GLSchemePremiumRate)
class GLSchemePremiumRateAdmin(admin.ModelAdmin):
    list_display = [
        "name", "rate_type", "age_band_start", "age_band_end",
        "gender", "rate_per_mille", "flat_rate",
        "effective_date", "is_active",
    ]
    list_filter = ["rate_type", "gender", "is_active"]
    search_fields = ["name"]
    ordering = ["rate_type", "age_band_start"]


@admin.register(GLHealthQuestion)
class GLHealthQuestionAdmin(admin.ModelAdmin):
    list_display = ["code", "question_text_short", "question_type", "category", "sort_order", "is_active"]
    list_filter = ["question_type", "category", "is_active"]
    search_fields = ["code", "question_text"]
    ordering = ["category", "sort_order"]

    def question_text_short(self, obj):
        return obj.question_text[:80] + "..." if len(obj.question_text) > 80 else obj.question_text
    question_text_short.short_description = "Question"


@admin.register(GLHealthQuestionnaire)
class GLHealthQuestionnaireAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "version", "effective_date", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["code", "name"]
    filter_horizontal = ["questions"]


# =============================================================================
# LAYER 2 — PRODUCT & RIDER ADMINS
# =============================================================================


@admin.register(GLSubProduct)
class GLSubProductAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["code", "name"]


@admin.register(GLProduct)
class GLProductAdmin(admin.ModelAdmin):
    list_display = [
        "code", "name", "sub_product",
        "min_members", "max_members",
        "free_cover_limit", "min_entry_age", "max_entry_age",
        "currency", "is_active",
    ]
    list_filter = ["sub_product", "is_active", "currency"]
    search_fields = ["code", "name"]
    fieldsets = (
        (None, {
            "fields": ("code", "name", "sub_product", "description"),
        }),
        ("Member Constraints", {
            "fields": ("min_members", "max_members"),
        }),
        ("Sum Assured Limits", {
            "fields": ("min_sum_assured", "max_sum_assured", "free_cover_limit"),
        }),
        ("Age Limits", {
            "fields": ("min_entry_age", "max_entry_age", "max_cover_age"),
        }),
        ("Salary Multiples", {
            "fields": ("salary_multiple_min", "salary_multiple_max"),
        }),
        ("Settings", {
            "fields": ("currency", "is_active"),
        }),
    )


@admin.register(GLRider)
class GLRiderAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "rider_type", "is_mandatory", "is_active"]
    list_filter = ["rider_type", "is_mandatory", "is_active"]
    search_fields = ["code", "name"]
    inlines = [GLRiderRateInline]


@admin.register(GLRiderRate)
class GLRiderRateAdmin(admin.ModelAdmin):
    list_display = [
        "rider", "age_band_start", "age_band_end", "gender",
        "rate_per_mille", "flat_amount", "effective_date", "is_active",
    ]
    list_filter = ["rider", "gender", "is_active"]
    ordering = ["rider", "age_band_start"]


# =============================================================================
# LAYER 3 — QUOTATION ADMINS
# =============================================================================


@admin.register(GLQuotation)
class GLQuotationAdmin(admin.ModelAdmin):
    list_display = [
        "quotation_number", "partner", "product", "status",
        "total_members", "total_sum_assured", "total_annual_premium",
        "quotation_date", "valid_until",
    ]
    list_filter = ["status", "product", "scheme_type"]
    search_fields = ["quotation_number", "partner__partner_number", "partner__company_name"]
    readonly_fields = ["quotation_number", "created_at", "updated_at"]
    date_hierarchy = "quotation_date"
    inlines = [GLQuotationCategoryInline, GLQuotationRiderInline]


# =============================================================================
# LAYER 4 — SCHEME & MEMBER ADMINS
# =============================================================================


@admin.register(GLScheme)
class GLSchemeAdmin(admin.ModelAdmin):
    list_display = [
        "scheme_number", "partner", "product", "status",
        "inception_date", "expiry_date",
        "total_members", "total_annual_premium",
    ]
    list_filter = ["status", "product", "scheme_type"]
    search_fields = ["scheme_number", "partner__partner_number", "partner__company_name"]
    readonly_fields = ["scheme_number", "created_at", "updated_at"]
    date_hierarchy = "inception_date"
    inlines = [GLSchemeCategoryInline, GLSchemeRiderInline]


@admin.register(GLSchemeCategory)
class GLSchemeCategoryAdmin(admin.ModelAdmin):
    list_display = [
        "scheme", "category_name", "salary_multiple", "flat_sum_assured",
        "premium_rate_per_mille", "is_active",
    ]
    list_filter = ["is_active"]
    search_fields = ["category_name", "scheme__scheme_number"]


@admin.register(GLSchemeMember)
class GLSchemeMemberAdmin(admin.ModelAdmin):
    list_display = [
        "member_number", "full_name_display", "scheme",
        "category", "status", "sum_assured", "premium_amount",
        "requires_medical_uw", "uw_status",
    ]
    list_filter = ["status", "uw_status", "requires_medical_uw", "gender"]
    search_fields = [
        "member_number", "first_name", "surname",
        "employee_number", "identification_number",
    ]
    readonly_fields = ["member_number", "created_at", "updated_at"]
    inlines = [GLSchemeMemberDependentInline]

    def full_name_display(self, obj):
        return obj.full_name
    full_name_display.short_description = "Full Name"


@admin.register(GLSchemeMemberDependent)
class GLSchemeMemberDependentAdmin(admin.ModelAdmin):
    list_display = [
        "member", "first_name", "surname", "relationship",
        "sum_assured", "is_active",
    ]
    list_filter = ["relationship", "is_active"]
    search_fields = ["first_name", "surname", "member__member_number"]


# =============================================================================
# LAYER 5 — MEDICAL UW ADMINS
# =============================================================================


@admin.register(GLMedicalCode)
class GLMedicalCodeAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "icd10_code", "category", "is_active"]
    list_filter = ["category", "is_active"]
    search_fields = ["code", "name", "icd10_code"]


@admin.register(GLMedicalLimit)
class GLMedicalLimitAdmin(admin.ModelAdmin):
    list_display = [
        "product", "age_from", "age_to",
        "sum_assured_from", "sum_assured_to", "is_active",
    ]
    list_filter = ["product", "is_active"]


@admin.register(GLUnderwritingDecision)
class GLUnderwritingDecisionAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "sort_order", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["code", "name"]


@admin.register(GLPersonalHabit)
class GLPersonalHabitAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "category", "risk_level", "is_active"]
    list_filter = ["category", "risk_level", "is_active"]
    search_fields = ["code", "name"]


@admin.register(GLMedicalHistory)
class GLMedicalHistoryAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "category", "risk_impact", "is_active"]
    list_filter = ["category", "risk_impact", "is_active"]
    search_fields = ["code", "name"]


@admin.register(GLMedicalFacility)
class GLMedicalFacilityAdmin(admin.ModelAdmin):
    list_display = [
        "code", "name", "facility_type", "city", "region",
        "is_approved", "is_active",
    ]
    list_filter = ["facility_type", "is_approved", "is_active", "region"]
    search_fields = ["code", "name", "city"]


@admin.register(GLMedicalPractitioner)
class GLMedicalPractitionerAdmin(admin.ModelAdmin):
    list_display = [
        "code", "name", "specialization", "facility",
        "is_approved", "is_active",
    ]
    list_filter = ["is_approved", "is_active"]
    search_fields = ["code", "name", "specialization", "license_number"]


@admin.register(GLMedicalCase)
class GLMedicalCaseAdmin(admin.ModelAdmin):
    list_display = [
        "case_number", "member", "facility", "status",
        "decision", "examination_date",
    ]
    list_filter = ["status", "decision"]
    search_fields = ["case_number", "member__member_number", "member__surname"]
    readonly_fields = ["case_number", "created_at", "updated_at"]
    filter_horizontal = ["diagnosis_codes", "personal_habits", "medical_history"]


# =============================================================================
# LAYER 6 — CLAIMS ADMINS
# =============================================================================


@admin.register(GLClaimType)
class GLClaimTypeAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "requires_medical_report", "is_active"]
    list_filter = ["requires_medical_report", "is_active"]
    search_fields = ["code", "name"]
    inlines = [GLClaimReasonInline]


@admin.register(GLClaimReason)
class GLClaimReasonAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "claim_type", "is_active"]
    list_filter = ["claim_type", "is_active"]
    search_fields = ["code", "name"]


@admin.register(GLClaimStatus)
class GLClaimStatusAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "sort_order", "is_terminal", "is_active"]
    list_filter = ["is_terminal", "is_active"]
    search_fields = ["code", "name"]
    ordering = ["sort_order"]


@admin.register(GLDischargeType)
class GLDischargeTypeAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["code", "name"]


@admin.register(GLCorrespondentType)
class GLCorrespondentTypeAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["code", "name"]


@admin.register(GLClaim)
class GLClaimAdmin(admin.ModelAdmin):
    list_display = [
        "claim_number", "scheme", "member_display", "claim_type", "status",
        "incident_date", "claim_amount", "approved_amount", "paid_amount",
        "reinsurance_notified",
    ]
    list_filter = ["status", "claim_type", "reinsurance_notified"]
    search_fields = [
        "claim_number", "member__member_number", "member__surname",
        "claimant_name", "scheme__scheme_number",
    ]
    readonly_fields = ["claim_number", "registration_date", "created_at", "updated_at"]
    date_hierarchy = "incident_date"
    inlines = [GLClaimInstallmentInline]

    def member_display(self, obj):
        return obj.member.full_name
    member_display.short_description = "Member"


@admin.register(GLClaimInstallment)
class GLClaimInstallmentAdmin(admin.ModelAdmin):
    list_display = [
        "claim", "installment_number", "due_date",
        "amount", "paid_amount", "status",
    ]
    list_filter = ["status"]
    search_fields = ["claim__claim_number"]


@admin.register(GLMedicalInvoice)
class GLMedicalInvoiceAdmin(admin.ModelAdmin):
    list_display = [
        "invoice_number", "facility", "invoice_date",
        "total_amount", "approved_amount", "paid_amount", "status",
    ]
    list_filter = ["status"]
    search_fields = ["invoice_number", "facility__name"]
    date_hierarchy = "invoice_date"


# =============================================================================
# LAYER 7 — RENEWAL ADMINS
# =============================================================================


@admin.register(GLSchemeRenewal)
class GLSchemeRenewalAdmin(admin.ModelAdmin):
    list_display = [
        "renewal_number", "scheme", "renewal_status",
        "current_expiry_date", "proposed_renewal_date",
        "previous_premium", "proposed_premium",
        "claims_experience_ratio",
    ]
    list_filter = ["renewal_status"]
    search_fields = ["renewal_number", "scheme__scheme_number"]
    readonly_fields = ["renewal_number", "created_at", "updated_at"]


@admin.register(GLSchemeRider)
class GLSchemeRiderAdmin(admin.ModelAdmin):
    list_display = ["scheme", "rider", "rate_per_mille", "flat_amount", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["scheme__scheme_number", "rider__name"]
