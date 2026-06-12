"""Marketing: campaigns, promotions, loyalty, referrals and lifecycle
journeys."""

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
        "organizations.Organization",
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
        "organizations.Organization",
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
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="loyalty_programs",
    )
    name = models.CharField(max_length=255)
    points_per_currency = models.DecimalField(max_digits=5, decimal_places=2, default=1)
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


# ---------------------------------------------------------------------------
# Referrals
# ---------------------------------------------------------------------------


class ReferralProgram(BaseModel):
    """Dual-sided referral configuration: what the referrer earns and what
    the referee gets, plus the anti-fraud cap per referrer."""

    class RewardType(models.TextChoices):
        LOYALTY_POINTS = "loyalty_points", "Loyalty Points"
        STORE_CREDIT = "store_credit", "Store Credit"

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="referral_programs",
    )
    name = models.CharField(max_length=255)
    referrer_reward_type = models.CharField(
        max_length=20, choices=RewardType.choices, default=RewardType.LOYALTY_POINTS
    )
    referrer_reward_value = models.DecimalField(max_digits=12, decimal_places=2)
    referee_reward_type = models.CharField(
        max_length=20, choices=RewardType.choices, default=RewardType.LOYALTY_POINTS
    )
    referee_reward_value = models.DecimalField(max_digits=12, decimal_places=2)
    #: A referee must spend at least this much before the referral qualifies.
    min_referee_spend = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    max_referrals_per_customer = models.PositiveIntegerField(default=20)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Referral(BaseModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        QUALIFIED = "qualified", "Qualified"
        REWARDED = "rewarded", "Rewarded"
        REJECTED = "rejected", "Rejected"

    program = models.ForeignKey(
        ReferralProgram, on_delete=models.CASCADE, related_name="referrals"
    )
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="referrals",
    )
    referrer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.CASCADE,
        related_name="referrals_made",
    )
    referee = models.ForeignKey(
        "customers.Customer",
        on_delete=models.SET_NULL,
        related_name="referrals_received",
        null=True,
        blank=True,
    )
    code = models.CharField(max_length=20, unique=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    qualified_at = models.DateTimeField(null=True, blank=True)
    rewarded_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["referrer", "status"]),
        ]

    def __str__(self):
        return f"Referral {self.code} ({self.get_status_display()})"


# ---------------------------------------------------------------------------
# Lifecycle journeys
# ---------------------------------------------------------------------------


class Journey(BaseModel):
    """An automated behavioral flow (win-back, abandoned booking, birthday,
    milestone). Steps fire in order with per-step delays; the journey
    runner is a Celery Beat sweep over due enrollments."""

    class TriggerType(models.TextChoices):
        ABANDONED_BOOKING = "abandoned_booking", "Abandoned Booking"
        WIN_BACK = "win_back", "Win-Back"
        BIRTHDAY = "birthday", "Birthday"
        MILESTONE = "milestone", "Milestone"
        CUSTOM = "custom", "Custom"

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="journeys",
    )
    name = models.CharField(max_length=255)
    trigger_type = models.CharField(max_length=30, choices=TriggerType.choices)
    #: Trigger tuning, e.g. {"inactive_days": 60} for win-back.
    trigger_config = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class JourneyStep(BaseModel):
    journey = models.ForeignKey(Journey, on_delete=models.CASCADE, related_name="steps")
    order = models.PositiveIntegerField()
    delay_hours = models.PositiveIntegerField(default=0)
    channel = models.CharField(max_length=20, choices=Channel.choices)
    template = models.ForeignKey(
        "communications.MessageTemplate",
        on_delete=models.PROTECT,
        related_name="journey_steps",
    )

    class Meta:
        ordering = ["journey", "order"]
        constraints = [
            models.UniqueConstraint(
                fields=["journey", "order"], name="uniq_journey_step_order"
            )
        ]

    def __str__(self):
        return f"{self.journey} step {self.order}"
