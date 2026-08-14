import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class UUIDModel(models.Model):
    """Abstract base for domain entities that use stable UUID identifiers."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class TimeStampedModel(models.Model):
    """Abstract base carrying immutable creation and mutable update timestamps."""

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class AuditedModel(TimeStampedModel):
    """Timestamped base with optional user attribution for writes."""

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(app_label)s_%(class)s_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(app_label)s_%(class)s_updated",
    )

    class Meta:
        abstract = True


class SoftDeleteModel(TimeStampedModel):
    """Abstract status-based deletion for records that must remain auditable."""

    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def soft_delete(self):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=["is_deleted", "deleted_at", "updated_at"])

    def restore(self):
        self.is_deleted = False
        self.deleted_at = None
        self.save(update_fields=["is_deleted", "deleted_at", "updated_at"])

    class Meta:
        abstract = True


class DomainEvent(UUIDModel):
    """Durable outbox event for reliable publication of domain changes."""

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PUBLISHED = "PUBLISHED", "Published"
        FAILED = "FAILED", "Failed"

    event_type = models.CharField(max_length=150, db_index=True)
    aggregate_type = models.CharField(max_length=100, db_index=True)
    aggregate_id = models.CharField(max_length=100, db_index=True)
    payload = models.JSONField(default=dict)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    occurred_at = models.DateTimeField(default=timezone.now, db_index=True)
    published_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)
    attempts = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["occurred_at", "id"]
        indexes = [
            models.Index(fields=["status", "occurred_at"]),
            models.Index(fields=["aggregate_type", "aggregate_id"]),
        ]

    def mark_published(self):
        self.status = self.Status.PUBLISHED
        self.published_at = timezone.now()
        self.last_error = ""
        self.save(update_fields=["status", "published_at", "last_error"])

    def mark_failed(self, error):
        self.status = self.Status.FAILED
        self.last_error = str(error)[:2000]
        self.attempts += 1
        self.save(update_fields=["status", "last_error", "attempts"])

    def __str__(self):
        return f"{self.event_type}:{self.aggregate_type}:{self.aggregate_id}"
