from django.contrib import admin

from .models import Policy, PolicyAuditLog, PolicyBenefit, PolicyEndorsement, PolicyMember, PolicyRider
from .permissions import has_ol_policy_permission


class PolicyMemberInline(admin.TabularInline):
    model = PolicyMember
    extra = 0
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by")


class PolicyRiderInline(admin.TabularInline):
    model = PolicyRider
    extra = 0
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by")


class PolicyBenefitInline(admin.TabularInline):
    model = PolicyBenefit
    extra = 0
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by")


@admin.register(Policy)
class PolicyAdmin(admin.ModelAdmin):
    list_display = (
        "policy_number",
        "policyholder_name",
        "product_plan_ref",
        "status",
        "currency",
        "sum_assured",
        "premium_amount",
        "risk_commencement_date",
        "maturity_date",
    )
    list_filter = ("status", "currency", "premium_frequency", "risk_commencement_date")
    search_fields = (
        "policy_number",
        "product_plan_ref",
        "partner__partner_number",
        "partner__legal_name",
        "partner__identification_number",
        "agent__partner_number",
        "agent__legal_name",
    )
    readonly_fields = ("policy_number", "version", "created_at", "updated_at", "created_by", "updated_by")
    fieldsets = (
        ("Contract identity", {"fields": ("policy_number", "proposal_ref", "version", "status")}),
        ("Parties and product", {"fields": ("partner", "agent", "product_plan_ref", "currency")}),
        ("Financial terms", {"fields": ("sum_assured", "premium_amount", "premium_frequency", "term_years")}),
        ("Dates and traceability", {"fields": ("risk_commencement_date", "maturity_date", "first_premium_receipt_ref", "contract_snapshot")}),
        ("Audit", {"fields": ("created_by", "created_at", "updated_by", "updated_at")}),
    )
    inlines = (PolicyMemberInline, PolicyRiderInline, PolicyBenefitInline)

    @admin.display(description="Policyholder")
    def policyholder_name(self, obj):
        return obj.partner.legal_name or obj.partner.partner_number

    def has_module_permission(self, request):
        return has_ol_policy_permission(request.user, "view")

    def has_view_permission(self, request, obj=None):
        return has_ol_policy_permission(request.user, "view")

    def has_add_permission(self, request):
        return has_ol_policy_permission(request.user, "create")

    def has_change_permission(self, request, obj=None):
        return has_ol_policy_permission(request.user, "service")

    def has_delete_permission(self, request, obj=None):
        return has_ol_policy_permission(request.user, "cancel")


@admin.register(PolicyMember)
class PolicyMemberAdmin(admin.ModelAdmin):
    list_display = ("name", "policy", "member_relation", "dob", "gender", "benefit_amount")
    search_fields = ("name", "policy__policy_number", "member_relation")
    list_filter = ("gender", "member_relation")
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by")

    def has_module_permission(self, request):
        return has_ol_policy_permission(request.user, "view")

    def has_view_permission(self, request, obj=None):
        return has_ol_policy_permission(request.user, "view")


@admin.register(PolicyRider)
class PolicyRiderAdmin(admin.ModelAdmin):
    list_display = ("rider_code", "policy", "sum_assured", "amount", "premium")
    search_fields = ("rider_code", "policy__policy_number")
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by")

    def has_module_permission(self, request):
        return has_ol_policy_permission(request.user, "view")

    def has_view_permission(self, request, obj=None):
        return has_ol_policy_permission(request.user, "view")


@admin.register(PolicyBenefit)
class PolicyBenefitAdmin(admin.ModelAdmin):
    list_display = ("benefit_type", "policy", "calculation_basis", "amount")
    search_fields = ("benefit_type", "policy__policy_number")
    list_filter = ("calculation_basis",)
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by")

    def has_module_permission(self, request):
        return has_ol_policy_permission(request.user, "view")

    def has_view_permission(self, request, obj=None):
        return has_ol_policy_permission(request.user, "view")


@admin.register(PolicyEndorsement)
class PolicyEndorsementAdmin(admin.ModelAdmin):
    list_display = ("endorsement_number", "policy", "endorsement_type", "effective_date", "status", "created_at")
    search_fields = ("endorsement_number", "policy__policy_number", "description")
    list_filter = ("endorsement_type", "status")
    readonly_fields = ("endorsement_number", "created_at", "updated_at", "created_by", "updated_by")

    def has_module_permission(self, request):
        return has_ol_policy_permission(request.user, "view")

    def has_view_permission(self, request, obj=None):
        return has_ol_policy_permission(request.user, "view")

    def has_add_permission(self, request):
        return has_ol_policy_permission(request.user, "endorse")

    def has_change_permission(self, request, obj=None):
        return has_ol_policy_permission(request.user, "endorse")


@admin.register(PolicyAuditLog)
class PolicyAuditLogAdmin(admin.ModelAdmin):
    list_display = ("policy", "event_type", "from_status", "to_status", "source_channel", "actor", "created_at")
    list_filter = ("event_type", "source_channel", "from_status", "to_status")
    search_fields = ("policy__policy_number", "event_type", "reason", "correlation_id")
    readonly_fields = (
        "policy",
        "actor",
        "event_type",
        "from_status",
        "to_status",
        "before_snapshot",
        "after_snapshot",
        "reason",
        "source_channel",
        "correlation_id",
        "created_at",
        "updated_at",
    )

    def has_module_permission(self, request):
        return has_ol_policy_permission(request.user, "view")

    def has_view_permission(self, request, obj=None):
        return has_ol_policy_permission(request.user, "view")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
