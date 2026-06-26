import uuid
import logging

from django.db import models
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


PARTNER_CATEGORY_CHOICES = [
    ("INDIVIDUAL", "Individual"),
    ("CORPORATE", "Corporate"),
]

# Deprecated — kept for backward compatibility. Use PARTNER_CATEGORY_CHOICES + PartnerTypeAssignment.
PARTNER_TYPE_CHOICES = [
    ("INDIVIDUAL", "Individual"),
    ("CORPORATE", "Corporate"),
    ("AGENT", "Agent"),
    ("BROKER", "Broker"),
]

PARTNER_STATUS_CHOICES = [
    ("ACTIVE", "Active"),
    ("INACTIVE", "Inactive"),
    ("SUSPENDED", "Suspended"),
]

IDENTIFICATION_TYPE_CHOICES = [
    ("NIN", "National Identification Number"),
    ("ZAN_ID", "Zanzibar ID"),
    ("PASSPORT", "Passport"),
    ("DRIVING_LICENSE", "Driving License"),
    ("TIN", "Tax Identification Number"),
    ("VOTER_ID", "Voter ID"),
    ("RESIDENT_PERMIT", "Resident Permit"),
    ("MILITARY_ID", "Military ID"),
]

TITLE_CHOICES = [
    ("Mr", "Mr"),
    ("Mrs", "Mrs"),
    ("Miss", "Miss"),
    ("Ms", "Ms"),
    ("Dr", "Dr"),
    ("Prof", "Prof"),
    ("Hon", "Hon"),
    ("Eng", "Eng"),
    ("Rev", "Rev"),
]

GENDER_CHOICES = [
    ("MALE", "Male"),
    ("FEMALE", "Female"),
]

MARITAL_STATUS_CHOICES = [
    ("SINGLE", "Single"),
    ("MARRIED", "Married"),
    ("DIVORCED", "Divorced"),
    ("WIDOWED", "Widowed"),
    ("SEPARATED", "Separated"),
]

POLITICAL_RISK_CHOICES = [
    ("LOW", "Low"),
    ("MEDIUM", "Medium"),
    ("HIGH", "High"),
    ("PEP", "Politically Exposed Person"),
]

AML_RISK_CHOICES = [
    ("LOW", "Low"),
    ("MEDIUM", "Medium"),
    ("HIGH", "High"),
]

INDUSTRY_CHOICES = [
    ("TECHNOLOGY", "Technology"),
    ("HEALTHCARE", "Healthcare & Pharmaceuticals"),
    ("FINANCIAL_SERVICES", "Financial Services & Banking"),
    ("CONSUMER_GOODS", "Consumer Goods & Retail"),
    ("ENERGY", "Energy & Utilities"),
    ("MANUFACTURING", "Manufacturing & Industrial"),
    ("TELECOMMUNICATIONS", "Telecommunications"),
    ("TRANSPORTATION", "Transportation & Logistics"),
    ("REAL_ESTATE", "Real Estate & Construction"),
    ("MEDIA", "Media & Entertainment"),
    ("AEROSPACE", "Aerospace & Defense"),
    ("AUTOMOTIVE", "Automotive"),
    ("AGRICULTURE", "Agriculture & Food Production"),
    ("HOSPITALITY", "Hospitality & Tourism"),
    ("EDUCATION", "Education & Training"),
    ("PROFESSIONAL_SERVICES", "Professional Services & Consulting"),
    ("INSURANCE", "Insurance"),
    ("MINING", "Mining & Metals"),
    ("CHEMICALS", "Chemicals"),
    ("TEXTILES", "Textiles & Apparel"),
    ("ENVIRONMENTAL", "Environmental Services"),
    ("BIOTECHNOLOGY", "Biotechnology"),
    ("E_COMMERCE", "E-commerce"),
    ("RENEWABLE_ENERGY", "Renewable Energy"),
    ("CYBERSECURITY", "Cybersecurity"),
    ("AI_ML", "AI & Machine Learning"),
    ("FINTECH", "Fintech"),
    ("LIFE_SCIENCES", "Life Sciences"),
    ("OIL_GAS", "Oil & Gas"),
    ("CONSUMER_ELECTRONICS", "Consumer Electronics"),
]

NATIONALITY_CHOICES = [
    ("Tanzanian", "Tanzanian"),
    ("Kenyan", "Kenyan"),
    ("Ugandan", "Ugandan"),
    ("Rwandan", "Rwandan"),
    ("Burundian", "Burundian"),
    ("Congolese", "Congolese"),
    ("South African", "South African"),
    ("Nigerian", "Nigerian"),
    ("Ghanaian", "Ghanaian"),
    ("Ethiopian", "Ethiopian"),
    ("Somali", "Somali"),
    ("Mozambican", "Mozambican"),
    ("Malawian", "Malawian"),
    ("Zambian", "Zambian"),
    ("Zimbabwean", "Zimbabwean"),
    ("Indian", "Indian"),
    ("Chinese", "Chinese"),
    ("British", "British"),
    ("American", "American"),
    ("Other", "Other"),
]


class PartnerType(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    branch = models.ForeignKey(
        "partner_onboarding.Branch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    location = models.ForeignKey(
        "partner_onboarding.Location",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "partner_partner_type"
        verbose_name = "Partner Type"
        verbose_name_plural = "Partner Types"
        ordering = ["name"]

    def __str__(self):
        return self.name


class PartnerTypeDocumentRequirement(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    partner_type = models.ForeignKey(
        PartnerType, on_delete=models.CASCADE, related_name="document_requirements"
    )
    code = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    is_required = models.BooleanField(default=True)
    is_mandatory = models.BooleanField(default=False)
    sort_order = models.PositiveSmallIntegerField(default=0)
    allow_multiple_uploads = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="created_document_requirements",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="updated_document_requirements",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "partner_partner_type_document_requirement"
        verbose_name = "Partner Type Document Requirement"
        verbose_name_plural = "Partner Type Document Requirements"
        ordering = ["partner_type", "sort_order", "code"]
        unique_together = [("partner_type", "code")]
        indexes = [
            models.Index(fields=["partner_type", "is_active"]),
        ]

    def __str__(self):
        return f"{self.partner_type.name} - {self.code}"


class Partner(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    partner_number = models.CharField(max_length=50, unique=True, db_index=True)
    partner_type = models.CharField(max_length=20, choices=PARTNER_TYPE_CHOICES)
    partner_category = models.CharField(
        max_length=20, choices=PARTNER_CATEGORY_CHOICES,
        blank=True, default="",
        help_text="Classification: INDIVIDUAL or CORPORATE. Preferred over partner_type.",
    )
    status = models.CharField(max_length=20, choices=PARTNER_STATUS_CHOICES, default="ACTIVE")

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
    industry = models.CharField(max_length=100, choices=INDUSTRY_CHOICES, blank=True)
    contact_person = models.CharField(max_length=200, blank=True)
    contact_person_phone = models.CharField(max_length=20, blank=True)
    contact_person_email = models.EmailField(blank=True)
    physical_address = models.TextField(blank=True)
    postal_address = models.TextField(blank=True)

    email = models.EmailField(unique=True)
    telephone_number = models.CharField(max_length=20, blank=True)
    mobile_number = models.CharField(max_length=20)
    political_risk = models.CharField(max_length=20, choices=POLITICAL_RISK_CHOICES, default="LOW")
    aml_risk = models.CharField(max_length=20, choices=AML_RISK_CHOICES, default="LOW")

    created_from_application = models.OneToOneField(
        "partner_onboarding.PartnerApplication",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="converted_partner",
    )
    activated_at = models.DateTimeField(null=True, blank=True)
    deactivated_at = models.DateTimeField(null=True, blank=True)
    deactivation_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "partner_partner"
        verbose_name = "Partner"
        verbose_name_plural = "Partners"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["partner_type"]),
        models.Index(fields=["email"]),
            models.Index(fields=["mobile_number"]),
            models.Index(fields=["identification_number"]),
            models.Index(fields=["tin_number"]),
            models.Index(fields=["-created_at"]),
        ]

    @property
    def effective_category(self):
        return self.partner_category or self.partner_type

    def __str__(self):
        cat = self.effective_category
        if cat == "INDIVIDUAL":
            return f"{self.first_name} {self.surname} ({self.partner_number})"
        return f"{self.company_name} ({self.partner_number})"

    @property
    def display_name(self):
        cat = self.effective_category
        if cat == "INDIVIDUAL":
            parts = filter(None, [self.title, self.first_name, self.other_name, self.surname])
            return " ".join(parts)
        return self.company_name

    @property
    def individual_profile(self):
        try:
            return self._individual_profile
        except IndividualProfile.DoesNotExist:
            return None

    @property
    def corporate_profile(self):
        try:
            return self._corporate_profile
        except CorporateProfile.DoesNotExist:
            return None


ASSIGNMENT_STATUS_CHOICES = [
    ("ACTIVE", "Active"),
    ("INACTIVE", "Inactive"),
]

FIELD_TYPE_CHOICES = [
    ("TEXT", "Text"),
    ("NUMBER", "Number"),
    ("DATE", "Date"),
    ("BOOLEAN", "Boolean"),
    ("DROPDOWN", "Dropdown"),
    ("MULTI_SELECT", "Multi Select"),
    ("FILE", "File"),
    ("CURRENCY", "Currency"),
    ("PERCENTAGE", "Percentage"),
]

KYC_STATUS_CHOICES = [
    ("NOT_SET", "Not Set"),
    ("PENDING_REVIEW", "Pending Review"),
    ("VERIFIED", "Verified"),
    ("REJECTED", "Rejected"),
    ("EXPIRED", "Expired"),
]

DOCUMENT_STATUS_CHOICES = [
    ("NOT_SUBMITTED", "Not Submitted"),
    ("UPLOADED", "Uploaded"),
    ("UNDER_REVIEW", "Under Review"),
    ("APPROVED", "Approved"),
    ("REJECTED", "Rejected"),
    ("EXPIRED", "Expired"),
]


# ============================================================================
# Configuration Models — define what is REQUIRED per Partner Type
# ============================================================================


class PartnerTypeFieldConfiguration(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    partner_type = models.ForeignKey(
        PartnerType, on_delete=models.CASCADE, related_name="field_configurations"
    )
    field_name = models.CharField(max_length=200)
    field_code = models.CharField(max_length=100)
    field_type = models.CharField(max_length=20, choices=FIELD_TYPE_CHOICES)
    default_value = models.TextField(blank=True)
    is_required = models.BooleanField(default=False)
    validation_rules = models.JSONField(blank=True, default=dict)
    display_order = models.PositiveSmallIntegerField(default=0)
    visibility_rules = models.JSONField(blank=True, default=dict)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "partner_type_field_config"
        verbose_name = "Partner Type Field Configuration"
        verbose_name_plural = "Partner Type Field Configurations"
        ordering = ["partner_type", "display_order", "field_name"]
        unique_together = [("partner_type", "field_code")]

    def __str__(self):
        return f"{self.partner_type.name} - {self.field_name}"


class PartnerTypeContactRequirement(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    partner_type = models.ForeignKey(
        PartnerType, on_delete=models.CASCADE, related_name="contact_requirements"
    )
    contact_type = models.CharField(max_length=50)
    is_required = models.BooleanField(default=True)
    multiple_allowed = models.BooleanField(default=False)
    display_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "partner_type_contact_requirement"
        verbose_name = "Partner Type Contact Requirement"
        verbose_name_plural = "Partner Type Contact Requirements"
        ordering = ["partner_type", "display_order", "contact_type"]
        unique_together = [("partner_type", "contact_type")]

    def __str__(self):
        return f"{self.partner_type.name} - {self.contact_type}"


class PartnerTypeBankRequirement(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    partner_type = models.ForeignKey(
        PartnerType, on_delete=models.CASCADE, related_name="bank_requirements"
    )
    bank_type = models.CharField(max_length=50)
    is_required = models.BooleanField(default=True)
    multiple_allowed = models.BooleanField(default=False)
    validation_rules = models.JSONField(blank=True, default=dict)
    display_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "partner_type_bank_requirement"
        verbose_name = "Partner Type Bank Requirement"
        verbose_name_plural = "Partner Type Bank Requirements"
        ordering = ["partner_type", "display_order", "bank_type"]
        unique_together = [("partner_type", "bank_type")]

    def __str__(self):
        return f"{self.partner_type.name} - {self.bank_type}"


# ============================================================================
# Transaction Models — actual data submitted per PartnerTypeAssignment
# ============================================================================


class PartnerDocument(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assignment = models.ForeignKey(
        "PartnerTypeAssignment", on_delete=models.CASCADE,
        related_name="documents",
    )
    document_requirement = models.ForeignKey(
        PartnerTypeDocumentRequirement, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="submitted_documents",
    )
    file = models.FileField(upload_to="partner_documents/%Y/%m/", blank=True)
    document_number = models.CharField(max_length=100, blank=True)
    issue_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="uploaded_partner_documents",
    )
    uploaded_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=30, choices=DOCUMENT_STATUS_CHOICES, default="NOT_SUBMITTED",
    )
    verification_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "partner_document"
        verbose_name = "Partner Document"
        verbose_name_plural = "Partner Documents"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["assignment"]),
            models.Index(fields=["status"]),
            models.Index(fields=["expiry_date"]),
            models.Index(fields=["assignment", "status"]),
        ]

    def __str__(self):
        req = self.document_requirement
        code = req.code if req else "Unknown"
        return f"{self.assignment.partner.partner_number} - {code}"


class PartnerDynamicFieldValue(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assignment = models.ForeignKey(
        "PartnerTypeAssignment", on_delete=models.CASCADE,
        related_name="field_values",
    )
    field_config = models.ForeignKey(
        PartnerTypeFieldConfiguration, on_delete=models.CASCADE,
        related_name="field_values",
    )
    value_json = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "partner_dynamic_field_value"
        verbose_name = "Partner Dynamic Field Value"
        verbose_name_plural = "Partner Dynamic Field Values"
        unique_together = [("assignment", "field_config")]
        indexes = [
            models.Index(fields=["assignment"]),
            models.Index(fields=["field_config"]),
        ]

    def __str__(self):
        return f"{self.assignment.partner.partner_number} - {self.field_config.field_code}"


class PartnerAssignmentContact(models.Model):
    CONTACT_TYPE_CHOICES = [
        ("PRIMARY", "Primary"),
        ("COMPLIANCE_OFFICER", "Compliance Officer"),
        ("TECHNICAL", "Technical"),
        ("BILLING", "Billing"),
        ("OTHER", "Other"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assignment = models.ForeignKey(
        "PartnerTypeAssignment", on_delete=models.CASCADE,
        related_name="assignment_contacts",
    )
    contact_requirement = models.ForeignKey(
        PartnerTypeContactRequirement, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="submitted_contacts",
    )
    contact_type = models.CharField(max_length=50)
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
        db_table = "partner_assignment_contact"
        verbose_name = "Assignment Contact"
        verbose_name_plural = "Assignment Contacts"
        ordering = ["-is_primary", "last_name"]
        indexes = [
            models.Index(fields=["assignment"]),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.assignment.partner.partner_number})"


class PartnerAssignmentBankAccount(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assignment = models.ForeignKey(
        "PartnerTypeAssignment", on_delete=models.CASCADE,
        related_name="assignment_bank_accounts",
    )
    bank_requirement = models.ForeignKey(
        PartnerTypeBankRequirement, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="submitted_bank_accounts",
    )
    bank_type = models.CharField(max_length=50)
    bank_name = models.CharField(max_length=200)
    branch_name = models.CharField(max_length=200, blank=True)
    account_name = models.CharField(max_length=200)
    account_number = models.CharField(max_length=50)
    swift_code = models.CharField(max_length=20, blank=True)
    currency = models.CharField(max_length=3, default="TZS")
    is_primary = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "partner_assignment_bank_account"
        verbose_name = "Assignment Bank Account"
        verbose_name_plural = "Assignment Bank Accounts"
        ordering = ["-is_primary"]
        indexes = [
            models.Index(fields=["assignment"]),
        ]

    def __str__(self):
        return f"{self.account_name} - {self.bank_name} ({self.assignment.partner.partner_number})"


class PartnerKYCProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assignment = models.ForeignKey(
        "PartnerTypeAssignment", on_delete=models.CASCADE,
        related_name="kyc_profiles",
    )
    kyc_status = models.CharField(max_length=30, choices=KYC_STATUS_CHOICES, default="NOT_SET")
    risk_score = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    risk_level = models.CharField(max_length=30, blank=True)
    last_review_date = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="reviewed_kyc_profiles",
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "partner_kyc_profile"
        verbose_name = "Partner KYC Profile"
        verbose_name_plural = "Partner KYC Profiles"
        unique_together = [("assignment",)]
        indexes = [
            models.Index(fields=["assignment"]),
            models.Index(fields=["kyc_status"]),
            models.Index(fields=["kyc_status", "risk_level"]),
        ]

    def __str__(self):
        return f"KYC {self.assignment.partner.partner_number} - {self.get_kyc_status_display()}"


class IndividualProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    partner = models.OneToOneField(
        Partner, on_delete=models.CASCADE,
        related_name="individual_profile",
    )
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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "partner_individual_profile"
        verbose_name = "Individual Profile"
        verbose_name_plural = "Individual Profiles"

    def __str__(self):
        parts = filter(None, [self.title, self.first_name, self.other_name, self.surname])
        return " ".join(parts) or self.partner.partner_number


class CorporateProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    partner = models.OneToOneField(
        Partner, on_delete=models.CASCADE,
        related_name="corporate_profile",
    )
    company_name = models.CharField(max_length=255, blank=True)
    tin_number = models.CharField(max_length=50, blank=True)
    incorporation_date = models.DateField(null=True, blank=True)
    industry = models.CharField(max_length=100, choices=INDUSTRY_CHOICES, blank=True)
    contact_person = models.CharField(max_length=200, blank=True)
    contact_person_phone = models.CharField(max_length=20, blank=True)
    contact_person_email = models.EmailField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "partner_corporate_profile"
        verbose_name = "Corporate Profile"
        verbose_name_plural = "Corporate Profiles"

    def __str__(self):
        return self.company_name or self.partner.partner_number


class PartnerTypeAssignment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    partner = models.ForeignKey(
        Partner, on_delete=models.CASCADE, related_name="type_assignments"
    )
    partner_type = models.ForeignKey(
        PartnerType, on_delete=models.PROTECT, related_name="assignments"
    )
    branch = models.ForeignKey(
        "partner_onboarding.Branch", on_delete=models.SET_NULL,
        null=True, blank=True,
    )
    location = models.ForeignKey(
        "partner_onboarding.Location", on_delete=models.SET_NULL,
        null=True, blank=True,
    )
    share_data_externally = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=ASSIGNMENT_STATUS_CHOICES, default="ACTIVE")
    effective_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "partner_type_assignment"
        verbose_name = "Partner Type Assignment"
        verbose_name_plural = "Partner Type Assignments"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["partner", "partner_type"],
                name="unique_partner_type_per_partner",
            ),
        ]
        indexes = [
            models.Index(fields=["partner", "status"]),
            models.Index(fields=["partner_type"]),
        ]

    def clean(self):
        if self.location and self.branch and self.location.branch_id != self.branch_id:
            from django.core.exceptions import ValidationError
            raise ValidationError(
                {"location": "Location branch must match the selected Branch."}
            )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.partner.partner_number} - {self.partner_type.name}"


class PartnerContact(models.Model):
    CONTACT_TYPE_CHOICES = [
        ("PRIMARY", "Primary"),
        ("SECONDARY", "Secondary"),
        ("BILLING", "Billing"),
        ("TECHNICAL", "Technical"),
        ("OTHER", "Other"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    partner = models.ForeignKey(Partner, on_delete=models.CASCADE, related_name="contacts")
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
        db_table = "partner_partner_contact"
        verbose_name = "Partner Contact"
        verbose_name_plural = "Partner Contacts"
        ordering = ["-is_primary", "last_name"]

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.partner.partner_number})"


class PartnerBankAccount(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    partner = models.ForeignKey(Partner, on_delete=models.CASCADE, related_name="bank_accounts")
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
        db_table = "partner_partner_bank_account"
        verbose_name = "Partner Bank Account"
        verbose_name_plural = "Partner Bank Accounts"
        ordering = ["-is_primary"]

    def __str__(self):
        return f"{self.account_name} - {self.bank_name} ({self.account_number})"


# ============================================================================
# Phase 4 — Enterprise Governance Models
# ============================================================================


class DocumentVersion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(
        PartnerDocument, on_delete=models.CASCADE,
        related_name="versions",
    )
    version_number = models.PositiveIntegerField()
    file = models.FileField(upload_to="partner_document_versions/%Y/%m/", blank=True)
    file_name = models.CharField(max_length=255, blank=True)
    file_size = models.PositiveIntegerField(null=True, blank=True)
    mime_type = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=30, default="UPLOADED")
    notes = models.TextField(blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True,
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    verification_status = models.CharField(max_length=30, blank=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="verified_document_versions",
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    verification_notes = models.TextField(blank=True)

    class Meta:
        db_table = "partner_document_version"
        verbose_name = "Document Version"
        verbose_name_plural = "Document Versions"
        ordering = ["document", "-version_number"]
        unique_together = [("document", "version_number")]

    def __str__(self):
        return f"{self.document} v{self.version_number}"


class KYCReviewHistory(models.Model):
    REVIEW_TYPE_CHOICES = [
        ("INITIAL", "Initial Verification"),
        ("PERIODIC", "Periodic Review"),
        ("ENHANCED_DUE_DILIGENCE", "Enhanced Due Diligence"),
        ("HIGH_RISK_ESCALATION", "High Risk Escalation"),
        ("REVIEW", "Manual Review"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    kyc_profile = models.ForeignKey(
        PartnerKYCProfile, on_delete=models.CASCADE,
        related_name="review_history",
    )
    review_type = models.CharField(max_length=30, choices=REVIEW_TYPE_CHOICES, default="REVIEW")
    previous_kyc_status = models.CharField(max_length=30, blank=True)
    new_kyc_status = models.CharField(max_length=30, blank=True)
    previous_risk_score = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    new_risk_score = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    previous_risk_level = models.CharField(max_length=30, blank=True)
    new_risk_level = models.CharField(max_length=30, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True,
    )
    decision_date = models.DateTimeField(default=timezone.now)
    comments = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "partner_kyc_review_history"
        verbose_name = "KYC Review History"
        verbose_name_plural = "KYC Review Histories"
        ordering = ["-decision_date"]
        indexes = [
            models.Index(fields=["kyc_profile", "-decision_date"]),
            models.Index(fields=["review_type"]),
        ]

    def __str__(self):
        return f"KYC Review {self.kyc_profile_id} - {self.review_type} ({self.decision_date})"


class PartnerTypeAssignmentHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assignment = models.ForeignKey(
        PartnerTypeAssignment, on_delete=models.CASCADE,
        related_name="status_history",
    )
    previous_status = models.CharField(max_length=20, blank=True)
    new_status = models.CharField(max_length=20)
    reason = models.TextField(blank=True)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True,
    )
    changed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "partner_type_assignment_history"
        verbose_name = "Partner Type Assignment History"
        verbose_name_plural = "Partner Type Assignment Histories"
        ordering = ["-changed_at"]
        indexes = [
            models.Index(fields=["assignment", "-changed_at"]),
        ]

    def __str__(self):
        return f"{self.assignment} {self.previous_status} -> {self.new_status}"
