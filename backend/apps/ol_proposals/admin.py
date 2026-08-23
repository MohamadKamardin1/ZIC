from django.contrib import admin

from .models import (
    OLProposal,
    OLProposalBeneficiary,
    OLProposalBenefit,
    OLProposalDocument,
    OLProposalFundAllocation,
    OLProposalHealthAnswer,
    OLProposalInstallmentConfig,
    OLProposalInstallmentRateRow,
    OLProposalMember,
    OLProposalPlanConfig,
    OLProposalRider,
)


class OLProposalDocumentInline(admin.TabularInline):
    model = OLProposalDocument
    extra = 0
    fk_name = "proposal"
    readonly_fields = ("id", "uploaded_at", "uploaded_by", "created_at", "updated_at")


class OLProposalBeneficiaryInline(admin.TabularInline):
    model = OLProposalBeneficiary
    extra = 0
    fk_name = "proposal"


@admin.register(OLProposal)
class OLProposalAdmin(admin.ModelAdmin):
    list_display = (
        "proposal_number",
        "partner_name_snapshot",
        "agent_name_snapshot",
        "status",
        "underwriting_status",
        "medical_required",
        "payment_ready",
        "currency",
        "expiry_date",
        "converted_policy",
        "source_channel",
        "created_by",
        "created_at",
    )
    list_filter = ("status", "underwriting_status", "payment_ready", "medical_required", "currency", "source_channel", "created_at")
    search_fields = ("proposal_number", "partner_name_snapshot", "agent_name_snapshot", "quotation__quote_number")
    ordering = ("-created_at",)
    date_hierarchy = "created_at"
    filter_horizontal = ()
    readonly_fields = ("id", "proposal_number", "created_by", "updated_by", "created_at", "updated_at")
    inlines = (OLProposalDocumentInline, OLProposalBeneficiaryInline)
    fieldsets = (
        ("Identity", {"fields": ("proposal_number", "quotation", "quotation_version", "status", "source_channel")}),
        ("Parties", {"fields": ("partner", "partner_name_snapshot", "agent_partner", "agent_name_snapshot", "employer_partner", "employer_name_snapshot")}),
        ("Commercial", {"fields": ("currency", "expiry_date", "converted_policy")}),
        ("Lifecycle", {"fields": ("payment_ready", "payment_ready_at", "underwriting_status", "medical_required")}),
        ("Reason", {"fields": ("reason_code", "reason_text")}),
        ("Snapshots", {"fields": ("prospect_snapshot", "plans_snapshot", "financial_summary_snapshot")}),
        ("Audit", {"fields": ("created_by", "updated_by", "created_at", "updated_at")}),
    )


@admin.register(OLProposalPlanConfig)
class OLProposalPlanConfigAdmin(admin.ModelAdmin):
    list_display = ("proposal", "plan_name_snapshot", "base_sum_assured", "term_years", "payment_period_years", "premium_frequency", "premium_amount", "is_selected")
    list_filter = ("premium_frequency", "is_selected")
    search_fields = ("proposal__proposal_number", "plan_name_snapshot", "sub_product_code")


@admin.register(OLProposalMember)
class OLProposalMemberAdmin(admin.ModelAdmin):
    list_display = ("proposal", "full_name_snapshot", "member_type", "date_of_birth", "age_at_quote", "gender", "relationship")
    list_filter = ("member_type", "gender")
    search_fields = ("proposal__proposal_number", "full_name_snapshot", "first_name", "last_name", "identity_number")


@admin.register(OLProposalInstallmentConfig)
class OLProposalInstallmentConfigAdmin(admin.ModelAdmin):
    list_display = ("proposal", "frequency", "number_of_installments", "installment_amount", "first_due_date", "currency", "is_selected")
    list_filter = ("frequency", "is_selected")


@admin.register(OLProposalInstallmentRateRow)
class OLProposalInstallmentRateRowAdmin(admin.ModelAdmin):
    list_display = ("installment_config", "sequence", "period_from", "period_to", "rate_percent", "rate", "charge")


@admin.register(OLProposalFundAllocation)
class OLProposalFundAllocationAdmin(admin.ModelAdmin):
    list_display = ("proposal", "fund_name_snapshot", "allocation_percentage", "allocation_amount", "is_selected")
    list_filter = ("is_selected",)


@admin.register(OLProposalRider)
class OLProposalRiderAdmin(admin.ModelAdmin):
    list_display = ("proposal", "rider_name_snapshot", "rider_sum_assured", "rider_term_years", "benefit_basis", "premium_amount", "is_selected")
    list_filter = ("benefit_basis", "is_selected")


@admin.register(OLProposalBenefit)
class OLProposalBenefitAdmin(admin.ModelAdmin):
    list_display = ("proposal", "code", "name", "benefit_type", "basis", "value", "sum_assured", "premium_amount", "is_selected")
    list_filter = ("basis", "is_selected", "benefit_type")


@admin.register(OLProposalBeneficiary)
class OLProposalBeneficiaryAdmin(admin.ModelAdmin):
    list_display = ("proposal", "person_name", "beneficial_type_name_snapshot", "share_percent", "is_primary", "is_minor", "guardian_name")
    list_filter = ("is_primary", "is_minor")


@admin.register(OLProposalDocument)
class OLProposalDocumentAdmin(admin.ModelAdmin):
    list_display = ("proposal", "document_type", "mandatory", "status", "uploaded_by", "uploaded_at")
    list_filter = ("status", "mandatory")
    search_fields = ("proposal__proposal_number", "document_type", "file_reference")


@admin.register(OLProposalHealthAnswer)
class OLProposalHealthAnswerAdmin(admin.ModelAdmin):
    list_display = ("proposal", "health_question", "triggers_medical", "score", "answered_at")
    list_filter = ("triggers_medical",)
    search_fields = ("proposal__proposal_number",)