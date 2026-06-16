"""Celery tasks for the AI workforce.

LLM calls are slow third-party requests, so they never run inside a web request
(per the "third-party calls never block requests" rule): views enqueue these and
return immediately. Transient provider failures (network, 429, 5xx) are retried
with backoff; final errors (bad key/model) are logged and dropped.
"""

from celery import shared_task
from celery.utils.log import get_task_logger

from ai.gateways import AIError
from ai.models import AIConversation
from ai.services import (
    generate_ai_segment,
    generate_assistant_reply,
    generate_recommendations,
)
from communications.models import Notification
from customers.models import CustomerSegment
from organizations.models import Organization

logger = get_task_logger(__name__)


@shared_task(bind=True, max_retries=3)
def generate_assistant_reply_task(self, conversation_id):
    """Answer a conversation by appending an assistant message."""
    conversation = AIConversation.objects.filter(pk=conversation_id).first()
    if conversation is None:
        logger.info("Conversation %s gone; nothing to answer.", conversation_id)
        return
    # Don't double-answer: the latest message must be from the user.
    last = conversation.messages.order_by("-created_at").first()
    if last is None or last.role != last.Role.USER:
        logger.info("Conversation %s has no pending user turn.", conversation_id)
        return
    try:
        generate_assistant_reply(conversation)
    except AIError as exc:
        if exc.retryable:
            raise self.retry(exc=exc, countdown=10 * 2**self.request.retries)
        logger.warning("Assistant reply failed for %s: %s", conversation_id, exc)


@shared_task(bind=True, max_retries=3)
def generate_recommendations_task(self, organization_id):
    """Refresh an organization's AI recommendations from its daily metrics."""
    organization = Organization.objects.filter(pk=organization_id).first()
    if organization is None:
        logger.info("Organization %s gone; skipping recommendations.", organization_id)
        return
    try:
        created = generate_recommendations(organization)
    except AIError as exc:
        if exc.retryable:
            raise self.retry(exc=exc, countdown=10 * 2**self.request.retries)
        logger.warning("Recommendations failed for org %s: %s", organization_id, exc)
        return
    logger.info("Created %d recommendations for org %s", len(created), organization_id)


@shared_task(bind=True, max_retries=3)
def generate_ai_segment_task(self, segment_id):
    """Generate criteria for an AI segment and materialize its membership."""
    segment = CustomerSegment.objects.filter(
        pk=segment_id, segment_type=CustomerSegment.SegmentType.AI
    ).first()
    if segment is None:
        logger.info("AI segment %s gone; nothing to generate.", segment_id)
        return
    try:
        generate_ai_segment(segment)
    except AIError as exc:
        if exc.retryable:
            raise self.retry(exc=exc, countdown=10 * 2**self.request.retries)
        logger.warning("AI segment generation failed for %s: %s", segment_id, exc)


@shared_task
def notify_recommendations_task(event_type=None, payload=None):
    """Subscriber to ``AI_RECOMMENDATIONS_GENERATED``: raise an in-app alert so
    staff see fresh recommendations without polling the dashboard.

    Demonstrates the domain-event seam — the AI engine never imports the
    communications layer; it only publishes, and this consumer reacts.
    """
    payload = payload or {}
    organization_id = payload.get("organization_id")
    count = int(payload.get("count") or 0)
    if not organization_id or count <= 0:
        return
    Notification.objects.create(
        organization_id=organization_id,
        type=Notification.NotificationType.ALERT,
        title=f"{count} new AI recommendation{'s' if count != 1 else ''}",
        message="Open the assistant to review and action the latest insights.",
        data={"source": event_type, "count": count},
    )
