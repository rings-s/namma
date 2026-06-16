"""Celery tasks for outbound messaging and SES event processing."""

from urllib.parse import urlsplit

import httpx
from celery import shared_task
from celery.utils.log import get_task_logger

from communications.gateways import SESError, TaqnyatError, WhatsAppError
from communications.models import EmailEvent, MessageDispatch
from communications.services import (
    process_ses_event,
    process_whatsapp_webhook,
    send_email_dispatch,
    send_sms_dispatch,
    send_whatsapp_dispatch,
)

logger = get_task_logger(__name__)


@shared_task(bind=True, max_retries=3)
def send_sms_dispatch_task(self, dispatch_id):
    """Send one queued SMS dispatch; retries transport-level failures."""
    dispatch = MessageDispatch.objects.filter(
        pk=dispatch_id, status=MessageDispatch.Status.QUEUED
    ).first()
    if dispatch is None:
        logger.info("Dispatch %s gone or no longer queued; nothing to do.", dispatch_id)
        return
    try:
        send_sms_dispatch(dispatch)
    except TaqnyatError as exc:
        if exc.status_code is None:
            # Network problem: the row is still queued, retry with backoff.
            raise self.retry(exc=exc, countdown=30 * 2**self.request.retries)
        logger.warning("Dispatch %s rejected by Taqnyat: %s", dispatch_id, exc)


@shared_task(bind=True, max_retries=3)
def send_whatsapp_dispatch_task(self, dispatch_id):
    """Send one queued WhatsApp dispatch; retries transient Cloud API failures."""
    dispatch = MessageDispatch.objects.filter(
        pk=dispatch_id, status=MessageDispatch.Status.QUEUED
    ).first()
    if dispatch is None:
        logger.info("Dispatch %s gone or no longer queued; nothing to do.", dispatch_id)
        return
    try:
        send_whatsapp_dispatch(dispatch)
    except WhatsAppError as exc:
        if exc.retryable:
            # Network/throttle problem: row is still queued, back off.
            raise self.retry(exc=exc, countdown=30 * 2**self.request.retries)
        logger.warning("Dispatch %s rejected by WhatsApp: %s", dispatch_id, exc)


@shared_task(bind=True, max_retries=3)
def process_whatsapp_webhook_task(self, event_id):
    """Apply delivery statuses from one stored WhatsApp webhook event.

    Loads the persisted payload by id (never carries it through the broker),
    applies statuses idempotently, and records the outcome. Retries on
    transient failure; dead-letters as FAILED once retries are exhausted so the
    recovery path (or an operator) can replay it.
    """
    from django.utils import timezone

    from communications.models import WhatsAppWebhookEvent

    event = (
        WhatsAppWebhookEvent.objects.filter(pk=event_id)
        .exclude(
            processing_status__in=(
                WhatsAppWebhookEvent.ProcessingStatus.PROCESSED,
                WhatsAppWebhookEvent.ProcessingStatus.IGNORED,
            )
        )
        .first()
    )
    if event is None:
        logger.info("WhatsApp event %s gone or already handled.", event_id)
        return
    try:
        applied = process_whatsapp_webhook(event.payload)
    except Exception as exc:
        if self.request.retries >= self.max_retries:
            WhatsAppWebhookEvent.objects.filter(pk=event.pk).update(
                processing_status=WhatsAppWebhookEvent.ProcessingStatus.FAILED,
                processed_at=timezone.now(),
            )
            logger.exception("WhatsApp event %s dead-lettered: %s", event_id, exc)
            raise
        raise self.retry(exc=exc, countdown=30 * 2**self.request.retries)
    event.statuses_applied = applied
    event.processing_status = (
        WhatsAppWebhookEvent.ProcessingStatus.PROCESSED
        if applied
        else WhatsAppWebhookEvent.ProcessingStatus.IGNORED
    )
    event.processed_at = timezone.now()
    event.save(
        update_fields=[
            "statuses_applied",
            "processing_status",
            "processed_at",
            "updated_at",
        ]
    )
    logger.info("Applied %d WhatsApp delivery statuses.", applied)


@shared_task(bind=True, max_retries=3)
def send_email_dispatch_task(self, dispatch_id):
    """Send one queued email dispatch; retries transient SES failures."""
    dispatch = MessageDispatch.objects.filter(
        pk=dispatch_id, status=MessageDispatch.Status.QUEUED
    ).first()
    if dispatch is None:
        logger.info("Dispatch %s gone or no longer queued; nothing to do.", dispatch_id)
        return
    try:
        send_email_dispatch(dispatch)
    except SESError as exc:
        if exc.retryable:
            # Throttling/network problem: row is still queued, back off.
            raise self.retry(exc=exc, countdown=30 * 2**self.request.retries)
        logger.warning("Dispatch %s rejected by SES: %s", dispatch_id, exc)


@shared_task(bind=True, max_retries=3)
def process_ses_event_task(self, event_id):
    """Apply one stored SES event to its dispatch/recipient/consent state."""
    event = EmailEvent.objects.filter(
        pk=event_id, processing_status=EmailEvent.ProcessingStatus.PENDING
    ).first()
    if event is None:
        logger.info("Event %s gone or already processed; nothing to do.", event_id)
        return
    try:
        process_ses_event(event)
    except Exception as exc:
        if self.request.retries >= self.max_retries:
            event.processing_status = EmailEvent.ProcessingStatus.FAILED
            event.save(update_fields=["processing_status", "updated_at"])
            raise
        raise self.retry(exc=exc, countdown=30 * 2**self.request.retries)


@shared_task
def reprocess_stuck_ses_events(older_than_minutes=10, limit=500):
    """Recovery sweep: re-enqueue SES events still PENDING or dead-lettered
    FAILED after ``older_than_minutes``. ``process_ses_event`` is idempotent
    (it re-converges dispatch/recipient state), so replay is safe; run this
    periodically so a transient outage never strands a delivery/bounce event."""
    from django.utils import timezone

    cutoff = timezone.now() - timezone.timedelta(minutes=older_than_minutes)
    stuck = list(
        EmailEvent.objects.filter(
            processing_status__in=(
                EmailEvent.ProcessingStatus.PENDING,
                EmailEvent.ProcessingStatus.FAILED,
            ),
            created_at__lte=cutoff,
        ).values_list("pk", flat=True)[:limit]
    )
    for pk in stuck:
        process_ses_event_task.delay(str(pk))
    if stuck:
        logger.info("Re-enqueued %d stuck SES events.", len(stuck))
    return len(stuck)


@shared_task(bind=True, max_retries=5)
def confirm_sns_subscription_task(self, subscribe_url):
    """Confirm an SNS topic subscription by visiting its SubscribeURL.

    Runs on a worker so the webhook request never blocks on AWS, and only
    follows HTTPS URLs on amazonaws.com — the URL arrives in an unsigned
    request body, so it is never trusted blindly (SSRF guard).
    """
    parts = urlsplit(subscribe_url)
    hostname = parts.hostname or ""
    if parts.scheme != "https" or not (
        hostname == "amazonaws.com" or hostname.endswith(".amazonaws.com")
    ):
        logger.warning("Refusing non-AWS SubscribeURL: %s", subscribe_url)
        return
    try:
        response = httpx.get(subscribe_url, timeout=10.0)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise self.retry(exc=exc, countdown=30 * 2**self.request.retries)
    logger.info("Confirmed SNS subscription via %s", parts.path)
