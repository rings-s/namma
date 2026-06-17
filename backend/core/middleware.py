"""Cross-cutting WSGI middleware.

``RequestIDMiddleware`` assigns (or honours an upstream) correlation id for the
request, exposes it as ``request.request_id`` and echoes it in the
``X-Request-ID`` response header, and binds it into the logging context so every
log line emitted while handling the request carries it. See :mod:`core.logging`.
"""

import uuid

from core.logging import request_id_var

#: Trusted only as an opaque label; capped so a hostile upstream cannot inject
#: unbounded data into log lines.
_MAX_REQUEST_ID_LENGTH = 64


class RequestIDMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        incoming = request.META.get("HTTP_X_REQUEST_ID", "").strip()
        request_id = incoming[:_MAX_REQUEST_ID_LENGTH] if incoming else uuid.uuid4().hex
        request.request_id = request_id
        token = request_id_var.set(request_id)
        try:
            response = self.get_response(request)
        finally:
            request_id_var.reset(token)
        response["X-Request-ID"] = request_id
        return response


__all__ = ["RequestIDMiddleware"]
