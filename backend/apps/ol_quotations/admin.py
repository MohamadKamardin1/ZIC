from django.contrib import admin

from .models import (
    OLQuotation,
    OLQuotationBeneficiary,
    OLQuotationBenefit,
    OLQuotationDocument,
    OLQuotationEvent,
    OLQuotationFinancialSummary,
    OLQuotationFundAllocation,
    OLQuotationInstallmentConfiguration,
    OLQuotationInstallmentRateRow,
    OLQuotationMember,
    OLQuotationPaymentDetail,
    OLQuotationPlanConfiguration,
    OLQuotationProduct,
    OLQuotationRiderSelection,
    OLQuotationUnderwriting,
    OLQuotationVersion,
)


class QuotationAuditFieldsMixin:
    readonly_fields = ["id", "created_at", "updated_at", "created_by", "updated_by"]


@admin.register(OLQuotation)
class OLQuotationAdmin(QuotationAuditFieldsMixin, admin.ModelAdmin):
    list_display = [
        "quote_number",
        "quote_name",
        "prospect_name",
        "plans_summary",
        "plan_count",
        "total_premium",
        "currency",
        "status_badge",
        "version",
        "quote_date",
        "agent",
        "created_by",
    ]
    list_filter = [
        "status",
        "currency",
        "quote_date",
        "expiry_date",
        "product",
        "agent",
        "location",
    ]
    search_fields = [
        "quote_number",
        "quote_name",
        "identity_number",
        "location",
        "members__identity_number",
        "partner__partner_number",
        "partner__legal_name",
        "partner__company_name",
        "partner__first_name",
        "partner__surname",
        "agent__username",
        "agent__first_name",
        "agent__last_name",
    ]
    ordering = ["-created_at"]
    list_select_related = ["partner", "linked_partner", "product", "product_version", "agent", "created_by"]

    @admin.display(description="Prospect", ordering="identity_number")
    def prospect_name(self, obj):
        member = next(
            (item for item in obj.members.all() if item.member_type == "LIFE_ASSURED"),
            None,
        )
        if member:
            return " ".join(
                part for part in [member.first_name, member.middle_name, member.last_name] if part
            ).strip()
        return obj.quote_name or obj.identity_number or "—"

    @admin.display(description="Plans")
    def plans_summary(self, obj):
        labels = []
        for configuration in obj.plan_configurations.all():
            if not configuration.is_selected:
                continue
            label = (
                f"{configuration.plan.code} - {configuration.plan.name}"
                if configuration.plan
                else configuration.sub_product_code or str(configuration.product_version)
            )
            if label and label not in labels:
                labels.append(label)
        return ", ".join(labels) or "—"

    @admin.display(description="Plan count")
    def plan_count(self, obj):
        return sum(1 for configuration in obj.plan_configurations.all() if configuration.is_selected)

    @admin.display(description="Status")
    def status_badge(self, obj):
        return f"{obj.get_status_display()} ({obj.status})"

    @admin.display(description="Version", ordering="current_version_number")
    def version(self, obj):
        return obj.current_version_number


@admin.register(OLQuotationProduct)
class OLQuotationProductAdmin(QuotationAuditFieldsMixin, admin.ModelAdmin):
    list_display = ["quotation", "product", "product_version", "product_name_snapshot", "currency", "is_selected", "is_primary"]
    list_filter = ["is_selected", "is_primary", "currency", "product"]
    search_fields = ["quotation__quote_number", "product__code", "product__name", "product_name_snapshot"]
    list_select_related = ["quotation", "product", "product_version"]


@admin.register(OLQuotationPlanConfiguration)
class OLQuotationPlanConfigurationAdmin(QuotationAuditFieldsMixin, admin.ModelAdmin):
    list_display = ["quotation", "product_version", "plan", "sub_product_code", "base_sum_assured", "term_years", "premium_frequency", "premium_amount", "is_selected"]
    list_filter = ["is_selected", "premium_frequency", "product_version", "plan"]
    search_fields = ["quotation__quote_number", "sub_product_code"]
    list_select_related = ["quotation", "product_version", "plan"]


@admin.register(OLQuotationMember)
class OLQuotationMemberAdmin(QuotationAuditFieldsMixin, admin.ModelAdmin):
    list_display = ["quotation", "member_type", "first_name", "last_name", "date_of_birth", "age_at_quote", "gender", "smoker_status"]
    list_filter = ["member_type", "gender", "smoker_status"]
    search_fields = ["quotation__quote_number", "first_name", "last_name", "identity_number"]
    list_select_related = ["quotation", "partner"]


@admin.register(OLQuotationInstallmentConfiguration)
class OLQuotationInstallmentConfigurationAdmin(QuotationAuditFieldsMixin, admin.ModelAdmin):
    list_display = ["quotation", "plan_configuration", "frequency", "number_of_installments", "installment_amount", "currency", "is_selected"]
    list_filter = ["frequency", "currency", "is_selected"]
    search_fields = ["quotation__quote_number", "frequency"]
    list_select_related = ["quotation", "plan_configuration"]


@admin.register(OLQuotationInstallmentRateRow)
class OLQuotationInstallmentRateRowAdmin(QuotationAuditFieldsMixin, admin.ModelAdmin):
    list_display = ["installment_configuration", "period_from", "period_to", "rate", "charge", "notes"]
    list_filter = ["period_from", "period_to"]
    search_fields = ["installment_configuration__quotation__quote_number", "notes"]
    list_select_related = ["installment_configuration"]


@admin.register(OLQuotationFundAllocation)
class OLQuotationFundAllocationAdmin(QuotationAuditFieldsMixin, admin.ModelAdmin):
    list_display = ["quotation", "fund", "allocation_percentage", "allocation_amount", "is_selected"]
    list_filter = ["is_selected", "fund"]
    search_fields = ["quotation__quote_number", "fund__code", "fund__name"]
    list_select_related = ["quotation", "fund"]


@admin.register(OLQuotationRiderSelection)
class OLQuotationRiderSelectionAdmin(QuotationAuditFieldsMixin, admin.ModelAdmin):
    list_display = ["quotation", "rider", "plan_configuration", "rider_sum_assured", "premium_amount", "is_selected"]
    list_filter = ["is_selected", "rider"]
    search_fields = ["quotation__quote_number", "rider__code", "rider__name"]
    list_select_related = ["quotation", "rider", "plan_configuration"]


@admin.register(OLQuotationPaymentDetail)
class OLQuotationPaymentDetailAdmin(QuotationAuditFieldsMixin, admin.ModelAdmin):
    list_display = ["quotation", "payer", "payment_method", "payment_reference", "amount", "currency"]
    list_filter = ["payment_method", "currency"]
    search_fields = ["quotation__quote_number", "payment_reference", "account_reference"]
    list_select_related = ["quotation", "payer"]


@admin.register(OLQuotationUnderwriting)
class OLQuotationUnderwritingAdmin(QuotationAuditFieldsMixin, admin.ModelAdmin):
    list_display = ["quotation", "medical_required", "financial_underwriting_required", "risk_class", "created_at"]
    list_filter = ["medical_required", "financial_underwriting_required", "risk_class"]
    search_fields = ["quotation__quote_number", "risk_class", "notes"]
    list_select_related = ["quotation"]


@admin.register(OLQuotationBeneficiary)
class OLQuotationBeneficiaryAdmin(QuotationAuditFieldsMixin, admin.ModelAdmin):
    list_display = ["quotation", "name", "relationship", "percentage", "identity_number"]
    list_filter = ["relationship"]
    search_fields = ["quotation__quote_number", "name", "identity_number"]
    list_select_related = ["quotation", "partner"]


@admin.register(OLQuotationBenefit)
class OLQuotationBenefitAdmin(QuotationAuditFieldsMixin, admin.ModelAdmin):
    list_display = ["quotation", "code", "name", "benefit_type", "sum_assured", "premium_amount", "is_selected"]
    list_filter = ["benefit_type", "is_selected"]
    search_fields = ["quotation__quote_number", "code", "name"]
    list_select_related = ["quotation"]


@admin.register(OLQuotationDocument)
class OLQuotationDocumentAdmin(QuotationAuditFieldsMixin, admin.ModelAdmin):
    list_display = ["quotation", "document_type", "file_reference", "status", "created_at"]
    list_filter = ["document_type", "status"]
    search_fields = ["quotation__quote_number", "document_type", "file_reference"]
    list_select_related = ["quotation"]


@admin.register(OLQuotationVersion)
class OLQuotationVersionAdmin(QuotationAuditFieldsMixin, admin.ModelAdmin):
    list_display = ["quotation", "version_number", "status", "change_reason", "created_at"]
    list_filter = ["status", "created_at"]
    search_fields = ["quotation__quote_number", "change_reason"]
    list_select_related = ["quotation"]
    readonly_fields = [field.name for field in OLQuotationVersion._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(OLQuotationFinancialSummary)
class OLQuotationFinancialSummaryAdmin(QuotationAuditFieldsMixin, admin.ModelAdmin):
    list_display = ["quotation", "currency", "total_sum_assured", "total_premium", "total_rider_premium", "total_benefit_premium", "updated_at"]
    list_filter = ["currency", "updated_at"]
    search_fields = ["quotation__quote_number"]
    list_select_related = ["quotation"]


@admin.register(OLQuotationEvent)
class OLQuotationEventAdmin(admin.ModelAdmin):
    list_display = ["quotation", "event_type", "from_status", "to_status", "actor", "created_at"]
    list_filter = ["event_type", "from_status", "to_status", "created_at"]
    search_fields = ["quotation__quote_number", "event_type", "notes"]
    list_select_related = ["quotation", "actor"]
    readonly_fields = [field.name for field in OLQuotationEvent._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
