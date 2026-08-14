"""
Group Credit — Database Models

Implements the 7-layer architecture for the Group Credit Module:
1. Setup & Parameters
2. Products & Riders
3. Quotations
4. Schemes & Borrowers (Members)
5. Medical Underwriting
6. Claims
7. Renewals

All tables use the 'gc_' prefix to isolate them within the module namespace.
"""

import uuid
from decimal import Decimal

from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator


# =============================================================================
# LAYER 1 — SETUP & PARAMETERS
# =============================================================================

class GCSchemeType(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gc_scheme_type"
        ordering = ["name"]
        verbose_name_plural = "GC Scheme Types"

    def __str__(self):
        return f"{self.code} - {self.name}"


class GCSchemeStatus(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    sort_order = models.IntegerField(default=0)
    is_terminal = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gc_scheme_status"
        ordering = ["sort_order", "name"]
        verbose_name_plural = "GC Scheme Statuses"

    def __str__(self):
        return self.name


class GCSchemeMemberStatus(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gc_scheme_member_status"
        ordering = ["name"]
        verbose_name_plural = "GC Scheme Member Statuses"

    def __str__(self):
        return self.name


class GCSchemeRenewalStatus(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gc_scheme_renewal_status"
        ordering = ["name"]
        verbose_name_plural = "GC Scheme Renewal Statuses"

    def __str__(self):
        return self.name


class GCLookupValue(models.Model):
    """Generic configurable dropdown values for GC module.

    Groups values by `category` (e.g. RATE_TYPE, GENDER, RIDER_TYPE).
    The frontend fetches /lookup-values/?category=<CAT> to populate dropdowns.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.CharField(max_length=50, db_index=True, help_text="Grouping key, e.g. RATE_TYPE, GENDER")
    value = models.CharField(max_length=50, help_text="Stored value / code")
    label = models.CharField(max_length=200, help_text="Human-readable display label")
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gc_lookup_value"
        ordering = ["category", "sort_order", "label"]
        unique_together = ("category", "value")
        verbose_name_plural = "GC Lookup Values"

    def __str__(self):
        return f"{self.category}: {self.value} — {self.label}"

class GCSchemePremiumRate(models.Model):
    RATE_TYPE_CHOICES = [
        ("BASE", "Base Rate"),
        ("LOADING", "Loading"),
        ("DISCOUNT", "Discount"),
    ]
    GENDER_CHOICES = [
        ("M", "Male"),
        ("F", "Female"),
        ("U", "Unisex"),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    rate_type = models.CharField(max_length=20, default="BASE")
    age_band_start = models.IntegerField(validators=[MinValueValidator(0)])
    age_band_end = models.IntegerField(validators=[MaxValueValidator(120)])
    gender = models.CharField(max_length=10, default="U")
    occupation_class = models.CharField(max_length=50, blank=True, null=True)
    rate_per_mille = models.DecimalField(max_digits=10, decimal_places=4, default=Decimal('0.0000'))
    flat_rate = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'))
    effective_date = models.DateField()
    expiry_date = models.DateField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gc_scheme_premium_rate"
        ordering = ["rate_type", "age_band_start"]
        verbose_name_plural = "GC Scheme Premium Rates"

    def __str__(self):
        return f"{self.name} ({self.age_band_start}-{self.age_band_end})"


class GCHealthQuestion(models.Model):
    QUESTION_TYPE_CHOICES = [
        ("YES_NO", "Yes / No"),
        ("TEXT", "Text Input"),
        ("CHOICE", "Multiple Choice"),
    ]
    CATEGORY_CHOICES = [
        ("GENERAL", "General Health"),
        ("LIFESTYLE", "Lifestyle & Habits"),
        ("FAMILY", "Family History"),
        ("SPECIFIC", "Specific Conditions"),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True)
    question_text = models.TextField()
    question_type = models.CharField(max_length=20, default="YES_NO")
    category = models.CharField(max_length=50, default="GENERAL")
    options = models.JSONField(blank=True, null=True, help_text="JSON list for CHOICE type")
    sort_order = models.IntegerField(default=0)
    is_required = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gc_health_question"
        ordering = ["category", "sort_order"]

    def __str__(self):
        return self.code


class GCHealthQuestionnaire(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    version = models.CharField(max_length=20, default="1.0")
    questions = models.ManyToManyField(GCHealthQuestion, related_name="questionnaires")
    effective_date = models.DateField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gc_health_questionnaire"
        ordering = ["-effective_date", "name"]

    def __str__(self):
        return f"{self.name} v{self.version}"


# =============================================================================
# LAYER 2 — PRODUCTS & RIDERS
# =============================================================================

class GCSubProduct(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gc_sub_product"
        ordering = ["name"]

    def __str__(self):
        return f"{self.code} - {self.name}"


class GCProduct(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sub_product = models.ForeignKey(GCSubProduct, on_delete=models.PROTECT, related_name="products")
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    min_members = models.IntegerField(default=1)
    max_members = models.IntegerField(blank=True, null=True)
    min_loan_amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'))
    max_loan_amount = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    min_entry_age = models.IntegerField(default=18)
    max_entry_age = models.IntegerField(default=65)
    max_cover_age = models.IntegerField(default=70)
    free_cover_limit = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'))
    currency = models.CharField(max_length=10, default="TZS")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gc_product"
        ordering = ["name"]

    def __str__(self):
        return f"{self.code} - {self.name}"


class GCRider(models.Model):
    RIDER_TYPE_CHOICES = [
        ("PTD", "Permanent Total Disability"),
        ("PPD", "Permanent Partial Disability"),
        ("CI", "Critical Illness"),
        ("FE", "Funeral Expense"),
        ("RET", "Retrenchment"),
        ("OTHER", "Other"),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    rider_type = models.CharField(max_length=20, default="OTHER")
    is_mandatory = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gc_rider"
        ordering = ["name"]

    def __str__(self):
        return f"{self.code} - {self.name}"


class GCRiderRate(models.Model):
    GENDER_CHOICES = [("M", "Male"), ("F", "Female"), ("U", "Unisex")]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rider = models.ForeignKey(GCRider, on_delete=models.CASCADE, related_name="rates")
    age_band_start = models.IntegerField(validators=[MinValueValidator(0)])
    age_band_end = models.IntegerField(validators=[MaxValueValidator(120)])
    gender = models.CharField(max_length=10, default="U")
    rate_per_mille = models.DecimalField(max_digits=10, decimal_places=4, default=Decimal('0.0000'))
    flat_amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'))
    effective_date = models.DateField()
    expiry_date = models.DateField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gc_rider_rate"
        ordering = ["rider", "age_band_start"]

    def __str__(self):
        return f"{self.rider.name} ({self.age_band_start}-{self.age_band_end})"


# =============================================================================
# LAYER 3 — QUOTATIONS
# =============================================================================

class GCQuotation(models.Model):
    STATUS_CHOICES = [
        ("DRAFT", "Draft"),
        ("SUBMITTED", "Submitted"),
        ("UNDER_REVIEW", "Under Review"),
        ("APPROVED", "Approved"),
        ("DECLINED", "Declined"),
        ("CONVERTED", "Converted to Scheme"),
        ("EXPIRED", "Expired"),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    quotation_number = models.CharField(max_length=50, unique=True)
    partner = models.ForeignKey("partners.Partner", on_delete=models.PROTECT, related_name="gc_quotations")
    product = models.ForeignKey(GCProduct, on_delete=models.PROTECT, related_name="quotations")
    scheme_type = models.ForeignKey(GCSchemeType, on_delete=models.PROTECT, related_name="quotations", null=True, blank=True)
    status = models.CharField(max_length=20, default="DRAFT")
    quotation_date = models.DateField(auto_now_add=True)
    valid_until = models.DateField(blank=True, null=True)
    total_members = models.IntegerField(default=0)
    total_loan_amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'))
    total_annual_premium = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'))
    experience_rating_factor = models.DecimalField(max_digits=5, decimal_places=4, default=Decimal('1.0000'))
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    admin_loading_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    free_cover_limit = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'))
    notes = models.TextField(blank=True)
    prepared_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="gc_prepared_quotations")
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="gc_approved_quotations")
    approved_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gc_quotation"
        ordering = ["-created_at"]

    def __str__(self):
        return self.quotation_number


class GCQuotationCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    quotation = models.ForeignKey(GCQuotation, on_delete=models.CASCADE, related_name="categories")
    category_name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    flat_loan_amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'), help_text="Default loan amount if flat")
    member_count = models.IntegerField(default=0)
    total_loan_amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'))
    annual_premium = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'))
    premium_rate_per_mille = models.DecimalField(max_digits=10, decimal_places=4, default=Decimal('0.0000'))
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gc_quotation_category"
        ordering = ["quotation", "sort_order"]

    def __str__(self):
        return f"{self.quotation.quotation_number} - {self.category_name}"


class GCQuotationRider(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    quotation = models.ForeignKey(GCQuotation, on_delete=models.CASCADE, related_name="riders")
    rider = models.ForeignKey(GCRider, on_delete=models.PROTECT, related_name="quotations")
    rate_per_mille = models.DecimalField(max_digits=10, decimal_places=4, default=Decimal('0.0000'))
    total_premium = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gc_quotation_rider"
        unique_together = ("quotation", "rider")

    def __str__(self):
        return f"{self.quotation.quotation_number} - {self.rider.name}"


# =============================================================================
# LAYER 4 — SCHEMES & BORROWERS (MEMBERS)
# =============================================================================

class GCScheme(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scheme_number = models.CharField(max_length=50, unique=True)
    partner = models.ForeignKey("partners.Partner", on_delete=models.PROTECT, related_name="gc_schemes")
    product = models.ForeignKey(GCProduct, on_delete=models.PROTECT, related_name="schemes")
    scheme_type = models.ForeignKey(GCSchemeType, on_delete=models.PROTECT, related_name="schemes", null=True, blank=True)
    status = models.ForeignKey(GCSchemeStatus, on_delete=models.PROTECT, related_name="schemes")
    converted_from_quotation = models.OneToOneField(GCQuotation, on_delete=models.SET_NULL, null=True, blank=True, related_name="converted_scheme")
    inception_date = models.DateField()
    expiry_date = models.DateField(blank=True, null=True)
    renewal_date = models.DateField(blank=True, null=True)
    free_cover_limit = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'))
    experience_rating_factor = models.DecimalField(max_digits=5, decimal_places=4, default=Decimal('1.0000'))
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    admin_loading_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    total_members = models.IntegerField(default=0)
    total_sum_assured = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'))
    total_annual_premium = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'))
    currency = models.CharField(max_length=10, default="TZS")
    policy_document = models.FileField(upload_to="gc_policies/", blank=True, null=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="gc_created_schemes")
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="gc_updated_schemes")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gc_scheme"
        ordering = ["-created_at"]

    def __str__(self):
        return self.scheme_number

    @property
    def is_expired(self):
        from django.utils import timezone
        if self.expiry_date:
            return timezone.now().date() > self.expiry_date
        return False

    @property
    def days_until_expiry(self):
        from django.utils import timezone
        if self.expiry_date:
            delta = self.expiry_date - timezone.now().date()
            return delta.days
        return None


class GCSchemeCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scheme = models.ForeignKey(GCScheme, on_delete=models.CASCADE, related_name="categories")
    category_name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    flat_loan_amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'))
    premium_rate_per_mille = models.DecimalField(max_digits=10, decimal_places=4, default=Decimal('0.0000'))
    min_entry_age = models.IntegerField(default=18)
    max_entry_age = models.IntegerField(default=65)
    max_cover_age = models.IntegerField(default=70)
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gc_scheme_category"
        ordering = ["scheme", "sort_order"]

    def __str__(self):
        return f"{self.scheme.scheme_number} - {self.category_name}"


class GCSchemeRider(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scheme = models.ForeignKey(GCScheme, on_delete=models.CASCADE, related_name="riders")
    rider = models.ForeignKey(GCRider, on_delete=models.PROTECT, related_name="schemes")
    rate_per_mille = models.DecimalField(max_digits=10, decimal_places=4, default=Decimal('0.0000'))
    flat_amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'))
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gc_scheme_rider"
        unique_together = ("scheme", "rider")

    def __str__(self):
        return f"{self.scheme.scheme_number} - {self.rider.name}"


class GCSchemeMember(models.Model):
    GENDER_CHOICES = [("M", "Male"), ("F", "Female"), ("U", "Unisex")]
    UW_STATUS_CHOICES = [
        ("NOT_REQUIRED", "Not Required"),
        ("PENDING", "Pending UW"),
        ("STANDARD", "Standard"),
        ("LOADED", "Loaded"),
        ("EXCLUDED", "Exclusion"),
        ("DECLINED", "Declined"),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    member_number = models.CharField(max_length=50, unique=True)
    scheme = models.ForeignKey(GCScheme, on_delete=models.CASCADE, related_name="members")
    category = models.ForeignKey(GCSchemeCategory, on_delete=models.PROTECT, related_name="members", null=True, blank=True)
    status = models.ForeignKey(GCSchemeMemberStatus, on_delete=models.PROTECT, related_name="members")
    
    first_name = models.CharField(max_length=100)
    surname = models.CharField(max_length=100)
    other_name = models.CharField(max_length=100, blank=True)
    gender = models.CharField(max_length=10)
    date_of_birth = models.DateField()
    identification_type = models.CharField(max_length=50, blank=True)
    identification_number = models.CharField(max_length=100, blank=True)
    nationality = models.CharField(max_length=100, blank=True)
    
    # Loan specifics
    loan_account_number = models.CharField(max_length=100, blank=True)
    loan_amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'))
    loan_term_months = models.IntegerField(default=12)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    outstanding_balance = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'))
    date_of_loan = models.DateField(blank=True, null=True)
    
    # Cover specifics (Sum Assured conceptually identical to Initial Loan Amount, but kept separate for flexibility)
    sum_assured = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'))
    premium_amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'))
    cover_start_date = models.DateField(blank=True, null=True)
    cover_end_date = models.DateField(blank=True, null=True)
    
    # Medical UW Flags
    requires_medical_uw = models.BooleanField(default=False)
    uw_status = models.CharField(max_length=20, default="NOT_REQUIRED")
    premium_loading_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    
    email = models.EmailField(blank=True)
    mobile_number = models.CharField(max_length=20, blank=True)
    physical_address = models.TextField(blank=True)
    beneficiary_details = models.JSONField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gc_scheme_member"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.member_number} - {self.first_name} {self.surname}"

    @property
    def full_name(self):
        names = [self.first_name, self.other_name, self.surname]
        return " ".join(filter(None, names))

    @property
    def age(self):
        from django.utils import timezone
        today = timezone.now().date()
        return today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))


class GCSchemeMemberDependent(models.Model):
    RELATIONSHIP_CHOICES = [
        ("SPOUSE", "Spouse"),
        ("CHILD", "Child"),
        ("PARENT", "Parent"),
        ("OTHER", "Other"),
    ]
    GENDER_CHOICES = [("M", "Male"), ("F", "Female"), ("U", "Unisex")]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    member = models.ForeignKey(GCSchemeMember, on_delete=models.CASCADE, related_name="dependents")
    relationship = models.CharField(max_length=20)
    first_name = models.CharField(max_length=100)
    surname = models.CharField(max_length=100)
    gender = models.CharField(max_length=10)
    date_of_birth = models.DateField()
    sum_assured = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'))
    premium_amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'))
    cover_start_date = models.DateField(blank=True, null=True)
    cover_end_date = models.DateField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gc_scheme_member_dependent"
        ordering = ["member", "created_at"]

    def __str__(self):
        return f"{self.first_name} {self.surname} ({self.get_relationship_display()} of {self.member.member_number})"


# =============================================================================
# LAYER 5 — MEDICAL UNDERWRITING
# =============================================================================

class GCMedicalCode(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    icd10_code = models.CharField(max_length=50, blank=True)
    category = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gc_medical_code"
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} - {self.name}"


class GCMedicalLimit(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(GCProduct, on_delete=models.CASCADE, related_name="medical_limits")
    age_from = models.IntegerField(default=0)
    age_to = models.IntegerField(default=120)
    sum_assured_from = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'))
    sum_assured_to = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'))
    required_tests = models.JSONField(help_text="List of required medical test codes")
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gc_medical_limit"
        ordering = ["product", "age_from", "sum_assured_from"]

    def __str__(self):
        return f"Limits for {self.product.name} (Age {self.age_from}-{self.age_to})"


class GCUnderwritingDecision(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gc_underwriting_decision"
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class GCPersonalHabit(models.Model):
    CATEGORY_CHOICES = [
        ("SMOKING", "Smoking"),
        ("ALCOHOL", "Alcohol Consumption"),
        ("DRUGS", "Drug Use"),
        ("SPORTS", "Hazardous Sports"),
        ("OTHER", "Other"),
    ]
    RISK_LEVEL_CHOICES = [("LOW", "Low"), ("MEDIUM", "Medium"), ("HIGH", "High")]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=50)
    risk_level = models.CharField(max_length=20, default="LOW")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gc_personal_habit"
        ordering = ["category", "name"]

    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"


class GCMedicalHistory(models.Model):
    CATEGORY_CHOICES = [
        ("CARDIOVASCULAR", "Cardiovascular"),
        ("RESPIRATORY", "Respiratory"),
        ("NEUROLOGICAL", "Neurological"),
        ("ONCOLOGY", "Oncology"),
        ("METABOLIC", "Metabolic"),
        ("OTHER", "Other"),
    ]
    RISK_IMPACT_CHOICES = [("LOW", "Low"), ("MEDIUM", "Medium"), ("HIGH", "High"), ("DECLINE", "Decline")]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=50)
    risk_impact = models.CharField(max_length=20, default="LOW")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gc_medical_history"
        ordering = ["category", "name"]
        verbose_name_plural = "GC Medical Histories"

    def __str__(self):
        return f"{self.name} ({self.get_risk_impact_display()})"


class GCMedicalFacility(models.Model):
    FACILITY_TYPE_CHOICES = [
        ("HOSPITAL", "Hospital"),
        ("CLINIC", "Clinic"),
        ("LABORATORY", "Laboratory"),
        ("SPECIALIST", "Specialist Center"),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    facility_type = models.CharField(max_length=50)
    address = models.TextField()
    city = models.CharField(max_length=100)
    region = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    contact_person = models.CharField(max_length=100, blank=True)
    is_approved = models.BooleanField(default=True)
    approved_date = models.DateField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gc_medical_facility"
        ordering = ["name"]
        verbose_name_plural = "GC Medical Facilities"

    def __str__(self):
        return self.name


class GCMedicalPractitioner(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    specialization = models.CharField(max_length=100)
    license_number = models.CharField(max_length=100)
    facility = models.ForeignKey(GCMedicalFacility, on_delete=models.CASCADE, related_name="practitioners")
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    is_approved = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gc_medical_practitioner"
        ordering = ["name"]

    def __str__(self):
        return f"Dr. {self.name} - {self.specialization}"


class GCMedicalCase(models.Model):
    STATUS_CHOICES = [
        ("OPEN", "Open"),
        ("IN_PROGRESS", "In Progress"),
        ("COMPLETED", "Completed"),
        ("CANCELLED", "Cancelled"),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case_number = models.CharField(max_length=50, unique=True)
    member = models.ForeignKey(GCSchemeMember, on_delete=models.CASCADE, related_name="medical_cases")
    facility = models.ForeignKey(GCMedicalFacility, on_delete=models.PROTECT, related_name="medical_cases", null=True, blank=True)
    practitioner = models.ForeignKey(GCMedicalPractitioner, on_delete=models.PROTECT, related_name="medical_cases", null=True, blank=True)
    examination_date = models.DateField(blank=True, null=True)
    
    # Findings
    diagnosis_codes = models.ManyToManyField(GCMedicalCode, blank=True)
    personal_habits = models.ManyToManyField(GCPersonalHabit, blank=True)
    medical_history = models.ManyToManyField(GCMedicalHistory, blank=True)
    
    questionnaire = models.ForeignKey(GCHealthQuestionnaire, on_delete=models.PROTECT, null=True, blank=True)
    questionnaire_responses = models.JSONField(blank=True, null=True)
    
    decision = models.ForeignKey(GCUnderwritingDecision, on_delete=models.PROTECT, null=True, blank=True)
    decision_notes = models.TextField(blank=True)
    premium_loading_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    exclusions = models.JSONField(blank=True, null=True)
    
    decided_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="gc_uw_decisions")
    decided_at = models.DateTimeField(blank=True, null=True)
    
    status = models.CharField(max_length=20, default="OPEN")
    medical_report = models.FileField(upload_to="gc_medical_reports/", blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gc_medical_case"
        ordering = ["-created_at"]

    def __str__(self):
        return self.case_number


# =============================================================================
# LAYER 6 — CLAIMS
# =============================================================================

class GCClaimType(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    requires_medical_report = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gc_claim_type"
        ordering = ["name"]

    def __str__(self):
        return self.name


class GCClaimReason(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    claim_type = models.ForeignKey(GCClaimType, on_delete=models.CASCADE, related_name="reasons")
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gc_claim_reason"
        ordering = ["claim_type", "name"]

    def __str__(self):
        return f"{self.claim_type.name} - {self.name}"


class GCClaimStatus(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    sort_order = models.IntegerField(default=0)
    is_terminal = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gc_claim_status"
        ordering = ["sort_order", "name"]
        verbose_name_plural = "GC Claim Statuses"

    def __str__(self):
        return self.name


class GCDischargeType(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gc_discharge_type"
        ordering = ["name"]

    def __str__(self):
        return self.name


class GCCorrespondentType(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gc_correspondent_type"
        ordering = ["name"]

    def __str__(self):
        return self.name


class GCClaim(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    claim_number = models.CharField(max_length=50, unique=True)
    scheme = models.ForeignKey(GCScheme, on_delete=models.PROTECT, related_name="claims")
    member = models.ForeignKey(GCSchemeMember, on_delete=models.PROTECT, related_name="claims")
    claim_type = models.ForeignKey(GCClaimType, on_delete=models.PROTECT, related_name="claims")
    claim_reason = models.ForeignKey(GCClaimReason, on_delete=models.PROTECT, related_name="claims", null=True, blank=True)
    status = models.ForeignKey(GCClaimStatus, on_delete=models.PROTECT, related_name="claims")
    
    incident_date = models.DateField()
    notification_date = models.DateField()
    registration_date = models.DateField(auto_now_add=True)
    
    # Financials (Claim amount is typically outstanding balance in Credit Life)
    sum_assured_at_claim = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'))
    outstanding_balance_at_claim = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'))
    claim_amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'))
    approved_amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'))
    paid_amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'))
    currency = models.CharField(max_length=10, default="TZS")
    
    # Claimant details (usually the Partner / Bank, but could be next of kin if balance < SA)
    discharge_type = models.ForeignKey(GCDischargeType, on_delete=models.PROTECT, null=True, blank=True)
    claimant_name = models.CharField(max_length=200, blank=True)
    claimant_relationship = models.CharField(max_length=100, blank=True)
    claimant_id_number = models.CharField(max_length=100, blank=True)
    claimant_phone = models.CharField(max_length=50, blank=True)
    claimant_email = models.EmailField(blank=True)
    claimant_bank_name = models.CharField(max_length=100, blank=True)
    claimant_bank_account = models.CharField(max_length=100, blank=True)
    
    # Documentation
    medical_report = models.FileField(upload_to="gc_claims/medical/", blank=True, null=True)
    death_certificate = models.FileField(upload_to="gc_claims/death_certs/", blank=True, null=True)
    supporting_documents = models.FileField(upload_to="gc_claims/support/", blank=True, null=True)
    
    # Processing
    investigation_notes = models.TextField(blank=True)
    assessment_notes = models.TextField(blank=True)
    rejection_reason = models.TextField(blank=True)
    
    # Reinsurance tracking
    reinsurance_notified = models.BooleanField(default=False)
    reinsurance_share = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    reinsurance_amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'))
    
    # Timestamps & Audit
    registered_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="gc_registered_claims")
    assessed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="gc_assessed_claims")
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="gc_approved_claims")
    paid_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="gc_paid_claims")
    
    assessed_at = models.DateTimeField(blank=True, null=True)
    approved_at = models.DateTimeField(blank=True, null=True)
    paid_at = models.DateTimeField(blank=True, null=True)
    closed_at = models.DateTimeField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gc_claim"
        ordering = ["-created_at"]

    def __str__(self):
        return self.claim_number

    @property
    def outstanding_amount(self):
        return self.approved_amount - self.paid_amount


class GCClaimInstallment(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("PROCESSING", "Processing"),
        ("PAID", "Paid"),
        ("CANCELLED", "Cancelled"),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    claim = models.ForeignKey(GCClaim, on_delete=models.CASCADE, related_name="installments")
    installment_number = models.IntegerField()
    due_date = models.DateField()
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'))
    status = models.CharField(max_length=20, default="PENDING")
    payment_reference = models.CharField(max_length=100, blank=True)
    payment_date = models.DateField(blank=True, null=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gc_claim_installment"
        ordering = ["claim", "installment_number"]

    def __str__(self):
        return f"{self.claim.claim_number} - Installment {self.installment_number}"


class GCMedicalInvoice(models.Model):
    STATUS_CHOICES = [
        ("RECEIVED", "Received"),
        ("UNDER_REVIEW", "Under Review"),
        ("APPROVED", "Approved"),
        ("PAID", "Paid"),
        ("REJECTED", "Rejected"),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    claim = models.ForeignKey(GCClaim, on_delete=models.CASCADE, related_name="medical_invoices", null=True, blank=True)
    member = models.ForeignKey(GCSchemeMember, on_delete=models.CASCADE, related_name="medical_invoices", null=True, blank=True)
    invoice_number = models.CharField(max_length=100)
    facility = models.ForeignKey(GCMedicalFacility, on_delete=models.PROTECT, related_name="invoices")
    invoice_date = models.DateField()
    due_date = models.DateField(blank=True, null=True)
    total_amount = models.DecimalField(max_digits=18, decimal_places=2)
    approved_amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'))
    paid_amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'))
    currency = models.CharField(max_length=10, default="TZS")
    status = models.CharField(max_length=20, default="RECEIVED")
    notes = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="gc_reviewed_invoices")
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="gc_approved_invoices")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gc_medical_invoice"
        ordering = ["-invoice_date"]

    def __str__(self):
        return f"Invoice {self.invoice_number} from {self.facility.name}"


# =============================================================================
# LAYER 7 — RENEWALS
# =============================================================================

class GCSchemeRenewal(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    renewal_number = models.CharField(max_length=50, unique=True)
    scheme = models.ForeignKey(GCScheme, on_delete=models.CASCADE, related_name="renewals")
    renewal_status = models.ForeignKey(GCSchemeRenewalStatus, on_delete=models.PROTECT, related_name="renewals")
    
    current_expiry_date = models.DateField()
    proposed_renewal_date = models.DateField()
    
    previous_premium = models.DecimalField(max_digits=18, decimal_places=2)
    proposed_premium = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'))
    
    previous_experience_factor = models.DecimalField(max_digits=5, decimal_places=4, default=Decimal('1.0000'))
    proposed_experience_factor = models.DecimalField(max_digits=5, decimal_places=4, default=Decimal('1.0000'))
    
    claims_experience_ratio = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    
    terms_document = models.FileField(upload_to="gc_renewals/", blank=True, null=True)
    notes = models.TextField(blank=True)
    
    initiated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="gc_initiated_renewals")
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="gc_approved_renewals")
    
    initiated_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gc_scheme_renewal"
        ordering = ["-created_at"]

    def __str__(self):
        return self.renewal_number
