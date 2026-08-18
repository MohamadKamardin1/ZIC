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
