import uuid
import logging

from django.db import models
from django.conf import settings

logger = logging.getLogger(__name__)


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


class Partner(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    partner_number = models.CharField(max_length=50, unique=True, db_index=True)
    partner_type = models.CharField(max_length=20, choices=PARTNER_TYPE_CHOICES)
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
            models.Index(fields=["partner_number"]),
            models.Index(fields=["email"]),
            models.Index(fields=["partner_type", "status"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        if self.partner_type == "INDIVIDUAL":
            return f"{self.first_name} {self.surname} ({self.partner_number})"
        return f"{self.company_name} ({self.partner_number})"

    @property
    def display_name(self):
        if self.partner_type == "INDIVIDUAL":
            parts = filter(None, [self.title, self.first_name, self.other_name, self.surname])
            return " ".join(parts)
        return self.company_name


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
