<<<<<<< HEAD
from django.db import models

# Create your models here.
=======
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


class Branch(BaseModel):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="branches"
    )
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=500, blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
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
>>>>>>> a3235b4 (feat(db): initialize core relational schema)
