from django.conf import settings
from django.db import models
from django.utils import timezone


class DashboardTask(models.Model):
    class Status(models.TextChoices):
        TODO = "TODO", "To do"
        IN_PROGRESS = "IN_PROGRESS", "In progress"
        DONE = "DONE", "Done"
        ARCHIVED = "ARCHIVED", "Archived"

    class Priority(models.TextChoices):
        LOW = "LOW", "Low"
        MEDIUM = "MEDIUM", "Medium"
        HIGH = "HIGH", "High"
        URGENT = "URGENT", "Urgent"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="dashboard_tasks")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.TODO, db_index=True)
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.MEDIUM, db_index=True)
    due_at = models.DateTimeField(null=True, blank=True, db_index=True)
    route = models.CharField(max_length=255, blank=True)
    entity_type = models.CharField(max_length=100, blank=True)
    entity_id = models.CharField(max_length=100, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_dashboard_tasks",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["status", "due_at", "-created_at"]
        indexes = [
            models.Index(fields=["owner", "status"]),
            models.Index(fields=["owner", "due_at"]),
        ]

    def mark_complete(self):
        self.status = self.Status.DONE
        self.completed_at = timezone.now()
        self.save(update_fields=["status", "completed_at", "updated_at"])


class DashboardAlert(models.Model):
    class Severity(models.TextChoices):
        INFO = "INFO", "Information"
        WARNING = "WARNING", "Warning"
        CRITICAL = "CRITICAL", "Critical"

    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        ACKNOWLEDGED = "ACKNOWLEDGED", "Acknowledged"
        DISMISSED = "DISMISSED", "Dismissed"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="dashboard_alerts")
    title = models.CharField(max_length=255)
    message = models.TextField()
    severity = models.CharField(max_length=20, choices=Severity.choices, default=Severity.INFO, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN, db_index=True)
    route = models.CharField(max_length=255, blank=True)
    entity_type = models.CharField(max_length=100, blank=True)
    entity_id = models.CharField(max_length=100, blank=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    acknowledged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="acknowledged_dashboard_alerts",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["owner", "status"]),
            models.Index(fields=["owner", "severity"]),
        ]


class DashboardNotification(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="dashboard_notifications")
    external_key = models.CharField(max_length=180)
    kind = models.CharField(max_length=80, default="SYSTEM")
    title = models.CharField(max_length=255)
    message = models.TextField(blank=True)
    status = models.CharField(max_length=80, blank=True)
    route = models.CharField(max_length=255, blank=True)
    entity_type = models.CharField(max_length=100, blank=True)
    entity_id = models.CharField(max_length=100, blank=True)
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["owner", "external_key"], name="dashboard_notification_owner_key_unique"),
        ]
        indexes = [
            models.Index(fields=["owner", "is_read", "created_at"]),
        ]


class CurrencyPair(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="currency_pairs")
    base_currency = models.CharField(max_length=3)
    quote_currency = models.CharField(max_length=3)
    is_active = models.BooleanField(default=True)
    target_rate = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["base_currency", "quote_currency"]
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "base_currency", "quote_currency"],
                name="currency_pair_owner_currencies_unique",
            ),
        ]


class CurrencyRate(models.Model):
    pair = models.ForeignKey(CurrencyPair, on_delete=models.CASCADE, related_name="rates")
    rate = models.DecimalField(max_digits=20, decimal_places=8)
    provider = models.CharField(max_length=80, default="frankfurter")
    as_of = models.DateField()
    fetched_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-as_of", "-fetched_at"]
        indexes = [
            models.Index(fields=["pair", "as_of"]),
        ]
