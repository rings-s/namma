"""AI assistant: conversations, messages and recommendations."""

from django.conf import settings
from django.db import models

from core.models import BaseModel


class AIProvenanceMixin(models.Model):
    """Provenance for any row produced by an LLM call.

    Captured at write time from the gateway's ``ChatResult`` so AI output stays
    auditable as providers and models change underneath us: incident review can
    tell which model/prompt produced a row, and cost/latency can be reported per
    tenant. Typed columns (not a JSON blob) so they stay queryable and indexable.
    Non-AI rows (e.g. a user's own chat turn) simply leave these at their
    defaults.
    """

    ai_provider = models.CharField(max_length=50, blank=True)
    ai_model = models.CharField(max_length=120, blank=True)
    #: Bumped in code whenever a system prompt changes materially, so a regression
    #: in output quality can be traced to the prompt revision that caused it.
    prompt_version = models.CharField(max_length=50, blank=True)
    prompt_tokens = models.PositiveIntegerField(default=0)
    completion_tokens = models.PositiveIntegerField(default=0)
    latency_ms = models.PositiveIntegerField(default=0)
    temperature = models.DecimalField(
        max_digits=3, decimal_places=2, null=True, blank=True
    )
    #: Provider-billed cost in SAR-equivalent; 0 for free/local runtimes.
    cost = models.DecimalField(max_digits=12, decimal_places=6, default=0)
    #: Optional model- or heuristic-reported confidence (0.000–1.000).
    confidence = models.DecimalField(
        max_digits=4, decimal_places=3, null=True, blank=True
    )

    class Meta:
        abstract = True


class AIConversation(BaseModel):
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="ai_conversations",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ai_conversations",
    )
    title = models.CharField(max_length=255, blank=True)
    context = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return self.title or f"Conversation {self.id}"


class AIMessage(AIProvenanceMixin, BaseModel):
    class Role(models.TextChoices):
        SYSTEM = "system", "System"
        USER = "user", "User"
        ASSISTANT = "assistant", "Assistant"
        TOOL = "tool", "Tool"

    conversation = models.ForeignKey(
        AIConversation, on_delete=models.CASCADE, related_name="messages"
    )
    role = models.CharField(max_length=10, choices=Role.choices)
    content = models.TextField()
    tokens_used = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.get_role_display()} message in {self.conversation_id}"


class AIRecommendation(AIProvenanceMixin, BaseModel):
    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        DISMISSED = "dismissed", "Dismissed"
        ACTIONED = "actioned", "Actioned"

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="ai_recommendations",
    )
    type = models.CharField(max_length=100)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    priority = models.CharField(
        max_length=10, choices=Priority.choices, default=Priority.MEDIUM
    )
    data = models.JSONField(default=dict, blank=True)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.ACTIVE
    )
    dismissed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "status"]),
        ]
        constraints = [
            # Makes generate_recommendations' get_or_create genuinely
            # idempotent: a concurrent manual + scheduled refresh can't insert
            # the same active recommendation twice.
            models.UniqueConstraint(
                fields=["organization", "title", "status"],
                name="uniq_active_recommendation_per_title",
            ),
        ]

    def __str__(self):
        return self.title
