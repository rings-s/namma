"""Celery tasks for analytics: nightly daily-metric roll-up (audit P1)."""

import datetime as dt

from celery import shared_task
from celery.utils.log import get_task_logger

from analytics.services import roll_up_all_organizations, roll_up_day

logger = get_task_logger(__name__)


@shared_task
def roll_up_daily_metrics_task(day=None):
    """Nightly roll-up across all organizations.

    ``day`` is an optional ISO date string (``YYYY-MM-DD``); when omitted the
    service defaults to yesterday, which is closed in every tenant timezone by
    the time this fires just after midnight. Safe to replay — each write is an
    update_or_create on the metric's unique key.
    """
    parsed = dt.date.fromisoformat(day) if day else None
    processed = roll_up_all_organizations(parsed)
    logger.info("Daily roll-up complete for %s organizations.", processed)
    return processed


@shared_task
def roll_up_organization_day_task(organization_id, day):
    """Back-fill / re-run a single organization's roll-up for one day."""
    roll_up_day(organization_id, dt.date.fromisoformat(day))
    logger.info("Rolled up organization %s for %s.", organization_id, day)
