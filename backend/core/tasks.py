"""Core platform tasks: the PDPL data-retention sweep (audit P1)."""

from celery import shared_task
from celery.utils.log import get_task_logger

from core.retention import sweep_all

logger = get_task_logger(__name__)


@shared_task
def run_retention_sweep_task():
    """Apply every active RetentionPolicy across all tenants.

    Idempotent: deletes are bounded by a ``created_at`` cutoff and anonymise
    updates only touch rows still carrying personal data, so a re-run after a
    crash is safe.
    """
    applied = sweep_all()
    logger.info("Retention sweep applied %s policies.", applied)
    return applied
