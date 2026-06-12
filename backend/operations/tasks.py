"""Celery tasks for operations: commission calculation off the request path."""

from celery import shared_task
from celery.utils.log import get_task_logger
from django.core.exceptions import ValidationError

from operations.services import calculate_sale_commissions

logger = get_task_logger(__name__)


@shared_task
def calculate_sale_commissions_task(sale_id):
    """Compute commission entries for one completed sale. Idempotent —
    the service refuses to double-write a sale's commissions."""
    from commerce.models import Sale

    sale = (
        Sale.objects.select_related("employee", "organization")
        .filter(pk=sale_id)
        .first()
    )
    if sale is None:
        logger.info("Sale %s gone.", sale_id)
        return
    try:
        entries = calculate_sale_commissions(sale)
    except ValidationError as exc:
        logger.warning("Sale %s not commissionable: %s", sale_id, exc)
        return
    logger.info("Sale %s: %d commission entries written.", sale_id, len(entries))
