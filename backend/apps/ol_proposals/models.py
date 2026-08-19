import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class ProposalStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    ACTIVE = "ACTIVE", "Active"
    CONVERTED = "CONVERTED", "Converted"
    CANCELLED = "CANCELLED", "Cancelled"


class OLProposal(models.Model):
    """Minimal proposal handoff aggregate created from a finalized OL quotation."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    quotation = models.ForeignKey(
        "ol_quotations.OLQuotation",
        on_delete=models.PROTECT,
        related_name="proposals",
    )
    quotation_version = models.ForeignKey(
        "ol_quotations.OLQuotationVersion",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="proposals",
    )
    proposal_number = models.CharField(max_length=50, unique=True, db_index=True)
    status = models.CharField(
        max_length=20,
        choices=ProposalStatus.choices,
        default=ProposalStatus.DRAFT,
        db_index=True,
    )
    prospect_snapshot = models.JSONField(default=dict, blank=True)
    plans_snapshot = models.JSONField(default=list, blank=True)
    financial_summary_snapshot = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_ol_proposals",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ol_quotation_proposal"
        verbose_name = "OL Proposal"
        verbose_name_plural = "OL Proposals"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["quotation", "status"]),
            models.Index(fields=["quotation_version"]),
            models.Index(fields=["status", "created_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["quotation", "quotation_version"],
                name="ol_proposal_quotation_version_unique",
            ),
        ]

    def clean(self):
        errors = {}
        if self.quotation_version_id and self.quotation_id:
            version_quotation_id = getattr(self.quotation_version, "quotation_id", None)
            if version_quotation_id and version_quotation_id != self.quotation_id:
                errors["quotation_version"] = "Proposal version must belong to the proposal quotation."
        if not isinstance(self.prospect_snapshot, dict):
            errors["prospect_snapshot"] = "Prospect snapshot must be a JSON object."
        if not isinstance(self.plans_snapshot, list):
            errors["plans_snapshot"] = "Plans snapshot must be a JSON array."
        if not isinstance(self.financial_summary_snapshot, dict):
            errors["financial_summary_snapshot"] = "Financial summary snapshot must be a JSON object."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return self.proposal_number
