import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

# =============================================================================
# Legacy compatible status choices (extended) — authoritative catalog lives in
# ol_parameters.OLProposalStatus; these choices keep old call-sites working.
# =============================================================================


class ProposalStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    ENRICHMENT = "ENRICHMENT", "Enrichment"
    PENDING_UNDERWRITING = "PENDING_UNDERWRITING", "Pending underwriting"
    PAYMENT_READY = "PAYMENT_READY", "Payment ready"
    AWAITING_FIRST_PREMIUM = "AWAITING_FIRST_PREMIUM", "Awaiting first premium"
    CONVERTED = "CONVERTED", "Converted"
    CANCELLED = "CANCELLED", "Cancelled"
    EXPIRED = "EXPIRED", "Expired"


class UnderwritingStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    MEDICAL_REQUIRED = "MEDICAL_REQUIRED", "Medical required"
    UNDER_REVIEW = "UNDER_REVIEW", "Under review"
    CLEARED = "CLEARED", "Cleared"
    DECLINED = "DECLINED", "Declined"


class ProposalDocumentStatus(models.TextChoices):
    REQUESTED = "REQUESTED", "Requested"
    UPLOADED = "UPLOADED", "Uploaded"
    VERIFIED = "VERIFIED", "Verified"
    REJECTED = "REJECTED", "Rejected"
    GENERATED = "GENERATED", "Generated"


class ProposalSourceChannel(models.TextChoices):
    WEB = "WEB", "Web"
    API = "API", "API"
    ADMIN = "ADMIN", "Admin"
    SYSTEM = "SYSTEM", "System"
    IMPORT = "IMPORT", "Import"
    PORTAL = "PORTAL", "Portal"
    BATCH = "BATCH", "Batch"
    QUICK_CREATE = "QUICK_CREATE", "Quick create"


ZERO = "0.00"


class OLProposal(models.Model):
    """The proposal handoff aggregate between a quotation and a policy.

    Extends the legacy minimal handoff model; legacy snapshots are retained for
    compatibility with `ol_quotations.convert_to_proposal`.
    """

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
    status = models.CharField(max_length=40, default="", db_index=True)

    partner = models.ForeignKey(
        "partners.Partner",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="ol_proposals_policyholder",
    )
    partner_name_snapshot = models.CharField(max_length=255, blank=True, default="")
    agent_partner = models.ForeignKey(
        "partners.Partner",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="ol_proposals_agent",
    )
    agent_name_snapshot = models.CharField(max_length=255, blank=True, default="")
    employer_partner = models.ForeignKey(
        "partners.Partner",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="ol_proposals_employer",
    )
    employer_name_snapshot = models.CharField(max_length=255, blank=True, default="")

    currency = models.CharField(max_length=3, default="TZS")
    expiry_date = models.DateField(null=True, blank=True, db_index=True)

    payment_ready = models.BooleanField(default=False, db_index=True)
    payment_ready_at = models.DateTimeField(null=True, blank=True)
    first_premium_commitment = models.ForeignKey(
        "ol_commitments.OLCommitment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="proposal_first_premiums",
        help_text="Linked first-premium commitment (source_type=PROPOSAL, installment 1).",
    )
    underwriting_status = models.CharField(
        max_length=40, choices=UnderwritingStatus.choices, default=UnderwritingStatus.PENDING, db_index=True
    )
    medical_required = models.BooleanField(default=False)
    converted_policy = models.ForeignKey(
        "ordinary_life.OLPolicy",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ol_proposals_converted",
    )

    reason_code = models.CharField(max_length=60, blank=True, default="")
    reason_text = models.TextField(blank=True, default="")

    # --- Enrichment (details not captured at quote stage) ---
    employment_reference = models.CharField(max_length=120, blank=True, default="")
    payroll_deduction = models.BooleanField(default=False)
    intermediary_channel = models.CharField(max_length=40, blank=True, default="")
    declaration_pep_flag = models.BooleanField(null=True, blank=True)
    declaration_aml_flag = models.BooleanField(null=True, blank=True)
    existing_policies_count = models.PositiveIntegerField(null=True, blank=True)
    occupation_risk_note = models.TextField(blank=True, default="")
    declarations_free_text = models.JSONField(default=dict, blank=True)
    bank_name = models.CharField(max_length=160, blank=True, default="")
    bank_account_name = models.CharField(max_length=200, blank=True, default="")
    bank_account_number = models.CharField(max_length=80, blank=True, default="")

    source_channel = models.CharField(
        max_length=30, choices=ProposalSourceChannel.choices, default=ProposalSourceChannel.WEB
    )

    # Legacy snapshots (kept for compatibility).
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
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_ol_proposals",
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
            models.Index(fields=["partner", "status"]),
            models.Index(fields=["payment_ready", "status"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["quotation", "quotation_version"],
                name="ol_proposal_quotation_version_unique",
            ),
        ]

    def _derive_snapshots(self):
        if self.partner_id and not self.partner_name_snapshot:
            self.partner_name_snapshot = str(self.partner)
        if self.agent_partner_id and not self.agent_name_snapshot:
            self.agent_name_snapshot = str(self.agent_partner)
        if self.employer_partner_id and not self.employer_name_snapshot:
            self.employer_name_snapshot = str(self.employer_partner)

    def reconcile_payment_ready(self):
        if self.payment_ready and not self.payment_ready_at:
            self.payment_ready_at = timezone.now()
        elif not self.payment_ready:
            self.payment_ready_at = None

    def save(self, *args, **kwargs):
        from apps.ol_proposals.services.parameter_resolver import default_proposal_status

        if not self.status:
            self.status = default_proposal_status() or ProposalStatus.DRAFT
        self._derive_snapshots()
        self.reconcile_payment_ready()
        return super().save(*args, **kwargs)

    def clean(self):
        from apps.ol_proposals.services.parameter_resolver import is_valid_proposal_status

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

        currency = (self.currency or "").strip().upper()
        if len(currency) != 3 or not currency.isalpha():
            errors["currency"] = "Currency must be a three-letter code."
        self.currency = currency

        status = (self.status or "").strip().upper()
        if status and is_valid_proposal_status(status, allow_empty_catalog=True) is False:
            errors["status"] = (
                f"Status '{status}' is not configured in the OL Proposal Status catalog. "
                "Configure it under OL Parameters > Policy Setup > OL Proposal Statuses."
            )
        self.status = status

        if self.employer_partner_id and self.partner_id and self.employer_partner_id == self.partner_id:
            errors["employer_partner"] = "The employer cannot be the same partner as the policyholder."
        if self.agent_partner_id and self.partner_id and self.agent_partner_id == self.partner_id:
            errors["agent_partner"] = "The intermediary cannot be the same partner as the policyholder."
        if self.agent_partner_id and not (self.intermediary_channel or "").strip():
            errors["intermediary_channel"] = (
                "A commission-relevant channel is required when an intermediary is selected."
            )
        if self.intermediary_channel:
            self.intermediary_channel = self.intermediary_channel.strip().upper()

        if not isinstance(self.declarations_free_text, dict):
            errors["declarations_free_text"] = "Declarations must be a JSON object."

        if self.pk:
            share_error = beneficiary_shares_error(self)
            if share_error:
                errors["beneficiaries"] = share_error

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return self.proposal_number


def beneficiary_shares_error(proposal, members=True):
    from decimal import Decimal

    beneficiaries = list(proposal.beneficiaries.all()) if members else []
    if not beneficiaries:
        return None
    total = sum((Decimal(str(item.share_percent or 0)) for item in beneficiaries), Decimal("0.00"))
    if total != Decimal("100.00"):
        return f"Beneficiary shares must total 100%, got {total:.2f}%."
    return None


class OLProposalPlanConfig(models.Model):
    """Carried product/plan configuration from the source quotation."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    proposal = models.ForeignKey(OLProposal, on_delete=models.CASCADE, related_name="plan_configs")
    product_version = models.ForeignKey(
        "ordinary_life.OLProductVersion",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="proposal_plan_configs",
    )
    plan = models.ForeignKey(
        "ordinary_life.OLPlan",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="proposal_plan_configs",
    )
    plan_name_snapshot = models.CharField(max_length=255, blank=True, default="")
    sub_product_code = models.CharField(max_length=80, blank=True, default="")
    section_number = models.PositiveSmallIntegerField(null=True, blank=True)
    base_sum_assured = models.DecimalField(max_digits=18, decimal_places=2)
    term_years = models.PositiveSmallIntegerField()
    payment_period_years = models.PositiveSmallIntegerField(null=True, blank=True)
    premium_frequency = models.CharField(max_length=40)
    quote_basis = models.CharField(max_length=80, default="SUM_ASSURED")
    estimated_maturity_value = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    premium_factor = models.CharField(max_length=80, default="NONE")
    premium_amount = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    is_selected = models.BooleanField(default=True)

    class Meta:
        db_table = "ol_proposal_plan_config"
        ordering = ["proposal", "-is_selected", "id"]
        indexes = [models.Index(fields=["proposal", "is_selected"])]

    def __str__(self):
        return f"{self.proposal.proposal_number}:{self.plan_name_snapshot or self.plan_id}"

    def clean(self):
        errors = {}
        if self.base_sum_assured is None or self.base_sum_assured <= 0:
            errors["base_sum_assured"] = "Base sum assured must be greater than zero."
        if self.term_years is None or self.term_years <= 0:
            errors["term_years"] = "Term must be greater than zero."
        if self.payment_period_years and self.term_years and self.payment_period_years > self.term_years:
            errors["payment_period_years"] = "Payment period cannot exceed policy term."
        if not (self.premium_frequency or "").strip():
            errors["premium_frequency"] = "Premium frequency is required."
        if errors:
            raise ValidationError(errors)


class OLProposalMember(models.Model):
    """Policyholder / life assured / dependent carried from the quotation."""

    MEMBER_TYPES = (
        ("POLICYHOLDER", "Policyholder"),
        ("LIFE_ASSURED", "Life assured"),
        ("DEPENDENT", "Dependent"),
        ("OTHER", "Other"),
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    proposal = models.ForeignKey(OLProposal, on_delete=models.CASCADE, related_name="members")
    member_type = models.CharField(max_length=30, choices=MEMBER_TYPES)
    partner = models.ForeignKey(
        "partners.Partner", on_delete=models.PROTECT, null=True, blank=True, related_name="ol_proposal_members"
    )
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    full_name_snapshot = models.CharField(max_length=300, blank=True, default="")
    identity_number = models.CharField(max_length=120, blank=True, default="")
    date_of_birth = models.DateField(null=True, blank=True)
    age_at_quote = models.PositiveSmallIntegerField(null=True, blank=True)
    gender = models.CharField(max_length=40, blank=True, default="")
    smoker_status = models.CharField(max_length=40, blank=True, default="")
    relationship = models.CharField(max_length=80, blank=True, default="")
    contact_phone = models.CharField(max_length=40, blank=True, default="")
    contact_email = models.EmailField(blank=True, default="")
    member_sum_assured = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    coverage_basis = models.CharField(max_length=50, blank=True, default="")

    class Meta:
        db_table = "ol_proposal_member"
        ordering = ["proposal", "member_type", "last_name", "first_name"]
        indexes = [models.Index(fields=["proposal", "member_type"])]

    def save(self, *args, **kwargs):
        if not self.full_name_snapshot:
            self.full_name_snapshot = f"{self.first_name} {self.last_name}".strip()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.proposal.proposal_number}:{self.full_name_snapshot}"


class OLProposalInstallmentConfig(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    proposal = models.ForeignKey(OLProposal, on_delete=models.CASCADE, related_name="installment_configs")
    plan_config = models.ForeignKey(OLProposalPlanConfig, on_delete=models.CASCADE, null=True, blank=True, related_name="installment_configs")
    frequency = models.CharField(max_length=40)
    annuity_period_years = models.PositiveSmallIntegerField(default=1)
    number_of_installments = models.PositiveIntegerField(default=1)
    after_maturity_benefits = models.BooleanField(default=False)
    before_maturity_benefits = models.BooleanField(default=False)
    installment_amount = models.DecimalField(max_digits=18, decimal_places=2)
    first_due_date = models.DateField(null=True, blank=True)
    currency = models.CharField(max_length=3, default="TZS")
    is_selected = models.BooleanField(default=True)

    class Meta:
        db_table = "ol_proposal_installment_config"
        ordering = ["proposal", "frequency"]
        indexes = [models.Index(fields=["proposal", "is_selected", "frequency"])]

    def __str__(self):
        return f"{self.proposal.proposal_number}:{self.frequency}"


class OLProposalInstallmentRateRow(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    installment_config = models.ForeignKey(OLProposalInstallmentConfig, on_delete=models.CASCADE, related_name="rate_rows")
    sequence = models.PositiveIntegerField(default=1)
    period_from = models.PositiveIntegerField()
    period_to = models.PositiveIntegerField()
    description = models.CharField(max_length=255, blank=True, default="")
    rate_percent = models.DecimalField(max_digits=7, decimal_places=4, default="0")
    rate = models.DecimalField(max_digits=18, decimal_places=8, default="0")
    charge = models.DecimalField(max_digits=18, decimal_places=2, default="0")
    notes = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        db_table = "ol_proposal_installment_rate_row"
        ordering = ["installment_config", "period_from"]
        constraints = [
            models.CheckConstraint(
                check=Q(period_from__gt=0) & Q(period_to__gte=models.F("period_from")),
                name="ol_proposal_installment_rate_period_valid",
            )
        ]


class OLProposalFundAllocation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    proposal = models.ForeignKey(OLProposal, on_delete=models.CASCADE, related_name="fund_allocations")
    plan_config = models.ForeignKey(OLProposalPlanConfig, on_delete=models.CASCADE, null=True, blank=True, related_name="fund_allocations")
    fund = models.ForeignKey(
        "ol_parameters.OLInvestmentFund", on_delete=models.PROTECT, related_name="proposal_allocations"
    )
    fund_name_snapshot = models.CharField(max_length=255, blank=True, default="")
    allocation_percentage = models.DecimalField(max_digits=7, decimal_places=4)
    allocation_amount = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    is_selected = models.BooleanField(default=True)

    class Meta:
        db_table = "ol_proposal_fund_allocation"
        ordering = ["proposal", "fund__code"]
        constraints = [
            models.CheckConstraint(
                check=Q(allocation_percentage__gte=0) & Q(allocation_percentage__lte=100),
                name="ol_proposal_fund_percentage_range",
            )
        ]


class OLProposalRider(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    proposal = models.ForeignKey(OLProposal, on_delete=models.CASCADE, related_name="riders")
    rider = models.ForeignKey(
        "ol_parameters.OLRiderSetup", on_delete=models.PROTECT, related_name="proposal_riders"
    )
    rider_name_snapshot = models.CharField(max_length=255, blank=True, default="")
    plan_config = models.ForeignKey(OLProposalPlanConfig, on_delete=models.CASCADE, null=True, blank=True, related_name="riders")
    rider_sum_assured = models.DecimalField(max_digits=18, decimal_places=2)
    rider_term_years = models.PositiveSmallIntegerField(null=True, blank=True)
    beneficial_type = models.ForeignKey(
        "ol_parameters.OLBeneficialType", on_delete=models.PROTECT, null=True, blank=True, related_name="ol_proposal_riders"
    )
    benefit_basis = models.CharField(max_length=20, default="FIXED")
    benefit_value = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    loading = models.DecimalField(max_digits=9, decimal_places=4, default="0")
    discount = models.DecimalField(max_digits=9, decimal_places=4, default="0")
    premium_amount = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    is_selected = models.BooleanField(default=True)

    class Meta:
        db_table = "ol_proposal_rider"
        ordering = ["proposal", "rider__code"]


class OLProposalBenefit(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    proposal = models.ForeignKey(OLProposal, on_delete=models.CASCADE, related_name="benefits")
    plan_config = models.ForeignKey(OLProposalPlanConfig, on_delete=models.CASCADE, null=True, blank=True, related_name="benefits")
    code = models.CharField(max_length=80)
    name = models.CharField(max_length=255)
    benefit_type = models.CharField(max_length=80, blank=True, default="")
    basis = models.CharField(max_length=20, default="FIXED")
    value = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    loading = models.DecimalField(max_digits=9, decimal_places=4, default="0")
    discount = models.DecimalField(max_digits=9, decimal_places=4, default="0")
    maximum_cap = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    sum_assured = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    premium_amount = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    is_selected = models.BooleanField(default=True)

    class Meta:
        db_table = "ol_proposal_benefit"
        ordering = ["proposal", "code"]


class OLProposalBeneficiary(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    proposal = models.ForeignKey(OLProposal, on_delete=models.CASCADE, related_name="beneficiaries")
    person_name = models.CharField(max_length=255)
    identity_type = models.CharField(max_length=80, blank=True, default="")
    identity_number = models.CharField(max_length=120, blank=True, default="")
    beneficial_type = models.ForeignKey(
        "ol_parameters.OLBeneficialType", on_delete=models.PROTECT, null=True, blank=True, related_name="ol_proposal_beneficiaries"
    )
    beneficial_type_name_snapshot = models.CharField(max_length=255, blank=True, default="")
    share_percent = models.DecimalField(max_digits=7, decimal_places=4)
    is_primary = models.BooleanField(default=False)
    is_minor = models.BooleanField(default=False)
    guardian_name = models.CharField(max_length=255, blank=True, default="")
    guardian_identity_type = models.CharField(max_length=80, blank=True, default="")
    guardian_identity_number = models.CharField(max_length=120, blank=True, default="")
    guardian_relationship = models.CharField(max_length=80, blank=True, default="")

    class Meta:
        db_table = "ol_proposal_beneficiary"
        ordering = ["proposal", "-is_primary", "person_name"]
        constraints = [
            models.CheckConstraint(
                check=Q(share_percent__gt=0) & Q(share_percent__lte=100),
                name="ol_proposal_beneficiary_share_range",
            )
        ]

    def __str__(self):
        return f"{self.proposal.proposal_number}:{self.person_name}"

    def clean(self):
        errors = {}
        if self.is_minor and not (self.guardian_name or "").strip():
            errors["guardian_name"] = "A guardian is required for a minor beneficiary."
        if not (self.person_name or "").strip():
            errors["person_name"] = "Beneficiary name is required."
        if errors:
            raise ValidationError(errors)


class OLProposalPrintTemplate(models.Model):
    """Versioned, parameter-managed HTML template used for proposal printouts."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=80)
    name = models.CharField(max_length=255)
    version = models.PositiveIntegerField(default=1)
    description = models.TextField(blank=True, default="")
    template_html = models.TextField()
    layout_variables = models.JSONField(default=dict, blank=True)
    effective_from = models.DateField(null=True, blank=True)
    effective_to = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ol_proposal_print_template"
        ordering = ["code", "-version"]
        constraints = [
            models.UniqueConstraint(fields=["code", "version"], name="ol_proposal_print_template_code_version_uq"),
        ]
        indexes = [
            models.Index(fields=["code", "is_active", "effective_from", "effective_to"], name="ol_prop_print_tpl_active_idx"),
        ]

    def __str__(self):
        return f"{self.code} v{self.version}"

    def clean(self):
        errors = {}
        self.code = (self.code or "").strip().upper()
        self.name = (self.name or "").strip()
        self.template_html = self.template_html or ""
        if not self.code:
            errors["code"] = "Template code is required."
        if not self.name:
            errors["name"] = "Template name is required."
        if self.version < 1:
            errors["version"] = "Template version must be positive."
        if not self.template_html.strip():
            errors["template_html"] = "Template HTML is required."
        if not isinstance(self.layout_variables, dict):
            errors["layout_variables"] = "Layout variables must be a JSON object."
        if self.effective_from and self.effective_to and self.effective_to < self.effective_from:
            errors["effective_to"] = "Effective-to cannot be before effective-from."
        if errors:
            raise ValidationError(errors)


class OLProposalDocument(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    proposal = models.ForeignKey(OLProposal, on_delete=models.CASCADE, related_name="documents")
    document_type = models.CharField(max_length=120, db_index=True)
    file_reference = models.CharField(max_length=500, blank=True, default="")
    html_reference = models.CharField(max_length=500, blank=True, default="")
    mime_type = models.CharField(max_length=120, default="application/pdf")
    mandatory = models.BooleanField(default=False)
    status = models.CharField(
        max_length=30, choices=ProposalDocumentStatus.choices, default=ProposalDocumentStatus.REQUESTED, db_index=True
    )
    rejection_reason = models.TextField(blank=True, default="")
    template = models.ForeignKey(
        "ol_proposals.OLProposalPrintTemplate",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="generated_documents",
    )
    template_version = models.PositiveIntegerField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="uploaded_ol_proposal_documents"
    )
    uploaded_at = models.DateTimeField(null=True, blank=True)
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="generated_ol_proposal_documents"
    )
    generated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ol_proposal_document"
        ordering = ["proposal", "document_type"]
        indexes = [
            models.Index(fields=["proposal", "document_type", "status"], name="ol_prop_doc_type_status_idx"),
            models.Index(fields=["proposal", "template_version"], name="ol_prop_doc_tpl_ver_idx"),
        ]

    def __str__(self):
        return f"{self.proposal.proposal_number}:{self.document_type}"

    def clean(self):
        errors = {}
        self.document_type = (self.document_type or "").strip().upper()
        self.file_reference = (self.file_reference or "").strip()
        self.html_reference = (self.html_reference or "").strip()
        self.mime_type = (self.mime_type or "application/pdf").strip().lower()
        if not self.document_type:
            errors["document_type"] = "Document type is required."
        if not isinstance(self.metadata, dict):
            errors["metadata"] = "Metadata must be a JSON object."
        if self.template_id and self.template_version is not None and self.template.version != self.template_version:
            errors["template_version"] = "Stored template version must match the selected template."
        if errors:
            raise ValidationError(errors)


class OLProposalHealthAnswer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    proposal = models.ForeignKey(OLProposal, on_delete=models.CASCADE, related_name="health_answers")
    questionnaire_item = models.ForeignKey(
        "ol_parameters.OLHealthQuestionnaireItem", on_delete=models.PROTECT, null=True, blank=True, related_name="ol_proposal_health_answers"
    )
    health_question = models.ForeignKey(
        "ol_parameters.OLHealthQuestion", on_delete=models.PROTECT, related_name="ol_proposal_health_answers"
    )
    answer = models.JSONField(default=dict, blank=True)
    score = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    triggers_medical = models.BooleanField(default=False)
    answered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ol_proposal_health_answer"
        ordering = ["proposal", "answered_at"]
        indexes = [models.Index(fields=["proposal", "triggers_medical"])]

    def __str__(self):
        return f"{self.proposal.proposal_number}:{self.health_question_id}"