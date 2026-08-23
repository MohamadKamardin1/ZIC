from django.contrib import admin

from apps.ordinary_life import models


class ValidatingAdmin(admin.ModelAdmin):
    """Run model validation before configuration or operational records persist."""

    def save_model(self, request, obj, form, change):
        obj.full_clean()
        super().save_model(request, obj, form, change)


class ReferenceAdmin(ValidatingAdmin):
    list_display = ("id", "is_active")
    list_filter = ("is_active",)
    search_fields = ("id",)


class ReadOnlyHistoryAdmin(admin.ModelAdmin):
    readonly_fields = [field.name for field in models.OLPolicyStatusHistory._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(models.OLLookupValue)
class LookupValueAdmin(ValidatingAdmin):
    list_display = ("category", "value", "label", "sort_order", "is_active")
    list_filter = ("category", "is_active")
    search_fields = ("category", "value", "label")


@admin.register(models.OLDefaultSystemParameter)
class DefaultSystemParameterAdmin(ValidatingAdmin):
    list_display = ("code", "name", "value", "is_active")
    list_filter = ("is_active",)
    search_fields = ("code", "name", "value")


@admin.register(models.OLProduct)
class ProductAdmin(ValidatingAdmin):
    list_display = ("code", "name", "is_active")
    list_filter = ("is_active",)
    search_fields = ("code", "name")


@admin.register(models.OLProductVersion)
class ProductVersionAdmin(ValidatingAdmin):
    list_display = ("product", "version_number", "effective_from", "effective_to", "currency", "is_active")
    list_filter = ("is_active", "currency")
    search_fields = ("product__code", "product__name")
    fieldsets = (
        ("Product version", {"fields": ("product", "version_number", "currency", "effective_from", "effective_to", "is_active")}),
        ("Eligibility and premium frequency", {"fields": ("min_entry_age", "max_entry_age", "min_term_years", "max_term_years", "payment_frequencies")}),
        ("Installment payment methods", {"fields": ("servicing_rules",), "description": "Optional JSON key installment_payment_modes restricts active OL Payment Modes for this product version. Leave it absent to allow all active payment modes."}),
        ("Underwriting and snapshots", {"fields": ("underwriting_rules", "snapshot", "calculation_approach")}),
        ("Audit", {"fields": ("created_at", "updated_at")}),
    )
    readonly_fields = ("created_at", "updated_at")


@admin.register(models.OLPlan)
class PlanAdmin(ValidatingAdmin):
    list_display = ("code", "name", "product_version", "minimum_sum_assured", "maximum_sum_assured", "is_active")
    list_filter = ("is_active",)
    search_fields = ("code", "name", "product_version__product__code")


@admin.register(models.OLBenefit)
class BenefitAdmin(ValidatingAdmin):
    list_display = ("code", "name", "benefit_type", "is_active")
    list_filter = ("benefit_type", "is_active")
    search_fields = ("code", "name")


@admin.register(models.OLRider)
class RiderAdmin(ValidatingAdmin):
    list_display = ("code", "name", "is_active")
    list_filter = ("is_active",)
    search_fields = ("code", "name")


@admin.register(models.OLProductBenefit)
class ProductBenefitAdmin(ValidatingAdmin):
    list_display = ("product_version", "benefit", "is_mandatory", "is_active")
    list_filter = ("is_mandatory", "is_active")
    search_fields = ("product_version__product__code", "benefit__code")


@admin.register(models.OLProductRider)
class ProductRiderAdmin(ValidatingAdmin):
    list_display = ("product_version", "rider", "is_mandatory", "is_active")
    list_filter = ("is_mandatory", "is_active")
    search_fields = ("product_version__product__code", "rider__code")


@admin.register(models.OLRateBand)
class RateBandAdmin(ValidatingAdmin):
    list_display = ("product_version", "plan", "min_age", "max_age", "min_term_years", "max_term_years", "rate", "is_active")
    list_filter = ("is_active",)
    search_fields = ("product_version__product__code", "plan__code")


@admin.register(models.OLGracePeriod)
class GracePeriodAdmin(ValidatingAdmin):
    list_display = ("id", "days", "is_active")
    list_filter = ("is_active",)


@admin.register(models.OLGracePeriodNotificationSchedule)
class GracePeriodNotificationScheduleAdmin(ValidatingAdmin):
    list_display = ("id", "days_past_due", "notification_type", "is_active")
    list_filter = ("notification_type", "is_active")


@admin.register(models.OLHealthQuestion)
class HealthQuestionAdmin(ValidatingAdmin):
    list_display = ("id", "category", "is_active")
    list_filter = ("category", "is_active")
    search_fields = ("question_text",)


@admin.register(models.OLHealthQuestionnaire)
class HealthQuestionnaireAdmin(ValidatingAdmin):
    list_display = ("id", "version", "effective_date", "is_active")
    list_filter = ("is_active",)


@admin.register(models.OLReinstatementWindow)
class ReinstatementWindowAdmin(ValidatingAdmin):
    list_display = ("id", "max_months", "requires_medical", "is_active")
    list_filter = ("requires_medical", "is_active")


@admin.register(models.OLApplication)
class ApplicationAdmin(ValidatingAdmin):
    list_display = ("application_number", "partner", "status", "submitted_at", "created_at")
    list_filter = ("status",)
    search_fields = ("application_number", "partner__name")


@admin.register(models.OLQuotationVersion)
class QuotationVersionAdmin(ValidatingAdmin):
    list_display = ("quotation", "version_number", "product_version", "calculated_at")
    search_fields = ("quotation__quotation_number", "calculation_hash")


@admin.register(models.OLUnderwritingCase)
class UnderwritingCaseAdmin(ValidatingAdmin):
    list_display = ("proposal", "decision", "risk_class", "reviewer", "created_at")
    list_filter = ("decision",)
    search_fields = ("proposal__proposal_number", "risk_class")


@admin.register(models.OLPaymentObligation)
class PaymentObligationAdmin(ValidatingAdmin):
    list_display = ("id", "obligation_type", "amount", "allocated_amount", "currency", "status", "due_date")
    list_filter = ("obligation_type", "status", "currency")
    search_fields = ("proposal__proposal_number", "policy__policy_number")


@admin.register(models.OLPremiumSchedule)
class PremiumScheduleAdmin(ValidatingAdmin):
    list_display = ("policy", "frequency", "total_premium", "installment_count", "is_current", "effective_from")
    list_filter = ("frequency", "currency", "is_current")
    search_fields = ("policy__policy_number",)


@admin.register(models.OLPolicyTransaction)
class PolicyTransactionAdmin(ValidatingAdmin):
    list_display = ("transaction_number", "policy", "transaction_type", "status", "effective_date", "amount")
    list_filter = ("transaction_type", "status", "currency")
    search_fields = ("transaction_number", "policy__policy_number", "idempotency_key")


@admin.register(models.OLEndorsement)
class EndorsementAdmin(ValidatingAdmin):
    list_display = ("endorsement_number", "policy", "endorsement_type", "status", "requested_effective_date")
    list_filter = ("status", "endorsement_type")
    search_fields = ("endorsement_number", "policy__policy_number")


@admin.register(models.OLDocumentRecord)
class DocumentRecordAdmin(ValidatingAdmin):
    list_display = ("id", "status", "proposal", "policy", "created_at")
    list_filter = ("status",)
    search_fields = ("document_type", "file_reference")


@admin.register(models.OLNote)
class NoteAdmin(ValidatingAdmin):
    list_display = ("id", "is_internal", "proposal", "policy", "created_by", "created_at")
    list_filter = ("is_internal",)
    search_fields = ("content",)


@admin.register(models.OLPolicyStatusHistory)
class PolicyStatusHistoryAdmin(ReadOnlyHistoryAdmin):
    list_display = ("policy", "previous_status", "new_status", "actor", "created_at")
    search_fields = ("policy__policy_number", "reason")


@admin.register(models.OLWorkflowEvent)
class WorkflowEventAdmin(admin.ModelAdmin):
    list_display = ("entity_type", "entity_id", "action", "previous_status", "new_status", "actor", "created_at")
    list_filter = ("entity_type", "action")
    search_fields = ("entity_type", "entity_id", "action", "reason")
    readonly_fields = [field.name for field in models.OLWorkflowEvent._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


for model in (
    models.OLComputationApproach,
    models.OLPolicyStatus,
    models.OLPolicyRenewalStatus,
    models.OLBeneficiaryType,
    models.OLCommitmentStatus,
    models.OLMemberCoverConfiguration,
):
    admin.site.register(model, ReferenceAdmin)
