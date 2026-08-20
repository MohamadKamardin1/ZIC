import logging
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

logger = logging.getLogger(__name__)

AUDIT_ACTION_CHOICES = [
    ("CREATE", "Create"),
    ("UPDATE", "Update"),
    ("DELETE", "Delete"),
    ("APPROVE", "Approve"),
    ("REJECT", "Reject"),
    ("SUBMIT", "Submit"),
    ("ACTIVATE", "Activate"),
    ("DEACTIVATE", "Deactivate"),
    ("ASSIGN", "Assign"),
    ("UNASSIGN", "Unassign"),
    ("UPLOAD", "Upload"),
    ("DOWNLOAD", "Download"),
    ("LOGIN", "Login"),
    ("LOGOUT", "Logout"),
    ("VERIFY", "Verify"),
    ("ESCALATE", "Escalate"),
    ("RENEW", "Renew"),
    ("EXPIRE", "Expire"),
]

APPROVAL_STATUS_CHOICES = [
    ("PENDING", "Pending"),
    ("APPROVED", "Approved"),
    ("REJECTED", "Rejected"),
    ("CANCELLED", "Cancelled"),
]

CONFIG_VERSION_STATUS_CHOICES = [
    ("DRAFT", "Draft"),
    ("ACTIVE", "Active"),
    ("RETIRED", "Retired"),
]


class AuditLog(models.Model):
    class ActorType(models.TextChoices):
        USER = "USER", "User"
        SYSTEM = "SYSTEM", "System"
        SERVICE = "SERVICE", "Service"
        IMPORT = "IMPORT", "Import"
        BATCH = "BATCH", "Batch"
        ANONYMOUS = "ANONYMOUS", "Anonymous"

    class SourceChannel(models.TextChoices):
        WEB = "WEB", "Web"
        API = "API", "API"
        ADMIN = "ADMIN", "Admin"
        SYSTEM = "SYSTEM", "System"
        IMPORT = "IMPORT", "Import"
        PORTAL = "PORTAL", "Portal"
        BATCH = "BATCH", "Batch"
        QUICK_CREATE = "QUICK_CREATE", "Quick create"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="audit_logs",
    )
    action_type = models.CharField(max_length=30, choices=AUDIT_ACTION_CHOICES, db_index=True)
    entity_type = models.CharField(max_length=100, db_index=True)
    entity_id = models.UUIDField(null=True, blank=True, db_index=True)
    entity_repr = models.CharField(max_length=255, blank=True)
    before_state = models.JSONField(blank=True, null=True)
    after_state = models.JSONField(blank=True, null=True)
    description = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.CharField(max_length=500, blank=True)
    request_id = models.CharField(max_length=50, blank=True)
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    actor_type = models.CharField(max_length=20, choices=ActorType.choices, default=ActorType.SYSTEM, db_index=True)
    action = models.CharField(max_length=50, blank=True, db_index=True)
    app_label = models.CharField(max_length=100, blank=True, db_index=True)
    model_name = models.CharField(max_length=100, blank=True, db_index=True)
    object_id = models.CharField(max_length=100, blank=True, db_index=True)
    object_repr = models.CharField(max_length=255, blank=True)
    changed_fields = models.JSONField(default=list, blank=True)
    reason = models.TextField(blank=True)
    source_channel = models.CharField(max_length=20, choices=SourceChannel.choices, default=SourceChannel.SYSTEM, db_index=True)
    correlation_id = models.CharField(max_length=100, blank=True, db_index=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        db_table = "governance_audit_log"
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["entity_type", "entity_id"]),
            models.Index(fields=["user", "-timestamp"]),
            models.Index(fields=["action_type", "-timestamp"]),
            models.Index(fields=["app_label", "model_name", "object_id"]),
            models.Index(fields=["actor_type", "created_at"]),
            models.Index(fields=["source_channel", "created_at"]),
            models.Index(fields=["correlation_id", "created_at"]),
        ]

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            from django.core.exceptions import ValidationError
            raise ValidationError("Audit events are immutable and cannot be updated.")
        if not self.action:
            self.action = self.action_type
        if not self.model_name:
            self.model_name = self.entity_type
        if not self.object_id and self.entity_id:
            self.object_id = str(self.entity_id)
        if not self.object_repr:
            self.object_repr = self.entity_repr
        if not self.reason:
            self.reason = self.description
        if not self.correlation_id:
            self.correlation_id = self.request_id
        if not self.created_at:
            self.created_at = self.timestamp
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        from django.core.exceptions import ValidationError
        raise ValidationError("Audit events are immutable and cannot be deleted.")

    def __str__(self):
        action = self.action or self.action_type
        entity = self.entity_type or self.model_name or "Object"
        representation = self.entity_repr or self.object_repr or self.object_id or self.entity_id
        return f"{action} on {entity} ({representation})" if representation else f"{action} on {entity}"


class ApprovalRequest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    module = models.CharField(max_length=100, db_index=True)
    entity_type = models.CharField(max_length=100)
    entity_id = models.UUIDField(db_index=True)
    entity_repr = models.CharField(max_length=255, blank=True)
    action = models.CharField(max_length=30)
    requested_data = models.JSONField(blank=True, null=True)
    current_data = models.JSONField(blank=True, null=True)
    status = models.CharField(
        max_length=30, choices=APPROVAL_STATUS_CHOICES,
        default="PENDING", db_index=True,
    )
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name="submitted_approvals",
    )
    submitted_at = models.DateTimeField(default=timezone.now)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="reviewed_approvals",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    comments = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "governance_approval_request"
        verbose_name = "Approval Request"
        verbose_name_plural = "Approval Requests"
        ordering = ["-submitted_at"]
        indexes = [
            models.Index(fields=["module", "status"]),
            models.Index(fields=["entity_type", "entity_id"]),
            models.Index(fields=["submitted_by", "-submitted_at"]),
        ]

    def __str__(self):
        return f"{self.action} on {self.entity_type} ({self.status})"


class ConfigurationVersion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    module = models.CharField(max_length=100, db_index=True)
    version_number = models.PositiveIntegerField()
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=CONFIG_VERSION_STATUS_CHOICES,
        default="DRAFT", db_index=True,
    )
    configuration_data = models.JSONField(blank=True, default=dict)
    change_summary = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="created_config_versions",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "governance_configuration_version"
        verbose_name = "Configuration Version"
        verbose_name_plural = "Configuration Versions"
        ordering = ["module", "-version_number"]
        unique_together = [("module", "version_number")]
        indexes = [
            models.Index(fields=["module", "status"]),
            models.Index(fields=["effective_from", "effective_to"]),
        ]

    def __str__(self):
        return f"{self.module} v{self.version_number} ({self.status})"


# Public compatibility name for future modules that use the AuditEvent terminology.
AuditEvent = AuditLog
