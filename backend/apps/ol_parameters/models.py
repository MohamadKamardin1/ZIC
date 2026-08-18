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


# =============================================================================
# OL POLICY SETUP PART 3
# =============================================================================


class OLHealthQuestionAnswerType(models.TextChoices):
    BOOLEAN = "BOOLEAN", "Boolean"
    TEXT = "TEXT", "Text"
    NUMBER = "NUMBER", "Number"
    DATE = "DATE", "Date"
    CHOICE = "CHOICE", "Choice"


class OLHealthQuestionImpact(models.TextChoices):
    NONE = "NONE", "None"
    LOW = "LOW", "Low"
    MEDIUM = "MEDIUM", "Medium"
    HIGH = "HIGH", "High"
    CRITICAL = "CRITICAL", "Critical"


class OLHealthQuestion(OLParameterBaseModel):
    """Reusable health-question catalog consumed by configurable underwriting questionnaires."""

    question_text = models.TextField()
    category = models.CharField(max_length=80, blank=True, default="")
    answer_type = models.CharField(
        max_length=20,
        choices=OLHealthQuestionAnswerType.choices,
        default=OLHealthQuestionAnswerType.BOOLEAN,
    )
    underwriting_impact = models.CharField(
        max_length=20,
        choices=OLHealthQuestionImpact.choices,
        default=OLHealthQuestionImpact.NONE,
    )
    requires_medical_followup = models.BooleanField(default=False)

    class Meta:
        ordering = ["category", "code"]
        constraints = [
            models.UniqueConstraint(fields=["code"], name="ol_health_question_code_uq"),
        ]
        indexes = [
            models.Index(fields=["category", "is_active"], name="ol_health_question_cat_idx"),
            models.Index(fields=["answer_type", "is_active"], name="ol_health_question_type_idx"),
            models.Index(fields=["requires_medical_followup", "is_active"], name="ol_health_question_med_idx"),
        ]

    def clean(self):
        super().clean()
        errors = {}
        self.question_text = (self.question_text or "").strip()
        self.category = (self.category or "").strip().upper()
        self.answer_type = (self.answer_type or "").strip().upper()
        self.underwriting_impact = (self.underwriting_impact or "NONE").strip().upper()
        if not self.question_text:
            errors["question_text"] = "Question text is required."
        if self.answer_type not in {choice for choice, _ in OLHealthQuestionAnswerType.choices}:
            errors["answer_type"] = "Unsupported health-question answer type."
        if self.underwriting_impact not in {choice for choice, _ in OLHealthQuestionImpact.choices}:
            errors["underwriting_impact"] = "Unsupported underwriting impact."
        if errors:
            raise ValidationError(errors)


class OLHealthQuestionnaireScope(models.TextChoices):
    PRODUCT = "PRODUCT", "Product"
    PLAN = "PLAN", "Plan"
    SCHEME = "SCHEME", "Scheme"
    GLOBAL = "GLOBAL", "Global"


class OLHealthQuestionnaire(OLEffectiveDateModel):
    """Effective-dated and versioned questionnaire header with configurable scope."""

    applies_to_scope = models.CharField(
        max_length=20,
        choices=OLHealthQuestionnaireScope.choices,
        default=OLHealthQuestionnaireScope.GLOBAL,
    )
    product = models.ForeignKey(
        "ordinary_life.OLProduct",
        on_delete=models.PROTECT,
        related_name="ol_parameter_health_questionnaires",
        null=True,
        blank=True,
    )
    plan = models.ForeignKey(
        "ordinary_life.OLPlan",
        on_delete=models.PROTECT,
        related_name="ol_parameter_health_questionnaires",
        null=True,
        blank=True,
    )
    scheme_code = models.CharField(max_length=100, blank=True, default="")
    sum_assured_threshold = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    age_threshold = models.PositiveSmallIntegerField(null=True, blank=True)
    version = models.CharField(max_length=50, default="1.0")

    class Meta:
        ordering = ["code", "-effective_from", "version"]
        constraints = [
            models.UniqueConstraint(fields=["code", "version"], name="ol_health_questionnaire_code_ver_uq"),
            models.CheckConstraint(
                check=models.Q(sum_assured_threshold__isnull=True) | models.Q(sum_assured_threshold__gte=0),
                name="ol_health_qnr_sum_nonneg",
            ),
        ]
        indexes = [
            models.Index(fields=["applies_to_scope", "is_active", "effective_from"], name="ol_health_qnr_scope_idx"),
            models.Index(fields=["product", "plan", "is_active"], name="ol_health_qnr_product_idx"),
            models.Index(fields=["code", "version"], name="ol_health_qnr_code_ver_idx"),
        ]

    def clean(self):
        super().clean()
        errors = {}
        self.applies_to_scope = (self.applies_to_scope or "GLOBAL").strip().upper()
        self.scheme_code = (self.scheme_code or "").strip().upper()
        self.version = (self.version or "").strip()
        if self.applies_to_scope not in {choice for choice, _ in OLHealthQuestionnaireScope.choices}:
            errors["applies_to_scope"] = "Unsupported questionnaire scope."
        if not self.version:
            errors["version"] = "Questionnaire version is required."
        if self.sum_assured_threshold is not None and self.sum_assured_threshold < 0:
            errors["sum_assured_threshold"] = "Sum-assured threshold cannot be negative."
        if self.age_threshold is not None and self.age_threshold < 1:
            errors["age_threshold"] = "Age threshold must be positive."
        if self.applies_to_scope == OLHealthQuestionnaireScope.GLOBAL:
            if self.product_id or self.plan_id or self.scheme_code:
                errors["applies_to_scope"] = "Global questionnaires cannot have product, plan, or scheme scope."
        elif self.applies_to_scope == OLHealthQuestionnaireScope.PRODUCT:
            if not self.product_id or self.plan_id or self.scheme_code:
                errors["product"] = "Product scope requires a product and cannot include plan or scheme scope."
        elif self.applies_to_scope == OLHealthQuestionnaireScope.PLAN:
            if not self.plan_id or self.scheme_code:
                errors["plan"] = "Plan scope requires a plan and cannot include scheme scope."
        elif self.applies_to_scope == OLHealthQuestionnaireScope.SCHEME:
            if not self.scheme_code or self.product_id or self.plan_id:
                errors["scheme_code"] = "Scheme scope requires a scheme code and cannot include product or plan scope."
        if self.product_id and not getattr(self.product, "is_active", True):
            errors["product"] = "Questionnaire product must be active."
        if self.plan_id and not getattr(self.plan, "is_active", True):
            errors["plan"] = "Questionnaire plan must be active."
        if self.plan_id and self.product_id:
            plan_product_id = getattr(getattr(self.plan, "product_version", None), "product_id", None)
            if plan_product_id and plan_product_id != self.product_id:
                errors["plan"] = "Questionnaire plan must belong to the selected product."
        if errors:
            raise ValidationError(errors)


class OLHealthQuestionnaireItem(OLParameterBaseModel):
    """Ordered question membership; mandatory items are progression blockers for future flows."""

    questionnaire = models.ForeignKey(
        OLHealthQuestionnaire,
        on_delete=models.CASCADE,
        related_name="items",
    )
    health_question = models.ForeignKey(
        OLHealthQuestion,
        on_delete=models.PROTECT,
        related_name="questionnaire_items",
    )
    sequence = models.PositiveIntegerField()
    mandatory = models.BooleanField(default=False)
    trigger_medical_requirement = models.BooleanField(default=False)
    score = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)

    class Meta:
        ordering = ["questionnaire", "sequence", "code"]
        constraints = [
            models.UniqueConstraint(fields=["code"], name="ol_health_qitem_code_uq"),
            models.UniqueConstraint(fields=["questionnaire", "health_question"], name="ol_health_qitem_question_uq"),
            models.UniqueConstraint(fields=["questionnaire", "sequence"], name="ol_health_qitem_sequence_uq"),
            models.CheckConstraint(check=models.Q(sequence__gt=0), name="ol_health_qitem_sequence_pos"),
            models.CheckConstraint(check=models.Q(score__isnull=True) | models.Q(score__gte=0), name="ol_health_qitem_score_nonneg"),
        ]
        indexes = [
            models.Index(fields=["questionnaire", "is_active", "sequence"], name="ol_health_qitem_order_idx"),
            models.Index(fields=["mandatory", "is_active"], name="ol_health_qitem_mand_idx"),
        ]

    def clean(self):
        super().clean()
        errors = {}
        if not self.questionnaire_id:
            errors["questionnaire"] = "Questionnaire is required."
        if not self.health_question_id:
            errors["health_question"] = "Health question is required."
        if self.sequence < 1:
            errors["sequence"] = "Questionnaire item sequence must be positive."
        if self.score is not None and self.score < 0:
            errors["score"] = "Question score/weight cannot be negative."
        if self.questionnaire_id and not getattr(self.questionnaire, "is_active", True):
            errors["questionnaire"] = "Questionnaire must be active."
        if self.health_question_id and not getattr(self.health_question, "is_active", True):
            errors["health_question"] = "Health question must be active."
        if errors:
            raise ValidationError(errors)


class OLNotificationEventType(models.TextChoices):
    PREMIUM_DUE = "PREMIUM_DUE", "Premium due"
    GRACE_START = "GRACE_START", "Grace start"
    GRACE_WARNING = "GRACE_WARNING", "Grace warning"
    PRE_LAPSE = "PRE_LAPSE", "Pre-lapse"
    LAPSE = "LAPSE", "Lapse"


class OLNotificationChannel(models.TextChoices):
    SYSTEM = "SYSTEM", "System"
    EMAIL = "EMAIL", "Email"
    SMS = "SMS", "SMS"
    PORTAL = "PORTAL", "Portal"
    OTHER = "OTHER", "Other"


class OLNotificationRecipientType(models.TextChoices):
    POLICYHOLDER = "POLICYHOLDER", "Policyholder"
    AGENT = "AGENT", "Agent"
    STAFF = "STAFF", "Staff"
    PARTNER = "PARTNER", "Partner"


class OLGracePeriodNotificationSchedule(OLEffectiveDateModel):
    """Effective-dated notification schedule relative to a premium/grace event."""

    event_type = models.CharField(max_length=30, choices=OLNotificationEventType.choices)
    days_offset = models.SmallIntegerField()
    notification_channel = models.CharField(max_length=20, choices=OLNotificationChannel.choices, default=OLNotificationChannel.SYSTEM)
    recipient_type = models.CharField(max_length=20, choices=OLNotificationRecipientType.choices, default=OLNotificationRecipientType.POLICYHOLDER)
    template_code = models.CharField(max_length=100, blank=True, default="")

    class Meta:
        ordering = ["event_type", "days_offset", "code"]
        constraints = [
            models.UniqueConstraint(fields=["code"], name="ol_grace_notify_code_uq"),
            models.CheckConstraint(check=models.Q(days_offset__gte=-3650) & models.Q(days_offset__lte=3650), name="ol_grace_notify_offset_rng"),
        ]
        indexes = [
            models.Index(fields=["event_type", "is_active", "effective_from"], name="ol_grace_notify_event_idx"),
            models.Index(fields=["notification_channel", "recipient_type"], name="ol_grace_notify_route_idx"),
        ]

    def clean(self):
        super().clean()
        errors = {}
        self.event_type = (self.event_type or "").strip().upper()
        self.notification_channel = (self.notification_channel or "SYSTEM").strip().upper()
        self.recipient_type = (self.recipient_type or "POLICYHOLDER").strip().upper()
        self.template_code = (self.template_code or "").strip().upper()
        if self.event_type not in {choice for choice, _ in OLNotificationEventType.choices}:
            errors["event_type"] = "Unsupported notification event type."
        if self.notification_channel not in {choice for choice, _ in OLNotificationChannel.choices}:
            errors["notification_channel"] = "Unsupported notification channel."
        if self.recipient_type not in {choice for choice, _ in OLNotificationRecipientType.choices}:
            errors["recipient_type"] = "Unsupported notification recipient type."
        if self.days_offset < -3650 or self.days_offset > 3650:
            errors["days_offset"] = "Notification offset must be between -3650 and 3650 days."
        if errors:
            raise ValidationError(errors)


class OLReinstatementWindow(OLEffectiveDateModel):
    """Effective-dated lapse reinstatement eligibility and financial requirements."""

    product = models.ForeignKey(
        "ordinary_life.OLProduct",
        on_delete=models.PROTECT,
        related_name="ol_parameter_reinstatement_windows",
        null=True,
        blank=True,
    )
    plan = models.ForeignKey(
        "ordinary_life.OLPlan",
        on_delete=models.PROTECT,
        related_name="ol_parameter_reinstatement_windows",
        null=True,
        blank=True,
    )
    days_after_lapse = models.PositiveIntegerField()
    maximum_reinstatements = models.PositiveIntegerField(null=True, blank=True)
    require_medical_underwriting = models.BooleanField(default=False)
    require_outstanding_premium_payment = models.BooleanField(default=True)
    interest_rate = models.DecimalField(max_digits=7, decimal_places=4, null=True, blank=True)
    penalty_rate = models.DecimalField(max_digits=7, decimal_places=4, null=True, blank=True)

    class Meta:
        ordering = ["product", "plan", "-effective_from", "code"]
        constraints = [
            models.UniqueConstraint(fields=["code"], name="ol_reinstate_window_code_uq"),
            models.CheckConstraint(check=models.Q(days_after_lapse__gt=0), name="ol_reinstate_days_pos"),
            models.CheckConstraint(check=models.Q(maximum_reinstatements__isnull=True) | models.Q(maximum_reinstatements__gt=0), name="ol_reinstate_max_pos"),
            models.CheckConstraint(check=models.Q(interest_rate__isnull=True) | (models.Q(interest_rate__gte=0) & models.Q(interest_rate__lte=100)), name="ol_reinstate_interest_rng"),
            models.CheckConstraint(check=models.Q(penalty_rate__isnull=True) | (models.Q(penalty_rate__gte=0) & models.Q(penalty_rate__lte=100)), name="ol_reinstate_penalty_rng"),
        ]
        indexes = [
            models.Index(fields=["product", "plan", "is_active", "effective_from"], name="ol_reinstate_scope_idx"),
            models.Index(fields=["require_medical_underwriting", "is_active"], name="ol_reinstate_med_idx"),
        ]

    def clean(self):
        super().clean()
        errors = {}
        _policy_setup_validate_product_plan(self, errors)
        if self.days_after_lapse <= 0:
            errors["days_after_lapse"] = "Days after lapse must be positive."
        if self.maximum_reinstatements is not None and self.maximum_reinstatements <= 0:
            errors["maximum_reinstatements"] = "Maximum reinstatements must be positive when supplied."
        for field_name, value in (("interest_rate", self.interest_rate), ("penalty_rate", self.penalty_rate)):
            if value is not None and (value < 0 or value > 100):
                errors[field_name] = "Rate must be between 0 and 100 percent."
        if errors:
            raise ValidationError(errors)
        candidates = self.__class__.objects.filter(product=self.product, plan=self.plan, is_active=True)
        if self.pk:
            candidates = candidates.exclude(pk=self.pk)
        for candidate in candidates:
            if _policy_setup_intervals_overlap(self.effective_from, self.effective_to, candidate.effective_from, candidate.effective_to):
                raise ValidationError({"code": "An active reinstatement window overlaps an existing row in the same scope."})


# =============================================================================
# OL PRODUCT SETUP
# =============================================================================


class OLPlanType(OLParameterBaseModel):
    """Catalog of Ordinary Life plan/product categories."""

    plan_category = models.CharField(max_length=50, default="INDIVIDUAL")

    class Meta:
        ordering = ["name", "code"]
        constraints = [
            models.UniqueConstraint(fields=["code"], name="ol_product_plan_type_code_uq"),
        ]
        indexes = [
            models.Index(fields=["plan_category", "is_active"], name="ol_product_plan_type_cat_idx"),
        ]

    def clean(self):
        super().clean()
        self.plan_category = (self.plan_category or "INDIVIDUAL").strip().upper()
        if not self.plan_category:
            raise ValidationError({"plan_category": "Plan category is required."})


class OLInsuranceClass(models.TextChoices):
    INDIVIDUAL = "INDIVIDUAL", "Individual"
    GROUP = "GROUP", "Group"
    CREDIT = "CREDIT", "Credit"
    INVESTMENT_LINKED = "INVESTMENT_LINKED", "Investment linked"


class OLProduct(OLEffectiveDateModel):
    """Table-driven Ordinary Life product definition used by future quotation and policy flows."""

    plan_type = models.ForeignKey(
        OLPlanType,
        on_delete=models.PROTECT,
        related_name="products",
    )
    insurance_class = models.CharField(max_length=30, choices=OLInsuranceClass.choices, default=OLInsuranceClass.INDIVIDUAL)
    currency = models.CharField(max_length=3, default="TZS")
    min_entry_age = models.PositiveSmallIntegerField(default=18)
    max_entry_age = models.PositiveSmallIntegerField(default=65)
    min_term = models.PositiveSmallIntegerField(default=1)
    max_term = models.PositiveSmallIntegerField(default=30)
    min_sum_assured = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    max_sum_assured = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    premium_frequencies = models.JSONField(default=list)
    allow_riders = models.BooleanField(default=False)
    allow_loans = models.BooleanField(default=False)
    allow_withdrawals = models.BooleanField(default=False)
    allow_surrender = models.BooleanField(default=True)
    allow_paidup = models.BooleanField(default=False)
    allow_bonus = models.BooleanField(default=False)
    investment_linked = models.BooleanField(default=False)

    class Meta:
        ordering = ["name", "code"]
        constraints = [
            models.UniqueConstraint(fields=["code"], name="ol_product_setup_code_uq"),
            models.CheckConstraint(check=models.Q(min_entry_age__lte=models.F("max_entry_age")), name="ol_product_setup_age_range_ck"),
            models.CheckConstraint(check=models.Q(min_term__gt=0) & models.Q(min_term__lte=models.F("max_term")), name="ol_product_setup_term_range_ck"),
            models.CheckConstraint(
                check=models.Q(min_sum_assured__isnull=True)
                | models.Q(max_sum_assured__isnull=True)
                | models.Q(min_sum_assured__lte=models.F("max_sum_assured")),
                name="ol_product_setup_sum_range_ck",
            ),
        ]
        indexes = [
            models.Index(fields=["plan_type", "is_active"], name="ol_product_setup_plan_idx"),
            models.Index(fields=["insurance_class", "is_active"], name="ol_product_setup_class_idx"),
            models.Index(fields=["currency", "is_active"], name="ol_product_setup_currency_idx"),
            models.Index(fields=["is_active", "effective_from", "effective_to"], name="ol_prod_setup_active_dates"),
        ]

    def clean(self):
        super().clean()
        errors = {}
        self.insurance_class = (self.insurance_class or OLInsuranceClass.INDIVIDUAL).strip().upper()
        self.currency = (self.currency or "").strip().upper()
        if self.insurance_class not in {choice for choice, _ in OLInsuranceClass.choices}:
            errors["insurance_class"] = "Unsupported insurance class."
        if len(self.currency) != 3 or not self.currency.isalpha():
            errors["currency"] = "Currency must be a three-letter code."
        if self.plan_type_id and not getattr(self.plan_type, "is_active", True):
            errors["plan_type"] = "Plan type must be active."
        if self.min_entry_age > self.max_entry_age:
            errors["max_entry_age"] = "Maximum entry age cannot be less than minimum entry age."
        if self.min_entry_age > 150 or self.max_entry_age > 150:
            errors["max_entry_age"] = "Entry age cannot exceed 150 years."
        if self.min_term < 1 or self.min_term > self.max_term:
            errors["max_term"] = "Maximum term must be at least the minimum term, and minimum term must be positive."
        if self.min_sum_assured is not None and self.min_sum_assured < 0:
            errors["min_sum_assured"] = "Minimum sum assured cannot be negative."
        if self.max_sum_assured is not None and self.max_sum_assured < 0:
            errors["max_sum_assured"] = "Maximum sum assured cannot be negative."
        if self.min_sum_assured is not None and self.max_sum_assured is not None and self.min_sum_assured > self.max_sum_assured:
            errors["max_sum_assured"] = "Maximum sum assured cannot be less than minimum sum assured."
        if not isinstance(self.premium_frequencies, list) or not self.premium_frequencies:
            errors["premium_frequencies"] = "At least one premium frequency is required."
        elif any(not isinstance(value, str) or not value.strip() for value in self.premium_frequencies):
            errors["premium_frequencies"] = "Premium frequencies must be a list of non-empty strings."
        else:
            self.premium_frequencies = list(dict.fromkeys(value.strip().upper() for value in self.premium_frequencies))
        if errors:
            raise ValidationError(errors)


class OLRateType(models.TextChoices):
    PERCENTAGE = "PERCENTAGE", "Percentage"
    FIXED = "FIXED", "Fixed"
    FACTOR = "FACTOR", "Factor"


class OLPlanTaxConfiguration(OLEffectiveDateModel):
    """Effective-dated, ordered tax component scoped to a Product Setup product or operational plan."""

    product = models.ForeignKey(
        OLProduct,
        on_delete=models.PROTECT,
        related_name="tax_configurations",
        null=True,
        blank=True,
    )
    plan = models.ForeignKey(
        "ordinary_life.OLPlan",
        on_delete=models.PROTECT,
        related_name="ol_parameter_tax_configurations",
        null=True,
        blank=True,
    )
    tax_type = models.CharField(max_length=50)
    tax_basis = models.CharField(max_length=50)
    rate_type = models.CharField(max_length=20, choices=OLRateType.choices, default=OLRateType.PERCENTAGE)
    rate_value = models.DecimalField(max_digits=18, decimal_places=6)
    apply_on = models.CharField(max_length=50)
    sequence = models.PositiveIntegerField(default=1)
    country_or_branch = models.CharField(max_length=80, blank=True, default="")

    class Meta:
        ordering = ["product", "plan", "sequence", "code"]
        constraints = [
            models.UniqueConstraint(fields=["code"], name="ol_product_tax_code_uq"),
            models.CheckConstraint(check=models.Q(sequence__gt=0), name="ol_product_tax_sequence_pos_ck"),
            models.CheckConstraint(check=models.Q(rate_value__gte=0), name="ol_product_tax_rate_nonneg_ck"),
        ]
        indexes = [
            models.Index(fields=["product", "plan", "is_active", "effective_from"], name="ol_product_tax_scope_idx"),
            models.Index(fields=["tax_type", "tax_basis", "is_active"], name="ol_product_tax_type_idx"),
        ]

    def clean(self):
        super().clean()
        errors = {}
        self.tax_type = (self.tax_type or "").strip().upper()
        self.tax_basis = (self.tax_basis or "").strip().upper()
        self.rate_type = (self.rate_type or OLRateType.PERCENTAGE).strip().upper()
        self.apply_on = (self.apply_on or "").strip().upper()
        self.country_or_branch = (self.country_or_branch or "").strip().upper()
        if not self.product_id and not self.plan_id:
            errors["product"] = "Tax configuration must be scoped to a product or plan."
        if not self.tax_type:
            errors["tax_type"] = "Tax type is required."
        if not self.tax_basis:
            errors["tax_basis"] = "Tax basis is required."
        if not self.apply_on:
            errors["apply_on"] = "Apply-on dimension is required."
        if self.rate_type not in {choice for choice, _ in OLRateType.choices}:
            errors["rate_type"] = "Unsupported tax rate type."
        if self.rate_value is None or self.rate_value < 0:
            errors["rate_value"] = "Tax rate value cannot be negative."
        elif self.rate_type == OLRateType.PERCENTAGE and self.rate_value > 100:
            errors["rate_value"] = "Percentage tax rate cannot exceed 100."
        if errors:
            raise ValidationError(errors)
        candidates = self.__class__.objects.filter(
            product=self.product,
            plan=self.plan,
            tax_type=self.tax_type,
            tax_basis=self.tax_basis,
            rate_type=self.rate_type,
            apply_on=self.apply_on,
            sequence=self.sequence,
            country_or_branch=self.country_or_branch,
            is_active=True,
        ).exclude(pk=self.pk)
        if any(_product_setup_intervals_overlap(self.effective_from, self.effective_to, candidate.effective_from, candidate.effective_to) for candidate in candidates):
            raise ValidationError({"code": "An active tax configuration overlaps an existing row in the same scope."})


class OLPlanTargetMarket(OLParameterBaseModel):
    """Target-market eligibility configuration for a Product Setup product or operational plan."""

    product = models.ForeignKey(
        OLProduct,
        on_delete=models.PROTECT,
        related_name="target_markets",
        null=True,
        blank=True,
    )
    plan = models.ForeignKey(
        "ordinary_life.OLPlan",
        on_delete=models.PROTECT,
        related_name="ol_parameter_target_markets",
        null=True,
        blank=True,
    )
    target_market_type = models.CharField(max_length=60)
    min_age = models.PositiveSmallIntegerField(null=True, blank=True)
    max_age = models.PositiveSmallIntegerField(null=True, blank=True)
    occupation_categories = models.JSONField(default=list, blank=True)
    residency_requirement = models.CharField(max_length=80, blank=True, default="")

    class Meta:
        ordering = ["product", "plan", "target_market_type", "code"]
        constraints = [
            models.UniqueConstraint(fields=["code"], name="ol_product_market_code_uq"),
            models.CheckConstraint(check=models.Q(max_age__isnull=True) | models.Q(min_age__isnull=True) | models.Q(max_age__gte=models.F("min_age")), name="ol_product_market_age_range_ck"),
        ]
        indexes = [
            models.Index(fields=["product", "plan", "is_active"], name="ol_product_market_scope_idx"),
            models.Index(fields=["target_market_type", "is_active"], name="ol_product_market_type_idx"),
        ]

    def clean(self):
        super().clean()
        errors = {}
        self.target_market_type = (self.target_market_type or "").strip().upper()
        self.residency_requirement = (self.residency_requirement or "").strip().upper()
        if not self.product_id and not self.plan_id:
            errors["product"] = "Target market must be scoped to a product or plan."
        if not self.target_market_type:
            errors["target_market_type"] = "Target-market type is required."
        if self.min_age is not None and self.max_age is not None and self.min_age > self.max_age:
            errors["max_age"] = "Maximum target-market age cannot be less than minimum age."
        if self.occupation_categories is not None and (
            not isinstance(self.occupation_categories, list)
            or any(not isinstance(value, str) or not value.strip() for value in self.occupation_categories)
        ):
            errors["occupation_categories"] = "Occupation categories must be a list of non-empty strings."
        else:
            self.occupation_categories = list(dict.fromkeys(value.strip().upper() for value in (self.occupation_categories or [])))
        if errors:
            raise ValidationError(errors)
        candidates = self.__class__.objects.filter(
            product=self.product,
            plan=self.plan,
            target_market_type=self.target_market_type,
            residency_requirement=self.residency_requirement,
            is_active=True,
        ).exclude(pk=self.pk)
        for candidate in candidates:
            if _product_setup_intervals_overlap(self.effective_from, self.effective_to, candidate.effective_from, candidate.effective_to) and _product_setup_intervals_overlap(self.min_age, self.max_age, candidate.min_age, candidate.max_age):
                raise ValidationError({"code": "An active target-market row overlaps an existing row in the same scope."})


class OLPlanRiskCategory(OLParameterBaseModel):
    """Underwriting risk class and loading basis scoped to a product, plan, or globally."""

    product = models.ForeignKey(
        OLProduct,
        on_delete=models.PROTECT,
        related_name="risk_categories",
        null=True,
        blank=True,
    )
    plan = models.ForeignKey(
        "ordinary_life.OLPlan",
        on_delete=models.PROTECT,
        related_name="ol_parameter_risk_categories",
        null=True,
        blank=True,
    )
    underwriting_class = models.CharField(max_length=60)
    loading_basis = models.CharField(max_length=60)

    class Meta:
        ordering = ["product", "plan", "underwriting_class", "code"]
        constraints = [
            models.UniqueConstraint(fields=["code"], name="ol_product_risk_code_uq"),
        ]
        indexes = [
            models.Index(fields=["product", "plan", "is_active"], name="ol_product_risk_scope_idx"),
            models.Index(fields=["underwriting_class", "is_active"], name="ol_product_risk_class_idx"),
        ]

    def clean(self):
        super().clean()
        errors = {}
        self.underwriting_class = (self.underwriting_class or "").strip().upper()
        self.loading_basis = (self.loading_basis or "").strip().upper()
        if not self.underwriting_class:
            errors["underwriting_class"] = "Underwriting class is required."
        if not self.loading_basis:
            errors["loading_basis"] = "Loading basis is required."
        if errors:
            raise ValidationError(errors)
        candidates = self.__class__.objects.filter(
            product=self.product,
            plan=self.plan,
            underwriting_class=self.underwriting_class,
            loading_basis=self.loading_basis,
            is_active=True,
        ).exclude(pk=self.pk)
        if any(_product_setup_intervals_overlap(self.effective_from, self.effective_to, candidate.effective_from, candidate.effective_to) for candidate in candidates):
            raise ValidationError({"code": "An active risk category overlaps an existing row in the same scope."})


class OLPlanOccupationRiskLimit(OLEffectiveDateModel):
    """Occupation-level sum-assured and loading limit for product or plan underwriting."""

    product = models.ForeignKey(
        OLProduct,
        on_delete=models.PROTECT,
        related_name="occupation_risk_limits",
        null=True,
        blank=True,
    )
    plan = models.ForeignKey(
        "ordinary_life.OLPlan",
        on_delete=models.PROTECT,
        related_name="ol_parameter_occupation_risk_limits",
        null=True,
        blank=True,
    )
    occupation_risk_category = models.CharField(max_length=80)
    max_sum_assured = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    loading_rate = models.DecimalField(max_digits=9, decimal_places=6, default=0)
    exclusion_flag = models.BooleanField(default=False)

    class Meta:
        ordering = ["product", "plan", "occupation_risk_category", "code"]
        constraints = [
            models.UniqueConstraint(fields=["code"], name="ol_product_occupation_limit_code_uq"),
            models.CheckConstraint(check=models.Q(max_sum_assured__isnull=True) | models.Q(max_sum_assured__gte=0), name="ol_product_occupation_sum_nonneg_ck"),
            models.CheckConstraint(check=models.Q(loading_rate__gte=0) & models.Q(loading_rate__lte=100), name="ol_product_occupation_loading_rng_ck"),
        ]
        indexes = [
            models.Index(fields=["product", "plan", "is_active", "effective_from"], name="ol_prod_occup_scope_idx"),
            models.Index(fields=["occupation_risk_category", "is_active"], name="ol_product_occupation_cat_idx"),
        ]

    def clean(self):
        super().clean()
        errors = {}
        self.occupation_risk_category = (self.occupation_risk_category or "").strip().upper()
        if not self.product_id and not self.plan_id:
            errors["product"] = "Occupation risk limit must be scoped to a product or plan."
        if not self.occupation_risk_category:
            errors["occupation_risk_category"] = "Occupation risk category is required."
        if self.max_sum_assured is not None and self.max_sum_assured < 0:
            errors["max_sum_assured"] = "Maximum sum assured cannot be negative."
        if self.loading_rate < 0 or self.loading_rate > 100:
            errors["loading_rate"] = "Loading rate must be between 0 and 100."
        if errors:
            raise ValidationError(errors)
        candidates = self.__class__.objects.filter(
            product=self.product,
            plan=self.plan,
            occupation_risk_category=self.occupation_risk_category,
            is_active=True,
        ).exclude(pk=self.pk)
        if any(_product_setup_intervals_overlap(self.effective_from, self.effective_to, candidate.effective_from, candidate.effective_to) for candidate in candidates):
            raise ValidationError({"code": "An active occupation risk limit overlaps an existing row in the same scope."})


class OLInvestmentFundRiskProfile(models.TextChoices):
    CONSERVATIVE = "CONSERVATIVE", "Conservative"
    MODERATE = "MODERATE", "Moderate"
    BALANCED = "BALANCED", "Balanced"
    AGGRESSIVE = "AGGRESSIVE", "Aggressive"


class OLInvestmentFundType(OLParameterBaseModel):
    """Catalog of investment-fund risk profiles."""

    risk_profile = models.CharField(max_length=30, choices=OLInvestmentFundRiskProfile.choices, default=OLInvestmentFundRiskProfile.MODERATE)

    class Meta:
        ordering = ["name", "code"]
        constraints = [
            models.UniqueConstraint(fields=["code"], name="ol_product_fund_type_code_uq"),
        ]
        indexes = [
            models.Index(fields=["risk_profile", "is_active"], name="ol_product_fund_type_risk_idx"),
        ]

    def clean(self):
        super().clean()
        self.risk_profile = (self.risk_profile or OLInvestmentFundRiskProfile.MODERATE).strip().upper()
        if self.risk_profile not in {choice for choice, _ in OLInvestmentFundRiskProfile.choices}:
            raise ValidationError({"risk_profile": "Unsupported investment-fund risk profile."})


class OLValuationFrequency(models.TextChoices):
    DAILY = "DAILY", "Daily"
    WEEKLY = "WEEKLY", "Weekly"
    MONTHLY = "MONTHLY", "Monthly"
    QUARTERLY = "QUARTERLY", "Quarterly"
    ANNUAL = "ANNUAL", "Annual"


class OLInvestmentFund(OLEffectiveDateModel):
    """Effective-dated investment fund catalog and allocation metadata."""

    fund_type = models.ForeignKey(
        OLInvestmentFundType,
        on_delete=models.PROTECT,
        related_name="funds",
    )
    currency = models.CharField(max_length=3, default="TZS")
    valuation_frequency = models.CharField(max_length=20, choices=OLValuationFrequency.choices, default=OLValuationFrequency.DAILY)
    unit_price = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)
    allocation_rules = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["name", "code"]
        constraints = [
            models.UniqueConstraint(fields=["code"], name="ol_product_fund_code_uq"),
            models.CheckConstraint(check=models.Q(unit_price__isnull=True) | models.Q(unit_price__gt=0), name="ol_product_fund_unit_price_pos_ck"),
        ]
        indexes = [
            models.Index(fields=["fund_type", "is_active"], name="ol_product_fund_type_idx"),
            models.Index(fields=["currency", "valuation_frequency", "is_active"], name="ol_product_fund_route_idx"),
            models.Index(fields=["is_active", "effective_from", "effective_to"], name="ol_prod_fund_active_dates"),
        ]

    def clean(self):
        super().clean()
        errors = {}
        self.currency = (self.currency or "").strip().upper()
        self.valuation_frequency = (self.valuation_frequency or OLValuationFrequency.DAILY).strip().upper()
        if len(self.currency) != 3 or not self.currency.isalpha():
            errors["currency"] = "Currency must be a three-letter code."
        if self.valuation_frequency not in {choice for choice, _ in OLValuationFrequency.choices}:
            errors["valuation_frequency"] = "Unsupported valuation frequency."
        if self.fund_type_id and not getattr(self.fund_type, "is_active", True):
            errors["fund_type"] = "Fund type must be active."
        if self.unit_price is not None and self.unit_price <= 0:
            errors["unit_price"] = "Unit price must be greater than zero."
        if not isinstance(self.allocation_rules, dict):
            errors["allocation_rules"] = "Allocation rules must be a JSON object."
        if errors:
            raise ValidationError(errors)


def _product_setup_intervals_overlap(start_a, end_a, start_b, end_b):
    """Return whether two inclusive date or numeric intervals overlap."""
    if end_a is not None and start_b is not None and end_a < start_b:
        return False
    if end_b is not None and start_a is not None and end_b < start_a:
        return False
    return True
