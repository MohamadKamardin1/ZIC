from django.contrib import admin

from .models import OLLoan, OLLoanInterestAccrual, OLLoanOffset, OLLoanRepayment, OLLoanSchedule
from .permissions import has_ol_loan_permission


class LoanChildReadOnlyAdmin(admin.ModelAdmin):
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by")

    def has_module_permission(self, request):
        return has_ol_loan_permission(request.user, "view")

    def has_view_permission(self, request, obj=None):
        return has_ol_loan_permission(request.user, "view")

    def has_add_permission(self, request):
        return has_ol_loan_permission(request.user, "configure")

    def has_change_permission(self, request, obj=None):
        return has_ol_loan_permission(request.user, "configure")

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(OLLoan)
class OLLoanAdmin(admin.ModelAdmin):
    list_display = (
        "loan_number",
        "policy_display",
        "partner_display",
        "currency",
        "principal_amount",
        "outstanding_balance",
        "status",
        "approval_required",
        "created_at",
    )
    list_filter = ("status", "currency", "approval_required", "compounding_frequency")
    search_fields = ("loan_number", "policy_ref__policy_number", "partner__legal_name", "partner__partner_number")
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by")
    list_select_related = ("policy_ref", "partner")
    ordering = ("-created_at", "loan_number")

    fieldsets = (
        ("Identity", {"fields": ("loan_number", "policy_ref", "partner", "currency")}),
        ("Financial terms", {"fields": ("principal_amount", "disbursed_amount", "interest_rate", "compounding_frequency", "term_months")}),
        ("Lifecycle", {"fields": ("disbursement_date", "maturity_date", "status", "approval_required", "reason")}),
        ("Balances", {"fields": ("total_repaid", "outstanding_balance")}),
        ("Traceability", {"fields": ("source_channel", "idempotency_key", "created_by", "created_at", "updated_by", "updated_at")}),
    )

    @admin.display(description="Policy")
    def policy_display(self, obj):
        return getattr(obj.policy_ref, "policy_number", "") or str(obj.policy_ref_id)

    @admin.display(description="Partner")
    def partner_display(self, obj):
        return getattr(obj.partner, "legal_name", "") or getattr(obj.partner, "partner_number", "")

    def has_module_permission(self, request):
        return has_ol_loan_permission(request.user, "view")

    def has_view_permission(self, request, obj=None):
        return has_ol_loan_permission(request.user, "view")

    def has_add_permission(self, request):
        return has_ol_loan_permission(request.user, "request")

    def has_change_permission(self, request, obj=None):
        return has_ol_loan_permission(request.user, "configure")

    def has_delete_permission(self, request, obj=None):
        return has_ol_loan_permission(request.user, "reverse")


@admin.register(OLLoanSchedule)
class OLLoanScheduleAdmin(LoanChildReadOnlyAdmin):
    list_display = ("loan", "installment_number", "due_date", "principal_due", "interest_due", "penalty_due", "amount_paid", "balance", "status")
    list_filter = ("status",)
    search_fields = ("loan__loan_number", "loan__policy_ref__policy_number")
    list_select_related = ("loan",)


@admin.register(OLLoanRepayment)
class OLLoanRepaymentAdmin(LoanChildReadOnlyAdmin):
    list_display = ("loan", "receipt_ref", "amount", "currency", "exchange_rate", "reason", "created_at")
    search_fields = ("loan__loan_number", "receipt_ref", "reason")
    list_select_related = ("loan",)


@admin.register(OLLoanInterestAccrual)
class OLLoanInterestAccrualAdmin(LoanChildReadOnlyAdmin):
    list_display = ("loan", "period_start", "period_end", "principal_base", "interest_amount", "penalty_amount", "cumulative_interest")
    list_filter = ("period_start", "period_end")
    search_fields = ("loan__loan_number",)
    list_select_related = ("loan",)


@admin.register(OLLoanOffset)
class OLLoanOffsetAdmin(LoanChildReadOnlyAdmin):
    list_display = ("loan", "source_type", "source_id", "offset_amount", "remaining_payout", "created_at")
    list_filter = ("source_type",)
    search_fields = ("loan__loan_number", "source_id", "reason")
    list_select_related = ("loan",)
