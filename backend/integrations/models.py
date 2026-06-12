"""Integrations: API keys, webhooks, devices and offline sync."""

from django.db import models

from core.models import BaseModel


class APIKey(BaseModel):
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="api_keys",
    )
    name = models.CharField(max_length=255)
    #: First 8 chars of the plaintext key — the lookup handle; the rest is
    #: only ever stored hashed.
    key_prefix = models.CharField(max_length=8, blank=True, db_index=True)
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
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="webhook_endpoints",
    )
    url = models.URLField()
    secret_hash = models.CharField(max_length=255)
    #: Fernet-encrypted copy of the signing secret — deliveries are HMAC-
    #: signed with the plaintext, which a hash alone cannot provide.
    signing_secret_encrypted = models.TextField(blank=True)
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
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="devices",
    )
    branch = models.ForeignKey(
        "organizations.Branch",
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
        "organizations.Organization",
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
        return (
            f"{self.get_operation_type_display()} {self.entity_type} from {self.device}"
        )


# ---------------------------------------------------------------------------
# Transactional outbox & webhook deliveries
# ---------------------------------------------------------------------------


class OutboundEvent(BaseModel):
    """Transactional outbox row: domain code appends events inside its own
    transaction; the dispatcher fans them out to webhook endpoints after
    commit, so an external delivery can never be triggered by a rolled-back
    mutation."""

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="outbound_events",
    )
    event_type = models.CharField(max_length=100)
    payload = models.JSONField(default=dict, blank=True)
    dispatched_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["organization", "event_type"]),
            models.Index(fields=["dispatched_at"]),
        ]

    def __str__(self):
        return f"{self.event_type} ({self.pk})"


class WebhookDelivery(BaseModel):
    """One endpoint's copy of one event, with full retry bookkeeping.
    Terminal states: delivered or dead (retries exhausted)."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        DELIVERED = "delivered", "Delivered"
        FAILED = "failed", "Failed (will retry)"
        DEAD = "dead", "Dead (retries exhausted)"

    endpoint = models.ForeignKey(
        WebhookEndpoint, on_delete=models.CASCADE, related_name="deliveries"
    )
    event = models.ForeignKey(
        OutboundEvent, on_delete=models.CASCADE, related_name="deliveries"
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    attempt_count = models.PositiveIntegerField(default=0)
    last_status_code = models.PositiveIntegerField(null=True, blank=True)
    last_error = models.CharField(max_length=500, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name_plural = "webhook deliveries"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["endpoint", "event"], name="uniq_delivery_per_endpoint_event"
            )
        ]
        indexes = [
            models.Index(fields=["status", "created_at"]),
        ]

    def __str__(self):
        return f"{self.event} -> {self.endpoint} ({self.get_status_display()})"


class IntegrationConnection(BaseModel):
    """A tenant's link to an external system (calendar, accounting,
    marketing). Credentials are encrypted at rest; sync state machines are
    per-provider workers layered on top of this record."""

    class Provider(models.TextChoices):
        GOOGLE_CALENDAR = "google_calendar", "Google Calendar"
        OUTLOOK_CALENDAR = "outlook_calendar", "Outlook Calendar"
        APPLE_CALENDAR = "apple_calendar", "Apple Calendar"
        QUICKBOOKS = "quickbooks", "QuickBooks"
        XERO = "xero", "Xero"
        MAILCHIMP = "mailchimp", "Mailchimp"
        INSTAGRAM = "instagram", "Instagram"
        FACEBOOK = "facebook", "Facebook"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CONNECTED = "connected", "Connected"
        ERROR = "error", "Error"
        DISCONNECTED = "disconnected", "Disconnected"

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="integration_connections",
    )
    provider = models.CharField(max_length=30, choices=Provider.choices)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    external_account_id = models.CharField(max_length=255, blank=True)
    credentials_encrypted = models.TextField(blank=True)
    settings = models.JSONField(default=dict, blank=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    last_error = models.CharField(max_length=500, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "provider"],
                name="uniq_integration_per_provider",
            )
        ]

    def __str__(self):
        return f"{self.get_provider_display()} for {self.organization}"
