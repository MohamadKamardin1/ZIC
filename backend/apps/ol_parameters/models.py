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
