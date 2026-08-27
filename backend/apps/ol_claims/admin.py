from django.contrib import admin

from .models import (
    OLClaim,
    OLClaimDocument,
    OLClaimFileNote,
    OLClaimItem,
    OLClaimRequisition,
    OLClaimant,
)
from .permissions import has_ol_claim_permission


class ClaimChildInline(admin.TabularInline):
    extra = 0
    readonly_fields = ("id", "created_at", "updated_at", "created_by", "updated_by")


class ClaimantInline(ClaimChildInline):
    model = OLClaimant
    fields = ("claimant_type", "relationship", "name", "identity_number", "age", "gender", "is_active")


class ClaimItemInline(ClaimChildInline):
    model = OLClaimItem
    fields = ("benefit_type", "sum_assured", "calculated_amount", "approved_amount", "adjustment_reason")


class ClaimDocumentInline(ClaimChildInline):
    model = OLClaimDocument
    fields = ("document_type", "file_reference", "mandatory_flag", "uploaded_by", "upload_date")


class ClaimNoteInline(ClaimChildInline):
    model = OLClaimFileNote
    fields = ("note_text",)


@admin.register(OLClaim)
class OLClaimAdmin(admin.ModelAdmin):
    list_display = (
        "claim_number",
        "policy_number",
        "claim_type",
        "claim_date",
        "status",
        "fraud_flag",
        "amount_display",
        "created_at",
    )
    list_filter = ("status", "claim_type", "fraud_flag", "claim_date", "source_channel")
    search_fields = (
        "claim_number",
        "policy_ref__policy_number",
        "policy_ref__partner__legal_name",
        "policy_ref__partner__partner_number",
        "cause_of_claim",
        "description",
    )
    readonly_fields = (
        "id",
        "claim_number",
        "registered_by",
        "admitted_by",
        "created_at",
        "updated_at",
    )
    fieldsets = (
        ("Claim identity", {"fields": ("id", "claim_number", "policy_ref", "claim_type", "status")}),
        ("Claim event", {"fields": ("claim_date", "admitted_date", "settled_date", "cause_of_claim", "description")}),
        ("Assessment and controls", {"fields": ("assessment_notes", "fraud_flag", "source_channel")}),
        ("Audit", {"fields": ("registered_by", "admitted_by", "created_by", "created_at", "updated_by", "updated_at")}),
    )
    inlines = (ClaimantInline, ClaimItemInline, ClaimDocumentInline, ClaimNoteInline)

    @admin.display(description="Policy")
    def policy_number(self, obj):
        return obj.policy_ref.policy_number

    @admin.display(description="Claim amount")
    def amount_display(self, obj):
        return sum(
            (item.approved_amount or item.calculated_amount for item in obj.items.all()),
            0,
        )

    def has_module_permission(self, request):
        return has_ol_claim_permission(request.user, "view")

    def has_view_permission(self, request, obj=None):
        return has_ol_claim_permission(request.user, "view")

    def has_add_permission(self, request):
        return has_ol_claim_permission(request.user, "register")

    def has_change_permission(self, request, obj=None):
        return has_ol_claim_permission(request.user, "assess")

    def has_delete_permission(self, request, obj=None):
        return has_ol_claim_permission(request.user, "cancel")


@admin.register(OLClaimant)
class OLClaimantAdmin(admin.ModelAdmin):
    list_display = ("name", "claim", "claimant_type", "relationship", "identity_number", "age", "gender", "is_active")
    list_filter = ("claimant_type", "gender", "is_active")
    search_fields = ("name", "identity_number", "claim__claim_number", "claim__policy_ref__policy_number")
    readonly_fields = ("id", "created_at", "updated_at", "created_by", "updated_by")

    def has_module_permission(self, request):
        return has_ol_claim_permission(request.user, "view")

    def has_view_permission(self, request, obj=None):
        return has_ol_claim_permission(request.user, "view")

    def has_add_permission(self, request):
        return has_ol_claim_permission(request.user, "register")

    def has_change_permission(self, request, obj=None):
        return has_ol_claim_permission(request.user, "assess")


@admin.register(OLClaimItem)
class OLClaimItemAdmin(admin.ModelAdmin):
    list_display = ("claim", "benefit_type", "sum_assured", "calculated_amount", "approved_amount")
    list_filter = ("benefit_type",)
    search_fields = ("claim__claim_number", "claim__policy_ref__policy_number", "benefit_type")
    readonly_fields = ("id", "created_at", "updated_at", "created_by", "updated_by")

    def has_module_permission(self, request):
        return has_ol_claim_permission(request.user, "view")

    def has_view_permission(self, request, obj=None):
        return has_ol_claim_permission(request.user, "view")

    def has_add_permission(self, request):
        return has_ol_claim_permission(request.user, "assess")

    def has_change_permission(self, request, obj=None):
        return has_ol_claim_permission(request.user, "assess")


@admin.register(OLClaimDocument)
class OLClaimDocumentAdmin(admin.ModelAdmin):
    list_display = ("claim", "document_type", "mandatory_flag", "uploaded_by", "upload_date")
    list_filter = ("document_type", "mandatory_flag", "upload_date")
    search_fields = ("claim__claim_number", "claim__policy_ref__policy_number", "document_type", "file_reference")
    readonly_fields = ("id", "created_at", "updated_at", "created_by", "updated_by")

    def has_module_permission(self, request):
        return has_ol_claim_permission(request.user, "view")

    def has_view_permission(self, request, obj=None):
        return has_ol_claim_permission(request.user, "view")

    def has_add_permission(self, request):
        return has_ol_claim_permission(request.user, "register")

    def has_change_permission(self, request, obj=None):
        return has_ol_claim_permission(request.user, "register")


@admin.register(OLClaimFileNote)
class OLClaimFileNoteAdmin(admin.ModelAdmin):
    list_display = ("claim", "note_preview", "created_by", "created_at")
    search_fields = ("claim__claim_number", "claim__policy_ref__policy_number", "note_text")
    readonly_fields = ("id", "created_at", "updated_at", "created_by", "updated_by")

    @admin.display(description="Note")
    def note_preview(self, obj):
        return obj.note_text[:100]

    def has_module_permission(self, request):
        return has_ol_claim_permission(request.user, "view")

    def has_view_permission(self, request, obj=None):
        return has_ol_claim_permission(request.user, "view")

    def has_add_permission(self, request):
        return has_ol_claim_permission(request.user, "assess")


@admin.register(OLClaimRequisition)
class OLClaimRequisitionAdmin(admin.ModelAdmin):
    list_display = ("requisition_number", "claim", "amount", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("requisition_number", "claim__claim_number", "claim__policy_ref__policy_number")
    readonly_fields = ("id", "requisition_number", "created_at", "updated_at", "created_by", "updated_by")

    def has_module_permission(self, request):
        return has_ol_claim_permission(request.user, "view")

    def has_view_permission(self, request, obj=None):
        return has_ol_claim_permission(request.user, "view")

    def has_add_permission(self, request):
        return has_ol_claim_permission(request.user, "requisition")

    def has_change_permission(self, request, obj=None):
        return has_ol_claim_permission(request.user, "requisition")
