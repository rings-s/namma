"""Organizations (tenants), settings, branches and operating hours."""

from django.db import models


from core.models import BaseModel, Weekday


class Organization(BaseModel):
    class TenantTier(models.TextChoices):
        STANDARD = "standard", "Standard"
        PREMIUM = "premium", "Premium"
        ENTERPRISE = "enterprise", "Enterprise"

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    industry = models.CharField(max_length=100, blank=True)
    logo_url = models.URLField(blank=True)
    website = models.URLField(blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=32, blank=True)
    timezone = models.CharField(max_length=64, default="Asia/Riyadh")
    currency = models.CharField(max_length=3, default="SAR")
    # ZATCA seller identity: every e-invoice must carry the legal VAT
    # registration (15 digits, starts/ends with 3), the CR number and the
    # national address. Kept on the organization — one legal identity per
    # tenant; branch-level addresses can be layered on later if a tenant
    # registers branches as separate ZATCA units.
    vat_number = models.CharField(max_length=15, blank=True)
    commercial_registration_number = models.CharField(max_length=20, blank=True)
    street_name = models.CharField(max_length=255, blank=True)
    building_number = models.CharField(max_length=4, blank=True)
    district = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=5, blank=True)
    is_active = models.BooleanField(default=True)
    tenant_tier = models.CharField(
        max_length=20, choices=TenantTier.choices, default=TenantTier.STANDARD
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def active_subscription(self):
        """Latest trialing/active subscription. Replaces the circular
        ``organizations.subscription_id`` FK from the design diagram."""
        return (
            self.subscriptions.filter(status__in=("trialing", "active"))
            .order_by("-created_at")
            .first()
        )


class OrganizationSettings(BaseModel):
    organization = models.OneToOneField(
        Organization, on_delete=models.CASCADE, related_name="settings"
    )
    booking_lead_time = models.PositiveIntegerField(
        default=0, help_text="Minimum lead time in minutes before a booking."
    )
    cancellation_policy = models.TextField(blank=True)
    auto_confirm_bookings = models.BooleanField(default=False)
    reminder_hours = models.PositiveIntegerField(default=24)

    class Meta:
        verbose_name_plural = "organization settings"

    def __str__(self):
        return f"Settings for {self.organization}"


class RetentionPolicy(BaseModel):
    """Per-tenant data retention configuration (PDPL §5.17).

    A worker sweeps expired rows per policy; financial/compliance records
    (invoices, ledgers, ZATCA documents) are deliberately not configurable —
    their retention is statutory, not tenant preference.
    """

    class EntityType(models.TextChoices):
        ANALYTICS_EVENTS = "analytics_events", "Analytics Events"
        AUDIT_LOGS = "audit_logs", "Audit Logs"
        ACCESS_LOGS = "access_logs", "Access Logs"
        MESSAGE_DISPATCHES = "message_dispatches", "Message Dispatches"
        NOTIFICATIONS = "notifications", "Notifications"
        IDEMPOTENCY_RECORDS = "idempotency_records", "Idempotency Records"
        SLOT_HOLDS = "slot_holds", "Slot Holds"

    class Action(models.TextChoices):
        DELETE = "delete", "Delete"
        ANONYMIZE = "anonymize", "Anonymize"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="retention_policies"
    )
    entity_type = models.CharField(max_length=50, choices=EntityType.choices)
    retention_days = models.PositiveIntegerField()
    action = models.CharField(
        max_length=20, choices=Action.choices, default=Action.DELETE
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "retention policies"
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "entity_type"],
                name="uniq_retention_policy_per_entity",
            )
        ]

    def __str__(self):
        return f"{self.get_entity_type_display()}: {self.retention_days}d"


class Branch(BaseModel):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="branches"
    )
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=500, blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    phone = models.CharField(max_length=32, blank=True)
    email = models.EmailField(blank=True)
    is_active = models.BooleanField(default=True)
    timezone = models.CharField(max_length=64, default="Asia/Riyadh")
    hijri_display_preference = models.BooleanField(default=False)
    ramadan_hours_override = models.JSONField(default=dict, blank=True)
    quiet_hours_start = models.TimeField(null=True, blank=True)
    quiet_hours_end = models.TimeField(null=True, blank=True)
    prayer_time_blocking = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = "branches"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["organization", "is_active"]),
        ]

    def __str__(self):
        return f"{self.organization} / {self.name}"


class BranchHour(BaseModel):
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="hours")
    day_of_week = models.PositiveSmallIntegerField(choices=Weekday.choices)
    open_time = models.TimeField(null=True, blank=True)
    close_time = models.TimeField(null=True, blank=True)
    is_closed = models.BooleanField(default=False)

    class Meta:
        ordering = ["day_of_week"]
        constraints = [
            models.UniqueConstraint(
                fields=["branch", "day_of_week"], name="uniq_branch_hour_per_day"
            )
        ]

    def __str__(self):
        return f"{self.branch} - {self.get_day_of_week_display()}"
