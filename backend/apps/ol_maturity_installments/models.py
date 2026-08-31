import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.common.models import AuditedModel, UUIDModel


class InstallmentSourceChannel(models.TextChoices):
    API = "API", "API"
    WEB = "WEB", "Web"
    PORTAL = "PORTAL", "Portal"
    ADMIN = "ADMIN", "Admin"
    SYSTEM = "SYSTEM", "System"
    BATCH = "BATCH", "Batch"


class InstallmentFrequency(models.TextChoices):
    SINGLE = "SINGLE", "Single"
    MONTHLY = "MONTHLY", "Monthly"
    QUARTERLY = "QUARTERLY", "Quarterly"
    HALF_YEARLY = "HALF_YEARLY", "Half yearly"
    ANNUAL = "ANNUAL", "Annual"


class InstallmentPlanStatus(models.TextChoices):
    CREATED = "CREATED", "Created"
    ACTIVE = "ACTIVE", "Active"
    COMPLETED = "COMPLETED", "Completed"
    TERMINATED = "TERMINATED", "Terminated"


class InstallmentItemStatus(models.TextChoices):
    SCHEDULED = "SCHEDULED", "Scheduled"
    PAYMENT_PENDING = "PAYMENT_PENDING", "Payment pending"
    PAID = "PAID", "Paid"
    MISSED = "MISSED", "Missed"
    WAIVED = "WAIVED", "Waived"


def generate_installment_plan_number():
    return f"MIP-{timezone.localdate():%Y%m%d}-{uuid.uuid4().hex[:10].upper()}"


class OLMaturityInstallmentPlan(UUIDModel, AuditedModel):
    """An auditable maturity installment schedule for one matured policy."""

    plan_number = models.CharField(max_length=45, unique=True, db_index=True, blank=True)
    policy_ref = models.ForeignKey(
        "ol_policies.Policy",
        on_delete=models.PROTECT,
        related_name="ol_maturity_installment_plans",
    )
    maturity_claim_ref = models.ForeignKey(
        "ol_policies.MaturityClaim",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ol_maturity_installment_plans",
    )
    partner = models.ForeignKey(
        "partners.Partner",
        on_delete=models.PROTECT,
        related_name="ol_maturity_installment_plans",
    )
    currency = models.CharField(max_length=3, default="TZS")
    total_maturity_value = models.DecimalField(max_digits=18, decimal_places=2)
    total_payable_amount = models.DecimalField(max_digits=18, decimal_places=2)
    installment_count = models.PositiveIntegerField()
    frequency = models.CharField(
        max_length=20,
        choices=InstallmentFrequency.choices,
        default=InstallmentFrequency.MONTHLY,
        db_index=True,
    )
    start_date = models.DateField(db_index=True)
    end_date = models.DateField()
    status = models.CharField(
        max_length=20,
        choices=InstallmentPlanStatus.choices,
        default=InstallmentPlanStatus.CREATED,
        db_index=True,
    )
    activated_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    terminated_at = models.DateTimeField(null=True, blank=True)
    activated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ol_maturity_installment_plans_activated",
    )
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ol_maturity_installment_plans_completed",
    )
    terminated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ol_maturity_installment_plans_terminated",
    )
    parameter_snapshot = models.JSONField(default=dict, blank=True)
    source_channel = models.CharField(
        max_length=20,
        choices=InstallmentSourceChannel.choices,
        default=InstallmentSourceChannel.API,
        db_index=True,
    )

    class Meta:
        db_table = "ol_maturity_installments_plan"
        ordering = ["-created_at", "plan_number"]
        indexes = [
            models.Index(fields=["policy_ref", "status"], name="ol_mip_policy_status_idx"),
            models.Index(fields=["status", "start_date"], name="ol_mip_status_date_idx"),
            models.Index(fields=["maturity_claim_ref"], name="ol_mip_maturity_claim_idx"),
        ]

    def __str__(self):
        return self.plan_number or "Unnumbered installment plan"

    def clean(self):
        errors = {}
        if self.start_date and self.end_date and self.end_date < self.start_date:
            errors["end_date"] = "End date cannot be before the start date."
        if self.total_maturity_value is not None and self.total_maturity_value < 0:
            errors["total_maturity_value"] = "Maturity value cannot be negative."
        if self.total_payable_amount is not None and self.total_payable_amount < 0:
            errors["total_payable_amount"] = "Total payable amount cannot be negative."
        if self.total_payable_amount is not None and self.total_maturity_value is not None:
            if self.total_payable_amount > self.total_maturity_value:
                errors["total_payable_amount"] = (
                    "Total payable amount cannot exceed the maturity value; a mismatch raises PLAN_CALCULATION_MISMATCH."
                )
        if self.installment_count is not None and self.installment_count < 1:
            errors["installment_count"] = "An installment plan must have at least one installment."
        if self.currency and (len(self.currency) != 3 or not self.currency.isalpha()):
            errors["currency"] = "Currency must be a three-letter code."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if not self.plan_number:
            self.plan_number = generate_installment_plan_number()
        super().save(*args, **kwargs)


class OLInstallmentItem(UUIDModel, AuditedModel):
    """A single maturity installment payment on a plan."""

    plan_ref = models.ForeignKey(
        OLMaturityInstallmentPlan,
        on_delete=models.CASCADE,
        related_name="items",
    )
    installment_number = models.PositiveIntegerField()
    due_date = models.DateField(db_index=True)
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=InstallmentItemStatus.choices,
        default=InstallmentItemStatus.SCHEDULED,
        db_index=True,
    )
    payment_requisition_ref = models.ForeignKey(
        "front_office.FORequisition",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ol_maturity_installment_items",
    )
    payment_reference = models.CharField(max_length=160, blank=True, default="")
    paid_date = models.DateField(null=True, blank=True)
    missed_date = models.DateField(null=True, blank=True)
    waived_date = models.DateField(null=True, blank=True)
    paid_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ol_maturity_installment_items_paid",
    )
    narration = models.TextField(blank=True, default="")

    class Meta:
        db_table = "ol_maturity_installments_item"
        ordering = ["plan_ref", "installment_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["plan_ref", "installment_number"],
                name="ol_mip_item_plan_number_uq",
            ),
        ]
        indexes = [
            models.Index(fields=["plan_ref", "status"], name="ol_mip_item_plan_status_idx"),
            models.Index(fields=["due_date", "status"], name="ol_mip_item_due_status_idx"),
        ]

    def __str__(self):
        return f"{self.plan_ref.plan_number}: installment {self.installment_number}"

    def clean(self):
        errors = {}
        if self.installment_number is not None and self.installment_number < 1:
            errors["installment_number"] = "Installment number must start at 1."
        if self.amount is not None and self.amount < 0:
            errors["amount"] = "Installment amount cannot be negative."
        if errors:
            raise ValidationError(errors)


class OLMaturityInstallmentConfig(UUIDModel, AuditedModel):
    """One-to-one snapshot of the calculation basis used for a plan."""

    plan_ref = models.OneToOneField(
        OLMaturityInstallmentPlan,
        on_delete=models.PROTECT,
        related_name="config",
    )
    calculation_basis = models.CharField(max_length=60, blank=True, default="")
    installment_rate_snapshot = models.JSONField(default=dict, blank=True)
    paid_up_rate_snapshot = models.JSONField(default=dict, blank=True)
    installment_charge_snapshot = models.JSONField(default=dict, blank=True)
    parameters_used = models.JSONField(default=list, blank=True)
    assumptions = models.JSONField(default=dict, blank=True)
    configured_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ol_maturity_installment_configs",
    )
    configured_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        db_table = "ol_maturity_installments_config"
        ordering = ["-configured_at"]
        indexes = [
            models.Index(fields=["calculation_basis"], name="ol_mip_config_basis_idx"),
        ]

    def __str__(self):
        return f"{self.plan_ref.plan_number}: {self.calculation_basis or 'Unspecified basis'}"
