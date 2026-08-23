from __future__ import annotations

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class DocumentTemplate(models.Model):
    """An approved, versioned HTML layout used by the shared print engine."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=120)
    name = models.CharField(max_length=255)
    document_type = models.CharField(max_length=120, db_index=True)
    version = models.PositiveIntegerField(default=1)
    layout_template_path = models.CharField(max_length=255)
    variables_schema = models.JSONField(default=dict, blank=True)
    branding_config_reference = models.CharField(
        max_length=120,
        default="COMPANY_BRANDING",
        blank=True,
    )
    is_active = models.BooleanField(default=True, db_index=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_document_templates",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["document_type", "code", "-version"]
        constraints = [
            models.UniqueConstraint(
                fields=["code", "version"],
                name="documents_template_code_version_uq",
            ),
        ]
        indexes = [
            models.Index(fields=["document_type", "is_active", "version"]),
        ]

    def __str__(self):
        return f"{self.name} v{self.version}"

    def clean(self):
        errors = {}
        self.code = (self.code or "").strip().upper()
        self.name = (self.name or "").strip()
        self.document_type = (self.document_type or "").strip().upper()
        self.layout_template_path = (self.layout_template_path or "").strip()
        self.branding_config_reference = (self.branding_config_reference or "COMPANY_BRANDING").strip().upper()
        if not self.code:
            errors["code"] = "Template code is required."
        if not self.name:
            errors["name"] = "Template name is required."
        if not self.document_type:
            errors["document_type"] = "Document type is required."
        if self.version < 1:
            errors["version"] = "Template version must be at least 1."
        if not self.layout_template_path:
            errors["layout_template_path"] = "A layout template path is required."
        if not isinstance(self.variables_schema, dict):
            errors["variables_schema"] = "Variables schema must be a JSON object."
        if self.approved_at and not self.approved_by_id:
            errors["approved_by"] = "An approver is required when approved_at is set."
        if errors:
            raise ValidationError(errors)


class DocumentInstance(models.Model):
    """An immutable render result linked to its source transaction and template."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document_type = models.CharField(max_length=120, db_index=True)
    source_app_label = models.CharField(max_length=100, db_index=True)
    source_model = models.CharField(max_length=120, db_index=True)
    source_object_id = models.CharField(max_length=120, db_index=True)
    template = models.ForeignKey(
        DocumentTemplate,
        on_delete=models.PROTECT,
        related_name="instances",
    )
    template_version = models.PositiveIntegerField()
    file_reference = models.CharField(max_length=500)
    preview_reference = models.CharField(max_length=500, blank=True, default="")
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generated_document_instances",
    )
    generated_at = models.DateTimeField(default=timezone.now, db_index=True)
    correlation_id = models.CharField(max_length=100, blank=True, default="", db_index=True)
    page_count = models.PositiveIntegerField(default=1)
    checksum = models.CharField(max_length=64)
    mime_type = models.CharField(max_length=120, default="application/pdf")
    status = models.CharField(max_length=30, default="GENERATED", db_index=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-generated_at", "-created_at"]
        indexes = [
            models.Index(fields=["source_app_label", "source_model", "source_object_id"]),
            models.Index(fields=["document_type", "generated_at"]),
        ]

    def __str__(self):
        return f"{self.document_type} / {self.source_model} / {self.source_object_id}"

    @property
    def source_type(self):
        return f"{self.source_app_label}.{self.source_model}"

    def clean(self):
        errors = {}
        self.document_type = (self.document_type or "").strip().upper()
        self.source_app_label = (self.source_app_label or "").strip().lower()
        self.source_model = (self.source_model or "").strip()
        self.source_object_id = (self.source_object_id or "").strip()
        self.file_reference = (self.file_reference or "").strip()
        self.preview_reference = (self.preview_reference or "").strip()
        self.mime_type = (self.mime_type or "application/pdf").strip().lower()
        if not self.document_type:
            errors["document_type"] = "Document type is required."
        if not self.source_app_label or not self.source_model or not self.source_object_id:
            errors["source"] = "A complete source app, model, and object identifier are required."
        if not self.template_id:
            errors["template"] = "A document template is required."
        if self.template_id and self.template_version != self.template.version:
            errors["template_version"] = "Template version must match the selected template."
        if not self.file_reference:
            errors["file_reference"] = "A generated file reference is required."
        if self.page_count < 1:
            errors["page_count"] = "Page count must be at least 1."
        if len((self.checksum or "").strip()) != 64:
            errors["checksum"] = "Checksum must be a SHA-256 hexadecimal digest."
        if errors:
            raise ValidationError(errors)
