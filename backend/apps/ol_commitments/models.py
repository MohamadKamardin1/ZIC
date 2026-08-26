import uuid
from decimal import Decimal

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.common.models import AuditedModel
from apps.ol_commitments.services.parameter_resolver import (
    compute_grace_envelope,
    default_commitment_status,
    is_valid_commitment_status,
)

ZERO = Decimal("0.00")


class CommitmentSourceType(models.TextChoices):
    PROPOSAL = "PROPOSAL", "Proposal"
    POLICY = "POLICY", "Policy"
    MANUAL = "MANUAL", "Manual"


class CommitmentSourceChannel(models.TextChoices):
    WEB = "WEB", "Web"
    API = "API", "API"
    ADMIN = "ADMIN", "Admin"
    SYSTEM = "SYSTEM", "System"
    IMPORT = "IMPORT", "Import"
    PORTAL = "PORTAL", "Portal"
    BATCH = "BATCH", "Batch"
    MANUAL = "MANUAL", "Manual"
    QUICK_CREATE = "QUICK_CREATE", "Quick create"


class NotificationEventType(models.TextChoices):
    PREMIUM_DUE = "PREMIUM_DUE", "Premium due"
    GRACE_START = "GRACE_START", "Grace start"
    GRACE_WARNING = "GRACE_WARNING", "Grace warning"
    PRE_LAPSE = "PRE_LAPSE", "Pre-lapse"
    LAPSE = "LAPSE", "Lapse"


class NotificationChannel(models.TextChoices):
    SYSTEM = "SYSTEM", "System"
    EMAIL = "EMAIL", "Email"
    SMS = "SMS", "SMS"
    PORTAL = "PORTAL", "Portal"
    OTHER = "OTHER", "Other"


class NotificationRecipientType(models.TextChoices):
    POLICYHOLDER = "POLICYHOLDER", "Policyholder"
    AGENT = "AGENT", "Agent"
    STAFF = "STAFF", "Staff"
    PARTNER = "PARTNER", "Partner"


class NotificationDispatchStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    DISPATCHED = "DISPATCHED", "Dispatched"
    FAILED = "FAILED", "Failed"
    SKIPPED = "SKIPPED", "Skipped"


_SOURCE_MODEL_MAP = {
    CommitmentSourceType.PROPOSAL: {
        "ol_proposals": {"olproposal"},
        "ordinary_life": {"olproposal"},
    },
    CommitmentSourceType.POLICY: {
        "ordinary_life": {"olpolicy"},
    },
}


class OLCommitment(AuditedModel):
    """A scheduled, parameter-validated premium obligation.

    Created for a proposal first premium (``PROPOSAL``), a policy renewal
    schedule row (``POLICY``), or an authorized operator entry (``MANUAL``).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    commitment_number = models.CharField(max_length=100, unique=True, db_index=True)
    idempotency_key = models.CharField(max_length=64, unique=True, null=True, blank=True, db_index=True)

    source_type = models.CharField(max_length=20, choices=CommitmentSourceType.choices, db_index=True)
    source_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )
    source_object_id = models.CharField(max_length=120, blank=True, default="")
    source = GenericForeignKey("source_content_type", "source_object_id")
    source_reference = models.CharField(max_length=120, blank=True, default="", db_index=True)

    partner = models.ForeignKey(
        "partners.Partner",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="ol_commitments",
    )
    partner_name_snapshot = models.CharField(max_length=255, blank=True, default="")
    product = models.ForeignKey(
        "ol_parameters.OLProduct",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="ol_commitments",
    )
    product_name_snapshot = models.CharField(max_length=255, blank=True, default="")
    plan = models.ForeignKey(
        "ordinary_life.OLPlan",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="ol_commitments",
    )
    plan_name_snapshot = models.CharField(max_length=255, blank=True, default="")

    currency = models.CharField(max_length=3, default="TZS")
    premium_frequency = models.CharField(max_length=30, blank=True, default="")
    installment_number = models.PositiveIntegerField(default=1)
    installment_count = models.PositiveIntegerField(default=1)
    due_date = models.DateField(db_index=True)
    premium_amount = models.DecimalField(max_digits=18, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=18, decimal_places=2, default=ZERO)
    amount_waived = models.DecimalField(max_digits=18, decimal_places=2, default=ZERO)
    balance = models.DecimalField(max_digits=18, decimal_places=2, default=ZERO, db_index=True)

    status = models.CharField(max_length=60, default="", db_index=True)
    grace_date = models.DateField(null=True, blank=True)
    warning_date = models.DateField(null=True, blank=True)
    pre_lapse_date = models.DateField(null=True, blank=True)
    lapse_date = models.DateField(null=True, blank=True)

    approval_required = models.BooleanField(default=False)
    reason_code = models.CharField(max_length=60, blank=True, default="")
    reason_text = models.TextField(blank=True, default="")
    lapse_review_flag = models.BooleanField(default=False, db_index=True)
    source_channel = models.CharField(
        max_length=30,
        choices=CommitmentSourceChannel.choices,
        default=CommitmentSourceChannel.SYSTEM,
    )

    class Meta:
        db_table = "ol_commitments_commitment"
        ordering = ["-due_date", "-created_at"]
        verbose_name = "OL Commitment"
        verbose_name_plural = "OL Commitments"
        constraints = [
            models.CheckConstraint(
                check=Q(premium_amount__gt=0),
                name="ol_commitment_premium_positive",
            ),
            models.CheckConstraint(
                check=Q(amount_paid__gte=0),
                name="ol_commitment_amount_paid_nonnegative",
            ),
            models.CheckConstraint(
                check=Q(amount_waived__gte=0),
                name="ol_commitment_amount_waived_nonnegative",
            ),
            models.CheckConstraint(
                check=Q(installment_number__gt=0) & Q(installment_count__gt=0),
                name="ol_commitment_installment_positive",
            ),
            models.UniqueConstraint(
                fields=["source_content_type", "source_object_id", "installment_number"],
                name="ol_commitment_source_installment_unique",
            ),
        ]
        indexes = [
            models.Index(fields=["status", "due_date"], name="ol_commitment_status_due_idx"),
            models.Index(fields=["source_type", "status"], name="ol_commitment_src_status_idx"),
            models.Index(fields=["partner", "due_date"], name="ol_commitment_partner_due_idx"),
            models.Index(fields=["product", "plan", "due_date"], name="ol_commitment_product_due_idx"),
            models.Index(fields=["currency", "due_date"], name="ol_commitment_currency_due_idx"),
        ]

    def __str__(self):
        return self.commitment_number

    def recompute_balance(self):
        self.balance = (
            (Decimal(self.premium_amount) or ZERO)
            - (Decimal(self.amount_paid) or ZERO)
            - (Decimal(self.amount_waived) or ZERO)
        )
        return self.balance

    def _derive_snapshots(self):
        if not self.partner_name_snapshot and self.partner_id:
            self.partner_name_snapshot = str(self.partner)
        if not self.product_name_snapshot and self.product_id:
            self.product_name_snapshot = getattr(self.product, "name", "") or str(self.product)
        if not self.plan_name_snapshot and self.plan_id:
            self.plan_name_snapshot = getattr(self.plan, "name", "") or str(self.plan)

    def _derive_source_reference(self):
        if self.source_reference or not self.source_content_type_id or not self.source_object_id:
            return
        source_object = None
        try:
            source_object = self.source
        except Exception:
            source_object = None
        if source_object is None:
            return
        for candidate in ("proposal_number", "policy_number", "quote_number", "application_number", "quotation_number"):
            value = getattr(source_object, candidate, "") or ""
            if value:
                self.source_reference = str(value)
                return

    def _apply_grace_envelope(self):
        if self.due_date is None:
            return
        if self.grace_date is not None or self.lapse_date is not None:
            return
        premium_frequency = (self.premium_frequency or "").strip().upper()
        if not premium_frequency and self.source:
            premium_frequency = (getattr(self.source, "payment_frequency", "") or "").strip().upper()
        envelope = compute_grace_envelope(
            self.due_date,
            product=self.product,
            plan=self.plan,
            premium_frequency=premium_frequency,
        )
        self.grace_date = envelope.grace_date
        self.warning_date = envelope.warning_date
        self.pre_lapse_date = envelope.pre_lapse_date
        self.lapse_date = envelope.lapse_date

    def save(self, *args, **kwargs):
        if not self.status:
            self.status = default_commitment_status() or self.status
        self._derive_snapshots()
        self._derive_source_reference()
        self._apply_grace_envelope()
        self.recompute_balance()
        return super().save(*args, **kwargs)

    def clean(self):
        errors = {}

        if not self.commitment_number:
            errors["commitment_number"] = "Commitment number is required."
        if self.premium_amount is not None and self.premium_amount <= 0:
            errors["premium_amount"] = "Premium amount must be greater than zero."
        if (self.amount_paid or ZERO) < 0:
            errors["amount_paid"] = "Amount paid cannot be negative."
        if (self.amount_waived or ZERO) < 0:
            errors["amount_waived"] = "Amount waived cannot be negative."
        if self.installment_number is None or self.installment_number <= 0:
            errors["installment_number"] = "Installment number must be positive."
        if self.installment_count is None or self.installment_count <= 0:
            errors["installment_count"] = "Installment count must be positive."

        currency = (self.currency or "").strip().upper()
        if len(currency) != 3 or not currency.isalpha():
            errors["currency"] = "Currency must be a three-letter code."
        self.currency = currency

        status = (self.status or "").strip().upper()
        if status and not is_valid_commitment_status(status):
            errors["status"] = (
                f"Status '{status}' is not configured in the OL Commitment Status "
                "parameter catalog. Configure it under OL Parameters > Policy Setup "
                "> OL Commitment Statuses."
            )
        self.status = status
        self.premium_frequency = (self.premium_frequency or "").strip().upper()

        if self.product_id and self.plan_id:
            plan_product_id = getattr(getattr(self.plan, "product_version", None), "product_id", None)
            if plan_product_id and plan_product_id != self.product_id:
                errors["plan"] = "Plan must belong to the selected product."

        if self.source_content_type_id and self.source_object_id:
            model = self.source_content_type.model_class()
            if model is not None:
                allowed = _is_allowed_source_model(self.source_type, model)
                if not allowed:
                    errors["source"] = (
                        f"Source type '{self.source_type}' cannot reference model "
                        f"'{model._meta.app_label}.{model._meta.model_name}'."
                    )

        if errors:
            raise ValidationError(errors)

    def full_clean_ex(self):
        self.clean()
        return self


def _is_allowed_source_model(source_type, model):
    mapping = _SOURCE_MODEL_MAP.get(source_type, {})
    return model._meta.app_label in mapping and model._meta.model_name in mapping[model._meta.app_label]


class OLCommitmentAllocation(AuditedModel):
    """A receipt amount posted against a commitment; reversals link to originals."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    commitment = models.ForeignKey(
        OLCommitment,
        on_delete=models.PROTECT,
        related_name="allocations",
    )
    receipt_reference = models.CharField(max_length=120, db_index=True)
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    # Amount booked in the commitment's own currency (amount * exchange_rate);
    # equals ``amount`` for same-currency allocations.
    converted_amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0.00"))
    payment_mode = models.CharField(max_length=60, blank=True, default="")
    currency = models.CharField(max_length=3, default="TZS")
    exchange_rate = models.DecimalField(max_digits=12, decimal_places=6, default=Decimal("1.000000"))
    reason = models.TextField(blank=True, default="")
    reversal_of = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="reversal_allocations",
    )
    allocated_at = models.DateTimeField(default=timezone.now)
    allocated_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="allocated_ol_commitments",
    )
    source_channel = models.CharField(
        max_length=30,
        choices=CommitmentSourceChannel.choices,
        default=CommitmentSourceChannel.SYSTEM,
    )

    class Meta:
        db_table = "ol_commitments_allocation"
        ordering = ["-allocated_at", "-created_at"]
        verbose_name = "OL Commitment Allocation"
        verbose_name_plural = "OL Commitment Allocations"
        constraints = [
            models.CheckConstraint(
                check=Q(amount__gt=0),
                name="ol_commitment_allocation_amount_positive",
            ),
            models.CheckConstraint(
                check=Q(exchange_rate__gt=0),
                name="ol_commitment_allocation_rate_positive",
            ),
            models.CheckConstraint(
                check=Q(converted_amount__gte=0),
                name="ol_commitment_allocation_converted_nonnegative",
            ),
            models.UniqueConstraint(
                fields=["commitment", "receipt_reference"],
                condition=Q(reversal_of__isnull=True),
                name="ol_commitment_allocation_receipt_unique",
            ),
        ]
        indexes = [
            models.Index(fields=["receipt_reference"], name="ol_alloc_receipt_ref_idx"),
            models.Index(fields=["commitment", "allocated_at"], name="ol_alloc_commitment_idx"),
        ]

    def __str__(self):
        return f"{self.receipt_reference} -> {self.amount} {self.currency}"

    def clean(self):
        errors = {}
        if self.amount is not None and self.amount <= 0:
            errors["amount"] = "Allocation amount must be greater than zero."
        if (self.exchange_rate or ZERO) <= 0:
            errors["exchange_rate"] = "Exchange rate must be greater than zero."
        currency = (self.currency or "").strip().upper()
        if len(currency) != 3 or not currency.isalpha():
            errors["currency"] = "Currency must be a three-letter code."
        self.currency = currency
        if self.reversal_of_id and self.reversal_of_id == self.pk:
            errors["reversal_of"] = "An allocation cannot reverse itself."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if not self.receipt_reference:
            self.receipt_reference = f"MANUAL-{uuid.uuid4().hex[:12].upper()}"
        return super().save(*args, **kwargs)


class OLCommitmentNotificationLog(AuditedModel):
    """One dispatch attempt per matched Grace Period Notification Schedule row."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    commitment = models.ForeignKey(
        OLCommitment,
        on_delete=models.CASCADE,
        related_name="notification_logs",
    )
    event_type = models.CharField(max_length=30, choices=NotificationEventType.choices, db_index=True)
    dispatch_on = models.DateField(db_index=True)
    notification_channel = models.CharField(
        max_length=20, choices=NotificationChannel.choices, default=NotificationChannel.SYSTEM
    )
    recipient_type = models.CharField(
        max_length=20,
        choices=NotificationRecipientType.choices,
        default=NotificationRecipientType.POLICYHOLDER,
    )
    recipient_identifier = models.CharField(max_length=200, blank=True, default="")
    template_code = models.CharField(max_length=100, blank=True, default="")
    status = models.CharField(
        max_length=20,
        choices=NotificationDispatchStatus.choices,
        default=NotificationDispatchStatus.PENDING,
        db_index=True,
    )
    payload = models.JSONField(default=dict, blank=True)
    dispatched_at = models.DateTimeField(null=True, blank=True)
    source_channel = models.CharField(
        max_length=30,
        choices=CommitmentSourceChannel.choices,
        default=CommitmentSourceChannel.SYSTEM,
    )

    class Meta:
        db_table = "ol_commitments_notification_log"
        ordering = ["-dispatch_on", "-created_at"]
        verbose_name = "OL Commitment Notification"
        verbose_name_plural = "OL Commitment Notifications"
        constraints = [
            models.UniqueConstraint(
                fields=["commitment", "event_type", "dispatch_on", "notification_channel", "recipient_type"],
                name="ol_commitment_notification_unique",
            )
        ]
        indexes = [
            models.Index(
                fields=["commitment", "status", "dispatch_on"],
                name="ol_commitment_notify_state_idx",
            )
        ]

    def __str__(self):
        return f"{self.commitment.commitment_number}:{self.event_type}@{self.dispatch_on}"

    def clean(self):
        errors = {}
        if not self.commitment_id:
            errors["commitment"] = "Commitment is required."
        if not self.dispatch_on:
            errors["dispatch_on"] = "Dispatch date is required."
        if errors:
            raise ValidationError(errors)
