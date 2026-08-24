from django.contrib import admin

from apps.front_office.receipts.config_models import (
    CompanyBankAccount,
    ReceiptNumberingRule,
    ReceiptPaymentModeRule,
)
from apps.front_office.receipts.models import (
    Receipt,
    ReceiptAllocation,
    ReceiptDocument,
    ReceiptReversal,
    ReceiptStatusHistory,
)


class ReceiptAllocationInline(admin.TabularInline):
    model = ReceiptAllocation
    extra = 0
    fk_name = "receipt"
    readonly_fields = ("id", "allocated_at", "allocated_by", "created_at", "updated_at", "created_by", "updated_by")


class ReceiptReversalInline(admin.TabularInline):
    model = ReceiptReversal
    extra = 0
    fk_name = "receipt"
    readonly_fields = ("id", "reversed_at", "reversed_by", "created_at", "updated_at", "created_by", "updated_by")


class ReceiptDocumentInline(admin.TabularInline):
    model = ReceiptDocument
    extra = 0
    fk_name = "receipt"
    readonly_fields = ("id", "uploaded_at", "uploaded_by", "created_at", "updated_at", "created_by", "updated_by")


class ReceiptStatusHistoryInline(admin.TabularInline):
    model = ReceiptStatusHistory
    extra = 0
    fk_name = "receipt"
    readonly_fields = ("id", "changed_at", "changed_by", "created_at", "updated_at", "created_by", "updated_by")


@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = (
        "receipt_number",
        "receipt_date",
        "branch_name_snapshot",
        "partner_name_snapshot",
        "payer_name",
        "source_module",
        "source_reference_id",
        "currency",
        "receipt_amount",
        "allocated_amount",
        "unallocated_amount",
        "payment_mode",
        "payment_reference",
        "status",
        "source_channel",
        "created_by",
        "created_at",
    )
    list_filter = ("status", "source_module", "currency", "payment_mode", "source_channel", "receipt_date", "created_at")
    search_fields = (
        "receipt_number",
        "payer_name",
        "partner_name_snapshot",
        "payment_reference",
        "source_reference_id",
    )
    ordering = ("-receipt_date", "-created_at")
    date_hierarchy = "receipt_date"
    readonly_fields = (
        "id",
        "allocated_amount",
        "unallocated_amount",
        "posted_at",
        "posted_by",
        "reversed_at",
        "reversed_by",
        "created_by",
        "updated_by",
        "created_at",
        "updated_at",
    )
    fieldsets = (
        (
            "Identity",
            {
                "fields": (
                    "receipt_number",
                    "idempotency_key",
                    "receipt_date",
                    "source_channel",
                )
            },
        ),
        (
            "Branch / Payer",
            {
                "fields": (
                    "branch",
                    "branch_name_snapshot",
                    "partner",
                    "partner_name_snapshot",
                    "payer_name",
                    "payer_identity",
                )
            },
        ),
        (
            "Source",
            {"fields": ("source_module", "source_reference_type", "source_reference_id")},
        ),
        (
            "Money",
            {
                "fields": (
                    "currency",
                    "exchange_rate",
                    "receipt_amount",
                    "allocated_amount",
                    "unallocated_amount",
                )
            },
        ),
        (
            "Payment",
            {
                "fields": (
                    "payment_mode",
                    "payment_reference",
                    "bank_account",
                    "bank_account_snapshot",
                    "narration",
                )
            },
        ),
        ("Lifecycle", {"fields": ("status", "cancellation_reason", "posted_at", "posted_by", "reversed_at", "reversed_by")}),
        ("Provenance", {"fields": ("created_by", "updated_by", "created_at", "updated_at")}),
    )
    inlines = (ReceiptAllocationInline, ReceiptReversalInline, ReceiptDocumentInline, ReceiptStatusHistoryInline)


@admin.register(ReceiptAllocation)
class ReceiptAllocationAdmin(admin.ModelAdmin):
    list_display = (
        "receipt",
        "target_type",
        "target_id",
        "target_display",
        "amount",
        "currency",
        "exchange_rate",
        "allocation_status",
        "reversal_of",
        "allocated_by",
        "allocated_at",
        "source_channel",
    )
    list_filter = ("target_type", "allocation_status", "currency", "source_channel", "allocated_at")
    search_fields = ("receipt__receipt_number", "target_id", "target_display", "narration")
    ordering = ("-allocated_at",)
    readonly_fields = ("id", "allocated_at", "created_at", "updated_at", "created_by", "updated_by")


@admin.register(ReceiptReversal)
class ReceiptReversalAdmin(admin.ModelAdmin):
    list_display = ("reversal_number", "receipt", "reason", "reversed_by", "reversed_at")
    list_filter = ("reversed_at",)
    search_fields = ("reversal_number", "receipt__receipt_number", "reason")
    ordering = ("-reversed_at",)
    readonly_fields = ("id", "reversed_at", "created_at", "updated_at", "created_by", "updated_by")


@admin.register(ReceiptDocument)
class ReceiptDocumentAdmin(admin.ModelAdmin):
    list_display = ("receipt", "document_type", "document_number", "filename", "mime_type", "status", "uploaded_by", "uploaded_at")
    list_filter = ("document_type", "status", "uploaded_at")
    search_fields = ("receipt__receipt_number", "document_number", "filename")
    ordering = ("-uploaded_at",)
    readonly_fields = ("id", "uploaded_at", "created_at", "updated_at", "created_by", "updated_by")


@admin.register(ReceiptStatusHistory)
class ReceiptStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ("receipt", "from_status", "to_status", "reason", "changed_by", "changed_at", "source_channel")
    list_filter = ("from_status", "to_status", "source_channel", "changed_at")
    search_fields = ("receipt__receipt_number", "reason")
    ordering = ("-changed_at",)
    readonly_fields = ("id", "changed_at", "created_at", "updated_at", "created_by", "updated_by")


@admin.register(ReceiptNumberingRule)
class ReceiptNumberingRuleAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "branch",
        "prefix",
        "sequence_padding",
        "next_sequence",
        "reset_frequency",
        "effective_from",
        "effective_to",
        "is_active",
    )
    list_filter = ("is_active", "reset_frequency", "branch")
    search_fields = ("code", "name", "prefix")
    ordering = ("code",)
    readonly_fields = ("id", "created_at", "updated_at", "created_by", "updated_by")


@admin.register(CompanyBankAccount)
class CompanyBankAccountAdmin(admin.ModelAdmin):
    list_display = ("code", "bank_name", "account_name", "currency", "branch", "is_default", "is_active")
    list_filter = ("is_active", "is_default", "currency", "branch")
    search_fields = ("code", "bank_name", "account_name", "account_number")
    ordering = ("code",)
    readonly_fields = ("id", "masked_account_number", "created_at", "updated_at", "created_by", "updated_by")


@admin.register(ReceiptPaymentModeRule)
class ReceiptPaymentModeRuleAdmin(admin.ModelAdmin):
    list_display = (
        "payment_mode",
        "requires_reference",
        "requires_bank_account",
        "min_amount",
        "max_amount",
        "is_active",
    )
    list_filter = ("is_active", "requires_reference", "requires_bank_account", "allows_cash", "allows_bank_transfer")
    search_fields = ("payment_mode",)
    ordering = ("payment_mode",)
    readonly_fields = ("id", "created_at", "updated_at", "created_by", "updated_by")
