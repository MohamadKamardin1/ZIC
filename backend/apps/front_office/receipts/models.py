"""Front Office Receipts — domain models.

The bounded context for cash/bank premium receipts, their allocations, and
their reversals. Receipts are the front-office write path for premium deposits
(notably the first premium of an OL proposal): a receipt is created as a draft,
posted once money is confirmed, then allocated against a target (an OL
Commitment for first premium) until fully allocated. Reversals are auditable,
linked, first-class records.

Status machine (``ReceiptStatus``):

    DRAFT -> POSTED -> PARTIALLY_ALLOCATED -> FULLY_ALLOCATED
       |         |                                 |
       +-- CANCELLED   +---------------------------+-- REVERSED

Amount invariants are enforced at the database level (positive amount, positive
exchange rate, non-negative unallocated balance) and recomputed on every save.
"""

import uuid
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.common.models import AuditedModel

ZERO = Decimal("0.00")


class ReceiptSourceModule(models.TextChoices):
    OL_PROPOSAL = "OL_PROPOSAL", "OL Proposal"
    OL_POLICY = "OL_POLICY", "OL Policy"
    GROUP_CREDIT = "GROUP_CREDIT", "Group Credit"
    MANUAL = "MANUAL", "Manual"
    OTHER = "OTHER", "Other"


class ReceiptSourceChannel(models.TextChoices):
    WEB = "WEB", "Web"
    API = "API", "API"
    ADMIN = "ADMIN", "Admin"
    SYSTEM = "SYSTEM", "System"
    IMPORT = "IMPORT", "Import"
    PORTAL = "PORTAL", "Portal"
    BATCH = "BATCH", "Batch"
    MANUAL = "MANUAL", "Manual"


class ReceiptStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    POSTED = "POSTED", "Posted"
    PARTIALLY_ALLOCATED = "PARTIALLY_ALLOCATED", "Partially allocated"
    FULLY_ALLOCATED = "FULLY_ALLOCATED", "Fully allocated"
    REVERSED = "REVERSED", "Reversed"
    CANCELLED = "CANCELLED", "Cancelled"


class ReceiptPaymentMode(models.TextChoices):
    CASH = "CASH", "Cash"
    BANK_TRANSFER = "BANK_TRANSFER", "Bank transfer"
    CHEQUE = "CHEQUE", "Cheque"
    MOBILE_MONEY = "M-PESA", "M-PESA"
    OTHER = "OTHER", "Other"


class ReceiptAllocationTargetType(models.TextChoices):
    OL_COMMITMENT = "OL_COMMITMENT", "OL Commitment"
    OL_PROPOSAL = "OL_PROPOSAL", "OL Proposal"
    OL_POLICY = "OL_POLICY", "OL Policy"
    MANUAL = "MANUAL", "Manual"


class ReceiptAllocationStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    REVERSED = "REVERSED", "Reversed"
    VOID = "VOID", "Void"


class ReceiptDocumentStatus(models.TextChoices):
    UPLOADED = "UPLOADED", "Uploaded"
    GENERATED = "GENERATED", "Generated"


def is_valid_receipt_status(value):
    return (value or "").strip().upper() in {code for code, _label in ReceiptStatus.choices}


def receipt_status_for_amounts(allocated, unallocated):
    """Derive the allocation status from the current amount split."""
    if allocated > ZERO and unallocated <= ZERO:
        return ReceiptStatus.FULLY_ALLOCATED
    if allocated > ZERO:
        return ReceiptStatus.PARTIALLY_ALLOCATED
    return ReceiptStatus.POSTED


class Receipt(AuditedModel):
    """A front-office premium receipt.

    ``receipt_number`` is the unique human identifier shown everywhere instead
    of the UUID; ``idempotency_key`` guards against duplicate submission of the
    same financial event. Amounts are stored in the receipt currency; foreign
    currency receipts carry ``exchange_rate`` to the functional currency (TZS).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Assigned at posting time by the numbering service; drafts carry no number.
    receipt_number = models.CharField(max_length=50, unique=True, null=True, blank=True, db_index=True)
    idempotency_key = models.CharField(max_length=64, unique=True, null=True, blank=True, db_index=True)
    receipt_date = models.DateField(db_index=True)

    branch = models.ForeignKey(
        "partner_onboarding.Branch",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="receipts",
    )
    branch_name_snapshot = models.CharField(max_length=200, blank=True, default="")

    partner = models.ForeignKey(
        "partners.Partner",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="receipts",
    )
    partner_name_snapshot = models.CharField(max_length=255, blank=True, default="")
    payer_name = models.CharField(max_length=255)
    payer_identity = models.CharField(max_length=100, blank=True, default="", help_text="National ID / TIN / policyholder identity snapshot.")

    source_module = models.CharField(
        max_length=30, choices=ReceiptSourceModule.choices, default=ReceiptSourceModule.MANUAL, db_index=True
    )
    source_reference_type = models.CharField(max_length=60, blank=True, default="", help_text="e.g. PROPOSAL_NUMBER, COMMITMENT_NUMBER, POLICY_NUMBER.")
    source_reference_id = models.CharField(max_length=120, blank=True, default="", db_index=True, help_text="Human reference of the source record (names, never UUIDs).")

    currency = models.CharField(max_length=3, default="TZS")
    exchange_rate = models.DecimalField(max_digits=12, decimal_places=6, default=Decimal("1.000000"))
    receipt_amount = models.DecimalField(max_digits=18, decimal_places=2)
    allocated_amount = models.DecimalField(max_digits=18, decimal_places=2, default=ZERO)
    unallocated_amount = models.DecimalField(max_digits=18, decimal_places=2, default=ZERO)

    payment_mode = models.CharField(
        max_length=30, choices=ReceiptPaymentMode.choices, default=ReceiptPaymentMode.CASH
    )
    payment_reference = models.CharField(max_length=120, blank=True, default="")
    bank_account = models.ForeignKey(
        "partners.PartnerBankAccount",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="receipts",
    )
    bank_account_snapshot = models.CharField(max_length=255, blank=True, default="")
    narration = models.TextField(blank=True, default="")

    status = models.CharField(max_length=30, choices=ReceiptStatus.choices, default=ReceiptStatus.DRAFT, db_index=True)
    posted_at = models.DateTimeField(null=True, blank=True)
    posted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="posted_receipts",
    )
    reversed_at = models.DateTimeField(null=True, blank=True)
    reversed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reversed_receipts",
    )
    cancellation_reason = models.TextField(blank=True, default="")
    # NOTE: ReceiptReversal.reversed_by uses a distinct related_name to avoid
    # a reverse-accessor clash on the User model.

    source_channel = models.CharField(
        max_length=30, choices=ReceiptSourceChannel.choices, default=ReceiptSourceChannel.API
    )

    class Meta:
        db_table = "front_office_receipt"
        verbose_name = "Receipt"
        verbose_name_plural = "Receipts"
        ordering = ["-receipt_date", "-created_at"]
        constraints = [
            models.CheckConstraint(check=Q(receipt_amount__gt=0), name="receipt_amount_positive"),
            models.CheckConstraint(check=Q(exchange_rate__gt=0), name="receipt_exchange_rate_positive"),
            models.CheckConstraint(check=Q(allocated_amount__gte=0), name="receipt_allocated_nonnegative"),
            models.CheckConstraint(check=Q(unallocated_amount__gte=0), name="receipt_unallocated_nonnegative"),
        ]
        indexes = [
            models.Index(fields=["status", "receipt_date"], name="receipt_status_date_idx"),
            models.Index(fields=["branch", "receipt_date"], name="receipt_branch_date_idx"),
            models.Index(fields=["source_module", "source_reference_id"], name="receipt_source_ref_idx"),
            models.Index(fields=["partner", "receipt_date"], name="receipt_partner_date_idx"),
            models.Index(fields=["currency", "receipt_date"], name="receipt_currency_date_idx"),
        ]

    def __str__(self):
        if self.receipt_number:
            return f"{self.receipt_number} ({self.payer_name})"
        return f"DRAFT {self.payer_name}"

    @property
    def display_partner(self):
        return self.partner_name_snapshot or self.payer_name

    def _derive_snapshots(self):
        if self.partner_id and not self.partner_name_snapshot:
            self.partner_name_snapshot = str(self.partner)
        if self.partner_id and not self.payer_name:
            self.payer_name = getattr(self.partner, "display_name", None) or str(self.partner)
        if self.branch_id and not self.branch_name_snapshot:
            self.branch_name_snapshot = str(self.branch)
        if self.bank_account_id and not self.bank_account_snapshot:
            self.bank_account_snapshot = str(self.bank_account)

    def recompute_allocated(self):
        """Keep allocated/unallocated consistent with the active allocation set."""
        if self.pk is not None:
            active = self.allocations.filter(
                reversal_of__isnull=True,
                allocation_status=ReceiptAllocationStatus.ACTIVE,
            )
            allocated = sum((Decimal(row.amount) for row in active), ZERO)
        else:
            allocated = Decimal(self.allocated_amount or ZERO)
        self.allocated_amount = allocated
        self.unallocated_amount = (Decimal(self.receipt_amount) or ZERO) - allocated

    def _derive_status(self):
        if self.status in (ReceiptStatus.REVERSED, ReceiptStatus.CANCELLED):
            return
        if not self.posted_at:
            if self.status not in (
                ReceiptStatus.POSTED,
                ReceiptStatus.PARTIALLY_ALLOCATED,
                ReceiptStatus.FULLY_ALLOCATED,
            ):
                self.status = ReceiptStatus.DRAFT
            return
        self.status = receipt_status_for_amounts(
            Decimal(self.allocated_amount or ZERO), Decimal(self.unallocated_amount or ZERO)
        )

    def save(self, *args, **kwargs):
        self._derive_snapshots()
        self.recompute_allocated()
        self._derive_status()
        return super().save(*args, **kwargs)

    def clean(self):
        errors = {}

        # Drafts are numbered at posting time; only non-draft receipts must
        # carry a human receipt number.
        if not (self.receipt_number or "").strip() and (self.status or "").strip().upper() != ReceiptStatus.DRAFT:
            errors["receipt_number"] = "Receipt number is required once the receipt is posted."
        if not self.receipt_date:
            errors["receipt_date"] = "Receipt date is required."
        if not (self.payer_name or "").strip():
            errors["payer_name"] = "Payer name is required."
        if self.receipt_amount is None or self.receipt_amount <= 0:
            errors["receipt_amount"] = "Receipt amount must be greater than zero."

        currency = (self.currency or "").strip().upper()
        if len(currency) != 3 or not currency.isalpha():
            errors["currency"] = "Currency must be a three-letter code."
        self.currency = currency

        if (self.exchange_rate or ZERO) <= 0:
            errors["exchange_rate"] = "Exchange rate must be greater than zero."

        status = (self.status or "").strip().upper()
        if not is_valid_receipt_status(status):
            errors["status"] = f"Status '{status}' is not a valid receipt status."
        self.status = status

        source_module = (self.source_module or "").strip().upper()
        if source_module in {
            ReceiptSourceModule.OL_PROPOSAL,
            ReceiptSourceModule.OL_POLICY,
            ReceiptSourceModule.GROUP_CREDIT,
        }:
            if not (self.source_reference_id or "").strip():
                errors["source_reference_id"] = (
                    "A source reference is required when the receipt originates from a source module."
                )
            if not (self.source_reference_type or "").strip():
                errors["source_reference_type"] = "A source reference type is required for the selected source module."

        if source_module == ReceiptSourceModule.OL_PROPOSAL and (self.source_reference_id or "").strip():
            from apps.ol_proposals.models import OLProposal

            if not OLProposal.objects.filter(proposal_number=self.source_reference_id).exists():
                errors["source_reference_id"] = (
                    f"No OL proposal exists with number '{self.source_reference_id}'."
                )

        if errors:
            raise ValidationError(errors)

    def full_clean_ex(self):
        self.clean()
        return self


class ReceiptAllocation(AuditedModel):
    """An amount of a receipt applied to a target (commitment, proposal, policy).

    The active allocation set drives ``Receipt.allocated_amount``. Reversals
    link to their original allocation through ``reversal_of`` so the money
    trail is fully auditable.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    receipt = models.ForeignKey(
        Receipt,
        on_delete=models.CASCADE,
        related_name="allocations",
    )
    target_type = models.CharField(
        max_length=30, choices=ReceiptAllocationTargetType.choices, default=ReceiptAllocationTargetType.OL_COMMITMENT
    )
    target_id = models.CharField(max_length=120, blank=True, default="", db_index=True)
    target_display = models.CharField(max_length=255, blank=True, default="")
    # OL commitment links (names are surfaced through target_display); the
    # OLCommitmentAllocation row is the commitments-side write that this record
    # mirrors so both ledgers reconcile (docs/OL_PROPOSALS_RECEIPTS_SEAM.md).
    commitment = models.ForeignKey(
        "ol_commitments.OLCommitment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="receipt_allocations",
    )
    ol_commitment_allocation = models.ForeignKey(
        "ol_commitments.OLCommitmentAllocation",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="receipt_allocations",
    )
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    currency = models.CharField(max_length=3, default="TZS")
    exchange_rate = models.DecimalField(max_digits=12, decimal_places=6, default=Decimal("1.000000"))
    # Multi-currency audit trail (prompt 5): the rate actually applied, its
    # provenance, and the converted amount in the target currency. ``amount``
    # stays the original receipt-currency amount; ``converted_amount`` is what
    # the commitment side books in its own currency.
    exchange_rate_used = models.DecimalField(max_digits=12, decimal_places=6, default=Decimal("1.000000"))
    exchange_rate_source = models.CharField(max_length=40, blank=True, default="")
    converted_amount = models.DecimalField(max_digits=18, decimal_places=2, default=ZERO)
    converted_currency = models.CharField(max_length=3, blank=True, default="")
    allocation_status = models.CharField(
        max_length=30, choices=ReceiptAllocationStatus.choices, default=ReceiptAllocationStatus.ACTIVE, db_index=True
    )
    reversal_of = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="reversal_allocations",
    )
    narration = models.TextField(blank=True, default="")
    allocated_at = models.DateTimeField(default=timezone.now)
    allocated_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="allocated_receipts",
    )
    source_channel = models.CharField(
        max_length=30, choices=ReceiptSourceChannel.choices, default=ReceiptSourceChannel.API
    )

    class Meta:
        db_table = "front_office_receipt_allocation"
        verbose_name = "Receipt Allocation"
        verbose_name_plural = "Receipt Allocations"
        ordering = ["-allocated_at", "-created_at"]
        constraints = [
            models.CheckConstraint(check=Q(amount__gt=0), name="receipt_allocation_amount_positive"),
            models.CheckConstraint(check=Q(exchange_rate__gt=0), name="receipt_allocation_rate_positive"),
            models.CheckConstraint(check=Q(exchange_rate_used__gt=0), name="receipt_allocation_rate_used_positive"),
            models.CheckConstraint(check=Q(converted_amount__gte=0), name="receipt_allocation_converted_nonnegative"),
        ]
        indexes = [
            models.Index(fields=["receipt", "target_type", "target_id"], name="receipt_alloc_target_idx"),
            models.Index(fields=["receipt", "allocation_status"], name="receipt_alloc_status_idx"),
        ]

    def __str__(self):
        return f"{self.receipt.receipt_number} -> {self.amount} {self.currency}"

    def clean(self):
        errors = {}
        if self.amount is None or self.amount <= 0:
            errors["amount"] = "Allocation amount must be greater than zero."
        if (self.exchange_rate or ZERO) <= 0:
            errors["exchange_rate"] = "Exchange rate must be greater than zero."
        if (self.exchange_rate_used or ZERO) <= 0:
            errors["exchange_rate_used"] = "Exchange rate used must be greater than zero."
        if (self.converted_amount or ZERO) < 0:
            errors["converted_amount"] = "Converted amount cannot be negative."
        currency = (self.currency or "").strip().upper()
        if len(currency) != 3 or not currency.isalpha():
            errors["currency"] = "Currency must be a three-letter code."
        self.currency = currency
        if self.reversal_of_id and self.reversal_of_id == self.pk:
            errors["reversal_of"] = "An allocation cannot reverse itself."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if not self.target_display and self.target_id:
            self.target_display = self.target_id
        return super().save(*args, **kwargs)


class ReceiptReversal(AuditedModel):
    """First-class record of a receipt reversal with a frozen allocation snapshot."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    receipt = models.ForeignKey(
        Receipt,
        on_delete=models.PROTECT,
        related_name="reversals",
    )
    reversal_number = models.CharField(max_length=50, unique=True, db_index=True)
    reason = models.TextField()
    reversed_allocations = models.JSONField(default=list, blank=True)
    reversed_at = models.DateTimeField(default=timezone.now)
    reversed_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reversed_receipt_records",
    )

    class Meta:
        db_table = "front_office_receipt_reversal"
        verbose_name = "Receipt Reversal"
        verbose_name_plural = "Receipt Reversals"
        ordering = ["-reversed_at", "-created_at"]
        indexes = [
            models.Index(fields=["receipt", "reversed_at"], name="receipt_reversal_receipt_idx"),
        ]

    def __str__(self):
        return f"{self.reversal_number} ({self.receipt.receipt_number})"

    def clean(self):
        errors = {}
        if not self.reversal_number:
            errors["reversal_number"] = "Reversal number is required."
        if not (self.reason or "").strip():
            errors["reason"] = "A reversal reason is required."
        if errors:
            raise ValidationError(errors)


class ReceiptPrintTemplate(models.Model):
    """Versioned, parameter-managed HTML template used for receipt printouts.

    Registered under the document template type ``RECEIPT`` (Prompt 8): the
    active effective template is resolved at print time and its code/version is
    frozen onto the generated ``ReceiptDocument`` so every printout retains the
    exact template that produced it.
    """

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
        db_table = "front_office_receipt_print_template"
        verbose_name = "Receipt Print Template"
        verbose_name_plural = "Receipt Print Templates"
        ordering = ["code", "-version"]
        constraints = [
            models.UniqueConstraint(fields=["code", "version"], name="receipt_print_template_code_version_uq"),
        ]
        indexes = [
            models.Index(fields=["code", "is_active", "effective_from", "effective_to"], name="receipt_print_tpl_active_idx"),
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


class ReceiptDocument(AuditedModel):
    """Printable receipt output and future control-number (government seam) records.

    ``UPLOADED`` rows are the future government/upload seam; ``GENERATED`` rows
    are produced by the unified print engine (``ReceiptPrintService``) and retain
    the source transaction (``receipt``), the template code/version used, and the
    generating user/timestamp so every printout is fully traceable.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    receipt = models.ForeignKey(
        Receipt,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    document_type = models.CharField(max_length=60, default="RECEIPT")
    document_number = models.CharField(max_length=120, blank=True, default="", help_text="Future government control number (e.g. TRA GST).")
    file_reference = models.CharField(max_length=255, blank=True, default="")
    html_reference = models.CharField(max_length=255, blank=True, default="")
    filename = models.CharField(max_length=255, blank=True, default="")
    mime_type = models.CharField(max_length=100, blank=True, default="application/pdf")
    status = models.CharField(
        max_length=30, choices=ReceiptDocumentStatus.choices, default=ReceiptDocumentStatus.UPLOADED, db_index=True
    )
    uploaded_at = models.DateTimeField(default=timezone.now)
    uploaded_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_receipt_documents",
    )
    # Print-engine traceability (Prompt 8): the exact template code/version used
    # to render this document and the user/timestamp that generated it.
    template = models.ForeignKey(
        ReceiptPrintTemplate,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="generated_documents",
    )
    template_version = models.PositiveIntegerField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    generated_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generated_receipt_documents",
    )
    generated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "front_office_receipt_document"
        verbose_name = "Receipt Document"
        verbose_name_plural = "Receipt Documents"
        ordering = ["-uploaded_at", "-created_at"]
        indexes = [
            models.Index(fields=["receipt", "document_type"], name="receipt_document_type_idx"),
            models.Index(fields=["receipt", "status", "template_version"], name="receipt_doc_tpl_ver_idx"),
        ]

    def __str__(self):
        return f"{self.receipt.receipt_number}:{self.document_type}"

    def clean(self):
        errors = {}
        self.document_type = (self.document_type or "").strip().upper() or "RECEIPT"
        self.file_reference = (self.file_reference or "").strip()
        self.html_reference = (self.html_reference or "").strip()
        self.mime_type = (self.mime_type or "application/pdf").strip().lower()
        if not isinstance(self.metadata, dict):
            errors["metadata"] = "Metadata must be a JSON object."
        if self.template_id and self.template_version is not None and self.template.version != self.template_version:
            errors["template_version"] = "Stored template version must match the selected template."
        if errors:
            raise ValidationError(errors)


class ReceiptStatusHistory(AuditedModel):
    """Auditable status transition log for a receipt."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    receipt = models.ForeignKey(
        Receipt,
        on_delete=models.CASCADE,
        related_name="status_history",
    )
    from_status = models.CharField(max_length=30, blank=True, default="")
    to_status = models.CharField(max_length=30)
    reason = models.TextField(blank=True, default="")
    changed_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="receipt_status_changes",
    )
    changed_at = models.DateTimeField(default=timezone.now)
    source_channel = models.CharField(
        max_length=30, choices=ReceiptSourceChannel.choices, default=ReceiptSourceChannel.API
    )

    class Meta:
        db_table = "front_office_receipt_status_history"
        verbose_name = "Receipt Status History"
        verbose_name_plural = "Receipt Status History"
        ordering = ["-changed_at", "-created_at"]
        indexes = [
            models.Index(fields=["receipt", "changed_at"], name="receipt_status_history_idx"),
        ]

    def __str__(self):
        return f"{self.receipt.receipt_number}: {self.from_status or '-'} -> {self.to_status}"


class ExchangeRate(models.Model):
    """A configured conversion rate between two currencies, effective from a date.

    Parameterized reference data (prompt 5): same-currency allocations need no
    rate; a cross-currency allocation either supplies an explicit rate or
    resolves the most recent active rate for the pair from this table. Rates are
    always quoted *from_currency -> to_currency* (e.g. USD -> TZS).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    from_currency = models.CharField(max_length=3)
    to_currency = models.CharField(max_length=3)
    rate = models.DecimalField(max_digits=18, decimal_places=8)
    effective_date = models.DateField()
    source = models.CharField(max_length=40, default="MANUAL")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "front_office_exchange_rate"
        verbose_name = "Exchange Rate"
        verbose_name_plural = "Exchange Rates"
        ordering = ["-effective_date", "-created_at"]
        constraints = [
            models.CheckConstraint(check=Q(rate__gt=0), name="exchange_rate_positive"),
        ]
        constraints += [
            models.UniqueConstraint(
                fields=["from_currency", "to_currency", "effective_date"],
                name="exchange_rate_pair_date_unique",
            ),
        ]
        indexes = [
            models.Index(
                fields=["from_currency", "to_currency", "effective_date"],
                name="exchange_rate_pair_date_idx",
            ),
        ]

    def __str__(self):
        return f"{self.from_currency}/{self.to_currency} @ {self.rate} ({self.effective_date})"

    def clean(self):
        errors = {}
        from_code = (self.from_currency or "").strip().upper()
        to_code = (self.to_currency or "").strip().upper()
        if len(from_code) != 3 or not from_code.isalpha():
            errors["from_currency"] = "From currency must be a three-letter code."
        if len(to_code) != 3 or not to_code.isalpha():
            errors["to_currency"] = "To currency must be a three-letter code."
        if from_code and from_code == to_code:
            errors["to_currency"] = "To currency must differ from the from currency."
        if self.rate is None or self.rate <= 0:
            errors["rate"] = "Rate must be greater than zero."
        self.from_currency = from_code
        self.to_currency = to_code
        if errors:
            raise ValidationError(errors)

    @classmethod
    def resolve(cls, from_currency, to_currency, effective_date=None):
        """Most recent active rate at or before ``effective_date`` (default today)."""
        from_code = (from_currency or "").strip().upper()
        to_code = (to_currency or "").strip().upper()
        if not from_code or not to_code:
            return None
        cutoff = effective_date or timezone.localdate()
        return (
            cls.objects.filter(
                from_currency=from_code,
                to_currency=to_code,
                is_active=True,
                effective_date__lte=cutoff,
            )
            .order_by("-effective_date", "-created_at")
            .first()
        )


class ReceiptImportMode(models.TextChoices):
    DRAFT = "DRAFT", "Draft only"
    POST = "POST", "Draft and post"
    ALLOCATE = "ALLOCATE", "Draft, post and allocate"


class ReceiptImportBatchStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    VALIDATED = "VALIDATED", "Validated"
    COMMITTED = "COMMITTED", "Committed"
    PARTIAL = "PARTIAL", "Partially committed"
    FAILED = "FAILED", "Failed"


class ReceiptImportRowStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    VALID = "VALID", "Valid"
    INVALID = "INVALID", "Invalid"
    COMMITTED = "COMMITTED", "Committed"
    FAILED = "FAILED", "Failed"
    DUPLICATE = "DUPLICATE", "Duplicate"


class ReceiptImportBatch(AuditedModel):
    """A bulk receipt import run: a validated CSV plus the commit trail (prompt 9).

    The batch owns a set of :class:`ReceiptImportRow` records, one per CSV row.
    Dry-run fills the rows and marks them VALID/INVALID/DUPLICATE without touching
    ``Receipt``. Commit replays the VALID (and any FAILED) rows into receipts,
    idempotently, and records the outcome per row so failed rows stay reprocessable.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch_number = models.CharField(max_length=60, unique=True, db_index=True)
    import_mode = models.CharField(
        max_length=30,
        choices=ReceiptImportMode.choices,
        default=ReceiptImportMode.DRAFT,
    )
    status = models.CharField(
        max_length=30,
        choices=ReceiptImportBatchStatus.choices,
        default=ReceiptImportBatchStatus.PENDING,
        db_index=True,
    )
    file_name = models.CharField(max_length=255, blank=True, default="")
    total_rows = models.PositiveIntegerField(default=0)
    valid_rows = models.PositiveIntegerField(default=0)
    invalid_rows = models.PositiveIntegerField(default=0)
    committed_rows = models.PositiveIntegerField(default=0)
    failed_rows = models.PositiveIntegerField(default=0)
    summary = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "front_office_receipt_import_batch"
        verbose_name = "Receipt Import Batch"
        verbose_name_plural = "Receipt Import Batches"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"], name="imp_batch_status_cat_idx"),
            models.Index(fields=["import_mode", "status"], name="imp_batch_mode_status_idx"),
        ]

    def __str__(self):
        return f"{self.batch_number} ({self.status})"


class ReceiptImportRow(AuditedModel):
    """A single CSV row within an import batch, with its validation and commit trail."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch = models.ForeignKey(
        ReceiptImportBatch, on_delete=models.CASCADE, related_name="rows"
    )
    row_number = models.PositiveIntegerField(db_index=True)
    row_hash = models.CharField(max_length=64, db_index=True)
    data = models.JSONField(default=dict, blank=True)
    status = models.CharField(
        max_length=30,
        choices=ReceiptImportRowStatus.choices,
        default=ReceiptImportRowStatus.PENDING,
        db_index=True,
    )
    validation_errors = models.JSONField(default=dict, blank=True)
    error_code = models.CharField(max_length=60, blank=True, default="")
    error_message = models.TextField(blank=True, default="")
    receipt = models.ForeignKey(
        Receipt,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="import_rows",
    )
    committed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "front_office_receipt_import_row"
        verbose_name = "Receipt Import Row"
        verbose_name_plural = "Receipt Import Rows"
        ordering = ["batch", "row_number"]
        indexes = [
            models.Index(fields=["batch", "status"], name="imp_row_batch_status_idx"),
        ]

    def __str__(self):
        return f"{self.batch.batch_number}:row{self.row_number} ({self.status})"
