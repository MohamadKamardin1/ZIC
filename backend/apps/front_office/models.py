import uuid
from django.db import models

class FOReceipt(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    receipt_number = models.CharField(max_length=50, unique=True)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    payment_method = models.CharField(max_length=50)
    payment_date = models.DateField()
    reference = models.CharField(max_length=100, blank=True, null=True, help_text="e.g. Policy Number or Proposal ID")
    status = models.CharField(max_length=50, default="COMPLETED")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "fo_receipt"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.receipt_number} - {self.amount}"


class FOCommission(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agent_id = models.CharField(max_length=50, help_text="Agent identifier")
    policy_reference = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    status = models.CharField(max_length=50, default="PENDING")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "fo_commission"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Comm: {self.agent_id} - {self.amount}"


class FOCommissionStatement(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agent_id = models.CharField(max_length=50)
    period_start = models.DateField()
    period_end = models.DateField()
    total_amount = models.DecimalField(max_digits=15, decimal_places=2)
    status = models.CharField(max_length=50, default="DRAFT")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "fo_commission_statement"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Stmt {self.agent_id} ({self.period_start} to {self.period_end})"


class FORequisition(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    requisition_number = models.CharField(max_length=50, unique=True)
    department = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    reason = models.TextField()
    status = models.CharField(max_length=50, default="PENDING")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "fo_requisition"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.requisition_number} - {self.amount}"


class FOPayment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment_number = models.CharField(max_length=50, unique=True)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    payment_method = models.CharField(max_length=50)
    payment_date = models.DateField()
    recipient = models.CharField(max_length=200)
    status = models.CharField(max_length=50, default="COMPLETED")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "fo_payment"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.payment_number} to {self.recipient}"


class FOParameter(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    key = models.CharField(max_length=100, unique=True)
    value = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "fo_parameter"
        ordering = ["key"]

    def __str__(self):
        return f"{self.key}: {self.value}"


# Front Office Receipts bounded context (see apps.front_office.receipts).
from apps.front_office.receipts.models import (  # noqa: E402,F401
    Receipt,
    ReceiptAllocation,
    ReceiptDocument,
    ReceiptReversal,
    ReceiptStatusHistory,
)
from apps.front_office.receipts.config_models import (  # noqa: E402,F401
    CompanyBankAccount,
    ReceiptNumberingRule,
    ReceiptPaymentModeRule,
)
