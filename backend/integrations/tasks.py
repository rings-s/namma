"""Celery tasks for integrations: webhook delivery with backoff."""

from celery import shared_task
from celery.utils.log import get_task_logger

from integrations.models import WebhookDelivery
from integrations.services import attempt_delivery

logger = get_task_logger(__name__)


@shared_task(bind=True, max_retries=7)
def deliver_webhook_task(self, delivery_id):
    """Deliver one webhook. Failed attempts retry with exponential backoff
    until the service marks the delivery dead; delivered/dead rows are
    terminal and never retried."""
    delivery = (
        WebhookDelivery.objects.select_related("endpoint", "event")
        .filter(
            pk=delivery_id,
            status__in=(
                WebhookDelivery.Status.PENDING,
                WebhookDelivery.Status.FAILED,
            ),
        )
        .first()
    )
    if delivery is None:
        logger.info("Webhook delivery %s gone or terminal.", delivery_id)
        return
    if attempt_delivery(delivery):
        return
    if delivery.status == WebhookDelivery.Status.FAILED:
        raise self.retry(countdown=min(30 * 2**self.request.retries, 3600))
    logger.error("Webhook delivery %s is dead after retries.", delivery_id)
