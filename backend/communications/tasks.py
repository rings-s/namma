"""Celery tasks for outbound messaging and SES event processing."""

from urllib.parse import urlsplit

import httpx
from celery import shared_task
from celery.utils.log import get_task_logger

from communications.gateways import SESError, TaqnyatError
from communications.models import EmailEvent, MessageDispatch
from communications.services import (
    process_ses_event,
    send_email_dispatch,
    send_sms_dispatch,
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
