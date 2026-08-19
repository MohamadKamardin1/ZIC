from django.contrib import admin

from .models import OLProposal


@admin.register(OLProposal)
class OLProposalAdmin(admin.ModelAdmin):
    list_display = (
        "proposal_number",
        "quotation",
        "quotation_version",
        "status",
        "created_by",
        "created_at",
    )
    list_filter = ("status", "created_at")
    search_fields = (
        "proposal_number",
        "quotation__quote_number",
        "quotation__quote_name",
    )
    ordering = ("-created_at",)
    readonly_fields = (
        "id",
        "quotation",
        "quotation_version",
        "proposal_number",
        "status",
        "prospect_snapshot",
        "plans_snapshot",
        "financial_summary_snapshot",
        "created_by",
        "created_at",
        "updated_at",
    )
