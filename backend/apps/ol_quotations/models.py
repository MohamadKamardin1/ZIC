import uuid
from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from django.utils import timezone


class QuotationStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    FINALIZED = "FINALIZED", "Finalized"
    CONVERTED = "CONVERTED", "Converted"
    EXPIRED = "EXPIRED", "Expired"


class QuotationBaseModel(models.Model):
    """Shared UUID, timestamp, and actor fields for quotation records."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(app_label)s_%(class)s_created",
    )
    updated_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(app_label)s_%(class)s_updated",
    )

    class Meta:
        abstract = True


class OLQuotation(QuotationBaseModel):
    """A draftable, auditable Ordinary Life quotation aggregate."""

    quote_number = models.CharField(max_length=50, unique=True, editable=False)
    quote_name = models.CharField(max_length=255, blank=True, default="")
    quote_date = models.DateField(default=timezone.localdate)
    status = models.CharField(
        max_length=20,
        choices=QuotationStatus.choices,
        default=QuotationStatus.DRAFT,
        db_index=True,
    )
    partner = models.ForeignKey(
        "partners.Partner",
        on_delete=models.PROTECT,
        related_name="ol_quotations_v2",
        null=True,
        blank=True,
    )
    linked_partner = models.ForeignKey(
        "partners.Partner",
        on_delete=models.PROTECT,
        related_name="linked_ol_quotations",
        null=True,
        blank=True,
    )
    product = models.ForeignKey(
        "ol_parameters.OLProduct",
        on_delete=models.PROTECT,
        related_name="quotations",
        null=True,
        blank=True,
    )
    product_version = models.ForeignKey(
        "ordinary_life.OLProductVersion",
        on_delete=models.PROTECT,
        related_name="parameter_quotations",
        null=True,
        blank=True,
    )
    currency = models.CharField(max_length=3, default="TZS")
    current_version_number = models.PositiveIntegerField(default=1)
    wizard_step_completion = models.JSONField(default=dict, blank=True)
    identity_type = models.CharField(max_length=50, blank=True, default="")
    identity_number = models.CharField(max_length=120, blank=True, default="")
    date_of_birth = models.DateField(null=True, blank=True)
    age_at_quote = models.PositiveSmallIntegerField(null=True, blank=True)
    gender = models.CharField(max_length=40, blank=True, default="")
    smoker_status = models.CharField(max_length=40, blank=True, default="")
    location = models.CharField(max_length=255, blank=True, default="")
    location_master = models.ForeignKey(
        "partner_onboarding.Location",
        on_delete=models.PROTECT,
        related_name="ol_quotations",
        null=True,
        blank=True,
    )
    agent = models.ForeignKey(
        "users.User",
        on_delete=models.PROTECT,
        related_name="ol_quotation_agent_records",
        null=True,
        blank=True,
    )
    agent_partner = models.ForeignKey(
        "partners.Partner",
        on_delete=models.PROTECT,
        related_name="ol_quotation_agent_records",
        null=True,
        blank=True,
    )
    address = models.TextField(blank=True, default="")
    partner_verified = models.BooleanField(default=False)
    approval_required = models.BooleanField(default=False)
    expiry_date = models.DateField(null=True, blank=True)
    total_sum_assured = models.DecimalField(
        max_digits=18, decimal_places=2, null=True, blank=True
    )
    total_premium = models.DecimalField(
        max_digits=18, decimal_places=2, null=True, blank=True
    )
    calculation_snapshot = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "ol_quotation_header"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["partner", "status", "created_at"]),
            models.Index(fields=["product", "status", "quote_date"]),
            models.Index(fields=["status", "expiry_date"]),
            models.Index(fields=["identity_type", "identity_number", "date_of_birth", "status"]),
            models.Index(fields=["agent_partner", "status", "created_at"]),
            models.Index(fields=["location_master", "status", "created_at"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=Q(total_sum_assured__isnull=True) | Q(total_sum_assured__gte=0),
                name="ol_quotation_total_sum_nonnegative",
            ),
            models.CheckConstraint(
                check=Q(total_premium__isnull=True) | Q(total_premium__gte=0),
                name="ol_quotation_total_premium_nonnegative",
            ),
        ]

    def clean(self):
        errors = {}
        self.quote_name = (self.quote_name or "").strip()
        self.currency = (self.currency or "").strip().upper()
        self.identity_type = (self.identity_type or "").strip().upper()
        self.gender = (self.gender or "").strip().upper()
        self.smoker_status = (self.smoker_status or "").strip().upper()
        if len(self.currency) != 3 or not self.currency.isalpha():
            errors["currency"] = "Currency must be a three-letter code."
        if self.expiry_date and self.expiry_date < self.quote_date:
            errors["expiry_date"] = "Expiry date cannot be before the quote date."
        if self.date_of_birth and self.date_of_birth > self.quote_date:
            errors["date_of_birth"] = "Date of birth cannot be after the quote date."
        if self.age_at_quote is not None and self.age_at_quote > 150:
            errors["age_at_quote"] = "Age cannot exceed 150 years."
        if self.current_version_number < 1:
            errors["current_version_number"] = "Current version number must be positive."
        if not isinstance(self.wizard_step_completion, dict):
            errors["wizard_step_completion"] = "Wizard step completion must be a JSON object."
        if self.status == QuotationStatus.CONVERTED and not self.calculation_snapshot:
            errors["calculation_snapshot"] = "A converted quotation must retain its calculation snapshot."
        if errors:
            raise ValidationError(errors)

    def calculate_age(self, as_of=None):
        if not self.date_of_birth:
            return None
        as_of = as_of or self.quote_date or date.today()
        return as_of.year - self.date_of_birth.year - (
            (as_of.month, as_of.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )

    def save(self, *args, **kwargs):
        if self.date_of_birth:
            self.age_at_quote = self.calculate_age()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.quote_number


class OLQuotationProduct(QuotationBaseModel):
    """Product and product-version selection captured in the quotation wizard."""

    quotation = models.ForeignKey(OLQuotation, on_delete=models.CASCADE, related_name="products")
    product = models.ForeignKey(
        "ol_parameters.OLProduct",
        on_delete=models.PROTECT,
        related_name="quotation_product_selections",
    )
    product_version = models.ForeignKey(
        "ordinary_life.OLProductVersion",
        on_delete=models.PROTECT,
        related_name="quotation_product_selections",
        null=True,
        blank=True,
    )
    product_name_snapshot = models.CharField(max_length=255, blank=True, default="")
    currency = models.CharField(max_length=3, default="TZS")
    is_selected = models.BooleanField(default=True)
    is_primary = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "ol_quotation_product"
        ordering = ["quotation", "-is_primary", "created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["quotation", "product", "product_version"],
                name="ol_quotation_product_scope_unique",
            ),
            models.UniqueConstraint(
                fields=["quotation"],
                condition=Q(is_primary=True),
                name="ol_quotation_one_primary_product",
            ),
        ]
        indexes = [
            models.Index(fields=["quotation", "is_selected"]),
            models.Index(fields=["product", "product_version"]),
        ]

    def clean(self):
        errors = {}
        self.currency = (self.currency or "").strip().upper()
        if len(self.currency) != 3 or not self.currency.isalpha():
            errors["currency"] = "Currency must be a three-letter code."
        if errors:
            raise ValidationError(errors)


class OLQuotationVersion(QuotationBaseModel):
    """Immutable version snapshot for quotation recalculation and conversion."""

    quotation = models.ForeignKey(OLQuotation, on_delete=models.CASCADE, related_name="versions")
    version_number = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=QuotationStatus.choices, default=QuotationStatus.DRAFT)
    snapshot = models.JSONField(default=dict, blank=True)
    change_reason = models.TextField(blank=True, default="")

    class Meta:
        db_table = "ol_quotations_version"
        ordering = ["quotation", "-version_number"]
        constraints = [
            models.UniqueConstraint(fields=["quotation", "version_number"], name="ol_quotations_version_unique")
        ]

    def clean(self):
        if self.version_number < 1:
            raise ValidationError({"version_number": "Version number must be positive."})
        if not isinstance(self.snapshot, dict):
            raise ValidationError({"snapshot": "Version snapshot must be a JSON object."})


class OLQuotationBenefit(QuotationBaseModel):
    """Optional benefit selection retained separately from rider selection."""

    quotation = models.ForeignKey(OLQuotation, on_delete=models.CASCADE, related_name="benefits")
    code = models.CharField(max_length=80)
    name = models.CharField(max_length=255)
    benefit_type = models.CharField(max_length=80, blank=True, default="")
    sum_assured = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    premium_amount = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    is_selected = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "ol_quotation_benefit"
        ordering = ["quotation", "code"]
        constraints = [
            models.UniqueConstraint(fields=["quotation", "code"], name="ol_quotation_benefit_code_unique"),
            models.CheckConstraint(check=Q(sum_assured__isnull=True) | Q(sum_assured__gte=0), name="ol_quotation_benefit_sum_nonnegative"),
            models.CheckConstraint(check=Q(premium_amount__isnull=True) | Q(premium_amount__gte=0), name="ol_quotation_benefit_premium_nonnegative"),
        ]

    def clean(self):
        errors = {}
        self.code = (self.code or "").strip().upper()
        self.name = (self.name or "").strip()
        if not self.code:
            errors["code"] = "Benefit code is required."
        if not self.name:
            errors["name"] = "Benefit name is required."
        if self.sum_assured is not None and self.sum_assured < 0:
            errors["sum_assured"] = "Benefit sum assured cannot be negative."
        if self.premium_amount is not None and self.premium_amount < 0:
            errors["premium_amount"] = "Benefit premium cannot be negative."
        if errors:
            raise ValidationError(errors)


class OLQuotationFinancialSummary(QuotationBaseModel):
    """Persisted financial totals prepared for future print and conversion flows."""

    quotation = models.OneToOneField(OLQuotation, on_delete=models.CASCADE, related_name="financial_summary")
    total_sum_assured = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))
    total_premium = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))
    total_rider_premium = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))
    total_benefit_premium = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))
    currency = models.CharField(max_length=3, default="TZS")
    calculation_snapshot = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "ol_quotation_financial_summary"

    def clean(self):
        errors = {}
        self.currency = (self.currency or "").strip().upper()
        if len(self.currency) != 3 or not self.currency.isalpha():
            errors["currency"] = "Currency must be a three-letter code."
        for field in ("total_sum_assured", "total_premium", "total_rider_premium", "total_benefit_premium"):
            if getattr(self, field) is not None and getattr(self, field) < 0:
                errors[field] = "Financial values cannot be negative."
        if errors:
            raise ValidationError(errors)


class OLQuotationDocument(QuotationBaseModel):
    """Document reference captured during quotation preparation."""

    quotation = models.ForeignKey(OLQuotation, on_delete=models.CASCADE, related_name="documents")
    document_type = models.CharField(max_length=80)
    file_reference = models.CharField(max_length=500)
    status = models.CharField(max_length=40, default="PENDING")
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "ol_quotation_document"
        ordering = ["quotation", "document_type", "created_at"]
        indexes = [models.Index(fields=["quotation", "document_type", "status"])]

    def clean(self):
        errors = {}
        self.document_type = (self.document_type or "").strip().upper()
        self.file_reference = (self.file_reference or "").strip()
        if not self.document_type:
            errors["document_type"] = "Document type is required."
        if not self.file_reference:
            errors["file_reference"] = "File reference is required."
        if errors:
            raise ValidationError(errors)


class OLQuotationPlanConfiguration(QuotationBaseModel):
    """A selected product-version/plan/sub-product configuration in a quote."""

    quotation = models.ForeignKey(
        OLQuotation, on_delete=models.CASCADE, related_name="plan_configurations"
    )
    product_version = models.ForeignKey(
        "ordinary_life.OLProductVersion",
        on_delete=models.PROTECT,
        related_name="quotation_plan_configurations",
    )
    plan = models.ForeignKey(
        "ordinary_life.OLPlan",
        on_delete=models.PROTECT,
        related_name="quotation_plan_configurations",
        null=True,
        blank=True,
    )
    sub_product_code = models.CharField(max_length=80, blank=True)
    is_selected = models.BooleanField(default=True)
    base_sum_assured = models.DecimalField(max_digits=18, decimal_places=2)
    term_years = models.PositiveSmallIntegerField()
    premium_frequency = models.CharField(max_length=40)
    premium_amount = models.DecimalField(
        max_digits=18, decimal_places=2, null=True, blank=True
    )
    coverage_rules = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "ol_quotation_plan_configuration"
        ordering = ["quotation", "-is_selected", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["quotation", "product_version", "plan", "sub_product_code"],
                name="ol_quotation_plan_config_scope_unique",
            ),
            models.CheckConstraint(
                check=Q(base_sum_assured__gt=0),
                name="ol_quotation_plan_config_sum_positive",
            ),
            models.CheckConstraint(
                check=Q(term_years__gt=0),
                name="ol_quotation_plan_config_term_positive",
            ),
            models.CheckConstraint(
                check=Q(premium_amount__isnull=True) | Q(premium_amount__gte=0),
                name="ol_quotation_plan_config_premium_nonnegative",
            ),
        ]
        indexes = [
            models.Index(fields=["quotation", "is_selected"]),
            models.Index(fields=["product_version", "plan"]),
        ]

    def clean(self):
        errors = {}
        self.premium_frequency = (self.premium_frequency or "").strip().upper()
        if not self.premium_frequency:
            errors["premium_frequency"] = "Premium frequency is required."
        if self.base_sum_assured is not None and self.base_sum_assured <= 0:
            errors["base_sum_assured"] = "Base sum assured must be greater than zero."
        if self.term_years is not None and self.term_years <= 0:
            errors["term_years"] = "Term must be greater than zero."
        if self.product_version_id and self.quotation_id:
            quotation = self.quotation
            if quotation.product_version_id and quotation.product_version_id != self.product_version_id:
                errors["product_version"] = "Plan configuration product version must match the quotation product version."
        if errors:
            raise ValidationError(errors)


class OLQuotationMember(QuotationBaseModel):
    """Policyholder, life assured, dependent, or other quoted life member."""

    MEMBER_TYPES = (
        ("POLICYHOLDER", "Policyholder"),
        ("LIFE_ASSURED", "Life assured"),
        ("DEPENDENT", "Dependent"),
        ("OTHER", "Other"),
    )

    quotation = models.ForeignKey(
        OLQuotation, on_delete=models.CASCADE, related_name="members"
    )
    member_type = models.CharField(max_length=30)
    partner = models.ForeignKey(
        "partners.Partner",
        on_delete=models.PROTECT,
        related_name="ol_quotation_members",
        null=True,
        blank=True,
    )
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    identity_number = models.CharField(max_length=120, blank=True)
    date_of_birth = models.DateField()
    age_at_quote = models.PositiveSmallIntegerField(null=True, blank=True)
    gender = models.CharField(max_length=40, blank=True)
    smoker_status = models.CharField(max_length=40, blank=True)
    relationship = models.CharField(max_length=80, blank=True)
    contact_phone = models.CharField(max_length=40, blank=True)
    contact_email = models.EmailField(blank=True)
    member_sum_assured = models.DecimalField(
        max_digits=18, decimal_places=2, null=True, blank=True
    )
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "ol_quotation_member"
        ordering = ["quotation", "member_type", "last_name", "first_name"]
        indexes = [
            models.Index(fields=["quotation", "member_type"]),
            models.Index(fields=["identity_number"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=Q(member_sum_assured__isnull=True) | Q(member_sum_assured__gte=0),
                name="ol_quotation_member_sum_nonnegative",
            ),
        ]

    def clean(self):
        errors = {}
        self.member_type = (self.member_type or "").strip().upper()
        self.gender = (self.gender or "").strip().upper()
        self.smoker_status = (self.smoker_status or "").strip().upper()
        if not self.member_type:
            errors["member_type"] = "Member type is required."
        if self.date_of_birth and self.date_of_birth > date.today():
            errors["date_of_birth"] = "Date of birth cannot be in the future."
        if self.age_at_quote is not None and self.age_at_quote > 150:
            errors["age_at_quote"] = "Age cannot exceed 150 years."
        if errors:
            raise ValidationError(errors)

    def calculate_age(self, as_of=None):
        as_of = as_of or date.today()
        return as_of.year - self.date_of_birth.year - (
            (as_of.month, as_of.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )

    def save(self, *args, **kwargs):
        if self.date_of_birth and self.age_at_quote is None:
            self.age_at_quote = self.calculate_age(self.quotation.quote_date if self.quotation_id else None)
        super().save(*args, **kwargs)


class OLQuotationInstallmentConfiguration(QuotationBaseModel):
    """Payment frequency and installment values selected for a quotation."""

    quotation = models.ForeignKey(
        OLQuotation, on_delete=models.CASCADE, related_name="installment_configurations"
    )
    plan_configuration = models.ForeignKey(
        OLQuotationPlanConfiguration,
        on_delete=models.CASCADE,
        related_name="installment_configurations",
        null=True,
        blank=True,
    )
    frequency = models.CharField(max_length=40)
    number_of_installments = models.PositiveIntegerField(default=1)
    installment_amount = models.DecimalField(max_digits=18, decimal_places=2)
    first_due_date = models.DateField(null=True, blank=True)
    currency = models.CharField(max_length=3, default="TZS")
    is_selected = models.BooleanField(default=True)

    class Meta:
        db_table = "ol_quotation_installment_configuration"
        ordering = ["quotation", "frequency"]
        constraints = [
            models.UniqueConstraint(
                fields=["quotation", "plan_configuration", "frequency"],
                name="ol_quotation_installment_scope_unique",
            ),
            models.CheckConstraint(
                check=Q(number_of_installments__gt=0),
                name="ol_quotation_installment_count_positive",
            ),
            models.CheckConstraint(
                check=Q(installment_amount__gt=0),
                name="ol_quotation_installment_amount_positive",
            ),
        ]
        indexes = [models.Index(fields=["quotation", "is_selected", "frequency"])]

    def clean(self):
        errors = {}
        self.frequency = (self.frequency or "").strip().upper()
        self.currency = (self.currency or "").strip().upper()
        if not self.frequency:
            errors["frequency"] = "Installment frequency is required."
        if len(self.currency) != 3 or not self.currency.isalpha():
            errors["currency"] = "Currency must be a three-letter code."
        if self.installment_amount is not None and self.installment_amount <= 0:
            errors["installment_amount"] = "Installment amount must be greater than zero."
        if errors:
            raise ValidationError(errors)


class OLQuotationInstallmentRateRow(QuotationBaseModel):
    """Rate/charge rows behind an installment configuration."""

    installment_configuration = models.ForeignKey(
        OLQuotationInstallmentConfiguration,
        on_delete=models.CASCADE,
        related_name="rate_rows",
    )
    period_from = models.PositiveIntegerField()
    period_to = models.PositiveIntegerField()
    rate = models.DecimalField(max_digits=18, decimal_places=8)
    charge = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "ol_quotation_installment_rate_row"
        ordering = ["installment_configuration", "period_from"]
        constraints = [
            models.UniqueConstraint(
                fields=["installment_configuration", "period_from", "period_to"],
                name="ol_quotation_installment_rate_scope_unique",
            ),
            models.CheckConstraint(
                check=Q(period_from__gt=0) & Q(period_to__gte=F("period_from")),
                name="ol_quotation_installment_rate_period_valid",
            ),
            models.CheckConstraint(
                check=Q(rate__gte=0) & Q(charge__gte=0),
                name="ol_quotation_installment_rate_nonnegative",
            ),
        ]

    def clean(self):
        errors = {}
        if self.period_from <= 0 or self.period_to < self.period_from:
            errors["period_to"] = "Rate period must be positive and end on or after its start."
        if self.rate is not None and self.rate < 0:
            errors["rate"] = "Rate cannot be negative."
        candidates = self.__class__.objects.filter(
            installment_configuration=self.installment_configuration
        ).exclude(pk=self.pk)
        for candidate in candidates:
            if self.period_from <= candidate.period_to and candidate.period_from <= self.period_to:
                errors["period_from"] = "Rate periods cannot overlap within an installment configuration."
                break
        if errors:
            raise ValidationError(errors)


class OLQuotationFundAllocation(QuotationBaseModel):
    """Allocation of quoted value or premium to an active configured fund."""

    quotation = models.ForeignKey(
        OLQuotation, on_delete=models.CASCADE, related_name="fund_allocations"
    )
    fund = models.ForeignKey(
        "ol_parameters.OLInvestmentFund",
        on_delete=models.PROTECT,
        related_name="quotation_allocations",
    )
    allocation_percentage = models.DecimalField(max_digits=7, decimal_places=4)
    allocation_amount = models.DecimalField(
        max_digits=18, decimal_places=2, null=True, blank=True
    )
    is_selected = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "ol_quotation_fund_allocation"
        ordering = ["quotation", "fund__code"]
        constraints = [
            models.UniqueConstraint(
                fields=["quotation", "fund"], name="ol_quotation_fund_unique"
            ),
            models.CheckConstraint(
                check=Q(allocation_percentage__gte=0) & Q(allocation_percentage__lte=100),
                name="ol_quotation_fund_percentage_range",
            ),
            models.CheckConstraint(
                check=Q(allocation_amount__isnull=True) | Q(allocation_amount__gte=0),
                name="ol_quotation_fund_amount_nonnegative",
            ),
        ]

    def clean(self):
        errors = {}
        if self.allocation_percentage is None or not 0 <= self.allocation_percentage <= 100:
            errors["allocation_percentage"] = "Allocation percentage must be between 0 and 100."
        if errors:
            raise ValidationError(errors)


class OLQuotationRiderSelection(QuotationBaseModel):
    """Rider selections driven by OL Rider Setup configuration."""

    quotation = models.ForeignKey(
        OLQuotation, on_delete=models.CASCADE, related_name="rider_selections"
    )
    rider = models.ForeignKey(
        "ol_parameters.OLRiderSetup",
        on_delete=models.PROTECT,
        related_name="quotation_selections",
    )
    plan_configuration = models.ForeignKey(
        OLQuotationPlanConfiguration,
        on_delete=models.CASCADE,
        related_name="rider_selections",
        null=True,
        blank=True,
    )
    rider_sum_assured = models.DecimalField(max_digits=18, decimal_places=2)
    premium_amount = models.DecimalField(
        max_digits=18, decimal_places=2, null=True, blank=True
    )
    is_selected = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "ol_quotation_rider_selection"
        ordering = ["quotation", "rider__code"]
        constraints = [
            models.UniqueConstraint(
                fields=["quotation", "rider", "plan_configuration"],
                name="ol_quotation_rider_scope_unique",
            ),
            models.CheckConstraint(
                check=Q(rider_sum_assured__gt=0),
                name="ol_quotation_rider_sum_positive",
            ),
            models.CheckConstraint(
                check=Q(premium_amount__isnull=True) | Q(premium_amount__gte=0),
                name="ol_quotation_rider_premium_nonnegative",
            ),
        ]

    def clean(self):
        errors = {}
        if self.rider_sum_assured is not None and self.rider_sum_assured <= 0:
            errors["rider_sum_assured"] = "Rider sum assured must be greater than zero."
        if errors:
            raise ValidationError(errors)


class OLQuotationPaymentDetail(QuotationBaseModel):
    """Payment method and payer detail captured during quotation preparation."""

    quotation = models.OneToOneField(
        OLQuotation, on_delete=models.CASCADE, related_name="payment_detail"
    )
    payer = models.ForeignKey(
        "partners.Partner",
        on_delete=models.PROTECT,
        related_name="ol_quotation_payment_details",
        null=True,
        blank=True,
    )
    payment_method = models.CharField(max_length=50)
    account_reference = models.CharField(max_length=150, blank=True)
    payment_reference = models.CharField(max_length=150, blank=True)
    amount = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default="TZS")
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "ol_quotation_payment_detail"

    def clean(self):
        errors = {}
        self.payment_method = (self.payment_method or "").strip().upper()
        self.currency = (self.currency or "").strip().upper()
        if not self.payment_method:
            errors["payment_method"] = "Payment method is required."
        if len(self.currency) != 3 or not self.currency.isalpha():
            errors["currency"] = "Currency must be a three-letter code."
        if self.amount is not None and self.amount < 0:
            errors["amount"] = "Payment amount cannot be negative."
        if errors:
            raise ValidationError(errors)


class OLQuotationUnderwriting(QuotationBaseModel):
    """Underwriting answers and calculated medical/financial flags for the quote."""

    quotation = models.OneToOneField(
        OLQuotation, on_delete=models.CASCADE, related_name="underwriting_detail"
    )
    medical_required = models.BooleanField(default=False)
    financial_underwriting_required = models.BooleanField(default=False)
    risk_class = models.CharField(max_length=60, blank=True)
    health_answers = models.JSONField(default=dict, blank=True)
    medical_requirements = models.JSONField(default=list, blank=True)
    declarations = models.JSONField(default=dict, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "ol_quotation_underwriting"

    def clean(self):
        errors = {}
        if not isinstance(self.health_answers, dict):
            errors["health_answers"] = "Health answers must be a JSON object."
        if not isinstance(self.medical_requirements, list):
            errors["medical_requirements"] = "Medical requirements must be a JSON list."
        if not isinstance(self.declarations, dict):
            errors["declarations"] = "Declarations must be a JSON object."
        if errors:
            raise ValidationError(errors)


class OLQuotationBeneficiary(QuotationBaseModel):
    """Beneficiary allocation captured for future proposal/policy conversion."""

    quotation = models.ForeignKey(
        OLQuotation, on_delete=models.CASCADE, related_name="beneficiaries"
    )
    partner = models.ForeignKey(
        "partners.Partner",
        on_delete=models.PROTECT,
        related_name="ol_quotation_beneficiaries",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=255)
    relationship = models.CharField(max_length=100)
    percentage = models.DecimalField(max_digits=7, decimal_places=4)
    identity_number = models.CharField(max_length=120, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "ol_quotation_beneficiary"
        ordering = ["quotation", "name"]
        constraints = [
            models.CheckConstraint(
                check=Q(percentage__gt=0) & Q(percentage__lte=100),
                name="ol_quotation_beneficiary_percentage_range",
            ),
        ]
        indexes = [models.Index(fields=["quotation", "percentage"])]

    def clean(self):
        errors = {}
        if not (self.name or "").strip():
            errors["name"] = "Beneficiary name is required."
        if self.percentage is None or not 0 < self.percentage <= 100:
            errors["percentage"] = "Beneficiary percentage must be greater than zero and at most 100."
        if errors:
            raise ValidationError(errors)


class OLQuotationEvent(models.Model):
    """Immutable quotation lifecycle and wizard history row."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    quotation = models.ForeignKey(
        OLQuotation, on_delete=models.CASCADE, related_name="events"
    )
    event_type = models.CharField(max_length=80)
    from_status = models.CharField(max_length=20, blank=True)
    to_status = models.CharField(max_length=20, blank=True)
    actor = models.ForeignKey(
        "users.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="ol_quotation_events"
    )
    notes = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ol_quotation_event"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["quotation", "created_at"]),
            models.Index(fields=["event_type", "created_at"]),
        ]

    def __str__(self):
        return f"{self.quotation.quote_number}:{self.event_type}"


# Specification-compatible aliases retained for downstream quotation and frontend contracts.
OLQuotationPlanConfig = OLQuotationPlanConfiguration
OLQuotationInstallmentConfig = OLQuotationInstallmentConfiguration
OLQuotationRider = OLQuotationRiderSelection
