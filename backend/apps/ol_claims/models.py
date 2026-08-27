import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.common.models import AuditedModel, UUIDModel


CLAIM_DOC_REF = "docs/OL_CLAIMS_DESIGN.md"


class ClaimStatus(models.TextChoices):
    REGISTERED = "REGISTERED", "Registered"
    PENDING_MEDICAL = "PENDING_MEDICAL", "Pending medical review"
    ASSESSMENT = "ASSESSMENT", "Assessment"
    ASSESSED = "ASSESSED", "Assessed"
    REQUISITION = "REQUISITION", "Requisition"
    REQUISITIONED = "REQUISITIONED", "Requisitioned"
    APPROVED = "APPROVED", "Approved"
    SETTLED = "SETTLED", "Settled"
    REJECTED = "REJECTED", "Rejected"
    CANCELLED = "CANCELLED", "Cancelled"


class ClaimantType(models.TextChoices):
    POLICYHOLDER = "POLICYHOLDER", "Policyholder"
    INSURED = "INSURED", "Insured"
    DEPENDENT = "DEPENDENT", "Dependent"


class ClaimSourceChannel(models.TextChoices):
    API = "API", "API"
    WEB = "WEB", "Web"
    PORTAL = "PORTAL", "Portal"
    ADMIN = "ADMIN", "Admin"
    SYSTEM = "SYSTEM", "System"
    BATCH = "BATCH", "Batch"


class ClaimMedicalStatus(models.TextChoices):
    NONE = "NONE", "No medical review"
    PENDING = "PENDING", "Pending medical review"
    CLEARED = "CLEARED", "Medical review cleared"
    REJECTED = "REJECTED", "Medical review rejected"
    LOADING = "LOADING", "Medical loading applied"


class ClaimRequisitionStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    REQUISITIONED = "REQUISITIONED", "Requisitioned"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"
    PAID = "PAID", "Paid"
    CANCELLED = "CANCELLED", "Cancelled"


def generate_claim_number():
    return f"CLM-{timezone.localdate():%Y%m%d}-{uuid.uuid4().hex[:10].upper()}"


def generate_requisition_number():
    return f"CLM-REQ-{timezone.localdate():%Y%m%d}-{uuid.uuid4().hex[:10].upper()}"


class OLClaim(UUIDModel, AuditedModel):
    """An auditable Ordinary Life claim and its policy-level lifecycle state."""

    claim_number = models.CharField(max_length=45, unique=True, db_index=True, blank=True)
    idempotency_key = models.CharField(max_length=64, unique=True, null=True, blank=True, db_index=True)
    idempotency_fingerprint = models.JSONField(default=dict, blank=True)
    policy_ref = models.ForeignKey(
        "ol_policies.Policy",
        on_delete=models.PROTECT,
        related_name="ol_claims",
    )
    claim_type = models.CharField(max_length=80, db_index=True)
    claimant_ref = models.ForeignKey(
        "OLClaimant",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="referenced_claims",
    )
    claim_date = models.DateField(default=timezone.localdate, db_index=True)
    admitted_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=30,
        choices=ClaimStatus.choices,
        default=ClaimStatus.REGISTERED,
        db_index=True,
    )
    cause_of_claim = models.CharField(max_length=255, blank=True, default="")
    description = models.TextField(blank=True, default="")
    assessment_notes = models.TextField(blank=True, default="")
    fraud_flag = models.BooleanField(default=False, db_index=True)
    fraud_flag_reason = models.TextField(blank=True, default="")
    waiver_of_premium_days = models.PositiveIntegerField(default=0)
    waiver_of_premium_until = models.DateField(null=True, blank=True)
    waiver_of_premium_applied = models.BooleanField(default=False)
    medical_status = models.CharField(
        max_length=20,
        choices=ClaimMedicalStatus.choices,
        default=ClaimMedicalStatus.NONE,
        db_index=True,
    )
    medical_result = models.CharField(max_length=30, blank=True, default="")
    medical_reason = models.TextField(blank=True, default="")
    medical_requested_at = models.DateTimeField(null=True, blank=True)
    medical_reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ol_claims_medical_reviewed",
    )
    medical_reviewed_at = models.DateTimeField(null=True, blank=True)
    medical_loading_factor = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)
    registered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ol_claims_registered",
    )
    admitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ol_claims_admitted",
    )
    settled_date = models.DateField(null=True, blank=True)
    source_channel = models.CharField(
        max_length=20,
        choices=ClaimSourceChannel.choices,
        default=ClaimSourceChannel.API,
        db_index=True,
    )

    class Meta:
        db_table = "ol_claims_claim"
        ordering = ["-created_at", "claim_number"]
        indexes = [
            models.Index(fields=["policy_ref", "status"], name="ol_claim_policy_status_idx"),
            models.Index(fields=["claim_type", "claim_date"], name="ol_claim_type_date_idx"),
            models.Index(fields=["status", "fraud_flag"], name="ol_claim_status_fraud_idx"),
            models.Index(fields=["medical_status", "status"], name="ol_claim_medical_status_idx"),
        ]

    def __str__(self):
        return self.claim_number or "Unnumbered claim"

    def clean(self):
        errors = {}
        if self.claim_date and self.admitted_date and self.admitted_date < self.claim_date:
            errors["admitted_date"] = "Admitted date cannot be before the claim date."
        if self.settled_date and self.claim_date and self.settled_date < self.claim_date:
            errors["settled_date"] = "Settled date cannot be before the claim date."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if not self.claim_number:
            self.claim_number = generate_claim_number()
        super().save(*args, **kwargs)


class OLClaimant(UUIDModel, AuditedModel):
    claim = models.ForeignKey(OLClaim, on_delete=models.CASCADE, related_name="claimants")
    claimant_type = models.CharField(max_length=20, choices=ClaimantType.choices, db_index=True)
    relationship = models.CharField(max_length=80, blank=True, default="")
    name = models.CharField(max_length=255)
    identity_number = models.CharField(max_length=100, blank=True, default="")
    age = models.PositiveIntegerField(null=True, blank=True)
    gender = models.CharField(max_length=30, blank=True, default="")
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "ol_claims_claimant"
        ordering = ["name", "created_at"]
        indexes = [
            models.Index(fields=["claim", "claimant_type"], name="ol_claimant_claim_type_idx"),
            models.Index(fields=["identity_number"], name="ol_claimant_identity_idx"),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_claimant_type_display()})"

    def clean(self):
        if self.age is not None and self.age > 150:
            raise ValidationError({"age": "Claimant age must be 150 years or less."})


class OLClaimItem(UUIDModel, AuditedModel):
    claim = models.ForeignKey(OLClaim, on_delete=models.CASCADE, related_name="items")
    benefit_type = models.CharField(max_length=100, db_index=True)
    sum_assured = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    calculated_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    approved_amount = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    adjustment_reason = models.TextField(blank=True, default="")

    class Meta:
        db_table = "ol_claims_claim_item"
        ordering = ["benefit_type", "created_at"]
        indexes = [
            models.Index(fields=["claim", "benefit_type"], name="ol_claim_item_benefit_idx"),
        ]

    def __str__(self):
        return f"{self.claim.claim_number}: {self.benefit_type}"

    def clean(self):
        errors = {}
        if self.sum_assured is not None and self.sum_assured < 0:
            errors["sum_assured"] = "Sum assured cannot be negative."
        if self.calculated_amount is not None and self.calculated_amount < 0:
            errors["calculated_amount"] = "Calculated amount cannot be negative."
        if self.approved_amount is not None:
            if self.approved_amount < 0:
                errors["approved_amount"] = "Approved amount cannot be negative."
            elif self.calculated_amount is not None and self.approved_amount > self.calculated_amount:
                errors["approved_amount"] = "Approved amount cannot exceed calculated amount."
        if errors:
            raise ValidationError(errors)


class OLClaimDocument(UUIDModel, AuditedModel):
    claim = models.ForeignKey(OLClaim, on_delete=models.CASCADE, related_name="documents")
    document_type = models.CharField(max_length=100, db_index=True)
    file_reference = models.CharField(max_length=500)
    mandatory_flag = models.BooleanField(default=False, db_index=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ol_claim_documents_uploaded",
    )
    upload_date = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        db_table = "ol_claims_claim_document"
        ordering = ["document_type", "-upload_date"]
        indexes = [
            models.Index(fields=["claim", "mandatory_flag"], name="ol_claim_doc_mandatory_idx"),
        ]

    def __str__(self):
        return f"{self.claim.claim_number}: {self.document_type}"


class OLClaimFileNote(UUIDModel, AuditedModel):
    claim = models.ForeignKey(OLClaim, on_delete=models.CASCADE, related_name="file_notes")
    note_text = models.TextField()

    class Meta:
        db_table = "ol_claims_claim_file_note"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["claim", "created_at"], name="ol_claim_note_created_idx"),
        ]

    def __str__(self):
        return f"{self.claim.claim_number}: note"


class OLClaimRequisition(UUIDModel, AuditedModel):
    claim = models.OneToOneField(OLClaim, on_delete=models.PROTECT, related_name="requisition")
    requisition_number = models.CharField(max_length=55, unique=True, db_index=True, blank=True)
    amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    bank_details_json = models.JSONField(default=dict, blank=True)
    status = models.CharField(
        max_length=25,
        choices=ClaimRequisitionStatus.choices,
        default=ClaimRequisitionStatus.DRAFT,
        db_index=True,
    )

    class Meta:
        db_table = "ol_claims_claim_requisition"
        ordering = ["-created_at", "requisition_number"]
        indexes = [
            models.Index(fields=["claim", "status"], name="ol_claim_req_status_idx"),
        ]

    def __str__(self):
        return self.requisition_number or "Unnumbered requisition"

    def clean(self):
        if self.amount is not None and self.amount < 0:
            raise ValidationError({"amount": "Requisition amount cannot be negative."})

    def save(self, *args, **kwargs):
        if not self.requisition_number:
            self.requisition_number = generate_requisition_number()
        super().save(*args, **kwargs)


class ClaimLoanOffsetStatus(models.TextChoices):
    APPLIED = "APPLIED", "Applied"
    REVERSED = "REVERSED", "Reversed"


class OLClaimLoanOffset(UUIDModel, AuditedModel):
    """Immutable financial evidence linking a claim payout to a policy-loan offset."""

    claim = models.OneToOneField(OLClaim, on_delete=models.PROTECT, related_name="loan_offset")
    loan = models.ForeignKey(
        "ol_policies.PolicyLoan",
        on_delete=models.PROTECT,
        related_name="claim_offsets",
    )
    gross_amount = models.DecimalField(max_digits=18, decimal_places=2)
    offset_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    net_payout = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=ClaimLoanOffsetStatus.choices, default=ClaimLoanOffsetStatus.APPLIED, db_index=True)
    applied_at = models.DateTimeField(default=timezone.now, db_index=True)
    reason = models.TextField(blank=True, default="")
    loan_breakdown = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = "ol_claims_loan_offset"
        ordering = ["-applied_at"]
        indexes = [
            models.Index(fields=["loan", "status"], name="ol_claim_offset_loan_idx"),
            models.Index(fields=["claim", "applied_at"], name="ol_claim_offset_claim_idx"),
        ]

    def __str__(self):
        return f"{self.claim.claim_number}: {self.loan.loan_number}"

    def clean(self):
        errors = {}
        if self.gross_amount < 0:
            errors["gross_amount"] = "Gross claim amount cannot be negative."
        if self.offset_amount < 0:
            errors["offset_amount"] = "Loan offset cannot be negative."
        if self.net_payout < 0:
            errors["net_payout"] = "Net payout cannot be negative."
        if self.offset_amount > self.gross_amount:
            errors["offset_amount"] = "Loan offset cannot exceed gross claim amount."
        if self.net_payout != self.gross_amount - self.offset_amount:
            errors["net_payout"] = "Net payout must equal gross claim amount less loan offset."
        if errors:
            raise ValidationError(errors)
