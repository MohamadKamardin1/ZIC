import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class OLParameterBaseModel(models.Model):
    """Common identity, lifecycle, effective-dating, and audit fields for OL parameters."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=100)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True, db_index=True)
    effective_from = models.DateField(null=True, blank=True, db_index=True)
    effective_to = models.DateField(null=True, blank=True, db_index=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["name", "code"]
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(effective_to__isnull=True)
                    | models.Q(effective_from__isnull=True)
                    | models.Q(effective_to__gte=models.F("effective_from"))
                ),
                name="%(app_label)s_%(class)s_effective_dates_valid",
            ),
        ]
        indexes = [
            models.Index(
                fields=["is_active", "effective_from", "effective_to"],
                name="%(app_label)s_%(class)s_active_dates_idx",
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.code})"

    def clean(self):
        super().clean()
        self.code = (self.code or "").strip()
        self.name = (self.name or "").strip()
        if not self.code:
            raise ValidationError({"code": "A parameter code is required."})
        if not self.name:
            raise ValidationError({"name": "A parameter name is required."})
        if self.effective_from and self.effective_to and self.effective_to < self.effective_from:
            raise ValidationError({"effective_to": "Effective-to cannot be before effective-from."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def deactivate(self):
        self.is_active = False


class OLEffectiveDateModel(OLParameterBaseModel):
    """Base for parameters whose effective-from date is mandatory."""

    class Meta:
        abstract = True

    def clean(self):
        super().clean()
        if not self.effective_from:
            raise ValidationError({"effective_from": "Effective-from is required for this parameter."})


class OLRateTableVersionModel(OLParameterBaseModel):
    """Version header for rate tables, allowing controlled supersession."""

    version = models.CharField(max_length=50)
    supersedes = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="superseding_versions",
    )
    is_current = models.BooleanField(default=False, db_index=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True
        constraints = [
            models.UniqueConstraint(
                fields=["code", "version"],
                name="%(app_label)s_%(class)s_code_version_unique",
            ),
        ]
        indexes = [
            models.Index(
                fields=["code", "is_current", "is_active"],
                name="%(app_label)s_%(class)s_current_idx",
            ),
        ]

    def clean(self):
        super().clean()
        self.version = (self.version or "").strip()
        if not self.version:
            raise ValidationError({"version": "A rate-table version is required."})
        if self.supersedes_id and self.pk and self.supersedes_id == self.pk:
            raise ValidationError({"supersedes": "A rate-table version cannot supersede itself."})


class OLRateRowBaseModel(models.Model):
    """Dimension fields shared by product/plan/age/gender/term rate rows."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product_code = models.CharField(max_length=100, blank=True, default="", db_index=True)
    plan_code = models.CharField(max_length=100, blank=True, default="", db_index=True)
    age_from = models.PositiveSmallIntegerField(null=True, blank=True)
    age_to = models.PositiveSmallIntegerField(null=True, blank=True)
    gender = models.CharField(max_length=30, blank=True, default="", db_index=True)
    term = models.PositiveIntegerField(null=True, blank=True, db_index=True)
    effective_from = models.DateField(null=True, blank=True, db_index=True)
    effective_to = models.DateField(null=True, blank=True, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    row_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["row_order", "age_from", "age_to"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(age_to__isnull=True)
                | models.Q(age_from__isnull=True)
                | models.Q(age_to__gte=models.F("age_from")),
                name="%(app_label)s_%(class)s_age_range_valid",
            ),
            models.CheckConstraint(
                check=(
                    models.Q(effective_to__isnull=True)
                    | models.Q(effective_from__isnull=True)
                    | models.Q(effective_to__gte=models.F("effective_from"))
                ),
                name="%(app_label)s_%(class)s_effective_dates_valid",
            ),
        ]
        indexes = [
            models.Index(
                fields=["product_code", "plan_code", "is_active"],
                name="%(app_label)s_%(class)s_dimension_idx",
            ),
            models.Index(
                fields=["effective_from", "effective_to"],
                name="%(app_label)s_%(class)s_dates_idx",
            ),
        ]

    def clean(self):
        super().clean()
        if self.age_from is not None and self.age_to is not None and self.age_to < self.age_from:
            raise ValidationError({"age_to": "Age-to cannot be less than age-from."})
        if self.effective_from and self.effective_to and self.effective_to < self.effective_from:
            raise ValidationError({"effective_to": "Effective-to cannot be before effective-from."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class OLParameterTableRegistry(models.Model):
    """Declarative table contract consumed by admin, APIs, and future frontends."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(max_length=120, unique=True)
    label = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    parameter_group = models.CharField(max_length=80, blank=True, default="", db_index=True)
    model_label = models.CharField(
        max_length=200,
        help_text="Django app_label.ModelName or a future resource identifier.",
    )
    visible_columns = models.JSONField(default=list, blank=True)
    searchable_fields = models.JSONField(default=list, blank=True)
    filter_fields = models.JSONField(default=list, blank=True)
    default_ordering = models.JSONField(default=list, blank=True)
    allowed_actions = models.JSONField(default=list, blank=True)
    export_support = models.BooleanField(default=False)
    permission_code = models.CharField(max_length=120, default="ol_parameters.view")
    permission_requirements = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_ol_parameter_tables",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_ol_parameter_tables",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["parameter_group", "label", "slug"]
        indexes = [
            models.Index(fields=["is_active", "parameter_group"], name="ol_pr_registry_act_grp_idx"),
            models.Index(fields=["model_label"], name="ol_params_registry_model_idx"),
        ]

    def __str__(self):
        return f"{self.label} ({self.slug})"

    def clean(self):
        super().clean()
        self.slug = slugify(self.slug or "")
        self.label = (self.label or "").strip()
        self.model_label = (self.model_label or "").strip()
        self.permission_code = (self.permission_code or "").strip().lower()
        if not self.slug:
            raise ValidationError({"slug": "A non-empty table slug is required."})
        if not self.label:
            raise ValidationError({"label": "A table label is required."})
        if not self.model_label:
            raise ValidationError({"model_label": "A model/resource identifier is required."})
        if "." not in self.permission_code:
            raise ValidationError({"permission_code": "Permission code must use module.action notation."})
        for field_name in ("visible_columns", "searchable_fields", "filter_fields", "default_ordering", "allowed_actions"):
            value = getattr(self, field_name)
            if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
                raise ValidationError({field_name: "This metadata field must be a list of non-empty strings."})
        if not isinstance(self.permission_requirements, dict):
            raise ValidationError({"permission_requirements": "Permission requirements must be a JSON object."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def required_permission(self, action="view"):
        configured = self.permission_requirements.get(action) if isinstance(self.permission_requirements, dict) else None
        return configured or self.permission_code


class OLDefaultParameterValueType(models.TextChoices):
    STRING = "STRING", "String"
    TEXT = "TEXT", "Text"
    INTEGER = "INTEGER", "Integer"
    DECIMAL = "DECIMAL", "Decimal"
    BOOLEAN = "BOOLEAN", "Boolean"
    DATE = "DATE", "Date"
    JSON = "JSON", "JSON"


class OLDefaultSystemParameter(OLParameterBaseModel):
    """Typed, effective-dated default used by Ordinary Life workflows."""

    parameter_key = models.CharField(max_length=100, unique=True)
    parameter_category = models.CharField(max_length=80, db_index=True)
    value_type = models.CharField(
        max_length=10,
        choices=OLDefaultParameterValueType.choices,
        default=OLDefaultParameterValueType.STRING,
    )
    string_value = models.TextField(null=True, blank=True)
    integer_value = models.IntegerField(null=True, blank=True)
    decimal_value = models.DecimalField(max_digits=24, decimal_places=8, null=True, blank=True)
    boolean_value = models.BooleanField(null=True, blank=True)
    date_value = models.DateField(null=True, blank=True)
    json_value = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ["parameter_category", "name", "parameter_key"]
        constraints = [
            models.UniqueConstraint(fields=["code"], name="ol_def_sys_code_unique"),
            models.CheckConstraint(
                check=models.Q(effective_to__isnull=True)
                | models.Q(effective_from__isnull=True)
                | models.Q(effective_to__gte=models.F("effective_from")),
                name="ol_def_sys_dates_valid",
            ),
        ]
        indexes = [
            models.Index(fields=["parameter_category", "is_active"], name="ol_def_sys_cat_active_idx"),
            models.Index(fields=["parameter_key", "is_active"], name="ol_def_sys_key_active_idx"),
        ]

    @property
    def value(self):
        field_name = {
            OLDefaultParameterValueType.STRING: "string_value",
            OLDefaultParameterValueType.TEXT: "string_value",
            OLDefaultParameterValueType.INTEGER: "integer_value",
            OLDefaultParameterValueType.DECIMAL: "decimal_value",
            OLDefaultParameterValueType.BOOLEAN: "boolean_value",
            OLDefaultParameterValueType.DATE: "date_value",
            OLDefaultParameterValueType.JSON: "json_value",
        }[self.value_type]
        return getattr(self, field_name)

    @value.setter
    def value(self, raw_value):
        field_name = {
            OLDefaultParameterValueType.STRING: "string_value",
            OLDefaultParameterValueType.TEXT: "string_value",
            OLDefaultParameterValueType.INTEGER: "integer_value",
            OLDefaultParameterValueType.DECIMAL: "decimal_value",
            OLDefaultParameterValueType.BOOLEAN: "boolean_value",
            OLDefaultParameterValueType.DATE: "date_value",
            OLDefaultParameterValueType.JSON: "json_value",
        }[self.value_type]
        for candidate in ("string_value", "integer_value", "decimal_value", "boolean_value", "date_value", "json_value"):
            setattr(self, candidate, raw_value if candidate == field_name else None)

    def set_typed_value(self, raw_value):
        self.value = raw_value

    def clean(self):
        if not self.code and self.parameter_key:
            self.code = self.parameter_key
        if not self.parameter_key and self.code:
            self.parameter_key = self.code
        if self.code and self.parameter_key and self.code != self.parameter_key:
            raise ValidationError({"code": "Code and parameter key must match for OL default parameters."})
        self.value_type = (self.value_type or "").upper()
        super().clean()
        if self.parameter_category:
            self.parameter_category = self.parameter_category.strip().upper()
        if self.value_type not in dict(OLDefaultParameterValueType.choices):
            raise ValidationError({"value_type": "Unsupported OL default parameter value type."})
        if self.value is None:
            raise ValidationError({"value": "A typed value is required."})
        if self.value_type == OLDefaultParameterValueType.JSON and not isinstance(self.value, (dict, list, str, int, float, bool)):
            raise ValidationError({"json_value": "JSON value must be JSON serializable."})


class OLCommissionRateType(models.TextChoices):
    PERCENTAGE = "PERCENTAGE", "Percentage"
    FIXED = "FIXED", "Fixed"
    FACTOR = "FACTOR", "Factor"


class OLOverrideCommissionSetup(OLEffectiveDateModel):
    """Priority-ordered commission override scoped to partner/product dimensions."""

    partner = models.ForeignKey(
        "partners.Partner",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="ol_commission_overrides",
        help_text="Optional partner or agent scope; agent partners are represented by this relation.",
    )
    intermediary_type = models.CharField(max_length=80, blank=True, default="", db_index=True)
    product = models.ForeignKey(
        "ordinary_life.OLProduct",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="ol_commission_overrides",
    )
    plan = models.ForeignKey(
        "ordinary_life.OLPlan",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="ol_commission_overrides",
    )
    rider = models.ForeignKey(
        "ordinary_life.OLRider",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="ol_commission_overrides",
    )
    channel = models.CharField(max_length=80, blank=True, default="", db_index=True)
    branch = models.ForeignKey(
        "partner_onboarding.Branch",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="ol_commission_overrides",
    )
    currency = models.CharField(max_length=3, blank=True, default="", db_index=True)
    premium_year_from = models.PositiveIntegerField(null=True, blank=True)
    premium_year_to = models.PositiveIntegerField(null=True, blank=True)
    policy_year_from = models.PositiveIntegerField(null=True, blank=True)
    policy_year_to = models.PositiveIntegerField(null=True, blank=True)
    rate_type = models.CharField(max_length=10, choices=OLCommissionRateType.choices)
    rate_value = models.DecimalField(max_digits=18, decimal_places=8)
    priority = models.PositiveIntegerField(default=100, db_index=True)
    reason = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["priority", "-effective_from", "code"]
        constraints = [
            models.UniqueConstraint(fields=["code"], name="ol_comm_override_code_unique"),
            models.CheckConstraint(
                check=models.Q(premium_year_to__isnull=True)
                | models.Q(premium_year_from__isnull=True)
                | models.Q(premium_year_to__gte=models.F("premium_year_from")),
                name="ol_comm_prem_years_valid",
            ),
            models.CheckConstraint(
                check=models.Q(policy_year_to__isnull=True)
                | models.Q(policy_year_from__isnull=True)
                | models.Q(policy_year_to__gte=models.F("policy_year_from")),
                name="ol_comm_policy_years_valid",
            ),
            models.CheckConstraint(check=models.Q(rate_value__gte=0), name="ol_comm_rate_nonnegative"),
        ]
        indexes = [
            models.Index(fields=["partner", "product", "plan", "rider", "is_active"], name="ol_comm_scope_active_idx"),
            models.Index(fields=["priority", "effective_from", "effective_to"], name="ol_comm_priority_dates_idx"),
        ]

    @staticmethod
    def _ranges_overlap(start_a, end_a, start_b, end_b):
        lower_boundaries_do_not_cross = end_a is None or start_b is None or start_b <= end_a
        upper_boundaries_do_not_cross = end_b is None or start_a is None or start_a <= end_b
        return lower_boundaries_do_not_cross and upper_boundaries_do_not_cross

    def clean(self):
        super().clean()
        self.rate_type = (self.rate_type or "").upper()
        self.currency = (self.currency or "").strip().upper()
        self.intermediary_type = (self.intermediary_type or "").strip().upper()
        self.channel = (self.channel or "").strip().upper()
        if self.plan_id and self.product_id:
            plan_product_id = getattr(self.plan, "product_id", None)
            if plan_product_id and plan_product_id != self.product_id:
                raise ValidationError({"plan": "Selected plan does not belong to the selected product."})
        if self.rate_type not in dict(OLCommissionRateType.choices):
            raise ValidationError({"rate_type": "Unsupported commission rate type."})
        if self.rate_value is None or self.rate_value < 0:
            raise ValidationError({"rate_value": "Rate value cannot be negative."})
        if self.rate_type == OLCommissionRateType.PERCENTAGE and self.rate_value > 100:
            raise ValidationError({"rate_value": "Percentage rate cannot exceed 100."})
        if self.premium_year_from is not None and self.premium_year_to is not None and self.premium_year_to < self.premium_year_from:
            raise ValidationError({"premium_year_to": "Premium year-to cannot be before year-from."})
        if self.policy_year_from is not None and self.policy_year_to is not None and self.policy_year_to < self.policy_year_from:
            raise ValidationError({"policy_year_to": "Policy year-to cannot be before year-from."})
        scope_fields = ("partner_id", "intermediary_type", "product_id", "plan_id", "rider_id", "channel", "branch_id", "currency")
        filters = {field: getattr(self, field) for field in scope_fields}
        candidates = type(self).objects.filter(is_active=True, **filters)
        if self.pk:
            candidates = candidates.exclude(pk=self.pk)
        for other in candidates.only(
            "id", "effective_from", "effective_to", "premium_year_from", "premium_year_to", "policy_year_from", "policy_year_to"
        ):
            if not self._ranges_overlap(self.effective_from, self.effective_to, other.effective_from, other.effective_to):
                continue
            if not self._ranges_overlap(self.premium_year_from, self.premium_year_to, other.premium_year_from, other.premium_year_to):
                continue
            if self._ranges_overlap(self.policy_year_from, self.policy_year_to, other.policy_year_from, other.policy_year_to):
                raise ValidationError({"effective_from": "An active commission override with the same scope and overlapping period already exists."})


class OLComputationApproach(OLEffectiveDateModel):
    """Named calculation strategy selected by product and future transaction engines."""

    calculation_area = models.CharField(max_length=80, db_index=True)
    calculation_basis = models.CharField(max_length=120)
    formula_key = models.CharField(max_length=120)
    sequence = models.PositiveIntegerField(default=1)
    configuration = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["calculation_area", "sequence", "name", "code"]
        constraints = [models.UniqueConstraint(fields=["code"], name="ol_compute_approach_code_unique")]
        indexes = [
            models.Index(fields=["calculation_area", "is_active"], name="ol_compute_area_active_idx"),
            models.Index(fields=["calculation_area", "sequence"], name="ol_compute_area_seq_idx"),
        ]

    def clean(self):
        super().clean()
        self.calculation_area = (self.calculation_area or "").strip().upper()
        self.calculation_basis = (self.calculation_basis or "").strip().upper()
        self.formula_key = (self.formula_key or "").strip()
        if not self.calculation_area:
            raise ValidationError({"calculation_area": "Calculation area is required."})
        if not self.calculation_basis:
            raise ValidationError({"calculation_basis": "Calculation basis is required."})
        if not self.formula_key:
            raise ValidationError({"formula_key": "Formula key is required."})
        if not isinstance(self.configuration, dict):
            raise ValidationError({"configuration": "Configuration must be a JSON object."})


class OLMaturityClaimSetup(OLEffectiveDateModel):
    """Effective-dated behavior for automatically initiated maturity claims."""

    product = models.ForeignKey(
        "ordinary_life.OLProduct",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="ol_maturity_claim_setups",
    )
    plan = models.ForeignKey(
        "ordinary_life.OLPlan",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="ol_maturity_claim_setups",
    )
    auto_create_maturity_claim = models.BooleanField(default=True)
    days_before_maturity_to_initiate = models.PositiveIntegerField(default=0)
    notification_days = models.PositiveIntegerField(default=0)
    default_payout_method = models.CharField(max_length=40, default="BANK_TRANSFER")
    require_documents = models.BooleanField(default=True)
    require_approval = models.BooleanField(default=True)
    maturity_claim_status_to_create = models.CharField(max_length=40, default="REPORTED")

    class Meta:
        ordering = ["-effective_from", "name", "code"]
        constraints = [models.UniqueConstraint(fields=["code"], name="ol_maturity_setup_code_unique")]
        indexes = [
            models.Index(fields=["product", "plan", "is_active"], name="ol_maturity_scope_active_idx"),
            models.Index(fields=["auto_create_maturity_claim", "is_active"], name="ol_maturity_auto_active_idx"),
        ]

    def clean(self):
        super().clean()
        self.default_payout_method = (self.default_payout_method or "").strip().upper()
        self.maturity_claim_status_to_create = (self.maturity_claim_status_to_create or "").strip().upper()
        if self.plan_id and self.product_id:
            plan_product_id = getattr(self.plan, "product_id", None)
            if plan_product_id and plan_product_id != self.product_id:
                raise ValidationError({"plan": "Selected plan does not belong to the selected product."})
        if not self.default_payout_method:
            raise ValidationError({"default_payout_method": "A default payout method is required."})
        if not self.maturity_claim_status_to_create:
            raise ValidationError({"maturity_claim_status_to_create": "A maturity claim status is required."})


class OLBeneficialTypeCategory(models.TextChoices):
    BENEFICIARY = "BENEFICIARY", "Beneficiary"
    BENEFIT = "BENEFIT", "Benefit"
    COVERAGE = "COVERAGE", "Coverage"
    OTHER = "OTHER", "Other"


def _policy_setup_intervals_overlap(start_a, end_a, start_b, end_b):
    """Return whether two inclusive date or numeric intervals overlap."""
    if end_a is not None and start_b is not None and end_a < start_b:
        return False
    if end_b is not None and start_a is not None and end_b < start_a:
        return False
    return True


def _policy_setup_validate_product_plan(instance, errors):
    if instance.plan_id and instance.product_id:
        plan_product_id = getattr(instance.plan, "product_version", None)
        plan_product_id = getattr(plan_product_id, "product_id", None)
        if plan_product_id and plan_product_id != instance.product_id:
            errors["plan"] = "Selected plan does not belong to the selected product."


class OLAnticipatedEndowmentInstallmentRate(OLEffectiveDateModel):
    """Effective-dated anticipated endowment installment rate by product dimensions."""

    product = models.ForeignKey(
        "ordinary_life.OLProduct",
        on_delete=models.PROTECT,
        related_name="ol_anticipated_endowment_rates",
    )
    plan = models.ForeignKey(
        "ordinary_life.OLPlan",
        on_delete=models.PROTECT,
        related_name="ol_anticipated_endowment_rates",
        null=True,
        blank=True,
    )
    installment_type = models.CharField(max_length=40, default="ANTICIPATED_ENDOWMENT")
    frequency = models.CharField(max_length=30, default="ANNUAL")
    age_from = models.PositiveSmallIntegerField(null=True, blank=True)
    age_to = models.PositiveSmallIntegerField(null=True, blank=True)
    term_from = models.PositiveSmallIntegerField(null=True, blank=True)
    term_to = models.PositiveSmallIntegerField(null=True, blank=True)
    policy_year_from = models.PositiveSmallIntegerField(null=True, blank=True)
    policy_year_to = models.PositiveSmallIntegerField(null=True, blank=True)
    rate_factor = models.DecimalField(max_digits=18, decimal_places=8)
    currency = models.CharField(max_length=3, blank=True, default="")

    class Meta:
        ordering = ["product", "plan", "frequency", "age_from", "term_from", "policy_year_from", "code"]
        constraints = [
            models.UniqueConstraint(fields=["code"], name="ol_policy_endow_rate_code_uq"),
            models.CheckConstraint(check=models.Q(rate_factor__gte=0), name="ol_policy_endow_rate_nonnegative"),
            models.CheckConstraint(
                check=models.Q(age_to__isnull=True) | models.Q(age_from__isnull=True) | models.Q(age_to__gte=models.F("age_from")),
                name="ol_policy_endow_age_valid",
            ),
            models.CheckConstraint(
                check=models.Q(term_to__isnull=True) | models.Q(term_from__isnull=True) | models.Q(term_to__gte=models.F("term_from")),
                name="ol_policy_endow_term_valid",
            ),
            models.CheckConstraint(
                check=models.Q(policy_year_to__isnull=True) | models.Q(policy_year_from__isnull=True) | models.Q(policy_year_to__gte=models.F("policy_year_from")),
                name="ol_policy_endow_year_valid",
            ),
        ]
        indexes = [
            models.Index(fields=["product", "plan", "frequency"], name="ol_policy_endow_scope_idx"),
            models.Index(fields=["effective_from", "effective_to"], name="ol_policy_endow_dates_idx"),
        ]

    def clean(self):
        super().clean()
        errors = {}
        _policy_setup_validate_product_plan(self, errors)
        self.installment_type = (self.installment_type or "").strip().upper()
        self.frequency = (self.frequency or "").strip().upper()
        self.currency = (self.currency or "").strip().upper()
        if not self.installment_type:
            errors["installment_type"] = "Installment type is required."
        if not self.frequency:
            errors["frequency"] = "Frequency is required."
        if self.currency and (len(self.currency) != 3 or not self.currency.isalpha()):
            errors["currency"] = "Currency must be a three-letter code."
        for lower, upper, label in (
            (self.age_from, self.age_to, "age"),
            (self.term_from, self.term_to, "term"),
            (self.policy_year_from, self.policy_year_to, "policy year"),
        ):
            if lower is not None and upper is not None and upper < lower:
                errors[f"{label.replace(' ', '_')}_to"] = f"{label.title()}-to cannot be less than {label}-from."
        if self.rate_factor is None or self.rate_factor < 0:
            errors["rate_factor"] = "Rate or factor must be a non-negative decimal."
        if errors:
            raise ValidationError(errors)
        candidates = self.__class__.objects.filter(
            product=self.product,
            plan=self.plan,
            installment_type=self.installment_type,
            frequency=self.frequency,
            currency=self.currency,
            is_active=True,
        )
        if self.pk:
            candidates = candidates.exclude(pk=self.pk)
        for candidate in candidates:
            if not _policy_setup_intervals_overlap(self.effective_from, self.effective_to, candidate.effective_from, candidate.effective_to):
                continue
            if all(
                _policy_setup_intervals_overlap(getattr(self, lower), getattr(self, upper), getattr(candidate, lower), getattr(candidate, upper))
                for lower, upper in (
                    ("age_from", "age_to"),
                    ("term_from", "term_to"),
                    ("policy_year_from", "policy_year_to"),
                )
            ):
                raise ValidationError({"code": "An active anticipated endowment rate overlaps an existing row in the same scope."})


class OLGracePeriod(OLEffectiveDateModel):
    """Effective-dated premium grace/lapse timing by optional product scope."""

    product = models.ForeignKey(
        "ordinary_life.OLProduct",
        on_delete=models.PROTECT,
        related_name="ol_grace_periods",
        null=True,
        blank=True,
    )
    plan = models.ForeignKey(
        "ordinary_life.OLPlan",
        on_delete=models.PROTECT,
        related_name="ol_grace_periods",
        null=True,
        blank=True,
    )
    premium_frequency = models.CharField(max_length=30, blank=True, default="")
    grace_days = models.PositiveIntegerField(default=0)
    warning_days = models.PositiveIntegerField(default=0)
    pre_lapse_days = models.PositiveIntegerField(default=0)
    lapse_days = models.PositiveIntegerField(default=0)
    minimum_due_amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ["product", "plan", "premium_frequency", "-effective_from", "code"]
        constraints = [
            models.UniqueConstraint(fields=["code"], name="ol_policy_grace_code_uq"),
            models.CheckConstraint(check=models.Q(minimum_due_amount__isnull=True) | models.Q(minimum_due_amount__gte=0), name="ol_policy_grace_min_due_nonnegative"),
            models.CheckConstraint(check=models.Q(grace_days__lte=models.F("lapse_days")), name="ol_policy_grace_days_ordered"),
            models.CheckConstraint(check=models.Q(warning_days__lte=models.F("lapse_days")), name="ol_policy_grace_warning_valid"),
            models.CheckConstraint(check=models.Q(pre_lapse_days__lte=models.F("lapse_days")), name="ol_policy_grace_pre_lapse_valid"),
        ]
        indexes = [
            models.Index(fields=["product", "plan", "premium_frequency"], name="ol_policy_grace_scope_idx"),
            models.Index(fields=["is_active", "effective_from"], name="ol_policy_grace_active_idx"),
        ]

    def clean(self):
        super().clean()
        errors = {}
        _policy_setup_validate_product_plan(self, errors)
        self.premium_frequency = (self.premium_frequency or "").strip().upper()
        if self.grace_days > self.lapse_days:
            errors["grace_days"] = "Grace days cannot exceed lapse days."
        if self.warning_days > self.lapse_days:
            errors["warning_days"] = "Warning days cannot exceed lapse days."
        if self.pre_lapse_days > self.lapse_days:
            errors["pre_lapse_days"] = "Pre-lapse days cannot exceed lapse days."
        if self.minimum_due_amount is not None and self.minimum_due_amount < 0:
            errors["minimum_due_amount"] = "Minimum due amount cannot be negative."
        if errors:
            raise ValidationError(errors)
        candidates = self.__class__.objects.filter(
            product=self.product,
            plan=self.plan,
            premium_frequency=self.premium_frequency,
            is_active=True,
        )
        if self.pk:
            candidates = candidates.exclude(pk=self.pk)
        for candidate in candidates:
            if _policy_setup_intervals_overlap(self.effective_from, self.effective_to, candidate.effective_from, candidate.effective_to):
                raise ValidationError({"code": "An active grace-period row overlaps an existing row in the same scope."})


class OLPolicyStatus(OLParameterBaseModel):
    """Configurable policy lifecycle status and outgoing transition metadata."""

    display_order = models.PositiveIntegerField(default=0)
    badge_type = models.CharField(max_length=30, default="NEUTRAL")
    is_terminal = models.BooleanField(default=False)
    allowed_transitions = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["display_order", "name", "code"]
        constraints = [models.UniqueConstraint(fields=["code"], name="ol_policy_status_code_uq")]
        indexes = [
            models.Index(fields=["is_active", "display_order"], name="ol_policy_status_active_idx"),
            models.Index(fields=["is_terminal", "is_active"], name="ol_policy_status_terminal_idx"),
        ]

    def clean(self):
        super().clean()
        self.badge_type = (self.badge_type or "NEUTRAL").strip().upper()
        transitions = self.allowed_transitions if self.allowed_transitions is not None else []
        if not isinstance(transitions, list):
            raise ValidationError({"allowed_transitions": "Allowed transitions must be a JSON list of status codes."})
        normalized = []
        for transition in transitions:
            if not isinstance(transition, str) or not transition.strip():
                raise ValidationError({"allowed_transitions": "Each transition must be a non-empty status code."})
            target = transition.strip().upper()
            if target == self.code.upper():
                raise ValidationError({"allowed_transitions": "A policy status cannot transition to itself."})
            if target not in normalized:
                normalized.append(target)
        if self.is_terminal and normalized:
            raise ValidationError({"allowed_transitions": "Terminal policy statuses cannot have outgoing transitions."})
        if normalized:
            existing_codes = {
                code.upper()
                for code in self.__class__.objects.filter(is_active=True).exclude(pk=self.pk).values_list("code", flat=True)
            }
            missing = [target for target in normalized if target not in existing_codes]
            if missing:
                raise ValidationError({"allowed_transitions": f"Unknown active policy-status codes: {', '.join(missing)}."})
        self.allowed_transitions = normalized


class OLPolicyRenewalStatus(OLParameterBaseModel):
    """Configurable renewal lifecycle status catalog."""

    display_order = models.PositiveIntegerField(default=0)
    renewal_action = models.CharField(max_length=40, default="NONE")

    class Meta:
        ordering = ["display_order", "name", "code"]
        constraints = [models.UniqueConstraint(fields=["code"], name="ol_policy_renewal_status_code_uq")]
        indexes = [models.Index(fields=["is_active", "display_order"], name="ol_policy_renewal_active_idx")]

    def clean(self):
        super().clean()
        self.renewal_action = (self.renewal_action or "NONE").strip().upper()
        if not self.renewal_action:
            raise ValidationError({"renewal_action": "Renewal action is required."})


class OLBeneficialType(OLParameterBaseModel):
    """Flexible beneficiary, benefit, or coverage type catalog."""

    category = models.CharField(max_length=20, choices=OLBeneficialTypeCategory.choices, default=OLBeneficialTypeCategory.BENEFICIARY)
    calculation_basis = models.CharField(max_length=50, default="PERCENTAGE")
    default_ratio = models.DecimalField(max_digits=7, decimal_places=4, default=0)
    allows_multiple = models.BooleanField(default=True)

    class Meta:
        ordering = ["category", "name", "code"]
        constraints = [
            models.UniqueConstraint(fields=["code"], name="ol_beneficial_type_code_uq"),
            models.CheckConstraint(check=models.Q(default_ratio__gte=0) & models.Q(default_ratio__lte=100), name="ol_beneficial_ratio_valid"),
        ]
        indexes = [
            models.Index(fields=["category", "is_active"], name="ol_beneficial_type_cat_idx"),
            models.Index(fields=["is_active", "calculation_basis"], name="ol_beneficial_type_basis_idx"),
        ]

    def clean(self):
        super().clean()
        self.category = (self.category or "").strip().upper()
        self.calculation_basis = (self.calculation_basis or "PERCENTAGE").strip().upper()
        if self.category not in {choice for choice, _ in OLBeneficialTypeCategory.choices}:
            raise ValidationError({"category": "Unsupported beneficial type category."})
        if self.default_ratio is None or self.default_ratio < 0 or self.default_ratio > 100:
            raise ValidationError({"default_ratio": "Default ratio must be between 0 and 100."})


class OLMemberCoverConfiguration(OLEffectiveDateModel):
    """Effective-dated member/dependent eligibility and cover configuration."""

    product = models.ForeignKey(
        "ordinary_life.OLProduct",
        on_delete=models.PROTECT,
        related_name="ol_member_cover_configurations",
        null=True,
        blank=True,
    )
    plan = models.ForeignKey(
        "ordinary_life.OLPlan",
        on_delete=models.PROTECT,
        related_name="ol_member_cover_configurations",
        null=True,
        blank=True,
    )
    cover_type = models.CharField(max_length=40, default="INDIVIDUAL")
    member_relation = models.CharField(max_length=40, default="MEMBER")
    min_age = models.PositiveSmallIntegerField(null=True, blank=True)
    max_age = models.PositiveSmallIntegerField(null=True, blank=True)
    waiting_period_days = models.PositiveIntegerField(default=0)
    benefit_limit = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    premium_basis = models.CharField(max_length=50, default="MEMBER_PREMIUM")
    coverage_basis = models.CharField(max_length=50, default="SUM_ASSURED")

    class Meta:
        ordering = ["product", "plan", "cover_type", "member_relation", "min_age", "code"]
        constraints = [
            models.UniqueConstraint(fields=["code"], name="ol_member_cover_code_uq"),
            models.CheckConstraint(check=models.Q(max_age__isnull=True) | models.Q(min_age__isnull=True) | models.Q(max_age__gte=models.F("min_age")), name="ol_member_cover_age_valid"),
            models.CheckConstraint(check=models.Q(benefit_limit__isnull=True) | models.Q(benefit_limit__gte=0), name="ol_member_cover_limit_nonnegative"),
        ]
        indexes = [
            models.Index(fields=["product", "plan", "cover_type", "member_relation"], name="ol_member_cover_scope_idx"),
            models.Index(fields=["is_active", "effective_from"], name="ol_member_cover_active_idx"),
        ]

    def clean(self):
        super().clean()
        errors = {}
        _policy_setup_validate_product_plan(self, errors)
        self.cover_type = (self.cover_type or "").strip().upper()
        self.member_relation = (self.member_relation or "").strip().upper()
        self.premium_basis = (self.premium_basis or "").strip().upper()
        self.coverage_basis = (self.coverage_basis or "").strip().upper()
        if not self.cover_type:
            errors["cover_type"] = "Cover type is required."
        if not self.member_relation:
            errors["member_relation"] = "Member relation is required."
        if self.min_age is not None and self.max_age is not None and self.max_age < self.min_age:
            errors["max_age"] = "Maximum age cannot be less than minimum age."
        if self.benefit_limit is not None and self.benefit_limit < 0:
            errors["benefit_limit"] = "Benefit limit cannot be negative."
        if errors:
            raise ValidationError(errors)
        candidates = self.__class__.objects.filter(
            product=self.product,
            plan=self.plan,
            cover_type=self.cover_type,
            member_relation=self.member_relation,
            is_active=True,
        )
        if self.pk:
            candidates = candidates.exclude(pk=self.pk)
        for candidate in candidates:
            if not _policy_setup_intervals_overlap(self.effective_from, self.effective_to, candidate.effective_from, candidate.effective_to):
                continue
            if _policy_setup_intervals_overlap(self.min_age, self.max_age, candidate.min_age, candidate.max_age):
                raise ValidationError({"code": "An active member-cover row overlaps an existing row in the same scope."})


def validate_policy_status_transition_graph(queryset=None):
    """Validate that active policy-status transition targets form a valid catalog graph."""
    statuses = list((queryset or OLPolicyStatus.objects.filter(is_active=True)).all())
    by_code = {status.code.upper(): status for status in statuses}
    errors = {}
    for status in statuses:
        transitions = status.allowed_transitions or []
        missing = [code for code in transitions if code.upper() not in by_code]
        if missing:
            errors[status.code] = f"Unknown active policy-status transition targets: {', '.join(missing)}."
        if status.is_terminal and transitions:
            errors[status.code] = "Terminal policy statuses cannot have outgoing transitions."
    if errors:
        raise ValidationError(errors)
    return True


# =============================================================================
# OL POLICY SETUP PART 2
# =============================================================================


class OLSurrenderChargeType(models.TextChoices):
    NONE = "NONE", "None"
    PERCENTAGE = "PERCENTAGE", "Percentage"
    FIXED = "FIXED", "Fixed amount"
    FACTOR = "FACTOR", "Factor"


class OLPaidUpConversionBasis(models.TextChoices):
    PROPORTIONAL = "PROPORTIONAL", "Proportional"
    REDUCED_SUM_ASSURED = "REDUCED_SUM_ASSURED", "Reduced sum assured"
    CASH_VALUE = "CASH_VALUE", "Cash value"
    CUSTOM = "CUSTOM", "Custom formula"


class OLPaidUpEffectiveRule(models.TextChoices):
    IMMEDIATE = "IMMEDIATE", "Immediate"
    NEXT_ANNIVERSARY = "NEXT_ANNIVERSARY", "Next policy anniversary"
    NEXT_DUE_DATE = "NEXT_DUE_DATE", "Next premium due date"
    CONFIGURED_DATE = "CONFIGURED_DATE", "Configured effective date"


def _part2_validate_scope(instance, errors):
    if instance.plan_id and not instance.product_id:
        errors["plan"] = "A plan cannot be configured without its product scope."
    _policy_setup_validate_product_plan(instance, errors)


def _part2_rate_intervals_overlap(first, second):
    return all(
        _policy_setup_intervals_overlap(getattr(first, lower), getattr(first, upper), getattr(second, lower), getattr(second, upper))
        for lower, upper in (
            ("age_from", "age_to"),
            ("term_from", "term_to"),
            ("policy_year_from", "policy_year_to"),
        )
    )


class OLSurrenderSetup(OLEffectiveDateModel):
    """Effective-dated surrender eligibility and payout behavior."""

    product = models.ForeignKey(
        "ordinary_life.OLProduct",
        on_delete=models.PROTECT,
        related_name="ol_parameter_surrender_setups",
        null=True,
        blank=True,
    )
    plan = models.ForeignKey(
        "ordinary_life.OLPlan",
        on_delete=models.PROTECT,
        related_name="ol_parameter_surrender_setups",
        null=True,
        blank=True,
    )
    minimum_premiums_paid = models.PositiveIntegerField(default=0)
    minimum_policy_months = models.PositiveIntegerField(default=0)
    minimum_premium_paid_ratio = models.DecimalField(max_digits=7, decimal_places=4, default=0)
    surrender_charge_type = models.CharField(
        max_length=20,
        choices=OLSurrenderChargeType.choices,
        default=OLSurrenderChargeType.NONE,
    )
    surrender_charge_value = models.DecimalField(max_digits=18, decimal_places=8, default=0)
    partial_surrender_allowed = models.BooleanField(default=False)
    surrender_payout_days = models.PositiveIntegerField(default=0)
    require_approval = models.BooleanField(default=True)

    class Meta:
        ordering = ["product", "plan", "-effective_from", "name", "code"]
        constraints = [
            models.UniqueConstraint(fields=["code"], name="ol_surr_setup_code_uq"),
            models.CheckConstraint(
                check=models.Q(minimum_premium_paid_ratio__gte=0)
                & models.Q(minimum_premium_paid_ratio__lte=100),
                name="ol_surr_setup_ratio_valid",
            ),
            models.CheckConstraint(
                check=models.Q(surrender_charge_value__gte=0),
                name="ol_surr_setup_charge_nonneg",
            ),
        ]
        indexes = [
            models.Index(fields=["product", "plan", "is_active"], name="ol_surr_setup_scope_idx"),
            models.Index(fields=["is_active", "effective_from"], name="ol_surr_setup_dates_idx"),
        ]

    def clean(self):
        super().clean()
        errors = {}
        _part2_validate_scope(self, errors)
        self.surrender_charge_type = (self.surrender_charge_type or OLSurrenderChargeType.NONE).strip().upper()
        if self.surrender_charge_type not in {choice for choice, _ in OLSurrenderChargeType.choices}:
            errors["surrender_charge_type"] = "Unsupported surrender charge type."
        if self.minimum_premium_paid_ratio is None or not 0 <= self.minimum_premium_paid_ratio <= 100:
            errors["minimum_premium_paid_ratio"] = "Minimum premium paid ratio must be between 0 and 100."
        if self.surrender_charge_value is None or self.surrender_charge_value < 0:
            errors["surrender_charge_value"] = "Surrender charge value cannot be negative."
        if self.surrender_charge_type == OLSurrenderChargeType.NONE and self.surrender_charge_value:
            errors["surrender_charge_value"] = "A surrender charge value is not allowed when charge type is NONE."
        if errors:
            raise ValidationError(errors)
        candidates = self.__class__.objects.filter(product=self.product, plan=self.plan, is_active=True)
        if self.pk:
            candidates = candidates.exclude(pk=self.pk)
        for candidate in candidates:
            if _policy_setup_intervals_overlap(self.effective_from, self.effective_to, candidate.effective_from, candidate.effective_to):
                raise ValidationError({"code": "An active surrender setup overlaps an existing row in the same scope."})


class OLPaidUpSetup(OLEffectiveDateModel):
    """Effective-dated paid-up conversion eligibility and timing behavior."""

    product = models.ForeignKey(
        "ordinary_life.OLProduct",
        on_delete=models.PROTECT,
        related_name="ol_parameter_paid_up_setups",
        null=True,
        blank=True,
    )
    plan = models.ForeignKey(
        "ordinary_life.OLPlan",
        on_delete=models.PROTECT,
        related_name="ol_parameter_paid_up_setups",
        null=True,
        blank=True,
    )
    minimum_premiums_paid = models.PositiveIntegerField(default=0)
    minimum_policy_months = models.PositiveIntegerField(default=0)
    paidup_conversion_basis = models.CharField(
        max_length=30,
        choices=OLPaidUpConversionBasis.choices,
        default=OLPaidUpConversionBasis.PROPORTIONAL,
    )
    allow_paidup = models.BooleanField(default=True)
    paidup_effective_rule = models.CharField(
        max_length=30,
        choices=OLPaidUpEffectiveRule.choices,
        default=OLPaidUpEffectiveRule.NEXT_ANNIVERSARY,
    )

    class Meta:
        ordering = ["product", "plan", "-effective_from", "name", "code"]
        constraints = [
            models.UniqueConstraint(fields=["code"], name="ol_paidup_setup_code_uq"),
        ]
        indexes = [
            models.Index(fields=["product", "plan", "is_active"], name="ol_paidup_setup_scope_idx"),
            models.Index(fields=["allow_paidup", "is_active"], name="ol_paidup_setup_allow_idx"),
        ]

    def clean(self):
        super().clean()
        errors = {}
        _part2_validate_scope(self, errors)
        self.paidup_conversion_basis = (self.paidup_conversion_basis or OLPaidUpConversionBasis.PROPORTIONAL).strip().upper()
        self.paidup_effective_rule = (self.paidup_effective_rule or OLPaidUpEffectiveRule.NEXT_ANNIVERSARY).strip().upper()
        if self.paidup_conversion_basis not in {choice for choice, _ in OLPaidUpConversionBasis.choices}:
            errors["paidup_conversion_basis"] = "Unsupported paid-up conversion basis."
        if self.paidup_effective_rule not in {choice for choice, _ in OLPaidUpEffectiveRule.choices}:
            errors["paidup_effective_rule"] = "Unsupported paid-up effective rule."
        if self.allow_paidup and self.minimum_premiums_paid == 0 and self.minimum_policy_months == 0:
            errors["minimum_policy_months"] = "At least one paid-up eligibility threshold is required when paid-up conversion is allowed."
        if errors:
            raise ValidationError(errors)
        candidates = self.__class__.objects.filter(product=self.product, plan=self.plan, is_active=True)
        if self.pk:
            candidates = candidates.exclude(pk=self.pk)
        for candidate in candidates:
            if _policy_setup_intervals_overlap(self.effective_from, self.effective_to, candidate.effective_from, candidate.effective_to):
                raise ValidationError({"code": "An active paid-up setup overlaps an existing row in the same scope."})


class OLSurrenderValueRate(OLEffectiveDateModel):
    """Multi-dimensional surrender-value rate/factor table row."""

    table_code = models.CharField(max_length=100, blank=True, default="", db_index=True)
    rate_table_version = models.CharField(max_length=50, blank=True, default="", db_index=True)
    product = models.ForeignKey(
        "ordinary_life.OLProduct",
        on_delete=models.PROTECT,
        related_name="ol_parameter_surrender_value_rates",
    )
    plan = models.ForeignKey(
        "ordinary_life.OLPlan",
        on_delete=models.PROTECT,
        related_name="ol_parameter_surrender_value_rates",
        null=True,
        blank=True,
    )
    gender = models.CharField(max_length=30, blank=True, default="", db_index=True)
    smoker_status = models.CharField(max_length=30, blank=True, default="", db_index=True)
    age_from = models.PositiveSmallIntegerField(null=True, blank=True)
    age_to = models.PositiveSmallIntegerField(null=True, blank=True)
    term_from = models.PositiveSmallIntegerField(null=True, blank=True)
    term_to = models.PositiveSmallIntegerField(null=True, blank=True)
    policy_year_from = models.PositiveSmallIntegerField(null=True, blank=True)
    policy_year_to = models.PositiveSmallIntegerField(null=True, blank=True)
    rate_factor = models.DecimalField(max_digits=18, decimal_places=8)
    row_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["table_code", "rate_table_version", "product", "plan", "row_order", "age_from", "term_from", "policy_year_from", "code"]
        constraints = [
            models.UniqueConstraint(fields=["code"], name="ol_surr_value_rate_code_uq"),
            models.CheckConstraint(check=models.Q(rate_factor__gte=0), name="ol_surr_value_rate_nonneg"),
            models.CheckConstraint(
                check=models.Q(age_to__isnull=True) | models.Q(age_from__isnull=True) | models.Q(age_to__gte=models.F("age_from")),
                name="ol_surr_value_age_valid",
            ),
            models.CheckConstraint(
                check=models.Q(term_to__isnull=True) | models.Q(term_from__isnull=True) | models.Q(term_to__gte=models.F("term_from")),
                name="ol_surr_value_term_valid",
            ),
            models.CheckConstraint(
                check=models.Q(policy_year_to__isnull=True) | models.Q(policy_year_from__isnull=True) | models.Q(policy_year_to__gte=models.F("policy_year_from")),
                name="ol_surr_value_year_valid",
            ),
        ]
        indexes = [
            models.Index(fields=["table_code", "rate_table_version", "product", "plan"], name="ol_surr_value_scope_idx"),
            models.Index(fields=["product", "gender", "smoker_status"], name="ol_surr_value_dim_idx"),
            models.Index(fields=["is_active", "effective_from"], name="ol_surr_value_dates_idx"),
        ]

    def clean(self):
        super().clean()
        errors = {}
        _part2_validate_scope(self, errors)
        self.table_code = (self.table_code or "").strip().upper()
        self.rate_table_version = (self.rate_table_version or "").strip().upper()
        self.gender = (self.gender or "").strip().upper()
        self.smoker_status = (self.smoker_status or "").strip().upper()
        if not self.table_code and not self.rate_table_version:
            errors["table_code"] = "A table code or rate-table version is required."
        for lower, upper, label in (
            (self.age_from, self.age_to, "age"),
            (self.term_from, self.term_to, "term"),
            (self.policy_year_from, self.policy_year_to, "policy year"),
        ):
            if lower is not None and upper is not None and upper < lower:
                errors[f"{label.replace(' ', '_')}_to"] = f"{label.title()}-to cannot be less than {label}-from."
            if label != "age" and lower is not None and lower < 1:
                errors[f"{label.replace(' ', '_')}_from"] = f"{label.title()}-from must be at least 1."
        if self.rate_factor is None or self.rate_factor < 0:
            errors["rate_factor"] = "Surrender value rate/factor must be a non-negative decimal."
        if errors:
            raise ValidationError(errors)
        candidates = self.__class__.objects.filter(
            table_code=self.table_code,
            rate_table_version=self.rate_table_version,
            product=self.product,
            plan=self.plan,
            gender=self.gender,
            smoker_status=self.smoker_status,
            is_active=True,
        )
        if self.pk:
            candidates = candidates.exclude(pk=self.pk)
        for candidate in candidates:
            if _policy_setup_intervals_overlap(self.effective_from, self.effective_to, candidate.effective_from, candidate.effective_to) and _part2_rate_intervals_overlap(self, candidate):
                raise ValidationError({"code": "An active surrender-value rate overlaps an existing row in the same scope and table version."})


class OLPaidUpRate(OLEffectiveDateModel):
    """Multi-dimensional paid-up value rate/factor table row."""

    table_code = models.CharField(max_length=100, blank=True, default="", db_index=True)
    rate_table_version = models.CharField(max_length=50, blank=True, default="", db_index=True)
    product = models.ForeignKey(
        "ordinary_life.OLProduct",
        on_delete=models.PROTECT,
        related_name="ol_parameter_paid_up_rates",
    )
    plan = models.ForeignKey(
        "ordinary_life.OLPlan",
        on_delete=models.PROTECT,
        related_name="ol_parameter_paid_up_rates",
        null=True,
        blank=True,
    )
    gender = models.CharField(max_length=30, blank=True, default="", db_index=True)
    smoker_status = models.CharField(max_length=30, blank=True, default="", db_index=True)
    age_from = models.PositiveSmallIntegerField(null=True, blank=True)
    age_to = models.PositiveSmallIntegerField(null=True, blank=True)
    term_from = models.PositiveSmallIntegerField(null=True, blank=True)
    term_to = models.PositiveSmallIntegerField(null=True, blank=True)
    policy_year_from = models.PositiveSmallIntegerField(null=True, blank=True)
    policy_year_to = models.PositiveSmallIntegerField(null=True, blank=True)
    rate_factor = models.DecimalField(max_digits=18, decimal_places=8)
    row_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["table_code", "rate_table_version", "product", "plan", "row_order", "age_from", "term_from", "policy_year_from", "code"]
        constraints = [
            models.UniqueConstraint(fields=["code"], name="ol_paidup_rate_code_uq"),
            models.CheckConstraint(check=models.Q(rate_factor__gte=0), name="ol_paidup_rate_nonneg"),
            models.CheckConstraint(
                check=models.Q(age_to__isnull=True) | models.Q(age_from__isnull=True) | models.Q(age_to__gte=models.F("age_from")),
                name="ol_paidup_rate_age_valid",
            ),
            models.CheckConstraint(
                check=models.Q(term_to__isnull=True) | models.Q(term_from__isnull=True) | models.Q(term_to__gte=models.F("term_from")),
                name="ol_paidup_rate_term_valid",
            ),
            models.CheckConstraint(
                check=models.Q(policy_year_to__isnull=True) | models.Q(policy_year_from__isnull=True) | models.Q(policy_year_to__gte=models.F("policy_year_from")),
                name="ol_paidup_rate_year_valid",
            ),
        ]
        indexes = [
            models.Index(fields=["table_code", "rate_table_version", "product", "plan"], name="ol_paidup_rate_scope_idx"),
            models.Index(fields=["product", "gender", "smoker_status"], name="ol_paidup_rate_dim_idx"),
            models.Index(fields=["is_active", "effective_from"], name="ol_paidup_rate_dates_idx"),
        ]

    def clean(self):
        super().clean()
        errors = {}
        _part2_validate_scope(self, errors)
        self.table_code = (self.table_code or "").strip().upper()
        self.rate_table_version = (self.rate_table_version or "").strip().upper()
        self.gender = (self.gender or "").strip().upper()
        self.smoker_status = (self.smoker_status or "").strip().upper()
        if not self.table_code and not self.rate_table_version:
            errors["table_code"] = "A table code or rate-table version is required."
        for lower, upper, label in (
            (self.age_from, self.age_to, "age"),
            (self.term_from, self.term_to, "term"),
            (self.policy_year_from, self.policy_year_to, "policy year"),
        ):
            if lower is not None and upper is not None and upper < lower:
                errors[f"{label.replace(' ', '_')}_to"] = f"{label.title()}-to cannot be less than {label}-from."
            if label != "age" and lower is not None and lower < 1:
                errors[f"{label.replace(' ', '_')}_from"] = f"{label.title()}-from must be at least 1."
        if self.rate_factor is None or self.rate_factor < 0:
            errors["rate_factor"] = "Paid-up rate/factor must be a non-negative decimal."
        if errors:
            raise ValidationError(errors)
        candidates = self.__class__.objects.filter(
            table_code=self.table_code,
            rate_table_version=self.rate_table_version,
            product=self.product,
            plan=self.plan,
            gender=self.gender,
            smoker_status=self.smoker_status,
            is_active=True,
        )
        if self.pk:
            candidates = candidates.exclude(pk=self.pk)
        for candidate in candidates:
            if _policy_setup_intervals_overlap(self.effective_from, self.effective_to, candidate.effective_from, candidate.effective_to) and _part2_rate_intervals_overlap(self, candidate):
                raise ValidationError({"code": "An active paid-up rate overlaps an existing row in the same scope and table version."})


class OLCommitmentStatus(OLParameterBaseModel):
    """Configurable commitment status catalog, separate from transaction workflow state."""

    display_order = models.PositiveIntegerField(default=0)
    applies_to = models.CharField(max_length=50, default="COMMITMENT", db_index=True)
    is_terminal = models.BooleanField(default=False)

    class Meta:
        ordering = ["applies_to", "display_order", "name", "code"]
        constraints = [
            models.UniqueConstraint(fields=["code"], name="ol_commitment_status_code_uq"),
        ]
        indexes = [
            models.Index(fields=["applies_to", "is_active", "display_order"], name="ol_commitment_status_idx"),
            models.Index(fields=["is_terminal", "is_active"], name="ol_commitment_terminal_idx"),
        ]

    def clean(self):
        super().clean()
        self.code = (self.code or "").strip().upper()
        self.applies_to = (self.applies_to or "COMMITMENT").strip().upper()
        if not self.applies_to:
            raise ValidationError({"applies_to": "Status applicability is required."})
        if not self.code:
            raise ValidationError({"code": "A commitment status code is required."})
