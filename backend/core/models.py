"""Core abstract bases, shared enums and platform-level reference models."""

import uuid

from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.utils import timezone


# ---------------------------------------------------------------------------
# Shared enums
# ---------------------------------------------------------------------------


class Weekday(models.IntegerChoices):
    MONDAY = 0, "Monday"
    TUESDAY = 1, "Tuesday"
    WEDNESDAY = 2, "Wednesday"
    THURSDAY = 3, "Thursday"
    FRIDAY = 4, "Friday"
    SATURDAY = 5, "Saturday"
    SUNDAY = 6, "Sunday"


class Channel(models.TextChoices):
    SMS = "sms", "SMS"
    EMAIL = "email", "Email"
    WHATSAPP = "whatsapp", "WhatsApp"
    PUSH = "push", "Push"
    IN_APP = "in_app", "In-App"


# ---------------------------------------------------------------------------
# Abstract bases
# ---------------------------------------------------------------------------


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class BaseModel(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class SoftDeleteQuerySet(models.QuerySet):
    def delete(self):
        return super().update(deleted_at=timezone.now())

    def hard_delete(self):
        return super().delete()

    def alive(self):
        return self.filter(deleted_at__isnull=True)

    def dead(self):
        return self.filter(deleted_at__isnull=False)


class SoftDeleteManager(models.Manager):
    """Default manager that hides soft-deleted rows."""

    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).filter(
            deleted_at__isnull=True
        )


class SoftDeleteModel(models.Model):
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True
        base_manager_name = "all_objects"

    def delete(self, using=None, keep_parents=False):
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at", "updated_at"])

    def hard_delete(self, using=None, keep_parents=False):
        return super().delete(using=using, keep_parents=keep_parents)


# ---------------------------------------------------------------------------
# Reference models
# ---------------------------------------------------------------------------


class IdempotencyRecord(BaseModel):
    """Stored outcome of a mutating request that carried an Idempotency-Key.

    At-least-once clients (mobile/PWA retrying over flaky connections) replay
    the same key; the API answers with the stored response instead of
    re-executing the mutation. Keyed per user so tenants cannot collide or
    probe each other's keys.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="idempotency_records",
    )
    key = models.CharField(max_length=255)
    method = models.CharField(max_length=10)
    path = models.CharField(max_length=255)
    response_status = models.PositiveSmallIntegerField()
    # DRF response data still carries UUID/Decimal/datetime objects before
    # rendering; the Django encoder coerces them the same way the JSON
    # renderer would.
    response_body = models.JSONField(
        default=dict, blank=True, encoder=DjangoJSONEncoder
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "key", "method", "path"],
                name="uniq_idempotency_key_per_user_endpoint",
            )
        ]
        indexes = [
            models.Index(fields=["created_at"]),  # retention sweeps
        ]

    def __str__(self):
        return f"{self.method} {self.path} [{self.key}]"


class Country(BaseModel):
    name = models.CharField(max_length=120)
    code = models.CharField(max_length=2, unique=True)  # ISO 3166-1 alpha-2
    currency = models.CharField(max_length=3, blank=True)  # ISO 4217
    timezone = models.CharField(max_length=64, blank=True)

    class Meta:
        verbose_name_plural = "countries"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.code})"


class Currency(BaseModel):
    code = models.CharField(max_length=3, unique=True)  # ISO 4217
    name = models.CharField(max_length=80)
    symbol = models.CharField(max_length=8, blank=True)

    class Meta:
        verbose_name_plural = "currencies"
        ordering = ["code"]

    def __str__(self):
        return self.code


class Translation(BaseModel):
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="translations",
    )
    entity_type = models.CharField(max_length=100)
    entity_id = models.UUIDField()
    locale = models.CharField(max_length=10)  # e.g. "ar", "en"
    field = models.CharField(max_length=100)
    value = models.TextField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "entity_type", "entity_id", "locale", "field"],
                name="uniq_translation_per_field_locale",
            )
        ]
        indexes = [
            models.Index(fields=["organization", "entity_type", "entity_id"]),
        ]

    def __str__(self):
        return f"{self.entity_type}.{self.field} [{self.locale}]"


class AuditLog(BaseModel):
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="audit_logs",
        null=True,
        blank=True,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="audit_logs",
        null=True,
        blank=True,
    )
    action = models.CharField(max_length=100)
    entity_type = models.CharField(max_length=100)
    entity_id = models.UUIDField(null=True, blank=True)
    old_values = models.JSONField(default=dict, blank=True)
    new_values = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=512, blank=True)
    occurred_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "created_at"]),
            models.Index(fields=["entity_type", "entity_id"]),
        ]

    def __str__(self):
        return f"{self.action} {self.entity_type} @ {self.occurred_at:%Y-%m-%d %H:%M}"


class AccessLog(BaseModel):
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="access_logs",
        null=True,
        blank=True,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="access_logs",
        null=True,
        blank=True,
    )
    entity_type = models.CharField(max_length=100)
    entity_id = models.UUIDField(null=True, blank=True)
    action = models.CharField(max_length=100)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    accessed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-accessed_at"]
        indexes = [
            models.Index(fields=["organization", "accessed_at"]),
        ]

    def __str__(self):
        return f"{self.action} {self.entity_type} @ {self.accessed_at:%Y-%m-%d %H:%M}"
