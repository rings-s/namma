"""Request-correlation plumbing for structured logging (audit gap V3).

A per-request id is stashed in a context variable so any logger in the call
stack — including Celery's own — can stamp it onto every line without threading
the request through. ``RequestIDMiddleware`` populates it; ``RequestIDFilter``
reads it. This complements, never duplicates, the business-event trail in
:class:`core.models.AuditLog` / :class:`core.models.AccessLog`.
"""

import contextvars
import logging

#: Current request's correlation id; "-" outside a request (shell, beat, tests).
request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default="-"
)


class RequestIDFilter(logging.Filter):
    """Inject ``request_id`` onto every record so formatters can render it."""

    def filter(self, record):
        record.request_id = request_id_var.get()
        return True


__all__ = ["RequestIDFilter", "request_id_var"]
