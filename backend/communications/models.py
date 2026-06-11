<<<<<<< HEAD
from django.db import models

# Create your models here.
=======
"""Communications: message templates, dispatches, consent and notifications."""

from django.conf import settings
from django.db import models

from core.models import BaseModel, Channel


class MessageTemplate(BaseModel):
    class ApprovalStatus(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING = "pending", "Pending Approval"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    organization = models.ForeignKey(
        "organnizations.Organization",
        on_delete=models.CASCADE,
        related_name="message_templates",
    )
    name = models.CharField(max_length=255)
    channel = models.CharField(max_length=20, choices=Channel.choices)
    template_id_external = models.CharField(max_length=255, blank=True)
    content = models.TextField()
    variables = models.JSONField(default=list, blank=True)
    approval_status = models.CharField(
        max_length=20, choices=ApprovalStatus.choices, default=ApprovalStatus.DRAFT
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    rejected_reason = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.get_channel_display()})"


class MessageDispatch(BaseModel):
    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        SENT = "sent", "Sent"
        DELIVERED = "delivered", "Delivered"
        READ = "read", "Read"
        FAILED = "failed", "Failed"

    organization = models.ForeignKey(
        "organnizations.Organization",
        on_delete=models.CASCADE,
        related_name="message_dispatches",
    )
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.SET_NULL,
        related_name="message_dispatches",
        null=True,
        blank=True,
    )
    template = models.ForeignKey(
        MessageTemplate,
        on_delete=models.SET_NULL,
        related_name="dispatches",
        null=True,
        blank=True,
    )
    channel = models.CharField(max_length=20, choices=Channel.choices)
    recipient = models.CharField(max_length=255)
    content = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.QUEUED
    )
    external_message_id = models.CharField(max_length=255, blank=True)
    cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "message dispatches"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "created_at"]),
            models.Index(fields=["organization", "status"]),
        ]

    def __str__(self):
        return f"{self.get_channel_display()} to {self.recipient} ({self.get_status_display()})"


class ConsentRecord(BaseModel):
    class Purpose(models.TextChoices):
        MARKETING = "marketing", "Marketing"
        REMINDERS = "reminders", "Reminders"
        TRANSACTIONAL = "transactional", "Transactional"

    organization = models.ForeignKey(
        "organnizations.Organization",
        on_delete=models.CASCADE,
        related_name="consent_records",
    )
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.CASCADE,
        related_name="consent_records",
    )
    channel = models.CharField(max_length=20, choices=Channel.choices)
    purpose = models.CharField(
        max_length=20, choices=Purpose.choices, default=Purpose.MARKETING
    )
    granted_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    source = models.CharField(max_length=100, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.customer} consent: {self.get_channel_display()}/{self.get_purpose_display()}"


class Notification(BaseModel):
    class NotificationType(models.TextChoices):
        SYSTEM = "system", "System"
        APPOINTMENT = "appointment", "Appointment"
        BOOKING = "booking", "Booking"
        PAYMENT = "payment", "Payment"
        MARKETING = "marketing", "Marketing"
        ALERT = "alert", "Alert"

    organization = models.ForeignKey(
        "organnizations.Organization",
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
        null=True,
        blank=True,
    )
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.CASCADE,
        related_name="notifications",
        null=True,
        blank=True,
    )
    type = models.CharField(
        max_length=20, choices=NotificationType.choices, default=NotificationType.SYSTEM
    )
    channel = models.CharField(
        max_length=20, choices=Channel.choices, default=Channel.IN_APP
    )
    title = models.CharField(max_length=255)
    message = models.TextField(blank=True)
    data = models.JSONField(default=dict, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "read_at"]),
            models.Index(fields=["organization", "created_at"]),
        ]

    def __str__(self):
        return self.title


class NotificationTemplate(BaseModel):
    organization = models.ForeignKey(
        "organnizations.Organization",
        on_delete=models.CASCADE,
        related_name="notification_templates",
    )
    name = models.CharField(max_length=255)
    type = models.CharField(
        max_length=20,
        choices=Notification.NotificationType.choices,
        default=Notification.NotificationType.SYSTEM,
    )
    channel = models.CharField(max_length=20, choices=Channel.choices)
    subject = models.CharField(max_length=255, blank=True)
    body = models.TextField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.get_channel_display()})"
>>>>>>> a3235b4 (feat(db): initialize core relational schema)
