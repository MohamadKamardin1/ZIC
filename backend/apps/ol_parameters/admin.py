from django.contrib import admin, messages

from .models import (
    OLAnticipatedEndowmentInstallmentRate,
    OLBeneficialType,
    OLComputationApproach,
    OLDefaultSystemParameter,
    OLGracePeriod,
    OLMaturityClaimSetup,
    OLMemberCoverConfiguration,
    OLOverrideCommissionSetup,
    OLPaidUpRate,
    OLPaidUpSetup,
    OLCommitmentStatus,
    OLHealthQuestion,
    OLHealthQuestionnaire,
    OLHealthQuestionnaireItem,
    OLGracePeriodNotificationSchedule,
    OLReinstatementWindow,
    OLPlanType,
    OLProduct,
    OLPlanTaxConfiguration,
    OLPlanTargetMarket,
    OLPlanRiskCategory,
    OLPlanOccupationRiskLimit,
    OLInvestmentFundType,
    OLInvestmentFund,
    OLSurrenderSetup,
    OLSurrenderValueRate,
    OLParameterTableRegistry,
    OLPolicyRenewalStatus,
    OLPolicyStatus,
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


@admin.register(OLAnticipatedEndowmentInstallmentRate)
class OLAnticipatedEndowmentInstallmentRateAdmin(OLDefaultSetupAdmin):
    list_display = (
        "code", "name", "product", "plan", "installment_type", "frequency", "rate_factor",
        "effective_from", "effective_to", "is_active", "updated_at",
    )
    list_filter = ("is_active", "installment_type", "frequency", "currency", "effective_from", "effective_to")
    search_fields = ("code", "name", "description", "installment_type", "frequency", "currency", "product__code", "plan__code")
    ordering = ("product", "plan", "frequency", "age_from", "term_from", "code")
    autocomplete_fields = ("product", "plan")
    fieldsets = (
        ("Identity", {"fields": ("code", "name", "description", "is_active")}),
        ("Scope", {"fields": ("product", "plan", "installment_type", "frequency", "currency")}),
        ("Dimensions and rate", {"fields": ("age_from", "age_to", "term_from", "term_to", "policy_year_from", "policy_year_to", "rate_factor")}),
        ("Effective dates", {"fields": ("effective_from", "effective_to")}),
        ("Audit", {"fields": ("created_by", "created_at", "updated_by", "updated_at")}),
    )


@admin.register(OLGracePeriod)
class OLGracePeriodAdmin(OLDefaultSetupAdmin):
    list_display = (
        "code", "name", "product", "plan", "premium_frequency", "grace_days", "warning_days",
        "pre_lapse_days", "lapse_days", "effective_from", "effective_to", "is_active",
    )
    list_filter = ("is_active", "premium_frequency", "effective_from", "effective_to")
    search_fields = ("code", "name", "description", "premium_frequency", "product__code", "plan__code")
    ordering = ("product", "plan", "premium_frequency", "-effective_from", "code")
    autocomplete_fields = ("product", "plan")
    fieldsets = (
        ("Identity", {"fields": ("code", "name", "description", "is_active")}),
        ("Scope", {"fields": ("product", "plan", "premium_frequency")}),
        ("Timing", {"fields": ("grace_days", "warning_days", "pre_lapse_days", "lapse_days", "minimum_due_amount")}),
        ("Effective dates", {"fields": ("effective_from", "effective_to")}),
        ("Audit", {"fields": ("created_by", "created_at", "updated_by", "updated_at")}),
    )


@admin.register(OLPolicyStatus)
class OLPolicyStatusAdmin(OLDefaultSetupAdmin):
    list_display = ("display_order", "code", "name", "badge_type", "is_terminal", "is_active", "updated_at")
    list_filter = ("is_active", "is_terminal", "badge_type")
    search_fields = ("code", "name", "description", "badge_type")
    ordering = ("display_order", "name", "code")
    fieldsets = (
        ("Identity", {"fields": ("code", "name", "description", "is_active")}),
        ("Lifecycle", {"fields": ("display_order", "badge_type", "is_terminal", "allowed_transitions")}),
        ("Effective dates", {"fields": ("effective_from", "effective_to")}),
        ("Audit", {"fields": ("created_by", "created_at", "updated_by", "updated_at")}),
    )


@admin.register(OLPolicyRenewalStatus)
class OLPolicyRenewalStatusAdmin(OLDefaultSetupAdmin):
    list_display = ("display_order", "code", "name", "renewal_action", "is_active", "updated_at")
    list_filter = ("is_active", "renewal_action")
    search_fields = ("code", "name", "description", "renewal_action")
    ordering = ("display_order", "name", "code")
    fieldsets = (
        ("Identity", {"fields": ("code", "name", "description", "is_active")}),
        ("Renewal behavior", {"fields": ("display_order", "renewal_action")}),
        ("Effective dates", {"fields": ("effective_from", "effective_to")}),
        ("Audit", {"fields": ("created_by", "created_at", "updated_by", "updated_at")}),
    )


@admin.register(OLBeneficialType)
class OLBeneficialTypeAdmin(OLDefaultSetupAdmin):
    list_display = (
        "category", "code", "name", "calculation_basis", "default_ratio", "allows_multiple", "is_active", "updated_at",
    )
    list_filter = ("is_active", "category", "calculation_basis", "allows_multiple")
    search_fields = ("code", "name", "description", "category", "calculation_basis")
    ordering = ("category", "name", "code")
    fieldsets = (
        ("Identity", {"fields": ("code", "name", "description", "is_active")}),
        ("Beneficial behavior", {"fields": ("category", "calculation_basis", "default_ratio", "allows_multiple")}),
        ("Effective dates", {"fields": ("effective_from", "effective_to")}),
        ("Audit", {"fields": ("created_by", "created_at", "updated_by", "updated_at")}),
    )


@admin.register(OLMemberCoverConfiguration)
class OLMemberCoverConfigurationAdmin(OLDefaultSetupAdmin):
    list_display = (
        "code", "name", "product", "plan", "cover_type", "member_relation", "min_age", "max_age",
        "waiting_period_days", "effective_from", "effective_to", "is_active",
    )
    list_filter = ("is_active", "cover_type", "member_relation", "premium_basis", "coverage_basis", "effective_from", "effective_to")
    search_fields = ("code", "name", "description", "cover_type", "member_relation", "premium_basis", "coverage_basis", "product__code", "plan__code")
    ordering = ("product", "plan", "cover_type", "member_relation", "min_age", "code")
    autocomplete_fields = ("product", "plan")
    fieldsets = (
        ("Identity", {"fields": ("code", "name", "description", "is_active")}),
        ("Scope", {"fields": ("product", "plan", "cover_type", "member_relation")}),
        ("Eligibility and cover", {"fields": ("min_age", "max_age", "waiting_period_days", "benefit_limit", "premium_basis", "coverage_basis")}),
        ("Effective dates", {"fields": ("effective_from", "effective_to")}),
        ("Audit", {"fields": ("created_by", "created_at", "updated_by", "updated_at")}),
    )


@admin.register(OLSurrenderSetup)
class OLSurrenderSetupAdmin(OLDefaultSetupAdmin):
    list_display = (
        "code", "name", "product", "plan", "minimum_policy_months", "minimum_premiums_paid",
        "surrender_charge_type", "surrender_charge_value", "partial_surrender_allowed", "is_active", "updated_at",
    )
    list_filter = (
        "is_active", "surrender_charge_type", "partial_surrender_allowed", "require_approval",
        "effective_from", "effective_to",
    )
    search_fields = ("code", "name", "description", "surrender_charge_type", "product__code", "plan__code")
    ordering = ("product", "plan", "-effective_from", "code")
    autocomplete_fields = ("product", "plan")
    fieldsets = (
        ("Identity", {"fields": ("code", "name", "description", "is_active")}),
        ("Scope", {"fields": ("product", "plan")}),
        ("Eligibility", {"fields": ("minimum_premiums_paid", "minimum_policy_months", "minimum_premium_paid_ratio")}),
        ("Surrender behavior", {"fields": ("surrender_charge_type", "surrender_charge_value", "partial_surrender_allowed", "surrender_payout_days", "require_approval")}),
        ("Effective dates", {"fields": ("effective_from", "effective_to")}),
        ("Audit", {"fields": ("created_by", "created_at", "updated_by", "updated_at")}),
    )


@admin.register(OLPaidUpSetup)
class OLPaidUpSetupAdmin(OLDefaultSetupAdmin):
    list_display = (
        "code", "name", "product", "plan", "minimum_policy_months", "minimum_premiums_paid",
        "paidup_conversion_basis", "paidup_effective_rule", "allow_paidup", "is_active", "updated_at",
    )
    list_filter = ("is_active", "allow_paidup", "paidup_conversion_basis", "paidup_effective_rule", "effective_from", "effective_to")
    search_fields = ("code", "name", "description", "paidup_conversion_basis", "paidup_effective_rule", "product__code", "plan__code")
    ordering = ("product", "plan", "-effective_from", "code")
    autocomplete_fields = ("product", "plan")
    fieldsets = (
        ("Identity", {"fields": ("code", "name", "description", "is_active")}),
        ("Scope", {"fields": ("product", "plan")}),
        ("Eligibility", {"fields": ("minimum_premiums_paid", "minimum_policy_months", "allow_paidup")}),
        ("Conversion behavior", {"fields": ("paidup_conversion_basis", "paidup_effective_rule")}),
        ("Effective dates", {"fields": ("effective_from", "effective_to")}),
        ("Audit", {"fields": ("created_by", "created_at", "updated_by", "updated_at")}),
    )


class OLRatePart2Admin(OLDefaultSetupAdmin):
    list_filter = (
        "is_active", "table_code", "rate_table_version", "gender", "smoker_status", "effective_from", "effective_to",
    )
    search_fields = (
        "code", "name", "description", "table_code", "rate_table_version", "gender", "smoker_status",
        "product__code", "plan__code",
    )
    ordering = ("table_code", "rate_table_version", "product", "plan", "row_order", "age_from", "term_from", "policy_year_from", "code")
    autocomplete_fields = ("product", "plan")


@admin.register(OLSurrenderValueRate)
class OLSurrenderValueRateAdmin(OLRatePart2Admin):
    list_display = (
        "table_code", "rate_table_version", "code", "product", "plan", "gender", "smoker_status",
        "age_from", "age_to", "term_from", "term_to", "policy_year_from", "policy_year_to", "rate_factor", "is_active",
    )
    fieldsets = (
        ("Identity", {"fields": ("code", "name", "description", "is_active")}),
        ("Table and scope", {"fields": ("table_code", "rate_table_version", "product", "plan", "gender", "smoker_status")}),
        ("Dimensions and rate", {"fields": ("age_from", "age_to", "term_from", "term_to", "policy_year_from", "policy_year_to", "rate_factor", "row_order")}),
        ("Effective dates", {"fields": ("effective_from", "effective_to")}),
        ("Audit", {"fields": ("created_by", "created_at", "updated_by", "updated_at")}),
    )


@admin.register(OLPaidUpRate)
class OLPaidUpRateAdmin(OLRatePart2Admin):
    list_display = (
        "table_code", "rate_table_version", "code", "product", "plan", "gender", "smoker_status",
        "age_from", "age_to", "term_from", "term_to", "policy_year_from", "policy_year_to", "rate_factor", "is_active",
    )
    fieldsets = (
        ("Identity", {"fields": ("code", "name", "description", "is_active")}),
        ("Table and scope", {"fields": ("table_code", "rate_table_version", "product", "plan", "gender", "smoker_status")}),
        ("Dimensions and rate", {"fields": ("age_from", "age_to", "term_from", "term_to", "policy_year_from", "policy_year_to", "rate_factor", "row_order")}),
        ("Effective dates", {"fields": ("effective_from", "effective_to")}),
        ("Audit", {"fields": ("created_by", "created_at", "updated_by", "updated_at")}),
    )


@admin.register(OLCommitmentStatus)
class OLCommitmentStatusAdmin(OLDefaultSetupAdmin):
    list_display = ("display_order", "code", "name", "applies_to", "is_terminal", "is_active", "updated_at")
    list_filter = ("is_active", "applies_to", "is_terminal")
    search_fields = ("code", "name", "description", "applies_to")
    ordering = ("applies_to", "display_order", "name", "code")
    fieldsets = (
        ("Identity", {"fields": ("code", "name", "description", "is_active")}),
        ("Status behavior", {"fields": ("display_order", "applies_to", "is_terminal")}),
        ("Audit", {"fields": ("created_by", "created_at", "updated_by", "updated_at")}),
    )


@admin.register(OLHealthQuestion)
class OLHealthQuestionAdmin(OLDefaultSetupAdmin):
    list_display = ("category", "code", "name", "answer_type", "underwriting_impact", "requires_medical_followup", "is_active", "updated_at")
    list_filter = ("is_active", "category", "answer_type", "underwriting_impact", "requires_medical_followup")
    search_fields = ("code", "name", "description", "question_text", "category", "answer_type", "underwriting_impact")
    ordering = ("category", "name", "code")
    fieldsets = (
        ("Identity", {"fields": ("code", "name", "description", "is_active")}),
        ("Question", {"fields": ("question_text", "category", "answer_type", "underwriting_impact", "requires_medical_followup")}),
        ("Effective dates", {"fields": ("effective_from", "effective_to")}),
        ("Audit", {"fields": ("created_by", "created_at", "updated_by", "updated_at")}),
    )


@admin.register(OLHealthQuestionnaire)
class OLHealthQuestionnaireAdmin(OLDefaultSetupAdmin):
    list_display = ("code", "name", "version", "applies_to_scope", "product", "plan", "age_threshold", "is_active", "updated_at")
    list_filter = ("is_active", "applies_to_scope", "version", "effective_from", "effective_to")
    search_fields = ("code", "name", "description", "scheme_code", "version", "product__code", "plan__code")
    ordering = ("code", "-effective_from", "version")
    autocomplete_fields = ("product", "plan")
    fieldsets = (
        ("Identity", {"fields": ("code", "name", "description", "is_active")}),
        ("Scope and version", {"fields": ("applies_to_scope", "product", "plan", "scheme_code", "version")}),
        ("Thresholds", {"fields": ("sum_assured_threshold", "age_threshold")}),
        ("Effective dates", {"fields": ("effective_from", "effective_to")}),
        ("Audit", {"fields": ("created_by", "created_at", "updated_by", "updated_at")}),
    )


@admin.register(OLHealthQuestionnaireItem)
class OLHealthQuestionnaireItemAdmin(OLDefaultSetupAdmin):
    list_display = ("questionnaire", "sequence", "code", "health_question", "mandatory", "trigger_medical_requirement", "score", "is_active", "updated_at")
    list_filter = ("is_active", "mandatory", "trigger_medical_requirement", "questionnaire")
    search_fields = ("code", "name", "description", "questionnaire__code", "questionnaire__name", "health_question__code", "health_question__question_text")
    ordering = ("questionnaire", "sequence", "code")
    autocomplete_fields = ("questionnaire", "health_question")
    fieldsets = (
        ("Identity", {"fields": ("code", "name", "description", "is_active")}),
        ("Question membership", {"fields": ("questionnaire", "health_question", "sequence", "mandatory", "trigger_medical_requirement", "score")}),
        ("Audit", {"fields": ("created_by", "created_at", "updated_by", "updated_at")}),
    )


@admin.register(OLGracePeriodNotificationSchedule)
class OLGracePeriodNotificationScheduleAdmin(OLDefaultSetupAdmin):
    list_display = ("event_type", "days_offset", "code", "notification_channel", "recipient_type", "template_code", "is_active", "updated_at")
    list_filter = ("is_active", "event_type", "notification_channel", "recipient_type", "effective_from", "effective_to")
    search_fields = ("code", "name", "description", "event_type", "notification_channel", "recipient_type", "template_code")
    ordering = ("event_type", "days_offset", "code")
    fieldsets = (
        ("Identity", {"fields": ("code", "name", "description", "is_active")}),
        ("Schedule", {"fields": ("event_type", "days_offset", "notification_channel", "recipient_type", "template_code")}),
        ("Effective dates", {"fields": ("effective_from", "effective_to")}),
        ("Audit", {"fields": ("created_by", "created_at", "updated_by", "updated_at")}),
    )


@admin.register(OLPlanType)
class OLPlanTypeAdmin(OLDefaultSetupAdmin):
    list_display = ("code", "name", "plan_category", "is_active", "updated_by", "updated_at")
    list_filter = ("is_active", "plan_category")
    search_fields = ("code", "name", "description", "plan_category")
    ordering = ("name", "code")
    fieldsets = (
        ("Identity", {"fields": ("code", "name", "description", "plan_category", "is_active")}),
        ("Audit", {"fields": ("created_by", "created_at", "updated_by", "updated_at")}),
    )


@admin.register(OLProduct)
class OLProductAdmin(OLDefaultSetupAdmin):
    list_display = ("code", "name", "plan_type", "insurance_class", "currency", "min_entry_age", "max_entry_age", "is_active", "effective_from", "effective_to")
    list_filter = ("is_active", "plan_type", "insurance_class", "currency", "investment_linked", "effective_from", "effective_to")
    search_fields = ("code", "name", "description", "currency", "insurance_class", "plan_type__code", "plan_type__name")
    ordering = ("name", "code")
    autocomplete_fields = ("plan_type",)
    fieldsets = (
        ("Identity", {"fields": ("code", "name", "description", "plan_type", "insurance_class", "currency", "is_active")}),
        ("Eligibility", {"fields": ("min_entry_age", "max_entry_age", "min_term", "max_term", "min_sum_assured", "max_sum_assured", "premium_frequencies")}),
        ("Product behavior", {"fields": ("allow_riders", "allow_loans", "allow_withdrawals", "allow_surrender", "allow_paidup", "allow_bonus", "investment_linked")}),
        ("Effective dates", {"fields": ("effective_from", "effective_to")}),
        ("Audit", {"fields": ("created_by", "created_at", "updated_by", "updated_at")}),
    )


@admin.register(OLPlanTaxConfiguration)
class OLPlanTaxConfigurationAdmin(OLDefaultSetupAdmin):
    list_display = ("code", "name", "product", "plan", "tax_type", "rate_type", "rate_value", "apply_on", "sequence", "is_active", "effective_from", "effective_to")
    list_filter = ("is_active", "tax_type", "tax_basis", "rate_type", "apply_on", "country_or_branch", "effective_from", "effective_to")
    search_fields = ("code", "name", "description", "tax_type", "tax_basis", "apply_on", "country_or_branch", "product__code", "plan__code")
    ordering = ("product", "plan", "sequence", "code")
    autocomplete_fields = ("product", "plan")
    fieldsets = (
        ("Identity", {"fields": ("code", "name", "description", "is_active")}),
        ("Scope", {"fields": ("product", "plan", "country_or_branch")}),
        ("Tax rule", {"fields": ("tax_type", "tax_basis", "rate_type", "rate_value", "apply_on", "sequence")}),
        ("Effective dates", {"fields": ("effective_from", "effective_to")}),
        ("Audit", {"fields": ("created_by", "created_at", "updated_by", "updated_at")}),
    )


@admin.register(OLPlanTargetMarket)
class OLPlanTargetMarketAdmin(OLDefaultSetupAdmin):
    list_display = ("code", "name", "product", "plan", "target_market_type", "min_age", "max_age", "residency_requirement", "is_active")
    list_filter = ("is_active", "target_market_type", "residency_requirement", "effective_from", "effective_to")
    search_fields = ("code", "name", "description", "target_market_type", "residency_requirement", "product__code", "plan__code")
    ordering = ("product", "plan", "target_market_type", "code")
    autocomplete_fields = ("product", "plan")
    fieldsets = (
        ("Identity", {"fields": ("code", "name", "description", "is_active")}),
        ("Scope", {"fields": ("product", "plan")}),
        ("Eligibility", {"fields": ("target_market_type", "min_age", "max_age", "occupation_categories", "residency_requirement")}),
        ("Effective dates", {"fields": ("effective_from", "effective_to")}),
        ("Audit", {"fields": ("created_by", "created_at", "updated_by", "updated_at")}),
    )


@admin.register(OLPlanRiskCategory)
class OLPlanRiskCategoryAdmin(OLDefaultSetupAdmin):
    list_display = ("code", "name", "product", "plan", "underwriting_class", "loading_basis", "is_active", "effective_from", "effective_to")
    list_filter = ("is_active", "underwriting_class", "loading_basis", "effective_from", "effective_to")
    search_fields = ("code", "name", "description", "underwriting_class", "loading_basis", "product__code", "plan__code")
    ordering = ("product", "plan", "underwriting_class", "code")
    autocomplete_fields = ("product", "plan")
    fieldsets = (
        ("Identity", {"fields": ("code", "name", "description", "is_active")}),
        ("Scope and underwriting", {"fields": ("product", "plan", "underwriting_class", "loading_basis")}),
        ("Effective dates", {"fields": ("effective_from", "effective_to")}),
        ("Audit", {"fields": ("created_by", "created_at", "updated_by", "updated_at")}),
    )


@admin.register(OLPlanOccupationRiskLimit)
class OLPlanOccupationRiskLimitAdmin(OLDefaultSetupAdmin):
    list_display = ("code", "name", "product", "plan", "occupation_risk_category", "max_sum_assured", "loading_rate", "exclusion_flag", "is_active", "effective_from", "effective_to")
    list_filter = ("is_active", "occupation_risk_category", "exclusion_flag", "effective_from", "effective_to")
    search_fields = ("code", "name", "description", "occupation_risk_category", "product__code", "plan__code")
    ordering = ("product", "plan", "occupation_risk_category", "code")
    autocomplete_fields = ("product", "plan")
    fieldsets = (
        ("Identity", {"fields": ("code", "name", "description", "is_active")}),
        ("Scope and limit", {"fields": ("product", "plan", "occupation_risk_category", "max_sum_assured", "loading_rate", "exclusion_flag")}),
        ("Effective dates", {"fields": ("effective_from", "effective_to")}),
        ("Audit", {"fields": ("created_by", "created_at", "updated_by", "updated_at")}),
    )


@admin.register(OLInvestmentFundType)
class OLInvestmentFundTypeAdmin(OLDefaultSetupAdmin):
    list_display = ("code", "name", "risk_profile", "is_active", "updated_by", "updated_at")
    list_filter = ("is_active", "risk_profile")
    search_fields = ("code", "name", "description", "risk_profile")
    ordering = ("name", "code")
    fieldsets = (
        ("Identity", {"fields": ("code", "name", "description", "risk_profile", "is_active")}),
        ("Audit", {"fields": ("created_by", "created_at", "updated_by", "updated_at")}),
    )


@admin.register(OLInvestmentFund)
class OLInvestmentFundAdmin(OLDefaultSetupAdmin):
    list_display = ("code", "name", "fund_type", "currency", "valuation_frequency", "unit_price", "is_active", "effective_from", "effective_to")
    list_filter = ("is_active", "fund_type", "currency", "valuation_frequency", "effective_from", "effective_to")
    search_fields = ("code", "name", "description", "currency", "valuation_frequency", "fund_type__code", "fund_type__name")
    ordering = ("name", "code")
    autocomplete_fields = ("fund_type",)
    fieldsets = (
        ("Identity", {"fields": ("code", "name", "description", "fund_type", "currency", "is_active")}),
        ("Valuation", {"fields": ("valuation_frequency", "unit_price", "allocation_rules")}),
        ("Effective dates", {"fields": ("effective_from", "effective_to")}),
        ("Audit", {"fields": ("created_by", "created_at", "updated_by", "updated_at")}),
    )


@admin.register(OLReinstatementWindow)
class OLReinstatementWindowAdmin(OLDefaultSetupAdmin):
    list_display = ("code", "name", "product", "plan", "days_after_lapse", "maximum_reinstatements", "require_medical_underwriting", "is_active", "updated_at")
    list_filter = ("is_active", "require_medical_underwriting", "require_outstanding_premium_payment", "effective_from", "effective_to")
    search_fields = ("code", "name", "description", "product__code", "plan__code")
    ordering = ("product", "plan", "-effective_from", "code")
    autocomplete_fields = ("product", "plan")
    fieldsets = (
        ("Identity", {"fields": ("code", "name", "description", "is_active")}),
        ("Scope", {"fields": ("product", "plan")}),
        ("Window and requirements", {"fields": ("days_after_lapse", "maximum_reinstatements", "require_medical_underwriting", "require_outstanding_premium_payment", "interest_rate", "penalty_rate")}),
        ("Effective dates", {"fields": ("effective_from", "effective_to")}),
        ("Audit", {"fields": ("created_by", "created_at", "updated_by", "updated_at")}),
    )
