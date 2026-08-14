import uuid
import logging

from django.db import models
from django.conf import settings
from django.utils import timezone

from apps.partners.models import (
    IDENTIFICATION_TYPE_CHOICES,
    TITLE_CHOICES,
    GENDER_CHOICES,
    MARITAL_STATUS_CHOICES,
    POLITICAL_RISK_CHOICES,
    AML_RISK_CHOICES,
    INDUSTRY_CHOICES,
    NATIONALITY_CHOICES,
    PartnerTypeFieldConfiguration,
)

logger = logging.getLogger(__name__)


APPLICATION_STATUS_CHOICES = [
    ("ACTIVE", "Active"),
    ("DRAFT", "Draft"),
    ("SUBMITTED", "Submitted"),
    ("UNDER_REVIEW", "Under Review"),
    ("PENDING_DOCUMENTS", "Pending Documents"),
    ("COMPLIANCE_CHECK", "Compliance Check"),
    ("APPROVED", "Approved"),
    ("CONVERTED", "Converted to Partner"),
    ("REJECTED", "Rejected"),
    ("SUSPENDED", "Suspended"),
]

PARTNER_TYPE_CHOICES = [
    ("INDIVIDUAL", "Individual"),
    ("CORPORATE", "Corporate"),
]

DOCUMENT_TYPE_CHOICES = [
    ("NID", "National ID"),
    ("PASSPORT", "Passport"),
    ("ZAN_ID", "Zanzibar ID"),
    ("DRIVING_LICENSE", "Driving License"),
    ("TIN_CERTIFICATE", "TIN Certificate"),
    ("VOTER_ID", "Voter ID"),
    ("RESIDENT_PERMIT", "Resident Permit"),
    ("MILITARY_ID", "Military ID"),
    ("INCORPORATION_CERT", "Certificate of Incorporation"),
    ("MEMORANDUM", "Memorandum of Association"),
    ("BOARD_RESOLUTION", "Board Resolution"),
    ("OTHER", "Other"),
]

TASK_TYPE_CHOICES = [
    ("DOCUMENT_REQUEST", "Document Request"),
    ("COMPLIANCE_CHECK", "Compliance Check"),
    ("REVIEW", "Review"),
    ("APPROVAL", "Approval"),
    ("OTHER", "Other"),
]

TASK_STATUS_CHOICES = [
    ("PENDING", "Pending"),
    ("IN_PROGRESS", "In Progress"),
    ("COMPLETED", "Completed"),
    ("CANCELLED", "Cancelled"),
]

TASK_PRIORITY_CHOICES = [
    ("LOW", "Low"),
    ("MEDIUM", "Medium"),
    ("HIGH", "High"),
    ("URGENT", "Urgent"),
]


class PartnerApplication(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application_number = models.CharField(max_length=50, unique=True, db_index=True)
    partner_type = models.CharField(max_length=20, choices=PARTNER_TYPE_CHOICES)
    status = models.CharField(max_length=30, choices=APPLICATION_STATUS_CHOICES, default="ACTIVE")

    identification_type = models.CharField(max_length=30, choices=IDENTIFICATION_TYPE_CHOICES, blank=True)
    identification_number = models.CharField(max_length=100, blank=True)
    title = models.CharField(max_length=10, choices=TITLE_CHOICES, blank=True)
    first_name = models.CharField(max_length=100, blank=True)
    other_name = models.CharField(max_length=100, blank=True)
    surname = models.CharField(max_length=100, blank=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    marital_status = models.CharField(max_length=20, choices=MARITAL_STATUS_CHOICES, blank=True)
    occupation = models.CharField(max_length=200, blank=True)
    nationality = models.CharField(max_length=100, choices=NATIONALITY_CHOICES, blank=True)

    company_name = models.CharField(max_length=255, blank=True)
    tin_number = models.CharField(max_length=50, blank=True)
    incorporation_date = models.DateField(null=True, blank=True)
    company_incorporation = models.CharField(max_length=200, blank=True)
    industry = models.CharField(max_length=100, choices=INDUSTRY_CHOICES, blank=True)
    contact_person = models.CharField(max_length=200, blank=True)
    contact_person_phone = models.CharField(max_length=20, blank=True)
    contact_person_email = models.EmailField(blank=True)
    physical_address = models.TextField(blank=True)
    postal_address = models.TextField(blank=True)

    email = models.EmailField()
    telephone_number = models.CharField(max_length=20, blank=True)
    mobile_number = models.CharField(max_length=20)
    political_risk = models.CharField(max_length=20, choices=POLITICAL_RISK_CHOICES, default="LOW")
    aml_risk = models.CharField(max_length=20, choices=AML_RISK_CHOICES, default="LOW")

    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="submitted_applications",
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_applications",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approved_applications",
    )
    rejection_reason = models.TextField(blank=True)
    compliance_notes = models.TextField(blank=True)

    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    converted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    _previous_status = None

    class Meta:
        db_table = "onboarding_partner_application"
        verbose_name = "Partner Application"
        verbose_name_plural = "Partner Applications"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["application_number"]),
            models.Index(fields=["status"]),
            models.Index(fields=["partner_type", "status"]),
            models.Index(fields=["submitted_by", "status"]),
            models.Index(fields=["email"]),
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._previous_status = self.status

    def __str__(self):
        return f"Application {self.application_number} - {self.get_status_display()}"

    @property
    def display_name(self):
        if self.partner_type == "INDIVIDUAL":
            return f"{self.first_name} {self.surname}".strip()
        return self.company_name

    @property
    def previous_status(self):
        return self._previous_status

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self._previous_status = self.status


class PartnerApplicationEvent(models.Model):
    """Immutable business event history for an onboarding application."""

    EVENT_TYPES = [
        ("CREATED", "Created"),
        ("UPDATED", "Updated"),
        ("SUBMITTED", "Submitted"),
        ("REVIEW_STARTED", "Review Started"),
        ("DOCUMENTS_REQUESTED", "Documents Requested"),
        ("SENT_TO_COMPLIANCE", "Sent to Compliance"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        ("SUSPENDED", "Suspended"),
        ("RESUMED", "Resumed"),
        ("CONVERTED", "Converted"),
        ("DOCUMENT_UPLOADED", "Document Uploaded"),
        ("DOCUMENT_VERIFIED", "Document Verified"),
        ("TASK_CREATED", "Task Created"),
        ("TASK_COMPLETED", "Task Completed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(
        PartnerApplication, on_delete=models.CASCADE, related_name="events"
    )
    event_type = models.CharField(max_length=40, choices=EVENT_TYPES, db_index=True)
    from_status = models.CharField(max_length=30, blank=True)
    to_status = models.CharField(max_length=30, blank=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="onboarding_events",
    )
    notes = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "onboarding_partner_application_event"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["application", "-created_at"]),
            models.Index(fields=["event_type", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.application.application_number} - {self.event_type}"


class PartnerApplicationDocument(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(
        PartnerApplication,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    application_partner_type = models.ForeignKey(
        "ApplicationPartnerType",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="documents",
        help_text="Optional assignment scope; null means shared application evidence.",
    )
    document_type = models.CharField(max_length=50, choices=DOCUMENT_TYPE_CHOICES)
    document_name = models.CharField(max_length=255)
    file = models.FileField(upload_to="partner_documents/%Y/%m/")
    file_size = models.BigIntegerField(null=True, blank=True)
    mime_type = models.CharField(max_length=100, blank=True)
    is_verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="verified_documents",
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    verification_notes = models.TextField(blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="uploaded_documents",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "onboarding_partner_application_document"
        verbose_name = "Application Document"
        verbose_name_plural = "Application Documents"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_document_type_display()} - {self.document_name}"


class PartnerApplicationTask(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(
        PartnerApplication,
        on_delete=models.CASCADE,
        related_name="tasks",
    )
    task_type = models.CharField(max_length=50, choices=TASK_TYPE_CHOICES)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_onboarding_tasks",
    )
    status = models.CharField(max_length=20, choices=TASK_STATUS_CHOICES, default="PENDING")
    priority = models.CharField(max_length=10, choices=TASK_PRIORITY_CHOICES, default="MEDIUM")
    due_date = models.DateField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="completed_onboarding_tasks",
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "onboarding_partner_application_task"
        verbose_name = "Application Task"
        verbose_name_plural = "Application Tasks"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_task_type_display()} - {self.title}"


class Branch(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "onboarding_branch"
        verbose_name = "Branch"
        verbose_name_plural = "Branches"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Location(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="locations")
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "onboarding_location"
        verbose_name = "Location"
        verbose_name_plural = "Locations"
        ordering = ["name"]
        unique_together = [["branch", "code"]]

    def __str__(self):
        return f"{self.branch.name} - {self.name}"


class ApplicationPartnerType(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(
        PartnerApplication, on_delete=models.CASCADE, related_name="partner_types"
    )
    partner_type = models.ForeignKey(
        "partners.PartnerType", on_delete=models.CASCADE
    )
    branch = models.ForeignKey(
        Branch, on_delete=models.SET_NULL, null=True, blank=True
    )
    location = models.ForeignKey(
        Location, on_delete=models.SET_NULL, null=True, blank=True
    )
    region = models.CharField(max_length=100, blank=True, default="")
    share_data_externally = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "onboarding_application_partner_type"
        verbose_name = "Application Partner Type"
        verbose_name_plural = "Application Partner Types"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.application.application_number} - {self.partner_type.name}"


class ApplicationContact(models.Model):
    CONTACT_TYPE_CHOICES = [
        ("PRIMARY", "Primary"),
        ("SECONDARY", "Secondary"),
        ("BILLING", "Billing"),
        ("TECHNICAL", "Technical"),
        ("OTHER", "Other"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(
        PartnerApplication, on_delete=models.CASCADE, related_name="contacts"
    )
    application_partner_type = models.ForeignKey(
        "ApplicationPartnerType",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="contacts",
        help_text="Optional assignment scope; null means shared application contact.",
    )
    contact_type = models.CharField(max_length=20, choices=CONTACT_TYPE_CHOICES, default="SECONDARY")
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    mobile = models.CharField(max_length=20, blank=True)
    designation = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "onboarding_application_contact"
        verbose_name = "Application Contact"
        verbose_name_plural = "Application Contacts"
        constraints = [
            models.UniqueConstraint(
                fields=["application"],
                condition=models.Q(is_primary=True),
                name="uniq_onboarding_primary_contact",
            ),
        ]
        ordering = ["-is_primary", "last_name"]

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class ApplicationBankAccount(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(
        PartnerApplication, on_delete=models.CASCADE, related_name="bank_accounts"
    )
    application_partner_type = models.ForeignKey(
        "ApplicationPartnerType",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="bank_accounts",
        help_text="Optional assignment scope; null means shared application bank account.",
    )
    bank_name = models.CharField(max_length=200)
    branch_name = models.CharField(max_length=200, blank=True)
    account_name = models.CharField(max_length=200)
    account_number = models.CharField(max_length=50)
    swift_code = models.CharField(max_length=20, blank=True)
    iban = models.CharField(max_length=50, blank=True)
    currency = models.CharField(max_length=3, default="TZS")
    is_primary = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "onboarding_application_bank_account"
        verbose_name = "Application Bank Account"
        verbose_name_plural = "Application Bank Accounts"
        constraints = [
            models.UniqueConstraint(
                fields=["application"],
                condition=models.Q(is_primary=True),
                name="uniq_onboarding_primary_bank",
            ),
        ]
        ordering = ["-is_primary"]

    def __str__(self):
        return f"{self.account_name} - {self.bank_name}"


class ApplicationFieldValue(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(
        PartnerApplication, on_delete=models.CASCADE, related_name="field_values"
    )
    application_partner_type = models.ForeignKey(
        "ApplicationPartnerType",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="field_values",
        help_text="Optional assignment scope for this dynamic value.",
    )
    field_config = models.ForeignKey(
        PartnerTypeFieldConfiguration, on_delete=models.CASCADE, related_name="application_field_values"
    )
    value_json = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "onboarding_application_field_value"
        verbose_name = "Application Field Value"
        verbose_name_plural = "Application Field Values"
        constraints = [
            models.UniqueConstraint(
                fields=["application", "application_partner_type", "field_config"],
                name="uniq_onboarding_field_value_scope",
            ),
        ]
        ordering = ["field_config__display_order", "field_config__field_code"]

    def __str__(self):
        return f"{self.field_config.field_code}: {self.value_json}"


class UnifiedOnboardingRecord(models.Model):
    id = models.UUIDField(primary_key=True)
    record_type = models.CharField(max_length=20)
    application_id = models.UUIDField(null=True)
    partner_id = models.UUIDField(null=True)
    reference_number = models.CharField(max_length=50)
    display_name = models.CharField(max_length=255)
    partner_type = models.CharField(max_length=50)
    email = models.EmailField()
    mobile_number = models.CharField(max_length=50)
    application_status = models.CharField(max_length=50, null=True)
    kyc_status = models.CharField(max_length=50, null=True)
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "onboarding_unified_record"
        verbose_name = "Unified Onboarding Record"
        verbose_name_plural = "Unified Onboarding Records"
