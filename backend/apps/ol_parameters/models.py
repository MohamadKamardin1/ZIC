import uuid
import json
from decimal import Decimal

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


class OLAgentCommissionType(models.TextChoices):
    FIRST_PREMIUM = "FIRST_PREMIUM", "First premium"
    RENEWAL_PREMIUM = "RENEWAL_PREMIUM", "Renewal premium"
    ADMINISTRATIVE = "ADMINISTRATIVE", "Administrative"
    HIERARCHICAL = "HIERARCHICAL", "Hierarchical"
    OVERRIDE = "OVERRIDE", "Override"
    OTHER = "OTHER", "Other"


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


class OLAgentCommissionSetup(OLEffectiveDateModel):
    """Effective-dated agent/intermediary commission configuration for Ordinary Life."""

    partner = models.ForeignKey(
        "partners.Partner",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="ol_agent_commission_setups",
        help_text="Optional partner or agent scope; agent intermediaries are represented by this relation.",
    )
    intermediary_type = models.CharField(max_length=80, blank=True, default="", db_index=True)
    distribution_channel = models.CharField(max_length=80, blank=True, default="", db_index=True)
    product = models.ForeignKey(
        "ol_parameters.OLProduct",
        on_delete=models.PROTECT,
        related_name="agent_commission_setups",
    )
    plan = models.ForeignKey(
        "ordinary_life.OLPlan",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="ol_parameter_agent_commission_setups",
    )
    rider = models.ForeignKey(
        "ol_parameters.OLRiderSetup",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="agent_commission_setups",
    )
    currency = models.CharField(max_length=3, blank=True, default="", db_index=True)
    branch = models.ForeignKey(
        "partner_onboarding.Branch",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="ol_agent_commission_setups",
    )
    commission_type = models.CharField(max_length=30, choices=OLAgentCommissionType.choices, db_index=True)
    premium_year_from = models.PositiveIntegerField(null=True, blank=True)
    premium_year_to = models.PositiveIntegerField(null=True, blank=True)
    policy_year_from = models.PositiveIntegerField(null=True, blank=True)
    policy_year_to = models.PositiveIntegerField(null=True, blank=True)
    rate_type = models.CharField(max_length=10, choices=OLCommissionRateType.choices, db_index=True)
    rate_value = models.DecimalField(max_digits=18, decimal_places=8)
    minimum_commission = models.DecimalField(max_digits=18, decimal_places=8, null=True, blank=True)
    maximum_commission = models.DecimalField(max_digits=18, decimal_places=8, null=True, blank=True)
    priority = models.PositiveIntegerField(default=100, db_index=True)
    reason = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["priority", "commission_type", "-effective_from", "code"]
        constraints = [
            models.UniqueConstraint(fields=["code"], name="ol_agent_comm_setup_code_uq"),
            models.CheckConstraint(
                check=models.Q(premium_year_to__isnull=True)
                | models.Q(premium_year_from__isnull=True)
                | models.Q(premium_year_to__gte=models.F("premium_year_from")),
                name="ol_agent_comm_prem_years_ck",
            ),
            models.CheckConstraint(
                check=models.Q(policy_year_to__isnull=True)
                | models.Q(policy_year_from__isnull=True)
                | models.Q(policy_year_to__gte=models.F("policy_year_from")),
                name="ol_agent_comm_policy_years_ck",
            ),
            models.CheckConstraint(check=models.Q(rate_value__gte=0), name="ol_agent_comm_rate_nonneg_ck"),
            models.CheckConstraint(
                check=models.Q(minimum_commission__isnull=True) | models.Q(minimum_commission__gte=0),
                name="ol_agent_comm_min_nonneg_ck",
            ),
            models.CheckConstraint(
                check=models.Q(maximum_commission__isnull=True) | models.Q(maximum_commission__gte=0),
                name="ol_agent_comm_max_nonneg_ck",
            ),
            models.CheckConstraint(
                check=models.Q(maximum_commission__isnull=True)
                | models.Q(minimum_commission__isnull=True)
                | models.Q(maximum_commission__gte=models.F("minimum_commission")),
                name="ol_agent_comm_min_max_ck",
            ),
        ]
        indexes = [
            models.Index(
                fields=["partner", "product", "plan", "rider", "commission_type", "distribution_channel"],
                name="ol_agent_comm_scope_idx",
            ),
            models.Index(fields=["priority", "is_active", "effective_from"], name="ol_agent_comm_priority_idx"),
            models.Index(fields=["product", "commission_type", "is_active"], name="ol_agent_comm_product_idx"),
        ]

    @staticmethod
    def _ranges_overlap(start_a, end_a, start_b, end_b):
        if end_a is not None and start_b is not None and end_a < start_b:
            return False
        if end_b is not None and start_a is not None and end_b < start_a:
            return False
        return True

    def clean(self):
        super().clean()
        errors = {}
        self.intermediary_type = (self.intermediary_type or "").strip().upper()
        self.distribution_channel = (self.distribution_channel or "").strip().upper()
        self.currency = (self.currency or "").strip().upper()
        self.commission_type = (self.commission_type or "").strip().upper()
        self.rate_type = (self.rate_type or "").strip().upper()
        if not self.intermediary_type:
            errors["intermediary_type"] = "Intermediary type is required."
        if not self.distribution_channel:
            errors["distribution_channel"] = "Distribution channel is required."
        if self.currency and len(self.currency) != 3:
            errors["currency"] = "Currency must be a three-letter code when supplied."
        if self.commission_type not in dict(OLAgentCommissionType.choices):
            errors["commission_type"] = "Unsupported agent commission type."
        if self.rate_type not in dict(OLCommissionRateType.choices):
            errors["rate_type"] = "Unsupported commission rate type."
        if self.rate_value is None or self.rate_value < 0:
            errors["rate_value"] = "Rate value cannot be negative."
        if self.rate_type == OLCommissionRateType.PERCENTAGE and self.rate_value is not None and self.rate_value > 100:
            errors["rate_value"] = "Percentage commission rate cannot exceed 100."
        if self.minimum_commission is not None and self.minimum_commission < 0:
            errors["minimum_commission"] = "Minimum commission cannot be negative."
        if self.maximum_commission is not None and self.maximum_commission < 0:
            errors["maximum_commission"] = "Maximum commission cannot be negative."
        if (
            self.minimum_commission is not None
            and self.maximum_commission is not None
            and self.maximum_commission < self.minimum_commission
        ):
            errors["maximum_commission"] = "Maximum commission cannot be less than minimum commission."
        if self.premium_year_from is not None and self.premium_year_to is not None and self.premium_year_to < self.premium_year_from:
            errors["premium_year_to"] = "Premium year-to cannot be before year-from."
        if self.policy_year_from is not None and self.policy_year_to is not None and self.policy_year_to < self.policy_year_from:
            errors["policy_year_to"] = "Policy year-to cannot be before year-from."
        if self.plan_id and self.plan and self.product_id:
            plan_product_id = getattr(getattr(self.plan, "product_version", None), "product_id", None)
            if plan_product_id and plan_product_id != self.product_id:
                errors["plan"] = "Selected plan does not belong to the selected product."
        if self.rider_id and self.rider and self.rider.product_id and self.rider.product_id != self.product_id:
            errors["rider"] = "Selected rider does not belong to the selected product."
        if errors:
            raise ValidationError(errors)

        scope_fields = (
            "partner_id",
            "intermediary_type",
            "distribution_channel",
            "product_id",
            "plan_id",
            "rider_id",
            "currency",
            "branch_id",
            "commission_type",
        )
        filters = {field: getattr(self, field) for field in scope_fields}
        candidates = type(self).objects.filter(is_active=True, **filters).only(
            "id",
            "effective_from",
            "effective_to",
            "premium_year_from",
            "premium_year_to",
            "policy_year_from",
            "policy_year_to",
        )
        if self.pk:
            candidates = candidates.exclude(pk=self.pk)
        for other in candidates:
            if not self._ranges_overlap(self.effective_from, self.effective_to, other.effective_from, other.effective_to):
                continue
            if not self._ranges_overlap(self.premium_year_from, self.premium_year_to, other.premium_year_from, other.premium_year_to):
                continue
            if self._ranges_overlap(self.policy_year_from, self.policy_year_to, other.policy_year_from, other.policy_year_to):
                raise ValidationError({"effective_from": "An active agent commission setup with the same scope and overlapping period already exists."})


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


# =============================================================================
# OL PRODUCT RATING PART 1
# =============================================================================


class OLRatingTableBaseModel(models.Model):
    """Common table-header identity, lifecycle, effective-dating, and audit fields."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    table_code = models.CharField(max_length=100)
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
        ordering = ["table_code", "-effective_from", "version"]
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(effective_to__isnull=True)
                    | models.Q(effective_from__isnull=True)
                    | models.Q(effective_to__gte=models.F("effective_from"))
                ),
                name="%(app_label)s_%(class)s_dates_valid",
            ),
        ]
        indexes = [
            models.Index(
                fields=["table_code", "is_active", "effective_from"],
                name="%(app_label)s_%(class)s_table_idx",
            ),
            models.Index(
                fields=["is_active", "effective_from", "effective_to"],
                name="%(app_label)s_%(class)s_active_idx",
            ),
        ]

    def __str__(self):
        version = getattr(self, "version", "")
        return f"{self.table_code} v{version}" if version else self.table_code

    def clean(self):
        super().clean()
        self.table_code = (self.table_code or "").strip().upper()
        self.name = (self.name or "").strip()
        if not self.table_code:
            raise ValidationError({"table_code": "A rating table code is required."})
        if not self.name:
            raise ValidationError({"name": "A rating table name is required."})
        if self.effective_from and self.effective_to and self.effective_to < self.effective_from:
            raise ValidationError({"effective_to": "Effective-to cannot be before effective-from."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


def _rating_row_dates_within_table(instance, errors):
    table = getattr(instance, "table", None)
    if not instance.table_id:
        errors["table"] = "A rating table is required."
        return
    if not getattr(table, "is_active", True):
        errors["table"] = "The rating table must be active."
    if instance.effective_from and table.effective_from and instance.effective_from < table.effective_from:
        errors["effective_from"] = "Row effective-from cannot precede the table effective-from."
    if instance.effective_to and table.effective_to and instance.effective_to > table.effective_to:
        errors["effective_to"] = "Row effective-to cannot extend beyond the table effective-to."


def _rating_intervals_overlap(left, right, fields):
    return all(
        _product_setup_intervals_overlap(
            getattr(left, f"{field}_from", getattr(left, field, None)),
            getattr(left, f"{field}_to", getattr(left, field, None)),
            getattr(right, f"{field}_from", getattr(right, field, None)),
            getattr(right, f"{field}_to", getattr(right, field, None)),
        )
        for field in fields
    )


class OLPremiumRatingBasis(models.TextChoices):
    SUM_ASSURED = "SUM_ASSURED", "Sum assured"
    AGE_TERM = "AGE_TERM", "Age and term"
    PREMIUM = "PREMIUM", "Premium"
    FLAT = "FLAT", "Flat"
    CUSTOM = "CUSTOM", "Custom"


class OLPremiumRateUnit(models.TextChoices):
    PER_THOUSAND_SUM_ASSURED = "PER_THOUSAND_SUM_ASSURED", "Per thousand sum assured"
    PERCENTAGE = "PERCENTAGE", "Percentage"
    FIXED_AMOUNT = "FIXED_AMOUNT", "Fixed amount"
    FACTOR = "FACTOR", "Factor"


class OLPremiumRateTable(OLRatingTableBaseModel):
    """Versioned premium-rate table scoped to a Product Setup product and optional operational plan."""

    product = models.ForeignKey(
        OLProduct,
        on_delete=models.PROTECT,
        related_name="premium_rate_tables",
    )
    plan = models.ForeignKey(
        "ordinary_life.OLPlan",
        on_delete=models.PROTECT,
        related_name="ol_parameter_premium_rate_tables",
        null=True,
        blank=True,
    )
    rating_basis = models.CharField(max_length=40, choices=OLPremiumRatingBasis.choices, default=OLPremiumRatingBasis.AGE_TERM)
    currency = models.CharField(max_length=3, blank=True, default="")
    version = models.CharField(max_length=50, default="1.0")

    class Meta(OLRatingTableBaseModel.Meta):
        ordering = ["table_code", "-effective_from", "version"]
        constraints = [
            models.CheckConstraint(check=models.Q(effective_to__isnull=True) | models.Q(effective_from__isnull=True) | models.Q(effective_to__gte=models.F("effective_from")), name="ol_prem_table_dates_valid"),
            models.UniqueConstraint(fields=["table_code", "version"], name="ol_prem_table_code_ver_uq"),
        ]
        indexes = [
            models.Index(fields=["product", "plan", "is_active", "effective_from"], name="ol_prem_table_scope_idx"),
            models.Index(fields=["table_code", "version"], name="ol_prem_table_ver_idx"),
        ]

    def clean(self):
        super().clean()
        errors = {}
        self.rating_basis = (self.rating_basis or "").strip().upper()
        self.currency = (self.currency or "").strip().upper()
        self.version = (self.version or "").strip()
        if self.rating_basis not in {choice for choice, _ in OLPremiumRatingBasis.choices}:
            errors["rating_basis"] = "Unsupported premium rating basis."
        if not self.version:
            errors["version"] = "Premium rate table version is required."
        if self.currency and (len(self.currency) != 3 or not self.currency.isalpha()):
            errors["currency"] = "Currency must be a three-letter code when supplied."
        if self.product_id and not getattr(self.product, "is_active", True):
            errors["product"] = "Premium rate table product must be active."
        if self.plan_id and not getattr(self.plan, "is_active", True):
            errors["plan"] = "Premium rate table plan must be active."
        if errors:
            raise ValidationError(errors)


class OLPremiumRateRow(OLParameterBaseModel):
    """Multi-dimensional premium rate row belonging to one versioned rate table."""

    table = models.ForeignKey(
        OLPremiumRateTable,
        on_delete=models.CASCADE,
        related_name="rows",
    )
    gender = models.CharField(max_length=30, db_index=True)
    smoker_status = models.CharField(max_length=30, db_index=True)
    age_from = models.PositiveSmallIntegerField()
    age_to = models.PositiveSmallIntegerField()
    term_from = models.PositiveSmallIntegerField()
    term_to = models.PositiveSmallIntegerField()
    frequency = models.CharField(max_length=30, db_index=True)
    sum_assured_band_from = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    sum_assured_band_to = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    rate = models.DecimalField(max_digits=18, decimal_places=8)
    rate_unit = models.CharField(max_length=30, choices=OLPremiumRateUnit.choices, default=OLPremiumRateUnit.PER_THOUSAND_SUM_ASSURED)

    class Meta:
        ordering = ["table", "gender", "smoker_status", "frequency", "age_from", "term_from", "code"]
        constraints = [
            models.CheckConstraint(check=models.Q(effective_to__isnull=True) | models.Q(effective_from__isnull=True) | models.Q(effective_to__gte=models.F("effective_from")), name="ol_prem_row_dates_valid"),
            models.UniqueConstraint(fields=["code"], name="ol_prem_rate_row_code_uq"),
            models.CheckConstraint(check=models.Q(age_to__gte=models.F("age_from")), name="ol_prem_row_age_valid"),
            models.CheckConstraint(check=models.Q(term_to__gte=models.F("term_from")), name="ol_prem_row_term_valid"),
            models.CheckConstraint(check=models.Q(sum_assured_band_from__isnull=True) | models.Q(sum_assured_band_from__gte=0), name="ol_prem_row_sa_from_nonneg"),
            models.CheckConstraint(check=models.Q(sum_assured_band_to__isnull=True) | models.Q(sum_assured_band_to__gte=0), name="ol_prem_row_sa_to_nonneg"),
            models.CheckConstraint(check=models.Q(sum_assured_band_to__isnull=True) | models.Q(sum_assured_band_from__isnull=True) | models.Q(sum_assured_band_to__gte=models.F("sum_assured_band_from")), name="ol_prem_row_sa_valid"),
            models.CheckConstraint(check=models.Q(rate__gte=0), name="ol_prem_row_rate_nonneg"),
        ]
        indexes = [
            models.Index(fields=["table", "gender", "smoker_status", "frequency"], name="ol_prem_row_scope_idx"),
            models.Index(fields=["age_from", "age_to", "term_from", "term_to"], name="ol_prem_row_band_idx"),
            models.Index(fields=["is_active", "effective_from"], name="ol_prem_row_dates_idx"),
        ]

    def clean(self):
        super().clean()
        errors = {}
        _rating_row_dates_within_table(self, errors)
        self.gender = (self.gender or "").strip().upper()
        self.smoker_status = (self.smoker_status or "").strip().upper()
        self.frequency = (self.frequency or "").strip().upper()
        self.rate_unit = (self.rate_unit or "").strip().upper()
        if not self.gender:
            errors["gender"] = "Gender is required."
        if not self.smoker_status:
            errors["smoker_status"] = "Smoker status is required."
        if not self.frequency:
            errors["frequency"] = "Premium frequency is required."
        if self.age_from < 0 or self.age_to > 150 or self.age_to < self.age_from:
            errors["age_to"] = "Age band must be ordered and remain between 0 and 150 years."
        if self.term_from < 1 or self.term_to < self.term_from:
            errors["term_to"] = "Term band must be ordered and start at one year or later."
        if self.sum_assured_band_from is not None and self.sum_assured_band_from < 0:
            errors["sum_assured_band_from"] = "Sum-assured band cannot be negative."
        if self.sum_assured_band_to is not None and self.sum_assured_band_to < 0:
            errors["sum_assured_band_to"] = "Sum-assured band cannot be negative."
        if self.sum_assured_band_from is not None and self.sum_assured_band_to is not None and self.sum_assured_band_to < self.sum_assured_band_from:
            errors["sum_assured_band_to"] = "Sum-assured band-to cannot be less than band-from."
        if self.rate is None or self.rate < 0:
            errors["rate"] = "Premium rate must be a non-negative decimal."
        if self.rate_unit not in {choice for choice, _ in OLPremiumRateUnit.choices}:
            errors["rate_unit"] = "Unsupported premium rate unit."
        elif self.rate_unit == OLPremiumRateUnit.PERCENTAGE and self.rate > 100:
            errors["rate"] = "Percentage premium rate cannot exceed 100."
        if errors:
            raise ValidationError(errors)
        candidates = self.__class__.objects.filter(
            table=self.table,
            gender=self.gender,
            smoker_status=self.smoker_status,
            frequency=self.frequency,
            rate_unit=self.rate_unit,
            is_active=True,
        ).exclude(pk=self.pk)
        for candidate in candidates:
            if _product_setup_intervals_overlap(self.effective_from, self.effective_to, candidate.effective_from, candidate.effective_to) and _rating_intervals_overlap(self, candidate, ("age", "term", "sum_assured_band")):
                raise ValidationError({"code": "An active premium-rate row overlaps an existing row in the same table and dimensions."})


class OLMortalityRateTable(OLRatingTableBaseModel):
    """Versioned mortality basis table independent of product-specific premium tables."""

    version = models.CharField(max_length=50, default="1.0")

    class Meta(OLRatingTableBaseModel.Meta):
        ordering = ["table_code", "-effective_from", "version"]
        constraints = [
            models.CheckConstraint(check=models.Q(effective_to__isnull=True) | models.Q(effective_from__isnull=True) | models.Q(effective_to__gte=models.F("effective_from")), name="ol_mort_table_dates_valid"),
            models.UniqueConstraint(fields=["table_code", "version"], name="ol_mort_table_code_ver_uq"),
        ]
        indexes = [
            models.Index(fields=["table_code", "version"], name="ol_mort_table_ver_idx"),
            models.Index(fields=["is_active", "effective_from"], name="ol_mort_table_dates_idx"),
        ]

    def clean(self):
        super().clean()
        self.version = (self.version or "").strip()
        if not self.version:
            raise ValidationError({"version": "Mortality table version is required."})


class OLMortalityRateRow(OLParameterBaseModel):
    """Age, gender, smoking, and policy-year mortality assumption row."""

    table = models.ForeignKey(
        OLMortalityRateTable,
        on_delete=models.CASCADE,
        related_name="rows",
    )
    age = models.PositiveSmallIntegerField()
    gender = models.CharField(max_length=30, db_index=True)
    smoker_status = models.CharField(max_length=30, blank=True, default="", db_index=True)
    policy_year = models.PositiveSmallIntegerField(null=True, blank=True, db_index=True)
    mortality_rate = models.DecimalField(max_digits=18, decimal_places=12)

    class Meta:
        ordering = ["table", "age", "gender", "smoker_status", "policy_year", "code"]
        constraints = [
            models.CheckConstraint(check=models.Q(effective_to__isnull=True) | models.Q(effective_from__isnull=True) | models.Q(effective_to__gte=models.F("effective_from")), name="ol_mort_row_dates_valid"),
            models.UniqueConstraint(fields=["code"], name="ol_mort_rate_row_code_uq"),
            models.CheckConstraint(check=models.Q(age__lte=150), name="ol_mort_row_age_max_ck"),
            models.CheckConstraint(check=models.Q(policy_year__isnull=True) | models.Q(policy_year__gt=0), name="ol_mort_row_year_pos_ck"),
            models.CheckConstraint(check=models.Q(mortality_rate__gte=0), name="ol_mort_row_rate_nonneg"),
        ]
        indexes = [
            models.Index(fields=["table", "age", "gender", "smoker_status", "policy_year"], name="ol_mort_row_scope_idx"),
            models.Index(fields=["age", "gender", "smoker_status"], name="ol_mort_row_dim_idx"),
        ]

    def clean(self):
        super().clean()
        errors = {}
        _rating_row_dates_within_table(self, errors)
        self.gender = (self.gender or "").strip().upper()
        self.smoker_status = (self.smoker_status or "").strip().upper()
        if not self.gender:
            errors["gender"] = "Gender is required."
        if self.age < 0 or self.age > 150:
            errors["age"] = "Mortality age must be between 0 and 150 years."
        if self.policy_year is not None and self.policy_year < 1:
            errors["policy_year"] = "Policy year must be positive when supplied."
        if self.mortality_rate is None or self.mortality_rate < 0:
            errors["mortality_rate"] = "Mortality rate must be a non-negative decimal."
        if errors:
            raise ValidationError(errors)
        candidates = self.__class__.objects.filter(
            table=self.table,
            age=self.age,
            gender=self.gender,
            smoker_status=self.smoker_status,
            policy_year=self.policy_year,
            is_active=True,
        ).exclude(pk=self.pk)
        for candidate in candidates:
            if _product_setup_intervals_overlap(self.effective_from, self.effective_to, candidate.effective_from, candidate.effective_to):
                raise ValidationError({"code": "An active mortality-rate row duplicates an existing row in the same table and dimensions."})


class OLJointLifeType(models.TextChoices):
    FIRST_DEATH = "FIRST_DEATH", "First death"
    LAST_SURVIVOR = "LAST_SURVIVOR", "Last survivor"
    JOINT_AND_SURVIVOR = "JOINT_AND_SURVIVOR", "Joint and survivor"


class OLJointLifeAgeBasis(models.TextChoices):
    YOUNGER_LIFE = "YOUNGER_LIFE", "Younger life"
    OLDER_LIFE = "OLDER_LIFE", "Older life"
    AVERAGE_AGE = "AVERAGE_AGE", "Average age"
    JOINT_AGE = "JOINT_AGE", "Joint age"


class OLJointLifeSetup(OLEffectiveDateModel):
    """Effective-dated joint-life product or plan configuration."""

    product = models.ForeignKey(
        OLProduct,
        on_delete=models.PROTECT,
        related_name="joint_life_setups",
        null=True,
        blank=True,
    )
    plan = models.ForeignKey(
        "ordinary_life.OLPlan",
        on_delete=models.PROTECT,
        related_name="ol_parameter_joint_life_setups",
        null=True,
        blank=True,
    )
    joint_life_type = models.CharField(max_length=30, choices=OLJointLifeType.choices)
    age_basis = models.CharField(max_length=30, choices=OLJointLifeAgeBasis.choices)
    survivor_benefit_rule = models.CharField(max_length=120)
    premium_adjustment_factor = models.DecimalField(max_digits=12, decimal_places=6, default=1)
    underwriting_rule = models.CharField(max_length=120)

    class Meta:
        ordering = ["product", "plan", "joint_life_type", "-effective_from", "code"]
        constraints = [
            models.CheckConstraint(check=models.Q(effective_to__isnull=True) | models.Q(effective_from__isnull=True) | models.Q(effective_to__gte=models.F("effective_from")), name="ol_joint_life_dates_valid"),
            models.UniqueConstraint(fields=["code"], name="ol_joint_life_code_uq"),
            models.CheckConstraint(check=models.Q(premium_adjustment_factor__gt=0), name="ol_joint_life_factor_pos"),
        ]
        indexes = [
            models.Index(fields=["product", "plan", "is_active", "effective_from"], name="ol_joint_life_scope_idx"),
            models.Index(fields=["joint_life_type", "age_basis", "is_active"], name="ol_joint_life_type_idx"),
        ]

    def clean(self):
        super().clean()
        errors = {}
        self.joint_life_type = (self.joint_life_type or "").strip().upper()
        self.age_basis = (self.age_basis or "").strip().upper()
        self.survivor_benefit_rule = (self.survivor_benefit_rule or "").strip().upper()
        self.underwriting_rule = (self.underwriting_rule or "").strip().upper()
        if not self.product_id and not self.plan_id:
            errors["product"] = "Joint-life setup must be scoped to a product or plan."
        if self.product_id and not getattr(self.product, "is_active", True):
            errors["product"] = "Joint-life product must be active."
        if self.plan_id and not getattr(self.plan, "is_active", True):
            errors["plan"] = "Joint-life plan must be active."
        if self.joint_life_type not in {choice for choice, _ in OLJointLifeType.choices}:
            errors["joint_life_type"] = "Unsupported joint-life type."
        if self.age_basis not in {choice for choice, _ in OLJointLifeAgeBasis.choices}:
            errors["age_basis"] = "Unsupported joint-life age basis."
        if not self.survivor_benefit_rule:
            errors["survivor_benefit_rule"] = "Survivor benefit rule is required."
        if not self.underwriting_rule:
            errors["underwriting_rule"] = "Underwriting rule is required."
        if self.premium_adjustment_factor is None or self.premium_adjustment_factor <= 0:
            errors["premium_adjustment_factor"] = "Premium adjustment factor must be greater than zero."
        if errors:
            raise ValidationError(errors)
        candidates = self.__class__.objects.filter(
            product=self.product,
            plan=self.plan,
            joint_life_type=self.joint_life_type,
            is_active=True,
        ).exclude(pk=self.pk)
        if any(_product_setup_intervals_overlap(self.effective_from, self.effective_to, candidate.effective_from, candidate.effective_to) for candidate in candidates):
            raise ValidationError({"code": "An active joint-life setup overlaps an existing row in the same scope and type."})


# =============================================================================
# OL PRODUCT RATING PART 2
# =============================================================================


class OLRatingCalculationBasis(models.TextChoices):
    OUTSTANDING_PREMIUM = "OUTSTANDING_PREMIUM", "Outstanding premium"
    LOAN_BALANCE = "LOAN_BALANCE", "Loan balance"
    PREMIUM = "PREMIUM", "Premium"
    SUM_ASSURED = "SUM_ASSURED", "Sum assured"
    RESERVE = "RESERVE", "Reserve"
    POLICY_VALUE = "POLICY_VALUE", "Policy value"
    CUSTOM = "CUSTOM", "Custom"


class OLBonusType(models.TextChoices):
    REVERSIONARY = "REVERSIONARY", "Reversionary"
    TERMINAL = "TERMINAL", "Terminal"
    LOYALTY = "LOYALTY", "Loyalty"
    SPECIAL = "SPECIAL", "Special"
    GUARANTEED = "GUARANTEED", "Guaranteed"


class OLDeclarationFrequency(models.TextChoices):
    ANNUAL = "ANNUAL", "Annual"
    QUARTERLY = "QUARTERLY", "Quarterly"
    MONTHLY = "MONTHLY", "Monthly"
    ON_MATURITY = "ON_MATURITY", "On maturity"
    AD_HOC = "AD_HOC", "Ad hoc"


class OLInstallmentChargeType(models.TextChoices):
    FIXED = "FIXED", "Fixed amount"
    PERCENTAGE = "PERCENTAGE", "Percentage"
    FACTOR = "FACTOR", "Factor"


class OLInstallmentFrequency(models.TextChoices):
    SINGLE = "SINGLE", "Single"
    MONTHLY = "MONTHLY", "Monthly"
    QUARTERLY = "QUARTERLY", "Quarterly"
    HALF_YEARLY = "HALF_YEARLY", "Half yearly"
    ANNUAL = "ANNUAL", "Annual"


class OLInstallmentApplyOn(models.TextChoices):
    PREMIUM = "PREMIUM", "Premium"
    INSTALLMENT = "INSTALLMENT", "Installment"
    SUM_ASSURED = "SUM_ASSURED", "Sum assured"
    POLICY_VALUE = "POLICY_VALUE", "Policy value"
    DUE_AMOUNT = "DUE_AMOUNT", "Due amount"


class OLReserveLoadingType(models.TextChoices):
    EXPENSE = "EXPENSE", "Expense"
    RISK = "RISK", "Risk"
    CONTINGENCY = "CONTINGENCY", "Contingency"
    PROFIT = "PROFIT", "Profit"
    CAPITAL = "CAPITAL", "Capital"
    OTHER = "OTHER", "Other"


class OLReserveLoadingBasis(models.TextChoices):
    RESERVE = "RESERVE", "Reserve"
    PREMIUM = "PREMIUM", "Premium"
    SUM_ASSURED = "SUM_ASSURED", "Sum assured"
    POLICY_VALUE = "POLICY_VALUE", "Policy value"
    CUSTOM = "CUSTOM", "Custom"


def _rating_part2_validate_scope(instance, errors, *, require_scope=False):
    if require_scope and not instance.product_id and not instance.plan_id:
        errors["product"] = "This configuration must be scoped to a product or plan."
    if instance.product_id and not getattr(instance.product, "is_active", True):
        errors["product"] = "Selected product must be active."
    if instance.plan_id and not getattr(instance.plan, "is_active", True):
        errors["plan"] = "Selected plan must be active."
    _policy_setup_validate_product_plan(instance, errors)


def _rating_part2_dates_overlap(instance, candidates):
    return any(
        _product_setup_intervals_overlap(
            instance.effective_from,
            instance.effective_to,
            candidate.effective_from,
            candidate.effective_to,
        )
        for candidate in candidates
    )


class OLReinstatementInterestRate(OLEffectiveDateModel):
    """Interest rate applied when reinstatement financial obligations are calculated."""

    product = models.ForeignKey(
        "ol_parameters.OLProduct",
        on_delete=models.PROTECT,
        related_name="reinstatement_interest_rates",
        null=True,
        blank=True,
    )
    plan = models.ForeignKey(
        "ordinary_life.OLPlan",
        on_delete=models.PROTECT,
        related_name="ol_parameter_reinstatement_interest_rates",
        null=True,
        blank=True,
    )
    rate = models.DecimalField(max_digits=12, decimal_places=8)
    calculation_basis = models.CharField(max_length=40, choices=OLRatingCalculationBasis.choices, default=OLRatingCalculationBasis.OUTSTANDING_PREMIUM)

    class Meta:
        ordering = ["product", "plan", "calculation_basis", "-effective_from", "code"]
        constraints = [
            models.CheckConstraint(check=models.Q(effective_to__isnull=True) | models.Q(effective_from__isnull=True) | models.Q(effective_to__gte=models.F("effective_from")), name="ol_rein_interest_dates_ck"),
            models.UniqueConstraint(fields=["code"], name="ol_rein_interest_code_uq"),
            models.CheckConstraint(check=models.Q(rate__gte=0) & models.Q(rate__lte=100), name="ol_rein_interest_rate_rng_ck"),
        ]
        indexes = [
            models.Index(fields=["product", "plan", "calculation_basis", "is_active"], name="ol_rein_interest_scope_idx"),
            models.Index(fields=["effective_from", "effective_to", "is_active"], name="ol_rein_interest_dates_idx"),
        ]

    def clean(self):
        super().clean()
        errors = {}
        self.calculation_basis = (self.calculation_basis or "").strip().upper()
        _rating_part2_validate_scope(self, errors)
        if self.calculation_basis not in dict(OLRatingCalculationBasis.choices):
            errors["calculation_basis"] = "Unsupported reinstatement calculation basis."
        if self.rate is None or self.rate < 0 or self.rate > 100:
            errors["rate"] = "Reinstatement interest rate must be between 0 and 100."
        if errors:
            raise ValidationError(errors)
        candidates = self.__class__.objects.filter(
            product=self.product,
            plan=self.plan,
            calculation_basis=self.calculation_basis,
            is_active=True,
        ).exclude(pk=self.pk)
        if _rating_part2_dates_overlap(self, candidates):
            raise ValidationError({"code": "An active reinstatement interest rate overlaps an existing row in the same scope."})


class OLBonusRate(OLEffectiveDateModel):
    """Effective-dated bonus declaration assumption for an OL product or plan."""

    product = models.ForeignKey(
        "ol_parameters.OLProduct",
        on_delete=models.PROTECT,
        related_name="bonus_rates",
        null=True,
        blank=True,
    )
    plan = models.ForeignKey(
        "ordinary_life.OLPlan",
        on_delete=models.PROTECT,
        related_name="ol_parameter_bonus_rates",
        null=True,
        blank=True,
    )
    bonus_type = models.CharField(max_length=30, choices=OLBonusType.choices)
    rate = models.DecimalField(max_digits=12, decimal_places=8)
    valuation_year = models.PositiveSmallIntegerField(null=True, blank=True)
    declaration_frequency = models.CharField(max_length=20, choices=OLDeclarationFrequency.choices, blank=True, default="")

    class Meta:
        ordering = ["product", "plan", "bonus_type", "valuation_year", "-effective_from", "code"]
        constraints = [
            models.CheckConstraint(check=models.Q(effective_to__isnull=True) | models.Q(effective_from__isnull=True) | models.Q(effective_to__gte=models.F("effective_from")), name="ol_bonus_rate_dates_ck"),
            models.UniqueConstraint(fields=["code"], name="ol_bonus_rate_code_uq"),
            models.CheckConstraint(check=models.Q(rate__gte=0) & models.Q(rate__lte=100), name="ol_bonus_rate_rng_ck"),
            models.CheckConstraint(check=models.Q(valuation_year__isnull=True) | models.Q(valuation_year__gt=0), name="ol_bonus_year_pos_ck"),
        ]
        indexes = [
            models.Index(fields=["product", "plan", "bonus_type", "is_active"], name="ol_bonus_rate_scope_idx"),
            models.Index(fields=["valuation_year", "declaration_frequency", "is_active"], name="ol_bonus_rate_dim_idx"),
        ]

    def clean(self):
        super().clean()
        errors = {}
        self.bonus_type = (self.bonus_type or "").strip().upper()
        self.declaration_frequency = (self.declaration_frequency or "").strip().upper()
        _rating_part2_validate_scope(self, errors, require_scope=True)
        if self.bonus_type not in dict(OLBonusType.choices):
            errors["bonus_type"] = "Unsupported bonus type."
        if self.declaration_frequency and self.declaration_frequency not in dict(OLDeclarationFrequency.choices):
            errors["declaration_frequency"] = "Unsupported declaration frequency."
        if self.valuation_year is not None and self.valuation_year < 1:
            errors["valuation_year"] = "Valuation year must be positive."
        if self.rate is None or self.rate < 0 or self.rate > 100:
            errors["rate"] = "Bonus rate must be between 0 and 100."
        if errors:
            raise ValidationError(errors)
        candidates = self.__class__.objects.filter(
            product=self.product,
            plan=self.plan,
            bonus_type=self.bonus_type,
            valuation_year=self.valuation_year,
            declaration_frequency=self.declaration_frequency,
            is_active=True,
        ).exclude(pk=self.pk)
        if _rating_part2_dates_overlap(self, candidates):
            raise ValidationError({"code": "An active bonus rate overlaps an existing row in the same scope."})


class OLMortgageInterestFactor(OLEffectiveDateModel):
    """Interest factor for policy loans or mortgage-linked product calculations."""

    product = models.ForeignKey(
        "ol_parameters.OLProduct",
        on_delete=models.PROTECT,
        related_name="mortgage_interest_factors",
    )
    plan = models.ForeignKey(
        "ordinary_life.OLPlan",
        on_delete=models.PROTECT,
        related_name="ol_parameter_mortgage_interest_factors",
        null=True,
        blank=True,
    )
    factor = models.DecimalField(max_digits=12, decimal_places=8)
    calculation_basis = models.CharField(max_length=40, choices=OLRatingCalculationBasis.choices, default=OLRatingCalculationBasis.LOAN_BALANCE)

    class Meta:
        ordering = ["product", "plan", "calculation_basis", "-effective_from", "code"]
        constraints = [
            models.CheckConstraint(check=models.Q(effective_to__isnull=True) | models.Q(effective_from__isnull=True) | models.Q(effective_to__gte=models.F("effective_from")), name="ol_mortgage_factor_dates_ck"),
            models.UniqueConstraint(fields=["code"], name="ol_mortgage_factor_code_uq"),
            models.CheckConstraint(check=models.Q(factor__gt=0), name="ol_mortgage_factor_pos_ck"),
        ]
        indexes = [
            models.Index(fields=["product", "plan", "calculation_basis", "is_active"], name="ol_mortgage_factor_scope_idx"),
            models.Index(fields=["effective_from", "effective_to", "is_active"], name="ol_mortgage_factor_dates_idx"),
        ]

    def clean(self):
        super().clean()
        errors = {}
        self.calculation_basis = (self.calculation_basis or "").strip().upper()
        _rating_part2_validate_scope(self, errors, require_scope=True)
        if self.calculation_basis not in dict(OLRatingCalculationBasis.choices):
            errors["calculation_basis"] = "Unsupported mortgage calculation basis."
        if self.factor is None or self.factor <= 0:
            errors["factor"] = "Mortgage interest factor must be greater than zero."
        if errors:
            raise ValidationError(errors)
        candidates = self.__class__.objects.filter(
            product=self.product,
            plan=self.plan,
            calculation_basis=self.calculation_basis,
            is_active=True,
        ).exclude(pk=self.pk)
        if _rating_part2_dates_overlap(self, candidates):
            raise ValidationError({"code": "An active mortgage interest factor overlaps an existing row in the same scope."})


class OLInstallmentChargeRate(OLEffectiveDateModel):
    """Effective-dated charge applied to installment or premium transactions."""

    product = models.ForeignKey(
        "ol_parameters.OLProduct",
        on_delete=models.PROTECT,
        related_name="installment_charge_rates",
        null=True,
        blank=True,
    )
    plan = models.ForeignKey(
        "ordinary_life.OLPlan",
        on_delete=models.PROTECT,
        related_name="ol_parameter_installment_charge_rates",
        null=True,
        blank=True,
    )
    frequency = models.CharField(max_length=20, choices=OLInstallmentFrequency.choices)
    charge_type = models.CharField(max_length=20, choices=OLInstallmentChargeType.choices)
    rate_value = models.DecimalField(max_digits=12, decimal_places=8)
    apply_on = models.CharField(max_length=20, choices=OLInstallmentApplyOn.choices)

    class Meta:
        ordering = ["product", "plan", "frequency", "charge_type", "apply_on", "-effective_from", "code"]
        constraints = [
            models.CheckConstraint(check=models.Q(effective_to__isnull=True) | models.Q(effective_from__isnull=True) | models.Q(effective_to__gte=models.F("effective_from")), name="ol_install_charge_dates_ck"),
            models.UniqueConstraint(fields=["code"], name="ol_install_charge_code_uq"),
            models.CheckConstraint(check=models.Q(rate_value__gte=0), name="ol_install_charge_nonneg_ck"),
        ]
        indexes = [
            models.Index(fields=["product", "plan", "frequency", "is_active"], name="ol_install_charge_scope_idx"),
            models.Index(fields=["charge_type", "apply_on", "is_active"], name="ol_install_charge_dim_idx"),
        ]

    def clean(self):
        super().clean()
        errors = {}
        self.frequency = (self.frequency or "").strip().upper()
        self.charge_type = (self.charge_type or "").strip().upper()
        self.apply_on = (self.apply_on or "").strip().upper()
        _rating_part2_validate_scope(self, errors)
        if self.frequency not in dict(OLInstallmentFrequency.choices):
            errors["frequency"] = "Unsupported installment frequency."
        if self.charge_type not in dict(OLInstallmentChargeType.choices):
            errors["charge_type"] = "Unsupported installment charge type."
        if self.apply_on not in dict(OLInstallmentApplyOn.choices):
            errors["apply_on"] = "Unsupported installment charge apply-on dimension."
        if self.rate_value is None or self.rate_value < 0:
            errors["rate_value"] = "Installment charge value cannot be negative."
        elif self.charge_type == OLInstallmentChargeType.PERCENTAGE and self.rate_value > 100:
            errors["rate_value"] = "Percentage installment charge cannot exceed 100."
        if errors:
            raise ValidationError(errors)
        candidates = self.__class__.objects.filter(
            product=self.product,
            plan=self.plan,
            frequency=self.frequency,
            charge_type=self.charge_type,
            apply_on=self.apply_on,
            is_active=True,
        ).exclude(pk=self.pk)
        if _rating_part2_dates_overlap(self, candidates):
            raise ValidationError({"code": "An active installment charge overlaps an existing row in the same scope."})


class OLCashSurrenderValue(OLEffectiveDateModel):
    """Age, term, policy-year, and demographic surrender-value factor or rate row."""

    product = models.ForeignKey(
        "ol_parameters.OLProduct",
        on_delete=models.PROTECT,
        related_name="cash_surrender_values",
    )
    plan = models.ForeignKey(
        "ordinary_life.OLPlan",
        on_delete=models.PROTECT,
        related_name="ol_parameter_cash_surrender_values",
        null=True,
        blank=True,
    )
    policy_year_from = models.PositiveSmallIntegerField()
    policy_year_to = models.PositiveSmallIntegerField()
    age_from = models.PositiveSmallIntegerField(null=True, blank=True)
    age_to = models.PositiveSmallIntegerField(null=True, blank=True)
    term_from = models.PositiveSmallIntegerField(null=True, blank=True)
    term_to = models.PositiveSmallIntegerField(null=True, blank=True)
    gender = models.CharField(max_length=30, blank=True, default="", db_index=True)
    smoker_status = models.CharField(max_length=30, blank=True, default="", db_index=True)
    surrender_value_factor = models.DecimalField(max_digits=12, decimal_places=8, null=True, blank=True)
    rate = models.DecimalField(max_digits=12, decimal_places=8, null=True, blank=True)

    class Meta:
        ordering = ["product", "plan", "policy_year_from", "age_from", "term_from", "code"]
        constraints = [
            models.CheckConstraint(check=models.Q(effective_to__isnull=True) | models.Q(effective_from__isnull=True) | models.Q(effective_to__gte=models.F("effective_from")), name="ol_cash_surrender_dates_ck"),
            models.UniqueConstraint(fields=["code"], name="ol_cash_surrender_code_uq"),
            models.CheckConstraint(check=models.Q(policy_year_to__gte=models.F("policy_year_from")), name="ol_cash_surrender_year_ck"),
            models.CheckConstraint(check=models.Q(age_to__isnull=True) | models.Q(age_from__isnull=True) | models.Q(age_to__gte=models.F("age_from")), name="ol_cash_surrender_age_ck"),
            models.CheckConstraint(check=models.Q(term_to__isnull=True) | models.Q(term_from__isnull=True) | models.Q(term_to__gte=models.F("term_from")), name="ol_cash_surrender_term_ck"),
            models.CheckConstraint(check=(models.Q(surrender_value_factor__isnull=False) & models.Q(rate__isnull=True)) | (models.Q(surrender_value_factor__isnull=True) & models.Q(rate__isnull=False)), name="ol_cash_surrender_one_value_ck"),
            models.CheckConstraint(check=models.Q(surrender_value_factor__isnull=True) | (models.Q(surrender_value_factor__gte=0) & models.Q(surrender_value_factor__lte=1)), name="ol_cash_surrender_factor_rng_ck"),
            models.CheckConstraint(check=models.Q(rate__isnull=True) | (models.Q(rate__gte=0) & models.Q(rate__lte=100)), name="ol_cash_surrender_rate_rng_ck"),
        ]
        indexes = [
            models.Index(fields=["product", "plan", "is_active", "effective_from"], name="ol_cash_surrender_scope_idx"),
            models.Index(fields=["policy_year_from", "policy_year_to", "age_from", "age_to"], name="ol_cash_surrender_band_idx"),
            models.Index(fields=["gender", "smoker_status", "is_active"], name="ol_cash_surrender_demo_idx"),
        ]

    def clean(self):
        super().clean()
        errors = {}
        _rating_part2_validate_scope(self, errors, require_scope=True)
        self.gender = (self.gender or "").strip().upper()
        self.smoker_status = (self.smoker_status or "").strip().upper()
        if self.policy_year_from < 1 or self.policy_year_to < self.policy_year_from:
            errors["policy_year_to"] = "Policy-year band must be ordered and start at one."
        if self.age_from is not None and (self.age_from < 0 or self.age_from > 150):
            errors["age_from"] = "Age-from must be between 0 and 150."
        if self.age_to is not None and (self.age_to < 0 or self.age_to > 150 or (self.age_from is not None and self.age_to < self.age_from)):
            errors["age_to"] = "Age-to must be ordered and remain between 0 and 150."
        if self.term_from is not None and self.term_from < 1:
            errors["term_from"] = "Term-from must be at least one year."
        if self.term_to is not None and (self.term_to < 1 or (self.term_from is not None and self.term_to < self.term_from)):
            errors["term_to"] = "Term-to must be ordered and positive."
        if (self.surrender_value_factor is None) == (self.rate is None):
            errors["surrender_value_factor"] = "Provide exactly one surrender value factor or rate."
        if self.surrender_value_factor is not None and not 0 <= self.surrender_value_factor <= 1:
            errors["surrender_value_factor"] = "Surrender value factor must be between 0 and 1."
        if self.rate is not None and not 0 <= self.rate <= 100:
            errors["rate"] = "Surrender value rate must be between 0 and 100."
        if errors:
            raise ValidationError(errors)
        candidates = self.__class__.objects.filter(
            product=self.product,
            plan=self.plan,
            gender=self.gender,
            smoker_status=self.smoker_status,
            is_active=True,
        ).exclude(pk=self.pk)
        for candidate in candidates:
            if (
                _rating_part2_dates_overlap(self, [candidate])
                and _product_setup_intervals_overlap(self.policy_year_from, self.policy_year_to, candidate.policy_year_from, candidate.policy_year_to)
                and _product_setup_intervals_overlap(self.age_from, self.age_to, candidate.age_from, candidate.age_to)
                and _product_setup_intervals_overlap(self.term_from, self.term_to, candidate.term_from, candidate.term_to)
            ):
                raise ValidationError({"code": "An active cash surrender value overlaps an existing row in the same scope and dimensions."})


class OLReserveLoading(OLEffectiveDateModel):
    """Effective-dated reserve expense, risk, contingency, or capital loading."""

    product = models.ForeignKey(
        "ol_parameters.OLProduct",
        on_delete=models.PROTECT,
        related_name="reserve_loadings",
        null=True,
        blank=True,
    )
    plan = models.ForeignKey(
        "ordinary_life.OLPlan",
        on_delete=models.PROTECT,
        related_name="ol_parameter_reserve_loadings",
        null=True,
        blank=True,
    )
    loading_type = models.CharField(max_length=30, choices=OLReserveLoadingType.choices)
    loading_basis = models.CharField(max_length=30, choices=OLReserveLoadingBasis.choices)
    rate_value = models.DecimalField(max_digits=12, decimal_places=8)

    class Meta:
        ordering = ["product", "plan", "loading_type", "loading_basis", "-effective_from", "code"]
        constraints = [
            models.CheckConstraint(check=models.Q(effective_to__isnull=True) | models.Q(effective_from__isnull=True) | models.Q(effective_to__gte=models.F("effective_from")), name="ol_reserve_load_dates_ck"),
            models.UniqueConstraint(fields=["code"], name="ol_reserve_load_code_uq"),
            models.CheckConstraint(check=models.Q(rate_value__gte=0) & models.Q(rate_value__lte=100), name="ol_reserve_load_rate_rng_ck"),
        ]
        indexes = [
            models.Index(fields=["product", "plan", "loading_type", "is_active"], name="ol_reserve_load_scope_idx"),
            models.Index(fields=["loading_basis", "is_active", "effective_from"], name="ol_reserve_load_basis_idx"),
        ]

    def clean(self):
        super().clean()
        errors = {}
        self.loading_type = (self.loading_type or "").strip().upper()
        self.loading_basis = (self.loading_basis or "").strip().upper()
        _rating_part2_validate_scope(self, errors, require_scope=True)
        if self.loading_type not in dict(OLReserveLoadingType.choices):
            errors["loading_type"] = "Unsupported reserve loading type."
        if self.loading_basis not in dict(OLReserveLoadingBasis.choices):
            errors["loading_basis"] = "Unsupported reserve loading basis."
        if self.rate_value is None or self.rate_value < 0 or self.rate_value > 100:
            errors["rate_value"] = "Reserve loading value must be between 0 and 100."
        if errors:
            raise ValidationError(errors)
        candidates = self.__class__.objects.filter(
            product=self.product,
            plan=self.plan,
            loading_type=self.loading_type,
            loading_basis=self.loading_basis,
            is_active=True,
        ).exclude(pk=self.pk)
        if _rating_part2_dates_overlap(self, candidates):
            raise ValidationError({"code": "An active reserve loading overlaps an existing row in the same scope."})


# End of OL Product Rating Part 2


# =============================================================================
# OL RIDER SETUP
# =============================================================================


class OLRiderCategory(models.TextChoices):
    ACCIDENT = "ACCIDENT", "Accident"
    CRITICAL_ILLNESS = "CRITICAL_ILLNESS", "Critical illness"
    DISABILITY = "DISABILITY", "Disability"
    HEALTH = "HEALTH", "Health"
    SAVINGS = "SAVINGS", "Savings"
    WAIVER = "WAIVER", "Waiver"
    OTHER = "OTHER", "Other"


class OLRiderBenefitType(models.TextChoices):
    ACCIDENTAL_DEATH = "ACCIDENTAL_DEATH", "Accidental death"
    CRITICAL_ILLNESS = "CRITICAL_ILLNESS", "Critical illness"
    DEATH = "DEATH", "Death"
    DISABILITY = "DISABILITY", "Disability"
    HOSPITAL_CASH = "HOSPITAL_CASH", "Hospital cash"
    INCOME_REPLACEMENT = "INCOME_REPLACEMENT", "Income replacement"
    WAIVER_PREMIUM = "WAIVER_PREMIUM", "Waiver of premium"
    OTHER = "OTHER", "Other"


class OLRiderCalculationBasis(models.TextChoices):
    SUM_ASSURED = "SUM_ASSURED", "Sum assured"
    PREMIUM = "PREMIUM", "Premium"
    AGE_TERM = "AGE_TERM", "Age and term"
    FLAT = "FLAT", "Flat"
    CUSTOM = "CUSTOM", "Custom"


class OLRiderSetup(OLParameterBaseModel):
    """Parameterized rider catalog consumed by quotation, proposal, and policy flows."""

    rider_category = models.CharField(max_length=40, choices=OLRiderCategory.choices)
    benefit_type = models.CharField(max_length=50, choices=OLRiderBenefitType.choices)
    calculation_basis = models.CharField(max_length=30, choices=OLRiderCalculationBasis.choices, default=OLRiderCalculationBasis.SUM_ASSURED)
    min_age = models.PositiveSmallIntegerField(default=0)
    max_age = models.PositiveSmallIntegerField(default=150)
    min_term = models.PositiveSmallIntegerField(default=1)
    max_term = models.PositiveSmallIntegerField(default=100)
    min_sum_assured = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    max_sum_assured = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    waiting_period_days = models.PositiveIntegerField(default=0)
    allows_standalone = models.BooleanField(default=False)
    requires_underwriting = models.BooleanField(default=True)
    exclusion_rules = models.JSONField(default=dict, blank=True)
    product = models.ForeignKey(
        OLProduct,
        on_delete=models.PROTECT,
        related_name="rider_setups",
        null=True,
        blank=True,
    )
    plan = models.ForeignKey(
        "ordinary_life.OLPlan",
        on_delete=models.PROTECT,
        related_name="ol_parameter_rider_setups",
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["rider_category", "benefit_type", "name", "code"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(effective_to__isnull=True) | models.Q(effective_from__isnull=True) | models.Q(effective_to__gte=models.F("effective_from")),
                name="ol_rider_dates_valid",
            ),
            models.UniqueConstraint(fields=["code"], name="ol_rider_setup_code_uq"),
            models.CheckConstraint(check=models.Q(max_age__gte=models.F("min_age")), name="ol_rider_age_order_ck"),
            models.CheckConstraint(check=models.Q(min_age__lte=150) & models.Q(max_age__lte=150), name="ol_rider_age_range_ck"),
            models.CheckConstraint(check=models.Q(min_term__gte=1) & models.Q(max_term__gte=models.F("min_term")), name="ol_rider_term_range_ck"),
            models.CheckConstraint(check=models.Q(min_sum_assured__isnull=True) | models.Q(min_sum_assured__gte=0), name="ol_rider_min_sa_nonneg"),
            models.CheckConstraint(check=models.Q(max_sum_assured__isnull=True) | models.Q(max_sum_assured__gte=0), name="ol_rider_max_sa_nonneg"),
            models.CheckConstraint(check=models.Q(max_sum_assured__isnull=True) | models.Q(min_sum_assured__isnull=True) | models.Q(max_sum_assured__gte=models.F("min_sum_assured")), name="ol_rider_sa_order_ck"),
        ]
        indexes = [
            models.Index(fields=["rider_category", "benefit_type", "is_active"], name="ol_rider_setup_cat_idx"),
            models.Index(fields=["product", "plan", "is_active"], name="ol_rider_setup_scope_idx"),
            models.Index(fields=["requires_underwriting", "allows_standalone", "is_active"], name="ol_rider_setup_rule_idx"),
        ]

    def clean(self):
        super().clean()
        errors = {}
        self.rider_category = (self.rider_category or "").strip().upper()
        self.benefit_type = (self.benefit_type or "").strip().upper()
        self.calculation_basis = (self.calculation_basis or "").strip().upper()
        if self.rider_category not in dict(OLRiderCategory.choices):
            errors["rider_category"] = "Unsupported rider category."
        if self.benefit_type not in dict(OLRiderBenefitType.choices):
            errors["benefit_type"] = "Unsupported rider benefit type."
        if self.calculation_basis not in dict(OLRiderCalculationBasis.choices):
            errors["calculation_basis"] = "Unsupported rider calculation basis."
        if self.min_age < 0 or self.max_age > 150 or self.max_age < self.min_age:
            errors["max_age"] = "Rider age range must be ordered and remain between 0 and 150 years."
        if self.min_term < 1 or self.max_term < self.min_term:
            errors["max_term"] = "Rider term range must be ordered and start at one year or later."
        if self.min_sum_assured is not None and self.min_sum_assured < 0:
            errors["min_sum_assured"] = "Minimum sum assured cannot be negative."
        if self.max_sum_assured is not None and self.max_sum_assured < 0:
            errors["max_sum_assured"] = "Maximum sum assured cannot be negative."
        if self.min_sum_assured is not None and self.max_sum_assured is not None and self.max_sum_assured < self.min_sum_assured:
            errors["max_sum_assured"] = "Maximum sum assured cannot be less than minimum sum assured."
        if self.waiting_period_days < 0:
            errors["waiting_period_days"] = "Waiting period cannot be negative."
        if self.product_id and not getattr(self.product, "is_active", True):
            errors["product"] = "Rider product applicability must be active."
        if self.plan_id and not getattr(self.plan, "is_active", True):
            errors["plan"] = "Rider plan applicability must be active."
        _policy_setup_validate_product_plan(self, errors)
        if not isinstance(self.exclusion_rules, dict):
            errors["exclusion_rules"] = "Exclusion rules must be a JSON object."
        if errors:
            raise ValidationError(errors)


class OLRiderRateTable(OLRatingTableBaseModel):
    """Versioned rider rate table scoped to a rider and optional product or plan."""

    rider = models.ForeignKey(
        OLRiderSetup,
        on_delete=models.PROTECT,
        related_name="rate_tables",
    )
    product = models.ForeignKey(
        OLProduct,
        on_delete=models.PROTECT,
        related_name="rider_rate_tables",
        null=True,
        blank=True,
    )
    plan = models.ForeignKey(
        "ordinary_life.OLPlan",
        on_delete=models.PROTECT,
        related_name="ol_parameter_rider_rate_tables",
        null=True,
        blank=True,
    )
    rating_basis = models.CharField(max_length=40, choices=OLPremiumRatingBasis.choices, default=OLPremiumRatingBasis.AGE_TERM)
    version = models.CharField(max_length=50, default="1.0")

    class Meta:
        ordering = ["table_code", "rider", "-effective_from", "version"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(effective_to__isnull=True) | models.Q(effective_from__isnull=True) | models.Q(effective_to__gte=models.F("effective_from")),
                name="ol_rider_rt_dates_valid",
            ),
            models.UniqueConstraint(fields=["table_code", "version"], name="ol_rider_rt_code_ver_uq"),
        ]
        indexes = [
            models.Index(fields=["rider", "product", "plan", "is_active"], name="ol_rider_rt_scope_idx"),
            models.Index(fields=["table_code", "version"], name="ol_rider_rt_ver_idx"),
            models.Index(fields=["is_active", "effective_from"], name="ol_rider_rt_dates_idx"),
        ]

    def clean(self):
        super().clean()
        errors = {}
        self.rating_basis = (self.rating_basis or "").strip().upper()
        self.version = (self.version or "").strip()
        if self.rating_basis not in dict(OLPremiumRatingBasis.choices):
            errors["rating_basis"] = "Unsupported rider rating basis."
        if not self.version:
            errors["version"] = "Rider rate table version is required."
        if not self.rider_id:
            errors["rider"] = "A rider is required."
        elif not getattr(self.rider, "is_active", True):
            errors["rider"] = "Rider must be active."
        if self.product_id and not getattr(self.product, "is_active", True):
            errors["product"] = "Rider rate product must be active."
        if self.plan_id and not getattr(self.plan, "is_active", True):
            errors["plan"] = "Rider rate plan must be active."
        _policy_setup_validate_product_plan(self, errors)
        if self.rider_id:
            rider = self.rider
            if rider.product_id and rider.product_id != self.product_id:
                errors["product"] = "Rate table product must match the rider product applicability."
            if rider.plan_id and rider.plan_id != self.plan_id:
                errors["plan"] = "Rate table plan must match the rider plan applicability."
        if errors:
            raise ValidationError(errors)


class OLRiderRateRow(OLParameterBaseModel):
    """Multi-dimensional rider rate row belonging to one versioned rider rate table."""

    table = models.ForeignKey(
        OLRiderRateTable,
        on_delete=models.CASCADE,
        related_name="rows",
    )
    gender = models.CharField(max_length=30, db_index=True)
    smoker_status = models.CharField(max_length=30, db_index=True)
    age_from = models.PositiveSmallIntegerField()
    age_to = models.PositiveSmallIntegerField()
    term_from = models.PositiveSmallIntegerField()
    term_to = models.PositiveSmallIntegerField()
    frequency = models.CharField(max_length=30, blank=True, default="", db_index=True)
    sum_assured_band_from = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    sum_assured_band_to = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    rate = models.DecimalField(max_digits=18, decimal_places=8)
    rate_unit = models.CharField(max_length=30, choices=OLPremiumRateUnit.choices, default=OLPremiumRateUnit.PER_THOUSAND_SUM_ASSURED)

    class Meta:
        ordering = ["table", "gender", "smoker_status", "frequency", "age_from", "term_from", "code"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(effective_to__isnull=True) | models.Q(effective_from__isnull=True) | models.Q(effective_to__gte=models.F("effective_from")),
                name="ol_rider_row_dates_valid",
            ),
            models.UniqueConstraint(fields=["code"], name="ol_rider_rate_row_code_uq"),
            models.CheckConstraint(check=models.Q(age_to__gte=models.F("age_from")), name="ol_rider_row_age_order_ck"),
            models.CheckConstraint(check=models.Q(term_to__gte=models.F("term_from")), name="ol_rider_row_term_order_ck"),
            models.CheckConstraint(check=models.Q(sum_assured_band_from__isnull=True) | models.Q(sum_assured_band_from__gte=0), name="ol_rider_row_sa_from_ck"),
            models.CheckConstraint(check=models.Q(sum_assured_band_to__isnull=True) | models.Q(sum_assured_band_to__gte=0), name="ol_rider_row_sa_to_ck"),
            models.CheckConstraint(check=models.Q(sum_assured_band_to__isnull=True) | models.Q(sum_assured_band_from__isnull=True) | models.Q(sum_assured_band_to__gte=models.F("sum_assured_band_from")), name="ol_rider_row_sa_order_ck"),
            models.CheckConstraint(check=models.Q(rate__gte=0), name="ol_rider_row_rate_nonneg"),
        ]
        indexes = [
            models.Index(fields=["table", "gender", "smoker_status", "frequency"], name="ol_rider_row_scope_idx"),
            models.Index(fields=["age_from", "age_to", "term_from", "term_to"], name="ol_rider_row_band_idx"),
            models.Index(fields=["is_active", "effective_from"], name="ol_rider_row_dates_idx"),
        ]

    def clean(self):
        super().clean()
        errors = {}
        _rating_row_dates_within_table(self, errors)
        self.gender = (self.gender or "").strip().upper()
        self.smoker_status = (self.smoker_status or "").strip().upper()
        self.frequency = (self.frequency or "").strip().upper()
        self.rate_unit = (self.rate_unit or "").strip().upper()
        if not self.gender:
            errors["gender"] = "Gender is required."
        if not self.smoker_status:
            errors["smoker_status"] = "Smoker status is required."
        if self.age_from < 0 or self.age_to > 150 or self.age_to < self.age_from:
            errors["age_to"] = "Rider rate age band must be ordered and remain between 0 and 150 years."
        if self.term_from < 1 or self.term_to < self.term_from:
            errors["term_to"] = "Rider rate term band must be ordered and start at one year or later."
        if self.sum_assured_band_from is not None and self.sum_assured_band_from < 0:
            errors["sum_assured_band_from"] = "Sum-assured band cannot be negative."
        if self.sum_assured_band_to is not None and self.sum_assured_band_to < 0:
            errors["sum_assured_band_to"] = "Sum-assured band cannot be negative."
        if self.sum_assured_band_from is not None and self.sum_assured_band_to is not None and self.sum_assured_band_to < self.sum_assured_band_from:
            errors["sum_assured_band_to"] = "Sum-assured band-to cannot be less than band-from."
        if self.rate is None or self.rate < 0:
            errors["rate"] = "Rider rate must be a non-negative decimal."
        if self.rate_unit not in {choice for choice, _ in OLPremiumRateUnit.choices}:
            errors["rate_unit"] = "Unsupported rider rate unit."
        elif self.rate_unit == OLPremiumRateUnit.PERCENTAGE and self.rate > 100:
            errors["rate"] = "Percentage rider rate cannot exceed 100."
        if errors:
            raise ValidationError(errors)
        candidates = self.__class__.objects.filter(
            table=self.table,
            gender=self.gender,
            smoker_status=self.smoker_status,
            frequency=self.frequency,
            rate_unit=self.rate_unit,
            is_active=True,
        ).exclude(pk=self.pk)
        for candidate in candidates:
            if _product_setup_intervals_overlap(self.effective_from, self.effective_to, candidate.effective_from, candidate.effective_to) and _rating_intervals_overlap(self, candidate, ("age", "term", "sum_assured_band")):
                raise ValidationError({"code": "An active rider-rate row overlaps an existing row in the same table and dimensions."})


# End of OL Rider Setup


# =============================================================================
# OL LOAN SETUP
# =============================================================================
class OLLoanBasis(models.TextChoices):
    CASH_VALUE = "CASH_VALUE", "Cash value"
    PAID_UP_VALUE = "PAID_UP_VALUE", "Paid-up value"
    PREMIUM_BASED = "PREMIUM_BASED", "Premium based"
    OTHER = "OTHER", "Other"


class OLLoanEffectRule(models.TextChoices):
    DEDUCT_BALANCE = "DEDUCT_BALANCE", "Deduct loan balance"
    REDUCE_BENEFIT = "REDUCE_BENEFIT", "Reduce benefit"
    BLOCK_BENEFIT = "BLOCK_BENEFIT", "Block benefit"
    NET_BENEFIT = "NET_BENEFIT", "Pay benefit net of loan"
    NO_EFFECT = "NO_EFFECT", "No effect"
    OTHER = "OTHER", "Other"


class OLLoanCompoundingFrequency(models.TextChoices):
    DAILY = "DAILY", "Daily"
    MONTHLY = "MONTHLY", "Monthly"
    QUARTERLY = "QUARTERLY", "Quarterly"
    SEMI_ANNUAL = "SEMI_ANNUAL", "Semi-annual"
    ANNUAL = "ANNUAL", "Annual"
    OTHER = "OTHER", "Other"


class OLLoanInterestBasis(models.TextChoices):
    SIMPLE = "SIMPLE", "Simple interest"
    COMPOUND = "COMPOUND", "Compound interest"
    ACTUAL_365 = "ACTUAL_365", "Actual/365"
    ACTUAL_360 = "ACTUAL_360", "Actual/360"
    OTHER = "OTHER", "Other"


def _loan_setup_scope_overlaps(first, second):
    return (
        first.product_id == second.product_id
        and first.plan_id == second.plan_id
        and _product_setup_intervals_overlap(
            first.effective_from,
            first.effective_to,
            second.effective_from,
            second.effective_to,
        )
    )


class OLLoanSystemSetup(OLEffectiveDateModel):
    """Effective-dated configuration controlling Ordinary Life policy loans."""

    product = models.ForeignKey(
        "ol_parameters.OLProduct",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="loan_system_setups",
    )
    plan = models.ForeignKey(
        "ordinary_life.OLPlan",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="ol_parameter_loan_system_setups",
    )
    allow_policy_loans = models.BooleanField(default=True)
    loan_basis = models.CharField(max_length=30, choices=OLLoanBasis.choices, default=OLLoanBasis.CASH_VALUE)
    max_loan_percentage_of_cash_value = models.DecimalField(max_digits=18, decimal_places=8, default=Decimal("0"))
    min_loan_amount = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    max_loan_amount = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    loan_currency = models.CharField(max_length=3, blank=True, default="", db_index=True)
    repayment_options = models.JSONField(default=list, blank=True)
    auto_deduct_from_benefits = models.BooleanField(default=True)
    effect_on_claim = models.CharField(max_length=30, choices=OLLoanEffectRule.choices, default=OLLoanEffectRule.DEDUCT_BALANCE)
    effect_on_surrender = models.CharField(max_length=30, choices=OLLoanEffectRule.choices, default=OLLoanEffectRule.DEDUCT_BALANCE)
    effect_on_maturity = models.CharField(max_length=30, choices=OLLoanEffectRule.choices, default=OLLoanEffectRule.DEDUCT_BALANCE)
    require_approval = models.BooleanField(default=False)

    class Meta:
        ordering = ["product", "plan", "-effective_from", "code"]
        constraints = [
            models.UniqueConstraint(fields=["code"], name="ol_loan_system_code_uq"),
            models.CheckConstraint(
                check=models.Q(max_loan_percentage_of_cash_value__gte=0)
                & models.Q(max_loan_percentage_of_cash_value__lte=100),
                name="ol_loan_system_pct_rng",
            ),
            models.CheckConstraint(
                check=models.Q(min_loan_amount__isnull=True) | models.Q(min_loan_amount__gt=0),
                name="ol_loan_system_min_pos",
            ),
            models.CheckConstraint(
                check=models.Q(max_loan_amount__isnull=True) | models.Q(max_loan_amount__gt=0),
                name="ol_loan_system_max_pos",
            ),
            models.CheckConstraint(
                check=models.Q(max_loan_amount__isnull=True)
                | models.Q(min_loan_amount__isnull=True)
                | models.Q(max_loan_amount__gte=models.F("min_loan_amount")),
                name="ol_loan_system_min_max_ck",
            ),
        ]
        indexes = [
            models.Index(fields=["product", "plan", "is_active", "effective_from"], name="ol_loan_system_scope_idx"),
            models.Index(fields=["loan_basis", "is_active"], name="ol_loan_system_basis_idx"),
            models.Index(fields=["allow_policy_loans", "is_active"], name="ol_loan_system_allowed_idx"),
        ]

    def clean(self):
        super().clean()
        errors = {}
        self.loan_basis = (self.loan_basis or "").strip().upper()
        self.loan_currency = (self.loan_currency or "").strip().upper()
        for field_name in ("effect_on_claim", "effect_on_surrender", "effect_on_maturity"):
            setattr(self, field_name, (getattr(self, field_name) or "").strip().upper())
        if self.loan_basis not in dict(OLLoanBasis.choices):
            errors["loan_basis"] = "Unsupported loan basis."
        if self.loan_currency and len(self.loan_currency) != 3:
            errors["loan_currency"] = "Loan currency must be a three-letter code when supplied."
        if self.max_loan_percentage_of_cash_value is None or not 0 <= self.max_loan_percentage_of_cash_value <= 100:
            errors["max_loan_percentage_of_cash_value"] = "Loan percentage must be between 0 and 100."
        if self.min_loan_amount is not None and self.min_loan_amount <= 0:
            errors["min_loan_amount"] = "Minimum loan amount must be positive when supplied."
        if self.max_loan_amount is not None and self.max_loan_amount <= 0:
            errors["max_loan_amount"] = "Maximum loan amount must be positive when supplied."
        if self.min_loan_amount is not None and self.max_loan_amount is not None and self.max_loan_amount < self.min_loan_amount:
            errors["max_loan_amount"] = "Maximum loan amount cannot be less than minimum loan amount."
        if not isinstance(self.repayment_options, (dict, list)):
            errors["repayment_options"] = "Repayment options must be a JSON object or array."
        for field_name in ("effect_on_claim", "effect_on_surrender", "effect_on_maturity"):
            if getattr(self, field_name) not in dict(OLLoanEffectRule.choices):
                errors[field_name] = "Unsupported loan effect rule."
        if errors:
            raise ValidationError(errors)
        candidates = type(self).objects.filter(product=self.product, plan=self.plan, is_active=True).exclude(pk=self.pk)
        if any(_loan_setup_scope_overlaps(self, candidate) for candidate in candidates):
            raise ValidationError({"effective_from": "An active loan system setup overlaps an existing row in the same product/plan scope."})


class OLLoanInterestControl(OLEffectiveDateModel):
    """Effective-dated interest and capitalization configuration for Ordinary Life loans."""

    product = models.ForeignKey(
        "ol_parameters.OLProduct",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="loan_interest_controls",
    )
    plan = models.ForeignKey(
        "ordinary_life.OLPlan",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="ol_parameter_loan_interest_controls",
    )
    interest_rate = models.DecimalField(max_digits=18, decimal_places=8)
    compounding_frequency = models.CharField(max_length=20, choices=OLLoanCompoundingFrequency.choices, default=OLLoanCompoundingFrequency.ANNUAL)
    interest_calculation_basis = models.CharField(max_length=20, choices=OLLoanInterestBasis.choices, default=OLLoanInterestBasis.COMPOUND)
    grace_period_days = models.PositiveIntegerField(default=0)
    penalty_interest_rate = models.DecimalField(max_digits=18, decimal_places=8, null=True, blank=True)
    interest_suspension_rule = models.CharField(max_length=120, blank=True, default="")
    capitalize_interest = models.BooleanField(default=True)

    class Meta:
        ordering = ["product", "plan", "-effective_from", "code"]
        constraints = [
            models.UniqueConstraint(fields=["code"], name="ol_loan_interest_code_uq"),
            models.CheckConstraint(
                check=models.Q(interest_rate__gte=0) & models.Q(interest_rate__lte=100),
                name="ol_loan_interest_rate_rng",
            ),
            models.CheckConstraint(
                check=models.Q(penalty_interest_rate__isnull=True)
                | (models.Q(penalty_interest_rate__gte=0) & models.Q(penalty_interest_rate__lte=100)),
                name="ol_loan_interest_penalty_rng",
            ),
        ]
        indexes = [
            models.Index(fields=["product", "plan", "is_active", "effective_from"], name="ol_loan_interest_scope_idx"),
            models.Index(fields=["compounding_frequency", "interest_calculation_basis"], name="ol_loan_interest_basis_idx"),
            models.Index(fields=["capitalize_interest", "is_active"], name="ol_loan_interest_cap_idx"),
        ]

    def clean(self):
        super().clean()
        errors = {}
        self.compounding_frequency = (self.compounding_frequency or "").strip().upper()
        self.interest_calculation_basis = (self.interest_calculation_basis or "").strip().upper()
        self.interest_suspension_rule = (self.interest_suspension_rule or "").strip()
        if self.compounding_frequency not in dict(OLLoanCompoundingFrequency.choices):
            errors["compounding_frequency"] = "Unsupported compounding frequency."
        if self.interest_calculation_basis not in dict(OLLoanInterestBasis.choices):
            errors["interest_calculation_basis"] = "Unsupported interest calculation basis."
        if self.interest_rate is None or not 0 <= self.interest_rate <= 100:
            errors["interest_rate"] = "Interest rate must be between 0 and 100."
        if self.penalty_interest_rate is not None and not 0 <= self.penalty_interest_rate <= 100:
            errors["penalty_interest_rate"] = "Penalty interest rate must be between 0 and 100."
        if errors:
            raise ValidationError(errors)
        candidates = type(self).objects.filter(product=self.product, plan=self.plan, is_active=True).exclude(pk=self.pk)
        if any(_loan_setup_scope_overlaps(self, candidate) for candidate in candidates):
            raise ValidationError({"effective_from": "An active loan interest control overlaps an existing row in the same product/plan scope."})


# End of OL Loan Setup


# =============================================================================
# OL MEDICAL UNDERWRITING SETUP
# =============================================================================


class OLMedicalLimitType(models.TextChoices):
    AUTOMATIC = "AUTOMATIC", "Automatic"
    MEDICAL = "MEDICAL", "Medical"
    FINANCIAL = "FINANCIAL", "Financial"
    UNDERWRITING = "UNDERWRITING", "Underwriting"
    OTHER = "OTHER", "Other"


class OLMedicalRequiredFrequency(models.TextChoices):
    ONE_OFF = "ONE_OFF", "One-off"
    ANNUAL = "ANNUAL", "Annual"
    BIENNIAL = "BIENNIAL", "Biennial"
    EVERY_TWO_YEARS = "EVERY_TWO_YEARS", "Every two years"
    AS_REQUIRED = "AS_REQUIRED", "As required"
    OTHER = "OTHER", "Other"


class OLMedicalUnderwritingImpact(models.TextChoices):
    NONE = "NONE", "None"
    LOW = "LOW", "Low"
    MEDIUM = "MEDIUM", "Medium"
    HIGH = "HIGH", "High"
    CRITICAL = "CRITICAL", "Critical"


class OLPersonalHabitCategory(models.TextChoices):
    SMOKING = "SMOKING", "Smoking"
    ALCOHOL = "ALCOHOL", "Alcohol"
    DRUG = "DRUG", "Drug"
    OCCUPATION_HAZARD = "OCCUPATION_HAZARD", "Occupation hazard"
    LIFESTYLE = "LIFESTYLE", "Lifestyle"
    OTHER = "OTHER", "Other"


class OLMedicalApprovalStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    APPROVED = "APPROVED", "Approved"
    SUSPENDED = "SUSPENDED", "Suspended"
    REJECTED = "REJECTED", "Rejected"
    EXPIRED = "EXPIRED", "Expired"


def _medical_scope_overlaps(first, second):
    return (
        first.medical_code_id == second.medical_code_id
        and first.product_id == second.product_id
        and first.plan_id == second.plan_id
        and first.limit_type == second.limit_type
        and first.required_frequency == second.required_frequency
        and _product_setup_intervals_overlap(
            first.effective_from,
            first.effective_to,
            second.effective_from,
            second.effective_to,
        )
        and _product_setup_intervals_overlap(
            first.age_from,
            first.age_to,
            second.age_from,
            second.age_to,
        )
        and _product_setup_intervals_overlap(
            first.sum_assured_from,
            first.sum_assured_to,
            second.sum_assured_from,
            second.sum_assured_to,
        )
    )


class OLMedicalCode(OLParameterBaseModel):
    """Reusable medical examination, evidence, and underwriting code catalog."""

    medical_category = models.CharField(max_length=80, db_index=True)

    class Meta:
        ordering = ["medical_category", "name", "code"]
        constraints = [
            models.UniqueConstraint(fields=["code"], name="ol_medical_code_code_uq"),
        ]
        indexes = [
            models.Index(fields=["medical_category", "is_active"], name="ol_med_code_cat_idx"),
            models.Index(fields=["is_active", "effective_from"], name="ol_med_code_active_idx"),
        ]

    def clean(self):
        super().clean()
        self.medical_category = (self.medical_category or "").strip().upper()
        if not self.medical_category:
            raise ValidationError({"medical_category": "Medical category is required."})


class OLMedicalLimit(OLEffectiveDateModel):
    """Effective-dated medical evidence or examination limit by risk dimensions."""

    medical_code = models.ForeignKey(
        OLMedicalCode,
        on_delete=models.PROTECT,
        related_name="limits",
    )
    product = models.ForeignKey(
        "ol_parameters.OLProduct",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="medical_limits",
    )
    plan = models.ForeignKey(
        "ordinary_life.OLPlan",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="ol_parameter_medical_limits",
    )
    age_from = models.PositiveSmallIntegerField(default=0)
    age_to = models.PositiveSmallIntegerField(default=150)
    sum_assured_from = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    sum_assured_to = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    limit_type = models.CharField(max_length=30, choices=OLMedicalLimitType.choices, default=OLMedicalLimitType.MEDICAL)
    limit_amount = models.DecimalField(max_digits=18, decimal_places=2)
    required_frequency = models.CharField(max_length=30, choices=OLMedicalRequiredFrequency.choices, default=OLMedicalRequiredFrequency.ANNUAL)
    mandatory_flag = models.BooleanField(default=True)

    class Meta:
        ordering = ["medical_code", "product", "plan", "age_from", "sum_assured_from", "-effective_from", "code"]
        constraints = [
            models.UniqueConstraint(fields=["code"], name="ol_medical_limit_code_uq"),
            models.CheckConstraint(check=models.Q(age_from__gte=0) & models.Q(age_to__lte=150) & models.Q(age_to__gte=models.F("age_from")), name="ol_med_limit_age_rng"),
            models.CheckConstraint(check=models.Q(sum_assured_from__isnull=True) | models.Q(sum_assured_from__gte=0), name="ol_med_limit_sa_from_nonneg"),
            models.CheckConstraint(check=models.Q(sum_assured_to__isnull=True) | models.Q(sum_assured_to__gte=0), name="ol_med_limit_sa_to_nonneg"),
            models.CheckConstraint(check=models.Q(sum_assured_to__isnull=True) | models.Q(sum_assured_from__isnull=True) | models.Q(sum_assured_to__gte=models.F("sum_assured_from")), name="ol_med_limit_sa_order"),
            models.CheckConstraint(check=models.Q(limit_amount__gt=0), name="ol_med_limit_amount_pos"),
        ]
        indexes = [
            models.Index(fields=["medical_code", "product", "plan", "is_active"], name="ol_med_limit_scope_idx"),
            models.Index(fields=["limit_type", "required_frequency", "is_active"], name="ol_med_limit_type_idx"),
            models.Index(fields=["age_from", "age_to", "sum_assured_from"], name="ol_med_limit_dim_idx"),
            models.Index(fields=["effective_from", "effective_to"], name="ol_med_limit_dates_idx"),
        ]

    def clean(self):
        super().clean()
        errors = {}
        self.limit_type = (self.limit_type or "").strip().upper()
        self.required_frequency = (self.required_frequency or "").strip().upper()
        if self.limit_type not in dict(OLMedicalLimitType.choices):
            errors["limit_type"] = "Unsupported medical limit type."
        if self.required_frequency not in dict(OLMedicalRequiredFrequency.choices):
            errors["required_frequency"] = "Unsupported required medical frequency."
        if self.age_from < 0 or self.age_to > 150 or self.age_to < self.age_from:
            errors["age_to"] = "Medical limit age range must be ordered and remain between 0 and 150 years."
        if self.sum_assured_from is not None and self.sum_assured_from < 0:
            errors["sum_assured_from"] = "Minimum sum assured cannot be negative."
        if self.sum_assured_to is not None and self.sum_assured_to < 0:
            errors["sum_assured_to"] = "Maximum sum assured cannot be negative."
        if self.sum_assured_from is not None and self.sum_assured_to is not None and self.sum_assured_to < self.sum_assured_from:
            errors["sum_assured_to"] = "Maximum sum assured cannot be less than minimum sum assured."
        if self.limit_amount is None or self.limit_amount <= 0:
            errors["limit_amount"] = "Medical limit amount must be positive."
        if self.medical_code_id and not getattr(self.medical_code, "is_active", True):
            errors["medical_code"] = "Medical code must be active."
        if self.product_id and not getattr(self.product, "is_active", True):
            errors["product"] = "Medical limit product must be active."
        if self.plan_id and not getattr(self.plan, "is_active", True):
            errors["plan"] = "Medical limit plan must be active."
        _policy_setup_validate_product_plan(self, errors)
        if errors:
            raise ValidationError(errors)
        candidates = type(self).objects.filter(
            medical_code=self.medical_code,
            product=self.product,
            plan=self.plan,
            limit_type=self.limit_type,
            required_frequency=self.required_frequency,
            is_active=True,
        ).exclude(pk=self.pk)
        if any(_medical_scope_overlaps(self, candidate) for candidate in candidates):
            raise ValidationError({"effective_from": "An active medical limit overlaps an existing row in the same scope and dimensions."})


class OLPersonalHabit(OLParameterBaseModel):
    """Catalog of personal-habit questions consumed by underwriting workflows."""

    habit_category = models.CharField(max_length=40, choices=OLPersonalHabitCategory.choices)
    question_text = models.TextField()
    underwriting_impact = models.CharField(max_length=20, choices=OLMedicalUnderwritingImpact.choices, default=OLMedicalUnderwritingImpact.NONE)
    requires_evidence = models.BooleanField(default=False)

    class Meta:
        ordering = ["habit_category", "name", "code"]
        constraints = [
            models.UniqueConstraint(fields=["code"], name="ol_personal_habit_code_uq"),
        ]
        indexes = [
            models.Index(fields=["habit_category", "is_active"], name="ol_habit_cat_idx"),
            models.Index(fields=["underwriting_impact", "is_active"], name="ol_habit_impact_idx"),
            models.Index(fields=["requires_evidence", "is_active"], name="ol_habit_evidence_idx"),
        ]

    def clean(self):
        super().clean()
        errors = {}
        self.habit_category = (self.habit_category or "").strip().upper()
        self.underwriting_impact = (self.underwriting_impact or OLMedicalUnderwritingImpact.NONE).strip().upper()
        self.question_text = (self.question_text or "").strip()
        if self.habit_category not in dict(OLPersonalHabitCategory.choices):
            errors["habit_category"] = "Unsupported personal-habit category."
        if self.underwriting_impact not in dict(OLMedicalUnderwritingImpact.choices):
            errors["underwriting_impact"] = "Unsupported underwriting impact."
        if not self.question_text:
            errors["question_text"] = "Personal-habit question text is required."
        if errors:
            raise ValidationError(errors)


class OLMedicalHistory(OLParameterBaseModel):
    """Catalog of medical conditions and default underwriting consequences."""

    condition_category = models.CharField(max_length=80, db_index=True)
    severity = models.CharField(max_length=30, db_index=True)
    waiting_period_days = models.PositiveIntegerField(default=0)
    exclusion_flag = models.BooleanField(default=False)
    loading_flag = models.BooleanField(default=False)
    underwriting_note = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["condition_category", "severity", "name", "code"]
        constraints = [
            models.UniqueConstraint(fields=["code"], name="ol_med_history_code_uq"),
        ]
        indexes = [
            models.Index(fields=["condition_category", "is_active"], name="ol_med_hist_cat_idx"),
            models.Index(fields=["severity", "is_active"], name="ol_med_hist_severity_idx"),
            models.Index(fields=["exclusion_flag", "loading_flag", "is_active"], name="ol_med_hist_rules_idx"),
        ]

    def clean(self):
        super().clean()
        errors = {}
        self.condition_category = (self.condition_category or "").strip().upper()
        self.severity = (self.severity or "").strip().upper()
        self.underwriting_note = (self.underwriting_note or "").strip()
        if not self.condition_category:
            errors["condition_category"] = "Condition category is required."
        if not self.severity:
            errors["severity"] = "Condition severity is required."
        if self.waiting_period_days < 0:
            errors["waiting_period_days"] = "Waiting period cannot be negative."
        if errors:
            raise ValidationError(errors)


class OLMedicalFacility(OLParameterBaseModel):
    """Approved medical facility catalog with optional partner master linkage."""

    partner = models.ForeignKey(
        "partners.Partner",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="ol_medical_facilities",
    )
    facility_code = models.CharField(max_length=100, unique=True, db_index=True)
    facility_type = models.CharField(max_length=60)
    registration_number = models.CharField(max_length=120, blank=True, default="")
    address = models.TextField(blank=True, default="")
    city = models.CharField(max_length=100, blank=True, default="")
    country = models.CharField(max_length=100, blank=True, default="TZ")
    contact_email = models.EmailField(blank=True, default="")
    contact_phone = models.CharField(max_length=30, blank=True, default="")
    approval_status = models.CharField(max_length=20, choices=OLMedicalApprovalStatus.choices, default=OLMedicalApprovalStatus.PENDING, db_index=True)

    class Meta:
        ordering = ["name", "facility_code"]
        constraints = [
            models.UniqueConstraint(fields=["code"], name="ol_med_facility_code_uq"),
        ]
        indexes = [
            models.Index(fields=["facility_type", "approval_status", "is_active"], name="ol_med_facility_type_idx"),
            models.Index(fields=["city", "country", "is_active"], name="ol_med_facility_loc_idx"),
            models.Index(fields=["partner", "is_active"], name="ol_med_facility_partner_idx"),
        ]

    def clean(self):
        super().clean()
        errors = {}
        self.facility_code = (self.facility_code or "").strip().upper()
        self.facility_type = (self.facility_type or "").strip().upper()
        self.registration_number = (self.registration_number or "").strip().upper()
        self.city = (self.city or "").strip()
        self.country = (self.country or "TZ").strip().upper()
        self.contact_phone = (self.contact_phone or "").strip()
        self.approval_status = (self.approval_status or OLMedicalApprovalStatus.PENDING).strip().upper()
        if not self.facility_code:
            errors["facility_code"] = "Facility code is required."
        if not self.facility_type:
            errors["facility_type"] = "Facility type is required."
        if self.approval_status not in dict(OLMedicalApprovalStatus.choices):
            errors["approval_status"] = "Unsupported medical facility approval status."
        if self.partner_id:
            if not getattr(self.partner, "is_active", True):
                errors["partner"] = "Medical facility partner must be active."
            elif getattr(self.partner, "partner_type", "") not in {"SERVICE_PROVIDER", "MEDICAL_FACILITY", "MEDICAL_PROVIDER"}:
                errors["partner"] = "Linked partner must be a medical facility or service provider."
        if errors:
            raise ValidationError(errors)


class OLMedicalPractitioner(OLParameterBaseModel):
    """Medical practitioner catalog with optional partner and facility linkages."""

    partner = models.ForeignKey(
        "partners.Partner",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="ol_medical_practitioners",
    )
    practitioner_code = models.CharField(max_length=100, unique=True, db_index=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    specialty = models.CharField(max_length=100)
    license_number = models.CharField(max_length=120)
    medical_facility = models.ForeignKey(
        OLMedicalFacility,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="practitioners",
    )
    email = models.EmailField(blank=True, default="")
    phone = models.CharField(max_length=30, blank=True, default="")
    approval_status = models.CharField(max_length=20, choices=OLMedicalApprovalStatus.choices, default=OLMedicalApprovalStatus.PENDING, db_index=True)

    class Meta:
        ordering = ["last_name", "first_name", "practitioner_code"]
        constraints = [
            models.UniqueConstraint(fields=["code"], name="ol_med_practitioner_code_uq"),
            models.UniqueConstraint(fields=["license_number"], name="ol_med_practitioner_license_uq"),
        ]
        indexes = [
            models.Index(fields=["specialty", "approval_status", "is_active"], name="ol_med_practitioner_spec_idx"),
            models.Index(fields=["medical_facility", "is_active"], name="ol_med_practitioner_fac_idx"),
            models.Index(fields=["partner", "is_active"], name="ol_med_pract_partner_idx"),
        ]

    def clean(self):
        super().clean()
        errors = {}
        self.practitioner_code = (self.practitioner_code or "").strip().upper()
        self.first_name = (self.first_name or "").strip()
        self.last_name = (self.last_name or "").strip()
        self.specialty = (self.specialty or "").strip().upper()
        self.license_number = (self.license_number or "").strip().upper()
        self.phone = (self.phone or "").strip()
        self.approval_status = (self.approval_status or OLMedicalApprovalStatus.PENDING).strip().upper()
        if not self.practitioner_code:
            errors["practitioner_code"] = "Practitioner code is required."
        if not self.first_name:
            errors["first_name"] = "Practitioner first name is required."
        if not self.last_name:
            errors["last_name"] = "Practitioner last name is required."
        if not self.specialty:
            errors["specialty"] = "Practitioner specialty is required."
        if not self.license_number:
            errors["license_number"] = "Practitioner license number is required."
        if self.approval_status not in dict(OLMedicalApprovalStatus.choices):
            errors["approval_status"] = "Unsupported medical practitioner approval status."
        if self.partner_id:
            if not getattr(self.partner, "is_active", True):
                errors["partner"] = "Medical practitioner partner must be active."
            elif getattr(self.partner, "partner_type", "") not in {"MEDICAL_PRACTITIONER", "SERVICE_PROVIDER"}:
                errors["partner"] = "Linked partner must be a medical practitioner or service provider."
        if self.medical_facility_id and not getattr(self.medical_facility, "is_active", True):
            errors["medical_facility"] = "Medical facility must be active."
        if errors:
            raise ValidationError(errors)


# End of OL Medical Underwriting Setup


# =============================================================================
# OL CLAIM SETUP
# =============================================================================
class OLClaimCategory(models.TextChoices):
    DEATH = "DEATH", "Death"
    CRITICAL_ILLNESS = "CRITICAL_ILLNESS", "Critical illness"
    DISABILITY = "DISABILITY", "Disability"
    SURRENDER = "SURRENDER", "Surrender"
    MATURITY = "MATURITY", "Maturity"
    MEDICAL = "MEDICAL", "Medical"
    OTHER = "OTHER", "Other"


class OLClaimCalculationBasis(models.TextChoices):
    SUM_ASSURED = "SUM_ASSURED", "Sum assured"
    CASH_VALUE = "CASH_VALUE", "Cash value"
    BENEFIT_AMOUNT = "BENEFIT_AMOUNT", "Benefit amount"
    FIXED_AMOUNT = "FIXED_AMOUNT", "Fixed amount"
    PERCENTAGE = "PERCENTAGE", "Percentage"
    CUSTOM = "CUSTOM", "Custom"


class OLClaimDuplicateCheckRule(models.TextChoices):
    POLICY_AND_TYPE = "POLICY_AND_TYPE", "Policy and claim type"
    POLICY_AND_REASON = "POLICY_AND_REASON", "Policy and claim reason"
    POLICY_AND_EVENT_DATE = "POLICY_AND_EVENT_DATE", "Policy and event date"
    NONE = "NONE", "No duplicate check"
    CUSTOM = "CUSTOM", "Custom"


class OLClaimReasonCategory(models.TextChoices):
    EVENT = "EVENT", "Insured event"
    MEDICAL = "MEDICAL", "Medical condition"
    ADMINISTRATIVE = "ADMINISTRATIVE", "Administrative"
    FINANCIAL = "FINANCIAL", "Financial"
    DOCUMENTARY = "DOCUMENTARY", "Documentary"
    OTHER = "OTHER", "Other"


class OLClaimStatusBadgeType(models.TextChoices):
    NEUTRAL = "NEUTRAL", "Neutral"
    INFO = "INFO", "Information"
    WARNING = "WARNING", "Warning"
    SUCCESS = "SUCCESS", "Success"
    DANGER = "DANGER", "Danger"
    PRIMARY = "PRIMARY", "Primary"


class OLDischargeCategory(models.TextChoices):
    FULL_AND_FINAL = "FULL_AND_FINAL", "Full and final"
    PARTIAL = "PARTIAL", "Partial"
    RELEASE = "RELEASE", "Release"
    ASSIGNMENT = "ASSIGNMENT", "Assignment"
    OTHER = "OTHER", "Other"


class OLCorrespondenceCategory(models.TextChoices):
    CLAIM_ACKNOWLEDGEMENT = "CLAIM_ACKNOWLEDGEMENT", "Claim acknowledgement"
    DOCUMENT_REQUEST = "DOCUMENT_REQUEST", "Document request"
    ASSESSMENT = "ASSESSMENT", "Assessment"
    DECISION = "DECISION", "Decision"
    PAYMENT = "PAYMENT", "Payment"
    DISCHARGE = "DISCHARGE", "Discharge"
    OTHER = "OTHER", "Other"


class OLCommunicationChannel(models.TextChoices):
    LETTER = "LETTER", "Letter"
    EMAIL = "EMAIL", "Email"
    SMS = "SMS", "SMS"
    PORTAL = "PORTAL", "Portal"
    WHATSAPP = "WHATSAPP", "WhatsApp"
    SYSTEM = "SYSTEM", "System"
    OTHER = "OTHER", "Other"


def _claim_validate_json(value, field_name, expected_type):
    if value is None:
        return
    if not isinstance(value, expected_type):
        expected = "object" if expected_type is dict else "array"
        raise ValidationError({field_name: f"Expected a JSON {expected}."})
    try:
        json.dumps(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError({field_name: "Value must be valid JSON."}) from exc


class OLClaimType(OLParameterBaseModel):
    """Effective-dated configuration for an Ordinary Life claim type."""

    claim_category = models.CharField(max_length=30, choices=OLClaimCategory.choices, db_index=True)
    calculation_basis = models.CharField(max_length=30, choices=OLClaimCalculationBasis.choices, default=OLClaimCalculationBasis.SUM_ASSURED)
    duplicate_check_rule = models.CharField(max_length=35, choices=OLClaimDuplicateCheckRule.choices, default=OLClaimDuplicateCheckRule.POLICY_AND_TYPE)
    waiting_period_days = models.PositiveIntegerField(null=True, blank=True)
    payable_to_rules = models.JSONField(default=dict, blank=True)
    allow_waiver_of_premium = models.BooleanField(default=False)
    require_documents = models.JSONField(default=list, blank=True)
    require_approval = models.BooleanField(default=True)

    class Meta:
        ordering = ["claim_category", "name", "code"]
        constraints = [
            models.UniqueConstraint(fields=["code"], name="ol_claim_type_code_uq"),
            models.CheckConstraint(
                check=models.Q(waiting_period_days__isnull=True) | models.Q(waiting_period_days__gte=0),
                name="ol_claim_type_wait_ck",
            ),
        ]
        indexes = [
            models.Index(fields=["claim_category", "is_active"], name="ol_claim_type_cat_idx"),
            models.Index(fields=["require_approval", "is_active"], name="ol_claim_type_appr_idx"),
        ]

    def clean(self):
        super().clean()
        errors = {}
        self.claim_category = (self.claim_category or "").strip().upper()
        self.calculation_basis = (self.calculation_basis or "").strip().upper()
        self.duplicate_check_rule = (self.duplicate_check_rule or "").strip().upper()
        if self.claim_category not in dict(OLClaimCategory.choices):
            errors["claim_category"] = "Unsupported claim category."
        if self.calculation_basis not in dict(OLClaimCalculationBasis.choices):
            errors["calculation_basis"] = "Unsupported claim calculation basis."
        if self.duplicate_check_rule not in dict(OLClaimDuplicateCheckRule.choices):
            errors["duplicate_check_rule"] = "Unsupported duplicate-check rule."
        _claim_validate_json(self.payable_to_rules, "payable_to_rules", dict)
        _claim_validate_json(self.require_documents, "require_documents", list)
        if self.waiting_period_days is not None and self.waiting_period_days < 0:
            errors["waiting_period_days"] = "Waiting period cannot be negative."
        if errors:
            raise ValidationError(errors)


class OLClaimReason(OLParameterBaseModel):
    """Catalog of configurable reasons that may be attached to an OL claim."""

    claim_type = models.ForeignKey(
        OLClaimType,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="claim_reasons",
    )
    reason_category = models.CharField(max_length=30, choices=OLClaimReasonCategory.choices, db_index=True)

    class Meta:
        ordering = ["reason_category", "name", "code"]
        constraints = [models.UniqueConstraint(fields=["code"], name="ol_claim_reason_code_uq")]
        indexes = [
            models.Index(fields=["claim_type", "is_active"], name="ol_claim_reason_type_idx"),
            models.Index(fields=["reason_category", "is_active"], name="ol_claim_reason_cat_idx"),
        ]

    def clean(self):
        super().clean()
        errors = {}
        self.reason_category = (self.reason_category or "").strip().upper()
        if self.reason_category not in dict(OLClaimReasonCategory.choices):
            errors["reason_category"] = "Unsupported claim-reason category."
        if self.claim_type_id and not getattr(self.claim_type, "is_active", True):
            errors["claim_type"] = "Claim reason must reference an active claim type."
        if errors:
            raise ValidationError(errors)


class OLClaimStatus(OLParameterBaseModel):
    """Status catalog with a declarative directed transition graph."""

    display_order = models.PositiveIntegerField(default=0)
    badge_type = models.CharField(max_length=20, choices=OLClaimStatusBadgeType.choices, default=OLClaimStatusBadgeType.NEUTRAL)
    is_terminal = models.BooleanField(default=False)
    is_payable = models.BooleanField(default=False)
    allowed_transitions = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["display_order", "name", "code"]
        constraints = [models.UniqueConstraint(fields=["code"], name="ol_claim_status_code_uq")]
        indexes = [
            models.Index(fields=["display_order", "is_active"], name="ol_claim_status_order_idx"),
            models.Index(fields=["is_terminal", "is_active"], name="ol_claim_status_term_idx"),
        ]

    def clean(self):
        super().clean()
        errors = {}
        self.badge_type = (self.badge_type or "").strip().upper()
        self.code = (self.code or "").strip().upper()
        if self.badge_type not in dict(OLClaimStatusBadgeType.choices):
            errors["badge_type"] = "Unsupported claim-status badge type."
        _claim_validate_json(self.allowed_transitions, "allowed_transitions", list)
        transitions = []
        for transition in self.allowed_transitions or []:
            if not isinstance(transition, str) or not transition.strip():
                errors.setdefault("allowed_transitions", "Allowed transitions must be non-empty status codes.")
                continue
            normalized = transition.strip().upper()
            if normalized in transitions:
                errors.setdefault("allowed_transitions", "Allowed transitions cannot contain duplicates.")
            transitions.append(normalized)
        self.allowed_transitions = transitions
        if self.is_terminal and transitions:
            errors["allowed_transitions"] = "A terminal claim status cannot have outgoing transitions."
        if self.code and self.code in transitions:
            errors["allowed_transitions"] = "A claim status cannot transition to itself."
        if transitions and not errors.get("allowed_transitions"):
            existing = {
                code: active
                for code, active in OLClaimStatus.objects.exclude(pk=self.pk).filter(code__in=transitions).values_list("code", "is_active")
            }
            missing = sorted(set(transitions) - set(existing))
            inactive = sorted(code for code in transitions if code in existing and not existing[code])
            if missing:
                errors["allowed_transitions"] = f"Unknown claim-status transition target(s): {', '.join(missing)}."
            elif inactive:
                errors["allowed_transitions"] = f"Transition target(s) must be active: {', '.join(inactive)}."
        if errors:
            raise ValidationError(errors)

    def can_transition_to(self, target):
        target_code = (getattr(target, "code", target) or "").strip().upper()
        return bool(target_code and target_code in (self.allowed_transitions or []) and not self.is_terminal)

    def validate_transition_to(self, target):
        if not self.can_transition_to(target):
            target_code = (getattr(target, "code", target) or "").strip().upper()
            raise ValidationError({"allowed_transitions": f"Transition from {self.code} to {target_code} is not allowed."})


class OLDischargeType(OLParameterBaseModel):
    """Configurable discharge/release document type for claim settlement."""

    discharge_category = models.CharField(max_length=30, choices=OLDischargeCategory.choices, db_index=True)
    template_code = models.CharField(max_length=100, blank=True, default="", db_index=True)
    variables = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["discharge_category", "name", "code"]
        constraints = [models.UniqueConstraint(fields=["code"], name="ol_discharge_type_code_uq")]
        indexes = [
            models.Index(fields=["discharge_category", "is_active"], name="ol_discharge_cat_idx"),
            models.Index(fields=["template_code", "is_active"], name="ol_discharge_tpl_idx"),
        ]

    def clean(self):
        super().clean()
        errors = {}
        self.discharge_category = (self.discharge_category or "").strip().upper()
        self.template_code = (self.template_code or "").strip().upper()
        if self.discharge_category not in dict(OLDischargeCategory.choices):
            errors["discharge_category"] = "Unsupported discharge category."
        _claim_validate_json(self.variables, "variables", dict)
        if errors:
            raise ValidationError(errors)


class OLCorrespondentType(OLParameterBaseModel):
    """Catalog of correspondence templates/purposes used by claim workflows."""

    correspondence_category = models.CharField(max_length=35, choices=OLCorrespondenceCategory.choices, db_index=True)
    communication_channel = models.CharField(max_length=20, choices=OLCommunicationChannel.choices, db_index=True)
    purpose = models.CharField(max_length=200, blank=True, default="")

    class Meta:
        ordering = ["correspondence_category", "name", "code"]
        constraints = [models.UniqueConstraint(fields=["code"], name="ol_correspondent_type_code_uq")]
        indexes = [
            models.Index(fields=["correspondence_category", "is_active"], name="ol_corr_cat_idx"),
            models.Index(fields=["communication_channel", "is_active"], name="ol_corr_chan_idx"),
        ]

    def clean(self):
        super().clean()
        errors = {}
        self.correspondence_category = (self.correspondence_category or "").strip().upper()
        self.communication_channel = (self.communication_channel or "").strip().upper()
        self.purpose = (self.purpose or "").strip()
        if self.correspondence_category not in dict(OLCorrespondenceCategory.choices):
            errors["correspondence_category"] = "Unsupported correspondence category."
        if self.communication_channel not in dict(OLCommunicationChannel.choices):
            errors["communication_channel"] = "Unsupported communication channel."
        if errors:
            raise ValidationError(errors)


# End of OL Claim Setup
