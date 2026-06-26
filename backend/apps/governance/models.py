import uuid
import logging

from django.db import models
from django.conf import settings
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
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="audit_logs",
    )
    action_type = models.CharField(max_length=30, choices=AUDIT_ACTION_CHOICES, db_index=True)
    entity_type = models.CharField(max_length=100, db_index=True)
    entity_id = models.UUIDField(db_index=True)
    entity_repr = models.CharField(max_length=255, blank=True)
    before_state = models.JSONField(blank=True, null=True)
    after_state = models.JSONField(blank=True, null=True)
    description = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.CharField(max_length=500, blank=True)
    request_id = models.CharField(max_length=50, blank=True)
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        db_table = "governance_audit_log"
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["entity_type", "entity_id"]),
            models.Index(fields=["user", "-timestamp"]),
            models.Index(fields=["action_type", "-timestamp"]),
        ]

    def __str__(self):
        return f"{self.action_type} on {self.entity_type} ({self.entity_repr or self.entity_id})"


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
