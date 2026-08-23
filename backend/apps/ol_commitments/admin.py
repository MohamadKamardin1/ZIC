from django.contrib import admin

from .models import OLCommitment, OLCommitmentAllocation, OLCommitmentNotificationLog


class OLCommitmentAllocationInline(admin.TabularInline):
    model = OLCommitmentAllocation
    extra = 0
    fk_name = "commitment"
    readonly_fields = (
        "id",
        "allocated_at",
        "allocated_by",
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
    )


@admin.register(OLCommitment)
class OLCommitmentAdmin(admin.ModelAdmin):
    list_display = (
        "commitment_number",
        "source_type",
        "source_reference",
        "partner_name_snapshot",
        "product_name_snapshot",
        "plan_name_snapshot",
        "installment_number",
        "due_date",
        "premium_amount",
        "amount_paid",
        "amount_waived",
        "balance",
        "currency",
        "status",
        "grace_date",
        "lapse_date",
        "approval_required",
        "source_channel",
        "created_by",
        "created_at",
    )
    list_filter = ("status", "source_type", "currency", "approval_required", "source_channel", "due_date", "created_at")
    search_fields = (
        "commitment_number",
        "source_reference",
        "partner_name_snapshot",
        "product_name_snapshot",
        "plan_name_snapshot",
    )
    ordering = ("-due_date", "-created_at")
    date_hierarchy = "due_date"
    readonly_fields = (
        "id",
        "commitment_number",
        "idempotency_key",
        "balance",
        "grace_date",
        "warning_date",
        "pre_lapse_date",
        "lapse_date",
        "source_content_type",
        "source_object_id",
        "source_reference",
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
                    "commitment_number",
                    "idempotency_key",
                    "source_type",
                    "source_content_type",
                    "source_object_id",
                    "source_reference",
                )
            },
        ),
        (
            "Display",
            {
                "fields": (
                    "partner",
                    "partner_name_snapshot",
                    "product",
                    "product_name_snapshot",
                    "plan",
                    "plan_name_snapshot",
                )
            },
        ),
        (
            "Schedule",
            {
                "fields": (
                    "currency",
                    "installment_number",
                    "installment_count",
                    "due_date",
                    "premium_amount",
                    "amount_paid",
                    "amount_waived",
                    "balance",
                )
            },
        ),
        (
            "Lifecycle",
            {"fields": ("status", "grace_date", "warning_date", "pre_lapse_date", "lapse_date", "approval_required")},
        ),
        ("Reason", {"fields": ("reason_code", "reason_text")}),
        ("Provenance", {"fields": ("source_channel", "created_by", "updated_by", "created_at", "updated_at")}),
    )
    inlines = (OLCommitmentAllocationInline,)


@admin.register(OLCommitmentAllocation)
class OLCommitmentAllocationAdmin(admin.ModelAdmin):
    list_display = (
        "receipt_reference",
        "commitment",
        "amount",
        "payment_mode",
        "currency",
        "exchange_rate",
        "reversal_of",
        "reason",
        "allocated_by",
        "allocated_at",
        "source_channel",
    )
    list_filter = ("currency", "payment_mode", "source_channel", "allocated_at")
    search_fields = ("receipt_reference", "commitment__commitment_number", "reason")
    ordering = ("-allocated_at",)
    readonly_fields = (
        "id",
        "allocated_at",
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
    )


@admin.register(OLCommitmentNotificationLog)
class OLCommitmentNotificationLogAdmin(admin.ModelAdmin):
    list_display = (
        "commitment",
        "event_type",
        "dispatch_on",
        "notification_channel",
        "recipient_type",
        "recipient_identifier",
        "template_code",
        "status",
        "dispatched_at",
        "source_channel",
    )
    list_filter = ("event_type", "notification_channel", "recipient_type", "status", "dispatch_on")
    search_fields = ("commitment__commitment_number", "recipient_identifier", "template_code")
    ordering = ("-dispatch_on",)
    readonly_fields = ("id", "created_at", "updated_at", "created_by", "updated_by")
