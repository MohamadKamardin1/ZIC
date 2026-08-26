import uuid
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.common.models import AuditedModel

ZERO = Decimal("0.00")


class LoanStatus(models.TextChoices):
    REQUESTED = "REQUESTED", "Requested"
    APPROVED = "APPROVED", "Approved"
    DISBURSED = "DISBURSED", "Disbursed"
    ACTIVE = "ACTIVE", "Active"
    PARTIALLY_REPAID = "PARTIALLY_REPAID", "Partially repaid"
    SETTLED = "SETTLED", "Settled"
    DEFAULTED = "DEFAULTED", "Defaulted"
    OFFSET_ON_SURRENDER = "OFFSET_ON_SURRENDER", "Offset on surrender"
    OFFSET_ON_MATURITY = "OFFSET_ON_MATURITY", "Offset on maturity"
    OFFSET_ON_CLAIM = "OFFSET_ON_CLAIM", "Offset on claim"
    CLOSED = "CLOSED", "Closed"
    REJECTED = "REJECTED", "Rejected"


class LoanScheduleStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    PARTIALLY_PAID = "PARTIALLY_PAID", "Partially paid"
    PAID = "PAID", "Paid"
    OVERDUE = "OVERDUE", "Overdue"
    WAIVED = "WAIVED", "Waived"
    CANCELLED = "CANCELLED", "Cancelled"


class LoanOffsetSourceType(models.TextChoices):
    SURRENDER = "SURRENDER", "Surrender"
    MATURITY = "MATURITY", "Maturity"
    CLAIM = "CLAIM", "Claim"


class LoanSourceChannel(models.TextChoices):
    WEB = "WEB", "Web"
    API = "API", "API"
    ADMIN = "ADMIN", "Admin"
    SYSTEM = "SYSTEM", "System"
    IMPORT = "IMPORT", "Import"
    PORTAL = "PORTAL", "Portal"
    BATCH = "BATCH", "Batch"
    MANUAL = "MANUAL", "Manual"


class OLLoan(AuditedModel):
    """A policy-backed loan contract and its current financial position."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    loan_number = models.CharField(max_length=100, unique=True, db_index=True)
    policy_ref = models.ForeignKey(
        "ol_policies.Policy",
        on_delete=models.PROTECT,
        related_name="ol_loans",
    )
    partner = models.ForeignKey(
        "partners.Partner",
        on_delete=models.PROTECT,
        related_name="ol_loans",
    )
    currency = models.CharField(max_length=3, default="TZS")
    principal_amount = models.DecimalField(max_digits=18, decimal_places=2)
    disbursed_amount = models.DecimalField(max_digits=18, decimal_places=2, default=ZERO)
    interest_rate = models.DecimalField(max_digits=18, decimal_places=8)
    compounding_frequency = models.CharField(max_length=40)
    term_months = models.PositiveIntegerField()
    disbursement_date = models.DateField(null=True, blank=True)
    maturity_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=30, choices=LoanStatus.choices, default=LoanStatus.REQUESTED, db_index=True)
    total_repaid = models.DecimalField(max_digits=18, decimal_places=2, default=ZERO)
    outstanding_balance = models.DecimalField(max_digits=18, decimal_places=2, default=ZERO, db_index=True)
    approval_required = models.BooleanField(default=False, db_index=True)
    reason = models.TextField(blank=True, default="")
    source_channel = models.CharField(max_length=20, choices=LoanSourceChannel.choices, default=LoanSourceChannel.SYSTEM)
    idempotency_key = models.CharField(max_length=100, unique=True, null=True, blank=True, db_index=True)

    class Meta:
        db_table = "ol_loans_loan"
        ordering = ["-created_at", "loan_number"]
        verbose_name = "OL Loan"
        verbose_name_plural = "OL Loans"
        constraints = [
            models.CheckConstraint(check=Q(principal_amount__gt=0), name="ol_loan_principal_positive"),
            models.CheckConstraint(check=Q(disbursed_amount__gte=0), name="ol_loan_disbursed_nonnegative"),
            models.CheckConstraint(check=Q(interest_rate__gte=0), name="ol_loan_interest_nonnegative"),
            models.CheckConstraint(check=Q(term_months__gt=0), name="ol_loan_term_positive"),
            models.CheckConstraint(check=Q(total_repaid__gte=0), name="ol_loan_repaid_nonnegative"),
            models.CheckConstraint(check=Q(outstanding_balance__gte=0), name="ol_loan_outstanding_nonnegative"),
        ]
        indexes = [
            models.Index(fields=["policy_ref", "status"], name="ol_loan_policy_status_idx"),
            models.Index(fields=["partner", "status"], name="ol_loan_partner_status_idx"),
            models.Index(fields=["status", "maturity_date"], name="ol_loan_status_maturity_idx"),
            models.Index(fields=["currency", "status"], name="ol_loan_currency_status_idx"),
        ]

    def __str__(self):
        return self.loan_number

    def clean(self):
        errors = {}
        if self.principal_amount is not None and self.principal_amount <= 0:
            errors["principal_amount"] = "Principal amount must be greater than zero."
        if (self.disbursed_amount or ZERO) < 0:
            errors["disbursed_amount"] = "Disbursed amount cannot be negative."
        if self.interest_rate is not None and self.interest_rate < 0:
            errors["interest_rate"] = "Interest rate cannot be negative."
        if not self.compounding_frequency:
            errors["compounding_frequency"] = "Compounding frequency is required."
        if not self.term_months or self.term_months <= 0:
            errors["term_months"] = "Term must be greater than zero months."
        currency = (self.currency or "").strip().upper()
        if len(currency) != 3 or not currency.isalpha():
            errors["currency"] = "Currency must be a three-letter code."
        else:
            self.currency = currency
        if self.maturity_date and self.disbursement_date and self.maturity_date < self.disbursement_date:
            errors["maturity_date"] = "Maturity date cannot be before disbursement date."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if not self.loan_number:
            self.loan_number = f"LOAN-{timezone.localdate():%Y%m%d}-{uuid.uuid4().hex[:10].upper()}"
        self.currency = (self.currency or "TZS").strip().upper()
        return super().save(*args, **kwargs)


class OLLoanSchedule(AuditedModel):
    """One contractual loan repayment installment."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    loan = models.ForeignKey(OLLoan, on_delete=models.PROTECT, related_name="schedules")
    installment_number = models.PositiveIntegerField()
    due_date = models.DateField(db_index=True)
    principal_due = models.DecimalField(max_digits=18, decimal_places=2, default=ZERO)
    interest_due = models.DecimalField(max_digits=18, decimal_places=2, default=ZERO)
    penalty_due = models.DecimalField(max_digits=18, decimal_places=2, default=ZERO)
    amount_paid = models.DecimalField(max_digits=18, decimal_places=2, default=ZERO)
    balance = models.DecimalField(max_digits=18, decimal_places=2, default=ZERO)
    status = models.CharField(max_length=30, choices=LoanScheduleStatus.choices, default=LoanScheduleStatus.PENDING, db_index=True)
    reason = models.TextField(blank=True, default="")
    source_channel = models.CharField(max_length=20, choices=LoanSourceChannel.choices, default=LoanSourceChannel.SYSTEM)

    class Meta:
        db_table = "ol_loans_schedule"
        ordering = ["installment_number"]
        constraints = [
            models.UniqueConstraint(fields=["loan", "installment_number"], name="ol_loan_schedule_installment_unique"),
            models.CheckConstraint(check=Q(installment_number__gt=0), name="ol_loan_schedule_number_positive"),
            models.CheckConstraint(check=Q(principal_due__gte=0), name="ol_loan_schedule_principal_nonnegative"),
            models.CheckConstraint(check=Q(interest_due__gte=0), name="ol_loan_schedule_interest_nonnegative"),
            models.CheckConstraint(check=Q(penalty_due__gte=0), name="ol_loan_schedule_penalty_nonnegative"),
            models.CheckConstraint(check=Q(amount_paid__gte=0), name="ol_loan_schedule_paid_nonnegative"),
            models.CheckConstraint(check=Q(balance__gte=0), name="ol_loan_schedule_balance_nonnegative"),
        ]
        indexes = [
            models.Index(fields=["loan", "due_date"], name="ol_loan_schedule_due_idx"),
            models.Index(fields=["status", "due_date"], name="ol_loan_sched_status_due_idx"),
        ]

    def __str__(self):
        return f"{self.loan.loan_number} installment {self.installment_number}"

    def clean(self):
        errors = {}
        for field in ("principal_due", "interest_due", "penalty_due", "amount_paid", "balance"):
            if getattr(self, field) is not None and getattr(self, field) < 0:
                errors[field] = f"{field.replace('_', ' ').capitalize()} cannot be negative."
        if self.installment_number is not None and self.installment_number <= 0:
            errors["installment_number"] = "Installment number must be positive."
        if errors:
            raise ValidationError(errors)


class OLLoanRepayment(AuditedModel):
    """One repayment receipt and its immutable allocation breakdown."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    loan = models.ForeignKey(OLLoan, on_delete=models.PROTECT, related_name="repayments")
    receipt_ref = models.CharField(max_length=120, blank=True, default="", db_index=True)
    idempotency_key = models.CharField(max_length=100, unique=True, null=True, blank=True, db_index=True)
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    currency = models.CharField(max_length=3, default="TZS")
    exchange_rate = models.DecimalField(max_digits=18, decimal_places=8, default=Decimal("1.00000000"))
    allocation_breakdown = models.JSONField(default=dict, blank=True)
    reason = models.TextField(blank=True, default="")
    source_channel = models.CharField(max_length=20, choices=LoanSourceChannel.choices, default=LoanSourceChannel.SYSTEM)

    class Meta:
        db_table = "ol_loans_repayment"
        ordering = ["-created_at", "-id"]
        constraints = [
            models.CheckConstraint(check=Q(amount__gt=0), name="ol_loan_repayment_amount_positive"),
            models.CheckConstraint(check=Q(exchange_rate__gt=0), name="ol_loan_repayment_rate_positive"),
        ]
        indexes = [
            models.Index(fields=["loan", "created_at"], name="ol_loan_repayment_created_idx"),
            models.Index(fields=["receipt_ref"], name="ol_loan_repayment_receipt_idx"),
        ]

    def __str__(self):
        return f"{self.loan.loan_number} repayment {self.amount} {self.currency}"

    def clean(self):
        errors = {}
        if self.amount is not None and self.amount <= 0:
            errors["amount"] = "Repayment amount must be greater than zero."
        if self.exchange_rate is not None and self.exchange_rate <= 0:
            errors["exchange_rate"] = "Exchange rate must be greater than zero."
        currency = (self.currency or "").strip().upper()
        if len(currency) != 3 or not currency.isalpha():
            errors["currency"] = "Currency must be a three-letter code."
        else:
            self.currency = currency
        if errors:
            raise ValidationError(errors)


class OLLoanInterestAccrual(AuditedModel):
    """An idempotent interest and penalty calculation for one loan period."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    loan = models.ForeignKey(OLLoan, on_delete=models.PROTECT, related_name="interest_accruals")
    period_start = models.DateField()
    period_end = models.DateField()
    principal_base = models.DecimalField(max_digits=18, decimal_places=2)
    interest_amount = models.DecimalField(max_digits=18, decimal_places=2, default=ZERO)
    penalty_amount = models.DecimalField(max_digits=18, decimal_places=2, default=ZERO)
    cumulative_interest = models.DecimalField(max_digits=18, decimal_places=2, default=ZERO)
    source_channel = models.CharField(max_length=20, choices=LoanSourceChannel.choices, default=LoanSourceChannel.SYSTEM)

    class Meta:
        db_table = "ol_loans_interest_accrual"
        ordering = ["-period_end", "-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["loan", "period_start", "period_end"], name="ol_loan_accrual_period_unique"),
            models.CheckConstraint(check=Q(principal_base__gte=0), name="ol_loan_accrual_base_nonnegative"),
            models.CheckConstraint(check=Q(interest_amount__gte=0), name="ol_loan_accrual_interest_nonnegative"),
            models.CheckConstraint(check=Q(penalty_amount__gte=0), name="ol_loan_accrual_penalty_nonnegative"),
            models.CheckConstraint(check=Q(cumulative_interest__gte=0), name="ol_loan_accrual_cumulative_nonnegative"),
        ]
        indexes = [
            models.Index(fields=["loan", "period_end"], name="ol_loan_accrual_period_idx"),
        ]

    def __str__(self):
        return f"{self.loan.loan_number} accrual {self.period_start} to {self.period_end}"

    def clean(self):
        errors = {}
        if self.period_start and self.period_end and self.period_end < self.period_start:
            errors["period_end"] = "Accrual period end cannot be before its start."
        for field in ("principal_base", "interest_amount", "penalty_amount", "cumulative_interest"):
            if getattr(self, field) is not None and getattr(self, field) < 0:
                errors[field] = f"{field.replace('_', ' ').capitalize()} cannot be negative."
        if errors:
            raise ValidationError(errors)


class OLLoanOffset(AuditedModel):
    """A loan deduction from surrender, maturity, or claim proceeds."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    loan = models.ForeignKey(OLLoan, on_delete=models.PROTECT, related_name="offsets")
    source_type = models.CharField(max_length=20, choices=LoanOffsetSourceType.choices, db_index=True)
    source_id = models.CharField(max_length=120, db_index=True)
    offset_amount = models.DecimalField(max_digits=18, decimal_places=2)
    remaining_payout = models.DecimalField(max_digits=18, decimal_places=2)
    reason = models.TextField(blank=True, default="")
    source_channel = models.CharField(max_length=20, choices=LoanSourceChannel.choices, default=LoanSourceChannel.SYSTEM)

    class Meta:
        db_table = "ol_loans_offset"
        ordering = ["-created_at", "-id"]
        constraints = [
            models.UniqueConstraint(fields=["loan", "source_type", "source_id"], name="ol_loan_offset_source_unique"),
            models.CheckConstraint(check=Q(offset_amount__gt=0), name="ol_loan_offset_amount_positive"),
            models.CheckConstraint(check=Q(remaining_payout__gte=0), name="ol_loan_offset_payout_nonnegative"),
        ]
        indexes = [
            models.Index(fields=["source_type", "source_id"], name="ol_loan_offset_source_idx"),
            models.Index(fields=["loan", "created_at"], name="ol_loan_offset_loan_idx"),
        ]

    def __str__(self):
        return f"{self.loan.loan_number} offset {self.offset_amount} ({self.source_type})"

    def clean(self):
        errors = {}
        if self.offset_amount is not None and self.offset_amount <= 0:
            errors["offset_amount"] = "Offset amount must be greater than zero."
        if self.remaining_payout is not None and self.remaining_payout < 0:
            errors["remaining_payout"] = "Remaining payout cannot be negative."
        if not self.source_id:
            errors["source_id"] = "Offset source reference is required."
        if errors:
            raise ValidationError(errors)
