from django.contrib import admin
from django.db.models import Sum

from .models import (
    InstallmentItemStatus,
    OLInstallmentItem,
    OLMaturityInstallmentConfig,
    OLMaturityInstallmentPlan,
)
from .permissions import has_ol_maturity_installment_permission


class InstallmentChildInline(admin.TabularInline):
    extra = 0
    readonly_fields = ("id", "created_at", "updated_at", "created_by", "updated_by")


class InstallmentItemInline(InstallmentChildInline):
    model = OLInstallmentItem
    fields = (
        "installment_number",
        "due_date",
        "amount",
        "status",
        "payment_requisition_ref",
        "payment_reference",
        "paid_date",
        "missed_date",
        "waived_date",
        "paid_by",
        "narration",
    )


@admin.register(OLMaturityInstallmentPlan)
class OLMaturityInstallmentPlanAdmin(admin.ModelAdmin):
    list_display = (
        "plan_number",
        "policy_number",
        "policyholder",
        "currency",
        "total_payable_amount",
        "paid_amount",
        "balance",
        "installment_count",
        "frequency",
        "start_date",
        "end_date",
        "status",
        "created_at",
    )
    list_filter = ("status", "frequency", "currency", "start_date", "source_channel")
    search_fields = (
        "plan_number",
        "policy_ref__policy_number",
        "maturity_claim_ref__claim_number",
        "partner__legal_name",
        "partner__partner_number",
    )
    readonly_fields = (
        "id",
        "plan_number",
        "activated_at",
        "activated_by",
        "completed_at",
        "completed_by",
        "terminated_at",
        "terminated_by",
        "created_at",
        "updated_at",
    )
    fieldsets = (
        ("Plan identity", {"fields": ("id", "plan_number", "policy_ref", "maturity_claim_ref", "partner", "status")}),
        (
            "Schedule",
            {
                "fields": (
                    "currency",
                    "total_maturity_value",
                    "total_payable_amount",
                    "installment_count",
                    "frequency",
                    "start_date",
                    "end_date",
                )
            },
        ),
        (
            "Lifecycle",
            {
                "fields": (
                    "activated_at",
                    "activated_by",
                    "completed_at",
                    "completed_by",
                    "terminated_at",
                    "terminated_by",
                    "source_channel",
                )
            },
        ),
        ("Parameters snapshot", {"fields": ("parameter_snapshot",)}),
        ("Audit", {"fields": ("created_by", "created_at", "updated_by", "updated_at")}),
    )
    inlines = (InstallmentItemInline,)

    @admin.display(description="Policy")
    def policy_number(self, obj):
        return obj.policy_ref.policy_number

    @admin.display(description="Policyholder")
    def policyholder(self, obj):
        return obj.partner.legal_name or str(obj.partner)

    @admin.display(description="Paid amount")
    def paid_amount(self, obj):
        total = obj.items.filter(status=InstallmentItemStatus.PAID).aggregate(total=Sum("amount"))["total"]
        return f"{total or 0:.2f}"

    @admin.display(description="Balance")
    def balance(self, obj):
        total = obj.items.filter(status=InstallmentItemStatus.PAID).aggregate(total=Sum("amount"))["total"]
        return f"{(obj.total_payable_amount - (total or 0)):.2f}"

    def has_module_permission(self, request):
        return has_ol_maturity_installment_permission(request.user, "view")

    def has_view_permission(self, request, obj=None):
        return has_ol_maturity_installment_permission(request.user, "view")

    def has_add_permission(self, request):
        return has_ol_maturity_installment_permission(request.user, "create")

    def has_change_permission(self, request, obj=None):
        return has_ol_maturity_installment_permission(request.user, "process_payment")

    def has_delete_permission(self, request, obj=None):
        return has_ol_maturity_installment_permission(request.user, "cancel")


@admin.register(OLInstallmentItem)
class OLInstallmentItemAdmin(admin.ModelAdmin):
    list_display = ("plan_ref", "installment_number", "due_date", "amount", "status", "paid_date", "paid_by")
    list_filter = ("status", "due_date")
    search_fields = ("plan_ref__plan_number", "plan_ref__policy_ref__policy_number", "payment_reference")
    readonly_fields = ("id", "created_at", "updated_at", "created_by", "updated_by")

    def has_module_permission(self, request):
        return has_ol_maturity_installment_permission(request.user, "view")

    def has_view_permission(self, request, obj=None):
        return has_ol_maturity_installment_permission(request.user, "view")

    def has_add_permission(self, request):
        return has_ol_maturity_installment_permission(request.user, "create")

    def has_change_permission(self, request, obj=None):
        return has_ol_maturity_installment_permission(request.user, "process_payment")


@admin.register(OLMaturityInstallmentConfig)
class OLMaturityInstallmentConfigAdmin(admin.ModelAdmin):
    list_display = ("plan_ref", "calculation_basis", "configured_by", "configured_at")
    list_filter = ("calculation_basis", "configured_at")
    search_fields = ("plan_ref__plan_number", "plan_ref__policy_ref__policy_number")
    readonly_fields = (
        "id",
        "plan_ref",
        "calculation_basis",
        "installment_rate_snapshot",
        "paid_up_rate_snapshot",
        "installment_charge_snapshot",
        "parameters_used",
        "assumptions",
        "configured_by",
        "configured_at",
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
    )

    def has_module_permission(self, request):
        return has_ol_maturity_installment_permission(request.user, "view")

    def has_view_permission(self, request, obj=None):
        return has_ol_maturity_installment_permission(request.user, "view")

    def has_add_permission(self, request):
        return has_ol_maturity_installment_permission(request.user, "configure")

    def has_change_permission(self, request, obj=None):
        return has_ol_maturity_installment_permission(request.user, "configure")

    def has_delete_permission(self, request, obj=None):
        return False
