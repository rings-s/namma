"""In-process domain-event seam.

A deliberate, *explicit* alternative to Django signals (which this platform
avoids — see :mod:`core.audit`): a producing service calls :func:`publish` at a
known point in its flow, and subscribers are Celery tasks registered up-front in
an app's ``AppConfig.ready``. Nothing magical fires on ``save``.

Two guarantees, matching patterns already used elsewhere in the codebase:

* **Commit-safe.** Events are dispatched via ``transaction.on_commit``, so a
  subscriber can never react to a mutation that was rolled back — the same
  promise :class:`integrations.models.OutboundEvent` gives external webhooks,
  applied here to internal cross-app reactions.
* **Non-blocking.** Subscribers run as Celery tasks (``task.delay``), never
  inline, so publishing never adds latency to the request — in line with the
  rule that third-party/heavy work is always async.

This is the seam, not a full rewrite of existing wiring: adopt it producer by
producer. Reference adoption: ``ai.services.generate_recommendations`` publishes
:attr:`DomainEvent.AI_RECOMMENDATIONS_GENERATED`, consumed by
``ai.tasks.notify_recommendations_task``.

Usage
-----
Register a subscriber in an ``AppConfig.ready`` (runs once at startup)::

    from core.events import DomainEvent, subscribe
    from myapp.tasks import handle_it
    subscribe(DomainEvent.SOMETHING_HAPPENED, handle_it)

Publish from the producing service (ideally inside its transaction)::

    from core.events import DomainEvent, publish
    publish(DomainEvent.SOMETHING_HAPPENED, {"organization_id": str(org.id)})

Each subscriber task is called as ``task.delay(event_type=<str>, payload=<dict>)``,
so handlers take ``(self, event_type=None, payload=None)``. The payload crosses
the broker, so it must be JSON-serializable — pass ids, not model instances.
"""

import logging
from collections import defaultdict

from django.db import models, transaction

logger = logging.getLogger(__name__)


class DomainEvent(models.TextChoices):
    """The catalogue of internal events. Values are stable dotted slugs so they
    survive on the broker and in logs; add new members as producers adopt them."""

    AI_RECOMMENDATIONS_GENERATED = (
        "ai.recommendations_generated",
        "AI recommendations generated",
    )


#: event slug -> list of Celery tasks. Module-level so registration in
#: AppConfig.ready persists for the process's lifetime.
_subscribers: dict[str, list] = defaultdict(list)


def subscribe(event_type, task) -> None:
    """Register a Celery ``task`` as a subscriber to ``event_type``.

    Idempotent: re-registering the same task is a no-op, so an ``AppConfig.ready``
    that runs more than once (autoreload, test setup) cannot create duplicate
    deliveries.
    """
    event_type = str(event_type)
    if task not in _subscribers[event_type]:
        _subscribers[event_type].append(task)


def clear_subscribers() -> None:
    """Drop all registrations. Test-only — production registers once at startup."""
    _subscribers.clear()


def publish(event_type, payload: dict | None = None) -> None:
    """Fan ``event_type`` out to its subscribers after the current transaction
    commits.

    A no-op when nothing subscribes. Enqueue failures are logged, never raised:
    a broker hiccup must not roll back or break the producing service.
    """
    event_type = str(event_type)
    payload = payload or {}
    tasks = list(_subscribers.get(event_type, ()))
    if not tasks:
        return

    def _dispatch() -> None:
        for task in tasks:
            try:
                task.delay(event_type=event_type, payload=payload)
            except Exception:
                logger.exception(
                    "Failed to enqueue %s for domain event %s", task, event_type
                )

    transaction.on_commit(_dispatch)


__all__ = ["DomainEvent", "clear_subscribers", "publish", "subscribe"]
