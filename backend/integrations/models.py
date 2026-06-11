<<<<<<< HEAD
from django.db import models

# Create your models here.
=======
"""Integrations: API keys, webhooks, devices and offline sync."""

from django.db import models

from core.models import BaseModel


class APIKey(BaseModel):
    organization = models.ForeignKey(
        "organnizations.Organization",
        on_delete=models.CASCADE,
        related_name="api_keys",
    )
    name = models.CharField(max_length=255)
    key_hash = models.CharField(max_length=255)
    scopes = models.JSONField(default=list, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    rotated_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "API key"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "is_active"]),
        ]

    def __str__(self):
        return self.name


class WebhookEndpoint(BaseModel):
    organization = models.ForeignKey(
        "organnizations.Organization",
        on_delete=models.CASCADE,
        related_name="webhook_endpoints",
    )
    url = models.URLField()
    secret_hash = models.CharField(max_length=255)
    events = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    last_triggered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.url


class Device(BaseModel):
    class DeviceType(models.TextChoices):
        POS = "pos", "POS Terminal"
        TABLET = "tablet", "Tablet"
        KIOSK = "kiosk", "Kiosk"
        MOBILE = "mobile", "Mobile"
        OTHER = "other", "Other"

    organization = models.ForeignKey(
        "organnizations.Organization",
        on_delete=models.CASCADE,
        related_name="devices",
    )
    branch = models.ForeignKey(
        "organnizations.Branch",
        on_delete=models.SET_NULL,
        related_name="devices",
        null=True,
        blank=True,
    )
    device_uuid = models.CharField(max_length=64, unique=True)
    device_name = models.CharField(max_length=255)
    device_type = models.CharField(
        max_length=20, choices=DeviceType.choices, default=DeviceType.OTHER
    )
    last_sync_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.device_name


class SyncOperation(BaseModel):
    class OperationType(models.TextChoices):
        CREATE = "create", "Create"
        UPDATE = "update", "Update"
        DELETE = "delete", "Delete"

    class ConflictStatus(models.TextChoices):
        NONE = "none", "None"
        DETECTED = "detected", "Detected"
        RESOLVED = "resolved", "Resolved"

    organization = models.ForeignKey(
        "organnizations.Organization",
        on_delete=models.CASCADE,
        related_name="sync_operations",
    )
    device = models.ForeignKey(
        Device, on_delete=models.CASCADE, related_name="sync_operations"
    )
    operation_type = models.CharField(max_length=10, choices=OperationType.choices)
    entity_type = models.CharField(max_length=100)
    entity_id = models.UUIDField(null=True, blank=True)
    payload = models.JSONField(default=dict, blank=True)
    client_timestamp = models.DateTimeField()
    server_applied_at = models.DateTimeField(null=True, blank=True)
    conflict_status = models.CharField(
        max_length=10, choices=ConflictStatus.choices, default=ConflictStatus.NONE
    )
    conflict_resolution = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["device", "created_at"]),
            models.Index(fields=["organization", "conflict_status"]),
        ]

    def __str__(self):
        return f"{self.get_operation_type_display()} {self.entity_type} from {self.device}"
>>>>>>> a3235b4 (feat(db): initialize core relational schema)
