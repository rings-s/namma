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
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="message_templates",
    )
    name = models.CharField(max_length=255)
    channel = models.CharField(max_length=20, choices=Channel.choices)
    template_id_external = models.CharField(max_length=255, blank=True)
    subject = models.CharField(max_length=255, blank=True)
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
        "organizations.Organization",
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
    campaign_recipient = models.ForeignKey(
        "marketing.CampaignRecipient",
        on_delete=models.SET_NULL,
        related_name="dispatches",
        null=True,
        blank=True,
    )
    channel = models.CharField(max_length=20, choices=Channel.choices)
    recipient = models.CharField(max_length=255)
    subject = models.CharField(max_length=255, blank=True)
    content = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.QUEUED
    )
    # Webhook receivers look dispatches up by this on every delivery receipt
    # (3-5x per message); the index keeps that hot path off a full table scan.
    external_message_id = models.CharField(max_length=255, blank=True, db_index=True)
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


class EmailEvent(BaseModel):
    """One SES delivery event (via SNS), stored idempotently on the SNS id.

    Written exclusively by the SES webhook receiver; a worker applies the
    event to the matching dispatch (and its campaign recipient), so the
    receiver itself never touches the messaging domain.
    """

    class ProcessingStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSED = "processed", "Processed"
        IGNORED = "ignored", "Ignored"
        FAILED = "failed", "Failed"

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="email_events",
        null=True,
        blank=True,
    )
    dispatch = models.ForeignKey(
        MessageDispatch,
        on_delete=models.SET_NULL,
        related_name="email_events",
        null=True,
        blank=True,
    )
    sns_message_id = models.CharField(max_length=255, unique=True)
    event_type = models.CharField(max_length=50)
    ses_message_id = models.CharField(max_length=255, blank=True)
    payload = models.JSONField(default=dict, blank=True)
    processing_status = models.CharField(
        max_length=20,
        choices=ProcessingStatus.choices,
        default=ProcessingStatus.PENDING,
    )
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["ses_message_id"]),
        ]

    def __str__(self):
        return f"{self.event_type}:{self.sns_message_id}"


class WhatsAppWebhookEvent(BaseModel):
    """One inbound WhatsApp Cloud API webhook delivery, stored before it is
    applied — mirroring the SES/Moyasar pattern.

    Persisting the raw payload (instead of shipping it through the broker as a
    task argument) keeps the queue small, gives an audit/replay trail, and
    dedupes Meta's at-least-once retries via ``body_signature`` (a hash of the
    exact request body). A worker applies the delivery statuses; application is
    idempotent (timestamps set once, status only moves forward).
    """

    class ProcessingStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSED = "processed", "Processed"
        IGNORED = "ignored", "Ignored"
        FAILED = "failed", "Failed"

    body_signature = models.CharField(max_length=64, unique=True)
    payload = models.JSONField(default=dict, blank=True)
    processing_status = models.CharField(
        max_length=20,
        choices=ProcessingStatus.choices,
        default=ProcessingStatus.PENDING,
    )
    statuses_applied = models.PositiveIntegerField(default=0)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"WhatsApp webhook {self.body_signature[:12]} ({self.processing_status})"


class ConsentRecord(BaseModel):
    class Purpose(models.TextChoices):
        MARKETING = "marketing", "Marketing"
        REMINDERS = "reminders", "Reminders"
        TRANSACTIONAL = "transactional", "Transactional"

    organization = models.ForeignKey(
        "organizations.Organization",
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
        "organizations.Organization",
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
        "organizations.Organization",
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


# ---------------------------------------------------------------------------
# Unified conversation inbox
# ---------------------------------------------------------------------------


class Conversation(BaseModel):
    """One customer thread per channel in the omni-channel inbox, routable
    to branch staff with an explicit status workflow."""

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        ASSIGNED = "assigned", "Assigned"
        RESOLVED = "resolved", "Resolved"
        CLOSED = "closed", "Closed"

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="conversations",
    )
    branch = models.ForeignKey(
        "organizations.Branch",
        on_delete=models.SET_NULL,
        related_name="conversations",
        null=True,
        blank=True,
    )
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.CASCADE,
        related_name="conversations",
    )
    channel = models.CharField(max_length=20, choices=Channel.choices)
    subject = models.CharField(max_length=255, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.OPEN
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="assigned_conversations",
        null=True,
        blank=True,
    )
    last_message_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-last_message_at", "-created_at"]
        indexes = [
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["assigned_to", "status"]),
        ]

    def __str__(self):
        return f"{self.get_channel_display()} thread with {self.customer}"


class ConversationMessage(BaseModel):
    class Direction(models.TextChoices):
        INBOUND = "inbound", "Inbound"
        OUTBOUND = "outbound", "Outbound"

    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="messages"
    )
    direction = models.CharField(max_length=10, choices=Direction.choices)
    body = models.TextField()
    #: Outbound messages sent through a gateway link back to their dispatch
    #: for delivery/cost tracking; inbound and internal notes stay null.
    dispatch = models.ForeignKey(
        MessageDispatch,
        on_delete=models.SET_NULL,
        related_name="conversation_messages",
        null=True,
        blank=True,
    )
    sender_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="conversation_messages",
        null=True,
        blank=True,
    )
    attachments = models.JSONField(default=list, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["conversation", "created_at"]),
        ]

    def __str__(self):
        return f"{self.get_direction_display()} message in {self.conversation}"
