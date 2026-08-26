"""Front Office Receipts — configuration / reference-data models.

Prompt 2 scope: every configurable aspect of a receipt (numbering, company bank
accounts, payment-mode rules) lives here as editable, seeded reference data.
The module never hardcodes a branch, currency, payment mode, status, numbering
format, or bank account into code.
"""

import re
import uuid

from django.core.exceptions import ValidationError
from django.db import models

from apps.common.models import AuditedModel


class ResetFrequency(models.TextChoices):
    NEVER = "NEVER", "Never"
    YEARLY = "YEARLY", "Yearly"
    MONTHLY = "MONTHLY", "Monthly"
    DAILY = "DAILY", "Daily"


def mask_account_number(account_number):
    """Mask a bank account number, revealing only the last four digits."""
    digits = re.sub(r"\D", "", (account_number or "")).strip()
    if not digits:
        return "****"
    if len(digits) <= 4:
        return "*" * len(digits)
    return "*" * (len(digits) - 4) + digits[-4:]


class ReceiptNumberingRule(AuditedModel):
    """Branch-aware, concurrency-safe receipt numbering rule."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True, db_index=True)
    name = models.CharField(max_length=200)
    branch = models.ForeignKey(
        "partner_onboarding.Branch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="receipt_numbering_rules",
        help_text="Branch-specific rule; empty means the default rule.",
    )
    prefix = models.CharField(max_length=20)
    sequence_padding = models.PositiveSmallIntegerField(default=6)
    next_sequence = models.PositiveBigIntegerField(default=1)
    reset_frequency = models.CharField(
        max_length=20, choices=ResetFrequency.choices, default=ResetFrequency.YEARLY
    )
    last_reset_at = models.DateTimeField(null=True, blank=True, help_text="Used to detect period rollover for the reset frequency.")
    effective_from = models.DateField(null=True, blank=True)
    effective_to = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "front_office_receipt_numbering_rule"
        verbose_name = "Receipt Numbering Rule"
        verbose_name_plural = "Receipt Numbering Rules"
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} ({self.prefix})"

    def clean(self):
        errors = {}
        if not self.code.strip():
            errors["code"] = "Code is required."
        if not self.prefix.strip():
            errors["prefix"] = "Prefix is required."
        if self.sequence_padding is not None and self.sequence_padding < 1:
            errors["sequence_padding"] = "Sequence padding must be at least 1."
        if self.effective_from and self.effective_to and self.effective_to < self.effective_from:
            errors["effective_to"] = "Effective to cannot be before effective from."
        if errors:
            raise ValidationError(errors)


class CompanyBankAccount(AuditedModel):
    """A ZIC company bank account that receipts are deposited into."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True, db_index=True)
    bank_name = models.CharField(max_length=200)
    account_name = models.CharField(max_length=255)
    account_number = models.CharField(max_length=60)
    currency = models.CharField(max_length=3, default="TZS")
    branch = models.ForeignKey(
        "partner_onboarding.Branch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="company_bank_accounts",
    )
    is_default = models.BooleanField(default=False, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "front_office_company_bank_account"
        verbose_name = "Company Bank Account"
        verbose_name_plural = "Company Bank Accounts"
        ordering = ["code"]

    def __str__(self):
        return f"{self.bank_name} - {self.account_name} ({self.currency})"

    @property
    def masked_account_number(self):
        return mask_account_number(self.account_number)

    def clean(self):
        errors = {}
        if not self.code.strip():
            errors["code"] = "Code is required."
        if not self.account_number.strip():
            errors["account_number"] = "Account number is required."
        currency = (self.currency or "").strip().upper()
        if len(currency) != 3 or not currency.isalpha():
            errors["currency"] = "Currency must be a three-letter code."
        self.currency = currency
        if errors:
            raise ValidationError(errors)


class ReceiptPaymentModeRule(AuditedModel):
    """Payment-mode acceptance rule: requirements and allowed instruments."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment_mode = models.CharField(max_length=30, unique=True, db_index=True)
    requires_reference = models.BooleanField(default=False)
    requires_bank_account = models.BooleanField(default=False)
    allows_cash = models.BooleanField(default=False)
    allows_card = models.BooleanField(default=False)
    allows_mobile_money = models.BooleanField(default=False)
    allows_bank_transfer = models.BooleanField(default=False)
    allows_cheque = models.BooleanField(default=False)
    min_amount = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    max_amount = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "front_office_receipt_payment_mode_rule"
        verbose_name = "Receipt Payment Mode Rule"
        verbose_name_plural = "Receipt Payment Mode Rules"
        ordering = ["payment_mode"]

    def __str__(self):
        return self.payment_mode

    def clean(self):
        errors = {}
        mode = (self.payment_mode or "").strip().upper()
        if not mode:
            errors["payment_mode"] = "Payment mode is required."
        self.payment_mode = mode
        if self.min_amount is not None and self.min_amount < 0:
            errors["min_amount"] = "Minimum amount cannot be negative."
        if self.max_amount is not None and self.max_amount < 0:
            errors["max_amount"] = "Maximum amount cannot be negative."
        if (
            self.min_amount is not None
            and self.max_amount is not None
            and self.max_amount < self.min_amount
        ):
            errors["max_amount"] = "Maximum amount cannot be less than the minimum amount."
        if not any(
            (
                self.allows_cash,
                self.allows_card,
                self.allows_mobile_money,
                self.allows_bank_transfer,
                self.allows_cheque,
            )
        ):
            errors["__all__"] = (
                "At least one instrument must be allowed (cash, card, mobile money, bank transfer, or cheque)."
            )
        if errors:
            raise ValidationError(errors)
