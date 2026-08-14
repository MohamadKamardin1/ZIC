"""
Group Life Insurance Module — Database Models

This module implements the complete data model for Group Life insurance operations:
- Parameter / Setup tables (Scheme Types, Statuses, Premium Rates, Health Q&A)
- Product & Rider configuration
- Quotation engine
- Scheme & Member management
- Medical Underwriting
- Claims processing & installments
- Renewal tracking

All models follow ZIC codebase conventions:
- UUID primary keys
- `gl_` prefixed db_table names
- Explicit indexes on query-hot fields
- TextChoices enums for status fields
- `created_at` / `updated_at` timestamps
"""

import uuid
import logging

from django.db import models
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


# =============================================================================
# LAYER 1 — PARAMETER / SETUP TABLES (GL Scheme Setup)
# =============================================================================


class GLSchemeType(models.Model):
    """
    Classification of group life scheme types.
    Examples: Employer-Employee, Association, Cooperative, Credit Union.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gl_scheme_type"
        verbose_name = "GL Scheme Type"
        verbose_name_plural = "GL Scheme Types"
        ordering = ["name"]

    def __str__(self):
        return self.name


class GLLookupValue(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.CharField(max_length=50, db_index=True)
    value = models.CharField(max_length=50)
    label = models.CharField(max_length=200)
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gl_lookup_value"
        ordering = ["category", "sort_order", "label"]
        unique_together = ("category", "value")

    def __str__(self):
        return f"{self.category}: {self.value} — {self.label}"


class GLSchemeStatus(models.Model):
    """
    Operational lifecycle statuses for group life schemes.
    Examples: DRAFT, ACTIVE, EXPIRED, LAPSED, CANCELLED, SUSPENDED.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    sort_order = models.PositiveSmallIntegerField(default=0)
    is_terminal = models.BooleanField(
        default=False,
        help_text="If True, scheme cannot transition out of this status.",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gl_scheme_status"
        verbose_name = "GL Scheme Status"
        verbose_name_plural = "GL Scheme Statuses"
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class GLSchemeMemberStatus(models.Model):
    """
    Statuses for individual members within a scheme.
    Examples: ACTIVE, PENDING_UW, TERMINATED, SUSPENDED, DECEASED.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gl_scheme_member_status"
        verbose_name = "GL Scheme Member Status"
        verbose_name_plural = "GL Scheme Member Statuses"
        ordering = ["name"]

    def __str__(self):
        return self.name


class GLSchemeRenewalStatus(models.Model):
    """
    Statuses tracking scheme renewal milestones.
    Examples: PENDING, UNDER_NEGOTIATION, RENEWED, NON_RENEWING, LAPSED.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gl_scheme_renewal_status"
        verbose_name = "GL Scheme Renewal Status"
        verbose_name_plural = "GL Scheme Renewal Statuses"
        ordering = ["name"]

    def __str__(self):
        return self.name


class GLSchemePremiumRate(models.Model):
    """
    Premium rate configuration table supporting age-banded, flat,
    and occupation-class based rating approaches.
    """



    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    rate_type = models.CharField(max_length=20)
    age_band_start = models.PositiveSmallIntegerField(
        null=True, blank=True, help_text="Minimum age (inclusive) for age-band rates."
    )
    age_band_end = models.PositiveSmallIntegerField(
        null=True, blank=True, help_text="Maximum age (inclusive) for age-band rates."
    )
    gender = models.CharField(
        max_length=10, default="UNISEX"
    )
    occupation_class = models.CharField(
        max_length=50, blank=True,
        help_text="Occupation risk class code for occupation-based rates."
    )
    rate_per_mille = models.DecimalField(
        max_digits=12, decimal_places=6, null=True, blank=True,
        help_text="Premium rate per 1,000 of sum assured."
    )
    flat_rate = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text="Fixed flat premium amount."
    )
    effective_date = models.DateField()
    expiry_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gl_scheme_premium_rate"
        verbose_name = "GL Scheme Premium Rate"
        verbose_name_plural = "GL Scheme Premium Rates"
        ordering = ["rate_type", "age_band_start", "gender"]
        indexes = [
            models.Index(fields=["rate_type", "age_band_start", "age_band_end", "gender"]),
            models.Index(fields=["effective_date", "expiry_date"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        if self.rate_type == "AGE_BAND":
            return f"{self.name} ({self.age_band_start}-{self.age_band_end}, {self.gender})"
        return f"{self.name} ({self.get_rate_type_display()})"


class GLHealthQuestion(models.Model):
    """
    Individual health screening questions used in medical underwriting questionnaires.
    """



    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True)
    question_text = models.TextField()
    question_type = models.CharField(max_length=20)
    category = models.CharField(max_length=20, default="GENERAL")
    options = models.JSONField(
        blank=True, default=list,
        help_text="Available options for MULTIPLE_CHOICE type questions."
    )
    sort_order = models.PositiveSmallIntegerField(default=0)
    is_required = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gl_health_question"
        verbose_name = "GL Health Question"
        verbose_name_plural = "GL Health Questions"
        ordering = ["category", "sort_order"]

    def __str__(self):
        return f"[{self.code}] {self.question_text[:80]}"


class GLHealthQuestionnaire(models.Model):
    """
    Versioned collection of health questions assembled into a questionnaire form.
    Assigned to medical cases for member underwriting.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    version = models.CharField(max_length=20, default="1.0")
    questions = models.ManyToManyField(
        GLHealthQuestion, related_name="questionnaires", blank=True
    )
    effective_date = models.DateField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gl_health_questionnaire"
        verbose_name = "GL Health Questionnaire"
        verbose_name_plural = "GL Health Questionnaires"
        ordering = ["-effective_date", "name"]

    def __str__(self):
        return f"{self.name} v{self.version}"


# =============================================================================
# LAYER 2 — PRODUCT & RIDER CONFIGURATION
# =============================================================================


class GLSubProduct(models.Model):
    """
    High-level product classification.
    Examples: Group Term Life, Funeral Cover, Credit Life, Key Person.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gl_sub_product"
        verbose_name = "GL Sub Product"
        verbose_name_plural = "GL Sub Products"
        ordering = ["name"]

    def __str__(self):
        return self.name


class GLProduct(models.Model):
    """
    Concrete product definition with underwriting limits, age bands,
    Free Cover Limit (FCL), and salary multiple constraints.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    sub_product = models.ForeignKey(
        GLSubProduct, on_delete=models.PROTECT, related_name="products"
    )
    description = models.TextField(blank=True)

    # Member constraints
    min_members = models.PositiveIntegerField(
        default=10, help_text="Minimum number of members for this product."
    )
    max_members = models.PositiveIntegerField(
        null=True, blank=True, help_text="Maximum members allowed (null = unlimited)."
    )

    # Sum Assured limits
    min_sum_assured = models.DecimalField(
        max_digits=18, decimal_places=2, default=0,
        help_text="Minimum sum assured per member."
    )
    max_sum_assured = models.DecimalField(
        max_digits=18, decimal_places=2, null=True, blank=True,
        help_text="Maximum sum assured per member (null = unlimited)."
    )

    # Age constraints
    min_entry_age = models.PositiveSmallIntegerField(
        default=18, help_text="Minimum age at entry."
    )
    max_entry_age = models.PositiveSmallIntegerField(
        default=65, help_text="Maximum age at entry."
    )
    max_cover_age = models.PositiveSmallIntegerField(
        default=70, help_text="Maximum age for continued coverage."
    )

    # Free Cover Limit
    free_cover_limit = models.DecimalField(
        max_digits=18, decimal_places=2, default=0,
        help_text="Sum assured threshold above which medical underwriting is required."
    )

    # Salary multiples
    salary_multiple_min = models.DecimalField(
        max_digits=5, decimal_places=2, default=1.00,
        help_text="Minimum salary multiplier for sum assured calculation."
    )
    salary_multiple_max = models.DecimalField(
        max_digits=5, decimal_places=2, default=5.00,
        help_text="Maximum salary multiplier for sum assured calculation."
    )

    currency = models.CharField(max_length=3, default="TZS")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gl_product"
        verbose_name = "GL Product"
        verbose_name_plural = "GL Products"
        ordering = ["sub_product", "name"]
        indexes = [
            models.Index(fields=["code"]),
            models.Index(fields=["sub_product", "is_active"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.code})"


class GLRider(models.Model):
    """
    Supplementary benefit definitions that can be attached to a scheme.
    Examples: PTD, ADD, Critical Illness, Waiver of Premium, Funeral.
    """


    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    rider_type = models.CharField(max_length=20)
    is_mandatory = models.BooleanField(
        default=False, help_text="If True, this rider is always included with the product."
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gl_rider"
        verbose_name = "GL Rider"
        verbose_name_plural = "GL Riders"
        ordering = ["rider_type", "name"]

    def __str__(self):
        return f"{self.name} ({self.get_rider_type_display()})"


class GLRiderRate(models.Model):
    """
    Premium rating table for riders, supporting age-banded and flat-amount structures.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rider = models.ForeignKey(
        GLRider, on_delete=models.CASCADE, related_name="rates"
    )
    age_band_start = models.PositiveSmallIntegerField(null=True, blank=True)
    age_band_end = models.PositiveSmallIntegerField(null=True, blank=True)
    gender = models.CharField(
        max_length=10,
        default="UNISEX",
    )
    rate_per_mille = models.DecimalField(
        max_digits=12, decimal_places=6, null=True, blank=True,
        help_text="Rate per 1,000 of sum assured."
    )
    flat_amount = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text="Fixed flat premium amount for this rider."
    )
    effective_date = models.DateField()
    expiry_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gl_rider_rate"
        verbose_name = "GL Rider Rate"
        verbose_name_plural = "GL Rider Rates"
        ordering = ["rider", "age_band_start"]
        indexes = [
            models.Index(fields=["rider", "age_band_start", "age_band_end", "gender"]),
            models.Index(fields=["effective_date", "expiry_date"]),
        ]

    def __str__(self):
        band = f"{self.age_band_start}-{self.age_band_end}" if self.age_band_start else "All Ages"
        return f"{self.rider.name} Rate ({band}, {self.gender})"


# =============================================================================
# LAYER 3 — QUOTATION ENGINE
# =============================================================================


class GLQuotation(models.Model):
    """
    Group Life quotation for a corporate client, capturing premium
    computation, experience rating, and rider selections.
    """


    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    quotation_number = models.CharField(max_length=50, unique=True, db_index=True)
    partner = models.ForeignKey(
        "partners.Partner", on_delete=models.PROTECT,
        related_name="gl_quotations",
        help_text="The corporate client requesting the quotation."
    )
    product = models.ForeignKey(
        GLProduct, on_delete=models.PROTECT, related_name="quotations"
    )
    scheme_type = models.ForeignKey(
        GLSchemeType, on_delete=models.PROTECT, related_name="quotations"
    )
    status = models.CharField(
        max_length=20, default="DRAFT"
    )

    quotation_date = models.DateField(default=timezone.now)
    valid_until = models.DateField(
        null=True, blank=True,
        help_text="Expiry date after which the quotation is no longer valid."
    )

    # Aggregated totals
    total_members = models.PositiveIntegerField(default=0)
    total_sum_assured = models.DecimalField(
        max_digits=18, decimal_places=2, default=0
    )
    total_annual_premium = models.DecimalField(
        max_digits=18, decimal_places=2, default=0
    )

    # Rating factors
    experience_rating_factor = models.DecimalField(
        max_digits=8, decimal_places=4, default=1.0000,
        help_text="Multiplier based on claims experience (1.0 = standard)."
    )
    commission_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        help_text="Commission percentage for the intermediary."
    )
    admin_loading_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        help_text="Administrative expense loading percentage."
    )

    # Snapshot from product at quote time
    free_cover_limit = models.DecimalField(
        max_digits=18, decimal_places=2, default=0,
        help_text="FCL snapshot from product configuration at quote time."
    )

    notes = models.TextField(blank=True)
    prepared_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="gl_quotations_prepared"
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="gl_quotations_approved"
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gl_quotation"
        verbose_name = "GL Quotation"
        verbose_name_plural = "GL Quotations"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["quotation_number"]),
            models.Index(fields=["status"]),
            models.Index(fields=["partner", "status"]),
            models.Index(fields=["product"]),
            models.Index(fields=["-quotation_date"]),
        ]

    def __str__(self):
        return f"{self.quotation_number} — {self.partner} ({self.get_status_display()})"


class GLQuotationCategory(models.Model):
    """
    Member category breakdown within a quotation (e.g., Directors, Senior Staff).
    Each category has its own salary multiple or flat sum assured and computed premium.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    quotation = models.ForeignKey(
        GLQuotation, on_delete=models.CASCADE, related_name="categories"
    )
    category_name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    salary_multiple = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="Multiplier applied to annual salary to determine sum assured."
    )
    flat_sum_assured = models.DecimalField(
        max_digits=18, decimal_places=2, null=True, blank=True,
        help_text="Fixed sum assured (used instead of salary multiple)."
    )
    member_count = models.PositiveIntegerField(default=0)
    total_sum_assured = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    annual_premium = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    premium_rate_per_mille = models.DecimalField(
        max_digits=12, decimal_places=6, default=0,
        help_text="Applied premium rate per 1,000 of sum assured."
    )
    sort_order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gl_quotation_category"
        verbose_name = "GL Quotation Category"
        verbose_name_plural = "GL Quotation Categories"
        ordering = ["quotation", "sort_order"]

    def __str__(self):
        return f"{self.quotation.quotation_number} — {self.category_name}"


class GLQuotationRider(models.Model):
    """
    Rider selections attached to a quotation with computed premiums.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    quotation = models.ForeignKey(
        GLQuotation, on_delete=models.CASCADE, related_name="riders"
    )
    rider = models.ForeignKey(
        GLRider, on_delete=models.PROTECT, related_name="quotation_riders"
    )
    rate_per_mille = models.DecimalField(
        max_digits=12, decimal_places=6, default=0,
    )
    total_premium = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gl_quotation_rider"
        verbose_name = "GL Quotation Rider"
        verbose_name_plural = "GL Quotation Riders"
        ordering = ["quotation", "rider"]
        unique_together = [("quotation", "rider")]

    def __str__(self):
        return f"{self.quotation.quotation_number} — {self.rider.name}"


# =============================================================================
# LAYER 4 — SCHEME & MEMBER MANAGEMENT
# =============================================================================


class GLScheme(models.Model):
    """
    Active group life insurance scheme (policy contract).
    Created by converting an approved quotation or directly by an underwriter.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scheme_number = models.CharField(max_length=50, unique=True, db_index=True)
    partner = models.ForeignKey(
        "partners.Partner", on_delete=models.PROTECT,
        related_name="gl_schemes",
        help_text="The corporate policyholder."
    )
    product = models.ForeignKey(
        GLProduct, on_delete=models.PROTECT, related_name="schemes"
    )
    scheme_type = models.ForeignKey(
        GLSchemeType, on_delete=models.PROTECT, related_name="schemes"
    )
    status = models.ForeignKey(
        GLSchemeStatus, on_delete=models.PROTECT, related_name="schemes"
    )
    converted_from_quotation = models.OneToOneField(
        GLQuotation, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="converted_scheme",
        help_text="The quotation this scheme was converted from."
    )

    # Dates
    inception_date = models.DateField(
        help_text="Date the scheme coverage commences."
    )
    expiry_date = models.DateField(
        help_text="Date the scheme coverage expires (annual renewal date)."
    )
    renewal_date = models.DateField(
        null=True, blank=True,
        help_text="Next renewal date (set after renewal processing)."
    )

    # Rating & financial
    free_cover_limit = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    experience_rating_factor = models.DecimalField(
        max_digits=8, decimal_places=4, default=1.0000
    )
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    admin_loading_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    # Aggregated totals (updated by signals/services)
    total_members = models.PositiveIntegerField(default=0)
    total_sum_assured = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    total_annual_premium = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    currency = models.CharField(max_length=3, default="TZS")
    policy_document = models.FileField(
        upload_to="gl_policy_documents/%Y/%m/", blank=True,
        help_text="Uploaded policy schedule/document."
    )
    notes = models.TextField(blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="gl_schemes_created"
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="gl_schemes_updated"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gl_scheme"
        verbose_name = "GL Scheme"
        verbose_name_plural = "GL Schemes"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["scheme_number"]),
            models.Index(fields=["partner"]),
            models.Index(fields=["status"]),
            models.Index(fields=["product"]),
            models.Index(fields=["expiry_date"]),
            models.Index(fields=["partner", "status"]),
            models.Index(fields=["-inception_date"]),
        ]

    def __str__(self):
        return f"{self.scheme_number} — {self.partner}"

    @property
    def is_expired(self):
        return self.expiry_date and self.expiry_date < timezone.now().date()

    @property
    def days_until_expiry(self):
        if self.expiry_date:
            delta = self.expiry_date - timezone.now().date()
            return delta.days
        return None


class GLSchemeCategory(models.Model):
    """
    Member categories within a scheme (e.g., Directors, Senior, Junior Staff).
    Each category defines its own premium rate, salary multiple, and age limits.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scheme = models.ForeignKey(
        GLScheme, on_delete=models.CASCADE, related_name="categories"
    )
    category_name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    salary_multiple = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
    )
    flat_sum_assured = models.DecimalField(
        max_digits=18, decimal_places=2, null=True, blank=True,
    )
    premium_rate_per_mille = models.DecimalField(
        max_digits=12, decimal_places=6, default=0
    )
    min_entry_age = models.PositiveSmallIntegerField(null=True, blank=True)
    max_entry_age = models.PositiveSmallIntegerField(null=True, blank=True)
    max_cover_age = models.PositiveSmallIntegerField(null=True, blank=True)
    sort_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gl_scheme_category"
        verbose_name = "GL Scheme Category"
        verbose_name_plural = "GL Scheme Categories"
        ordering = ["scheme", "sort_order"]
        unique_together = [("scheme", "category_name")]

    def __str__(self):
        return f"{self.scheme.scheme_number} — {self.category_name}"


class GLSchemeRider(models.Model):
    """
    Riders attached to an active scheme.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scheme = models.ForeignKey(
        GLScheme, on_delete=models.CASCADE, related_name="riders"
    )
    rider = models.ForeignKey(
        GLRider, on_delete=models.PROTECT, related_name="scheme_riders"
    )
    rate_per_mille = models.DecimalField(
        max_digits=12, decimal_places=6, default=0
    )
    flat_amount = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gl_scheme_rider"
        verbose_name = "GL Scheme Rider"
        verbose_name_plural = "GL Scheme Riders"
        ordering = ["scheme", "rider"]
        unique_together = [("scheme", "rider")]

    def __str__(self):
        return f"{self.scheme.scheme_number} — {self.rider.name}"


class GLSchemeMember(models.Model):
    """
    Individual member enrolled in a group life scheme.
    Contains personal, employment, coverage, and underwriting data.
    """



    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scheme = models.ForeignKey(
        GLScheme, on_delete=models.CASCADE, related_name="members"
    )
    category = models.ForeignKey(
        GLSchemeCategory, on_delete=models.PROTECT,
        related_name="members",
    )
    member_number = models.CharField(max_length=50, unique=True, db_index=True)
    status = models.ForeignKey(
        GLSchemeMemberStatus, on_delete=models.PROTECT,
        related_name="members",
    )

    # Personal information
    first_name = models.CharField(max_length=100)
    surname = models.CharField(max_length=100)
    other_name = models.CharField(max_length=100, blank=True)
    gender = models.CharField(max_length=10)
    date_of_birth = models.DateField()
    identification_type = models.CharField(max_length=30, blank=True)
    identification_number = models.CharField(max_length=100, blank=True)
    nationality = models.CharField(max_length=100, blank=True, default="Tanzanian")

    # Employment details
    employee_number = models.CharField(
        max_length=100, blank=True,
        help_text="Employer's internal employee ID."
    )
    job_title = models.CharField(max_length=200, blank=True)
    date_of_employment = models.DateField(null=True, blank=True)
    annual_salary = models.DecimalField(
        max_digits=18, decimal_places=2, default=0,
        help_text="Annual gross salary used for sum assured calculation."
    )

    # Cover details
    sum_assured = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    premium_amount = models.DecimalField(
        max_digits=18, decimal_places=2, default=0,
        help_text="Computed annual premium for this member."
    )
    cover_start_date = models.DateField()
    cover_end_date = models.DateField(null=True, blank=True)

    # Underwriting
    requires_medical_uw = models.BooleanField(
        default=False,
        help_text="True if member's sum assured exceeds the Free Cover Limit."
    )
    uw_status = models.CharField(
        max_length=20, default="NOT_REQUIRED"
    )
    premium_loading_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        help_text="Additional premium loading for substandard risk."
    )

    # Contact
    email = models.EmailField(blank=True)
    mobile_number = models.CharField(max_length=20, blank=True)
    physical_address = models.TextField(blank=True)

    # Beneficiaries stored as structured JSON
    beneficiary_details = models.JSONField(
        blank=True, default=list,
        help_text="Array of beneficiary objects: [{name, relationship, percentage, id_number, phone}]"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gl_scheme_member"
        verbose_name = "GL Scheme Member"
        verbose_name_plural = "GL Scheme Members"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["scheme", "status"]),
            models.Index(fields=["member_number"]),
            models.Index(fields=["employee_number"]),
            models.Index(fields=["scheme", "category"]),
            models.Index(fields=["surname", "first_name"]),
            models.Index(fields=["identification_number"]),
        ]

    def __str__(self):
        return f"{self.member_number} — {self.first_name} {self.surname}"

    @property
    def full_name(self):
        parts = filter(None, [self.first_name, self.other_name, self.surname])
        return " ".join(parts)

    @property
    def age(self):
        if self.date_of_birth:
            today = timezone.now().date()
            return (
                today.year - self.date_of_birth.year
                - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
            )
        return None


class GLSchemeMemberDependent(models.Model):
    """
    Dependents covered under a member's group life policy.
    """



    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    member = models.ForeignKey(
        GLSchemeMember, on_delete=models.CASCADE, related_name="dependents"
    )
    relationship = models.CharField(max_length=20)
    first_name = models.CharField(max_length=100)
    surname = models.CharField(max_length=100)
    gender = models.CharField(max_length=10, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    sum_assured = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    premium_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    cover_start_date = models.DateField(null=True, blank=True)
    cover_end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gl_scheme_member_dependent"
        verbose_name = "GL Scheme Member Dependent"
        verbose_name_plural = "GL Scheme Member Dependents"
        ordering = ["member", "relationship", "surname"]

    def __str__(self):
        return f"{self.first_name} {self.surname} ({self.get_relationship_display()}) — {self.member.member_number}"


# =============================================================================
# LAYER 5 — MEDICAL UNDERWRITING
# =============================================================================


class GLMedicalCode(models.Model):
    """
    Medical diagnostic codes (ICD-10 aligned) for underwriting and claims.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    icd10_code = models.CharField(
        max_length=20, blank=True,
        help_text="ICD-10 standard classification code."
    )
    category = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gl_medical_code"
        verbose_name = "GL Medical Code"
        verbose_name_plural = "GL Medical Codes"
        ordering = ["code"]
        indexes = [
            models.Index(fields=["icd10_code"]),
            models.Index(fields=["category"]),
        ]

    def __str__(self):
        return f"{self.code} — {self.name}"


class GLMedicalLimit(models.Model):
    """
    Defines medical examination requirements based on age and sum assured thresholds.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        GLProduct, on_delete=models.CASCADE,
        null=True, blank=True, related_name="medical_limits",
        help_text="If null, applies to all products."
    )
    age_from = models.PositiveSmallIntegerField()
    age_to = models.PositiveSmallIntegerField()
    sum_assured_from = models.DecimalField(max_digits=18, decimal_places=2)
    sum_assured_to = models.DecimalField(
        max_digits=18, decimal_places=2, null=True, blank=True,
        help_text="Upper bound (null = unlimited)."
    )
    required_tests = models.JSONField(
        default=list,
        help_text="List of required test codes, e.g., ['ECG', 'HIV', 'LFT', 'FBS']"
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gl_medical_limit"
        verbose_name = "GL Medical Limit"
        verbose_name_plural = "GL Medical Limits"
        ordering = ["age_from", "sum_assured_from"]
        indexes = [
            models.Index(fields=["age_from", "age_to"]),
            models.Index(fields=["sum_assured_from", "sum_assured_to"]),
        ]

    def __str__(self):
        return f"Age {self.age_from}-{self.age_to}, SA {self.sum_assured_from}+"


class GLUnderwritingDecision(models.Model):
    """
    Possible underwriting decisions after medical evaluation.
    Examples: Standard, Premium Loading, Exclusion, Postpone, Decline.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    sort_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gl_underwriting_decision"
        verbose_name = "GL Underwriting Decision"
        verbose_name_plural = "GL Underwriting Decisions"
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class GLPersonalHabit(models.Model):
    """
    Personal habits and lifestyle factors affecting underwriting risk.
    """



    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=20)
    risk_level = models.CharField(max_length=10, default="LOW")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gl_personal_habit"
        verbose_name = "GL Personal Habit"
        verbose_name_plural = "GL Personal Habits"
        ordering = ["category", "name"]

    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"


class GLMedicalHistory(models.Model):
    """
    Medical history categories that impact underwriting decisions.
    """



    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=20)
    risk_impact = models.CharField(max_length=10, default="LOW")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gl_medical_history"
        verbose_name = "GL Medical History"
        verbose_name_plural = "GL Medical Histories"
        ordering = ["category", "name"]

    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"


class GLMedicalFacility(models.Model):
    """
    Approved medical facilities (hospitals, clinics, labs) for examinations.
    """


    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=300)
    facility_type = models.CharField(max_length=20)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    region = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    contact_person = models.CharField(max_length=200, blank=True)
    is_approved = models.BooleanField(default=False)
    approved_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gl_medical_facility"
        verbose_name = "GL Medical Facility"
        verbose_name_plural = "GL Medical Facilities"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["facility_type", "is_approved"]),
            models.Index(fields=["city"]),
            models.Index(fields=["region"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_facility_type_display()})"


class GLMedicalPractitioner(models.Model):
    """
    Licensed medical practitioners approved for underwriting examinations.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=300)
    specialization = models.CharField(max_length=200, blank=True)
    license_number = models.CharField(max_length=100, blank=True)
    facility = models.ForeignKey(
        GLMedicalFacility, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="practitioners",
    )
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    is_approved = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gl_medical_practitioner"
        verbose_name = "GL Medical Practitioner"
        verbose_name_plural = "GL Medical Practitioners"
        ordering = ["name"]

    def __str__(self):
        spec = f" — {self.specialization}" if self.specialization else ""
        return f"Dr. {self.name}{spec}"


class GLMedicalCase(models.Model):
    """
    Medical underwriting case for a scheme member whose sum assured exceeds
    the Free Cover Limit. Tracks examination, diagnosis, and decision.
    """


    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    member = models.ForeignKey(
        GLSchemeMember, on_delete=models.CASCADE, related_name="medical_cases"
    )
    case_number = models.CharField(max_length=50, unique=True, db_index=True)
    facility = models.ForeignKey(
        GLMedicalFacility, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="medical_cases",
    )
    practitioner = models.ForeignKey(
        GLMedicalPractitioner, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="medical_cases",
    )
    examination_date = models.DateField(null=True, blank=True)

    # Diagnosis and history
    diagnosis_codes = models.ManyToManyField(
        GLMedicalCode, related_name="medical_cases", blank=True
    )
    personal_habits = models.ManyToManyField(
        GLPersonalHabit, related_name="medical_cases", blank=True
    )
    medical_history = models.ManyToManyField(
        GLMedicalHistory, related_name="medical_cases", blank=True
    )

    # Questionnaire
    questionnaire = models.ForeignKey(
        GLHealthQuestionnaire, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="medical_cases",
    )
    questionnaire_responses = models.JSONField(
        blank=True, default=dict,
        help_text="Responses to the assigned questionnaire: {question_code: answer}"
    )

    # Decision
    decision = models.ForeignKey(
        GLUnderwritingDecision, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="medical_cases",
    )
    decision_notes = models.TextField(blank=True)
    premium_loading_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        help_text="Premium loading percentage applied after UW decision."
    )
    exclusions = models.JSONField(
        blank=True, default=list,
        help_text="List of excluded conditions/riders."
    )

    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="gl_uw_decisions",
    )
    decided_at = models.DateTimeField(null=True, blank=True)

    status = models.CharField(
        max_length=20, default="PENDING"
    )
    medical_report = models.FileField(
        upload_to="gl_medical_reports/%Y/%m/", blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gl_medical_case"
        verbose_name = "GL Medical Case"
        verbose_name_plural = "GL Medical Cases"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["case_number"]),
            models.Index(fields=["member"]),
            models.Index(fields=["status"]),
            models.Index(fields=["decision"]),
        ]

    def __str__(self):
        return f"{self.case_number} — {self.member.full_name}"


# =============================================================================
# LAYER 6 — CLAIMS PROCESSING
# =============================================================================


class GLClaimType(models.Model):
    """
    Classification of claim types.
    Examples: Death (Natural), Death (Accidental), PTD, Critical Illness, Funeral.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    requires_medical_report = models.BooleanField(
        default=True,
        help_text="Whether a medical report is mandatory for this claim type."
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gl_claim_type"
        verbose_name = "GL Claim Type"
        verbose_name_plural = "GL Claim Types"
        ordering = ["name"]

    def __str__(self):
        return self.name


class GLClaimReason(models.Model):
    """
    Specific reasons within a claim type.
    Example: Under Death (Natural) → Heart Disease, Cancer, Stroke.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    claim_type = models.ForeignKey(
        GLClaimType, on_delete=models.CASCADE, related_name="reasons"
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gl_claim_reason"
        verbose_name = "GL Claim Reason"
        verbose_name_plural = "GL Claim Reasons"
        ordering = ["claim_type", "name"]

    def __str__(self):
        return f"{self.claim_type.name} — {self.name}"


class GLClaimStatus(models.Model):
    """
    Claim verification milestones.
    Examples: LOGGED, DOCUMENT_VERIFICATION, INVESTIGATION, ASSESSED, APPROVED, PAID, REJECTED, CLOSED.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    sort_order = models.PositiveSmallIntegerField(default=0)
    is_terminal = models.BooleanField(
        default=False,
        help_text="If True, claim cannot transition out of this status."
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gl_claim_status"
        verbose_name = "GL Claim Status"
        verbose_name_plural = "GL Claim Statuses"
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class GLDischargeType(models.Model):
    """
    Discharge voucher types for claim settlements.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gl_discharge_type"
        verbose_name = "GL Discharge Type"
        verbose_name_plural = "GL Discharge Types"
        ordering = ["name"]

    def __str__(self):
        return self.name


class GLCorrespondentType(models.Model):
    """
    Types of external correspondents involved in claims communication.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gl_correspondent_type"
        verbose_name = "GL Correspondent Type"
        verbose_name_plural = "GL Correspondent Types"
        ordering = ["name"]

    def __str__(self):
        return self.name


class GLClaim(models.Model):
    """
    Core claim record for a group life member event (death, disability, illness).
    Tracks the full lifecycle from registration through assessment to settlement.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    claim_number = models.CharField(max_length=50, unique=True, db_index=True)
    scheme = models.ForeignKey(
        GLScheme, on_delete=models.PROTECT, related_name="claims"
    )
    member = models.ForeignKey(
        GLSchemeMember, on_delete=models.PROTECT, related_name="claims"
    )
    claim_type = models.ForeignKey(
        GLClaimType, on_delete=models.PROTECT, related_name="claims"
    )
    claim_reason = models.ForeignKey(
        GLClaimReason, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="claims",
    )
    status = models.ForeignKey(
        GLClaimStatus, on_delete=models.PROTECT, related_name="claims"
    )

    # Key dates
    incident_date = models.DateField(
        help_text="Date the insured event occurred."
    )
    notification_date = models.DateField(
        null=True, blank=True,
        help_text="Date ZIC was notified of the event."
    )
    registration_date = models.DateField(
        auto_now_add=True,
        help_text="Date the claim was formally registered in the system."
    )

    # Financial
    sum_assured_at_claim = models.DecimalField(
        max_digits=18, decimal_places=2, default=0,
        help_text="Member's sum assured at the time of claim."
    )
    claim_amount = models.DecimalField(
        max_digits=18, decimal_places=2, default=0,
        help_text="Total claimed amount."
    )
    approved_amount = models.DecimalField(
        max_digits=18, decimal_places=2, default=0,
        help_text="Amount approved for settlement."
    )
    paid_amount = models.DecimalField(
        max_digits=18, decimal_places=2, default=0,
        help_text="Total amount paid out so far."
    )
    currency = models.CharField(max_length=3, default="TZS")

    discharge_type = models.ForeignKey(
        GLDischargeType, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="claims",
    )

    # Claimant details
    claimant_name = models.CharField(max_length=300, blank=True)
    claimant_relationship = models.CharField(max_length=100, blank=True)
    claimant_id_number = models.CharField(max_length=100, blank=True)
    claimant_phone = models.CharField(max_length=20, blank=True)
    claimant_email = models.EmailField(blank=True)
    claimant_bank_name = models.CharField(max_length=200, blank=True)
    claimant_bank_account = models.CharField(max_length=50, blank=True)

    # Supporting documents
    medical_report = models.FileField(
        upload_to="gl_claim_medical_reports/%Y/%m/", blank=True
    )
    death_certificate = models.FileField(
        upload_to="gl_claim_death_certificates/%Y/%m/", blank=True
    )
    supporting_documents = models.JSONField(
        blank=True, default=list,
        help_text="Array of document references: [{name, file_url, type}]"
    )

    # Processing notes
    investigation_notes = models.TextField(blank=True)
    assessment_notes = models.TextField(blank=True)
    rejection_reason = models.TextField(blank=True)

    # Reinsurance
    reinsurance_notified = models.BooleanField(default=False)
    reinsurance_share = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        help_text="Reinsurer's share percentage of the claim."
    )
    reinsurance_amount = models.DecimalField(
        max_digits=18, decimal_places=2, default=0,
        help_text="Amount recoverable from reinsurer."
    )

    # Audit trail
    registered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="gl_claims_registered",
    )
    assessed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="gl_claims_assessed",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="gl_claims_approved",
    )
    paid_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="gl_claims_paid",
    )
    assessed_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gl_claim"
        verbose_name = "GL Claim"
        verbose_name_plural = "GL Claims"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["claim_number"]),
            models.Index(fields=["scheme"]),
            models.Index(fields=["member"]),
            models.Index(fields=["status"]),
            models.Index(fields=["claim_type"]),
            models.Index(fields=["incident_date"]),
            models.Index(fields=["scheme", "status"]),
        ]

    def __str__(self):
        return f"{self.claim_number} — {self.member.full_name} ({self.claim_type.name})"

    @property
    def outstanding_amount(self):
        return self.approved_amount - self.paid_amount


class GLClaimInstallment(models.Model):
    """
    Scheduled payment installments for claims paid in periodic tranches
    (e.g., disability annuities, funeral monthly payouts).
    """


    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    claim = models.ForeignKey(
        GLClaim, on_delete=models.CASCADE, related_name="installments"
    )
    installment_number = models.PositiveIntegerField()
    due_date = models.DateField()
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    status = models.CharField(
        max_length=20, default="SCHEDULED"
    )
    payment_reference = models.CharField(max_length=100, blank=True)
    payment_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gl_claim_installment"
        verbose_name = "GL Claim Installment"
        verbose_name_plural = "GL Claim Installments"
        ordering = ["claim", "installment_number"]
        unique_together = [("claim", "installment_number")]
        indexes = [
            models.Index(fields=["status", "due_date"]),
        ]

    def __str__(self):
        return f"{self.claim.claim_number} — Installment #{self.installment_number}"


class GLMedicalInvoice(models.Model):
    """
    Medical invoices submitted by facilities for member examinations or claim-related checkups.
    """


    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    claim = models.ForeignKey(
        GLClaim, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="medical_invoices",
    )
    member = models.ForeignKey(
        GLSchemeMember, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="medical_invoices",
    )
    invoice_number = models.CharField(max_length=100, unique=True)
    facility = models.ForeignKey(
        GLMedicalFacility, on_delete=models.PROTECT, related_name="invoices"
    )
    invoice_date = models.DateField()
    due_date = models.DateField(null=True, blank=True)
    total_amount = models.DecimalField(max_digits=18, decimal_places=2)
    approved_amount = models.DecimalField(
        max_digits=18, decimal_places=2, default=0
    )
    paid_amount = models.DecimalField(
        max_digits=18, decimal_places=2, default=0
    )
    currency = models.CharField(max_length=3, default="TZS")
    status = models.CharField(
        max_length=20, default="SUBMITTED"
    )
    notes = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="gl_invoices_reviewed",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="gl_invoices_approved",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gl_medical_invoice"
        verbose_name = "GL Medical Invoice"
        verbose_name_plural = "GL Medical Invoices"
        ordering = ["-invoice_date"]
        indexes = [
            models.Index(fields=["invoice_number"]),
            models.Index(fields=["status"]),
            models.Index(fields=["facility"]),
        ]

    def __str__(self):
        return f"Invoice {self.invoice_number} — {self.facility.name}"


# =============================================================================
# LAYER 7 — RENEWAL TRACKING
# =============================================================================


class GLSchemeRenewal(models.Model):
    """
    Tracks scheme renewal processing, including premium negotiations,
    experience rating adjustments, and renewal terms.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scheme = models.ForeignKey(
        GLScheme, on_delete=models.CASCADE, related_name="renewals"
    )
    renewal_number = models.CharField(max_length=50, unique=True, db_index=True)
    renewal_status = models.ForeignKey(
        GLSchemeRenewalStatus, on_delete=models.PROTECT, related_name="renewals"
    )

    current_expiry_date = models.DateField()
    proposed_renewal_date = models.DateField(null=True, blank=True)

    # Financial comparison
    previous_premium = models.DecimalField(
        max_digits=18, decimal_places=2, default=0
    )
    proposed_premium = models.DecimalField(
        max_digits=18, decimal_places=2, default=0
    )
    previous_experience_factor = models.DecimalField(
        max_digits=8, decimal_places=4, default=1.0000
    )
    proposed_experience_factor = models.DecimalField(
        max_digits=8, decimal_places=4, default=1.0000
    )
    claims_experience_ratio = models.DecimalField(
        max_digits=8, decimal_places=4, default=0,
        help_text="Claims paid / Premium earned ratio for the expiring period."
    )

    terms_document = models.FileField(
        upload_to="gl_renewal_documents/%Y/%m/", blank=True
    )
    notes = models.TextField(blank=True)

    initiated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="gl_renewals_initiated",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="gl_renewals_approved",
    )
    initiated_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gl_scheme_renewal"
        verbose_name = "GL Scheme Renewal"
        verbose_name_plural = "GL Scheme Renewals"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["renewal_number"]),
            models.Index(fields=["scheme"]),
            models.Index(fields=["renewal_status"]),
            models.Index(fields=["current_expiry_date"]),
        ]

    def __str__(self):
        return f"{self.renewal_number} — {self.scheme.scheme_number}"
