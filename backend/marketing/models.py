<<<<<<< HEAD
from django.db import models

# Create your models here.
=======
"""Marketing: campaigns, promotions and loyalty."""

from django.db import models

from core.models import BaseModel, Channel


class Campaign(BaseModel):
    class CampaignType(models.TextChoices):
        PROMOTIONAL = "promotional", "Promotional"
        TRANSACTIONAL = "transactional", "Transactional"
        REMINDER = "reminder", "Reminder"
        ANNOUNCEMENT = "announcement", "Announcement"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SCHEDULED = "scheduled", "Scheduled"
        SENDING = "sending", "Sending"
        SENT = "sent", "Sent"
        CANCELLED = "cancelled", "Cancelled"

    organization = models.ForeignKey(
        "organnizations.Organization",
        on_delete=models.CASCADE,
        related_name="campaigns",
    )
    name = models.CharField(max_length=255)
    type = models.CharField(
        max_length=20, choices=CampaignType.choices, default=CampaignType.PROMOTIONAL
    )
    channel = models.CharField(max_length=20, choices=Channel.choices)
    subject = models.CharField(max_length=255, blank=True)
    content = models.TextField(blank=True)
    target_audience = models.CharField(max_length=255, blank=True)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "status"]),
        ]

    def __str__(self):
        return self.name


class CampaignRecipient(BaseModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SENT = "sent", "Sent"
        DELIVERED = "delivered", "Delivered"
        OPENED = "opened", "Opened"
        CLICKED = "clicked", "Clicked"
        FAILED = "failed", "Failed"

    campaign = models.ForeignKey(
        Campaign, on_delete=models.CASCADE, related_name="recipients"
    )
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.CASCADE,
        related_name="campaign_receipts",
    )
    sent_at = models.DateTimeField(null=True, blank=True)
    opened_at = models.DateTimeField(null=True, blank=True)
    clicked_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )

    class Meta:
        indexes = [
            models.Index(fields=["campaign", "status"]),
        ]

    def __str__(self):
        return f"{self.campaign} -> {self.customer}"


class Promotion(BaseModel):
    class DiscountType(models.TextChoices):
        PERCENT = "percent", "Percentage"
        FIXED = "fixed", "Fixed Amount"

    organization = models.ForeignKey(
        "organnizations.Organization",
        on_delete=models.CASCADE,
        related_name="promotions",
    )
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, unique=True)
    discount_type = models.CharField(
        max_length=10, choices=DiscountType.choices, default=DiscountType.PERCENT
    )
    discount_value = models.DecimalField(max_digits=12, decimal_places=2)
    min_purchase = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    max_uses = models.PositiveIntegerField(null=True, blank=True)
    used_count = models.PositiveIntegerField(default=0)
    starts_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "is_active"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.code})"


class LoyaltyProgram(BaseModel):
    organization = models.ForeignKey(
        "organnizations.Organization",
        on_delete=models.CASCADE,
        related_name="loyalty_programs",
    )
    name = models.CharField(max_length=255)
    points_per_currency = models.DecimalField(
        max_digits=5, decimal_places=2, default=1
    )
    redemption_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.01)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class LoyaltyTransaction(BaseModel):
    class TransactionType(models.TextChoices):
        EARN = "earn", "Earn"
        REDEEM = "redeem", "Redeem"
        ADJUST = "adjust", "Adjust"
        EXPIRE = "expire", "Expire"

    loyalty_program = models.ForeignKey(
        LoyaltyProgram, on_delete=models.CASCADE, related_name="transactions"
    )
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.CASCADE,
        related_name="loyalty_transactions",
    )
    sale = models.ForeignKey(
        "commerce.Sale",
        on_delete=models.SET_NULL,
        related_name="loyalty_transactions",
        null=True,
        blank=True,
    )
    points = models.IntegerField()
    type = models.CharField(max_length=10, choices=TransactionType.choices)
    description = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["customer", "created_at"]),
        ]

    def __str__(self):
        return f"{self.get_type_display()} {self.points} pts for {self.customer}"
>>>>>>> a3235b4 (feat(db): initialize core relational schema)
