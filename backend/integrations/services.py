"""Integrations services: API key issuance and the webhook outbox.

API keys follow the issue-once pattern: the plaintext is returned a single
time at creation; only a prefix (lookup handle) and a SHA-256 hash persist.

Webhook fan-out is a transactional outbox: ``publish_event`` appends the
event and its per-endpoint delivery rows inside the caller's transaction;
the Celery dispatcher delivers after commit with HMAC-SHA256 signatures
(``X-Namaa-Signature``) and exponential-backoff retries.
"""

import hashlib
import hmac
import json
import secrets

from django.db import transaction
from django.utils import timezone

from core.crypto import decrypt_secret, encrypt_secret
from integrations.models import (
    APIKey,
    OutboundEvent,
    WebhookDelivery,
    WebhookEndpoint,
)

#: After this many failed attempts a delivery is dead — operators replay
#: dead deliveries explicitly instead of hammering a broken endpoint.
MAX_DELIVERY_ATTEMPTS = 8


def hash_key(plaintext):
    return hashlib.sha256(plaintext.encode()).hexdigest()


def issue_api_key(organization, name, scopes=None, expires_at=None):
    """Create an API key; returns (instance, plaintext). The plaintext is
    shown once and never recoverable afterwards."""
    plaintext = f"nmk_{secrets.token_urlsafe(32)}"
    api_key = APIKey.objects.create(
        organization=organization,
        name=name,
        key_prefix=plaintext[:8],
        key_hash=hash_key(plaintext),
        scopes=scopes or [],
        expires_at=expires_at,
    )
    return api_key, plaintext


def provision_webhook_endpoint(endpoint):
    """Mint the endpoint's signing secret; returns the plaintext once."""
    plaintext = secrets.token_urlsafe(32)
    endpoint.secret_hash = hash_key(plaintext)
    endpoint.signing_secret_encrypted = encrypt_secret(plaintext)
    endpoint.save(
        update_fields=["secret_hash", "signing_secret_encrypted", "updated_at"]
    )
    return plaintext


def publish_event(organization, event_type, payload):
    """Append an outbox event and a delivery row per subscribed endpoint.
    Call inside the domain transaction; dispatch happens after commit."""
    event = OutboundEvent.objects.create(
        organization=organization, event_type=event_type, payload=payload
    )
    endpoints = WebhookEndpoint.objects.filter(
        organization=organization, is_active=True
    )
    deliveries = [
        WebhookDelivery(endpoint=endpoint, event=event)
        for endpoint in endpoints
        if not endpoint.events or event_type in endpoint.events
    ]
    WebhookDelivery.objects.bulk_create(deliveries)
    event.dispatched_at = timezone.now()
    event.save(update_fields=["dispatched_at", "updated_at"])

    def enqueue():
        from integrations.tasks import deliver_webhook_task

        for delivery in deliveries:
            deliver_webhook_task.delay(str(delivery.pk))

    transaction.on_commit(enqueue)
    return event


def sign_payload(endpoint, body_bytes):
    secret = decrypt_secret(endpoint.signing_secret_encrypted)
    return hmac.new(secret.encode(), body_bytes, hashlib.sha256).hexdigest()


def attempt_delivery(delivery, transport=None):
    """One delivery attempt. Returns True when delivered; on failure marks
    the row failed (retryable) or dead and returns False."""
    import httpx

    endpoint = delivery.endpoint
    body = json.dumps(
        {
            "id": str(delivery.event_id),
            "type": delivery.event.event_type,
            "created_at": delivery.event.created_at.isoformat(),
            "data": delivery.event.payload,
        },
        default=str,
    ).encode()
    headers = {
        "Content-Type": "application/json",
        "X-Namaa-Event": delivery.event.event_type,
        "X-Namaa-Delivery": str(delivery.pk),
        "X-Namaa-Signature": f"sha256={sign_payload(endpoint, body)}",
    }
    delivery.attempt_count += 1
    try:
        with httpx.Client(timeout=10.0, transport=transport) as client:
            response = client.post(endpoint.url, content=body, headers=headers)
        delivery.last_status_code = response.status_code
        succeeded = response.is_success
        delivery.last_error = "" if succeeded else f"HTTP {response.status_code}"
    except httpx.HTTPError as exc:
        delivery.last_status_code = None
        delivery.last_error = str(exc)[:500]
        succeeded = False

    if succeeded:
        delivery.status = WebhookDelivery.Status.DELIVERED
        delivery.delivered_at = timezone.now()
        WebhookEndpoint.objects.filter(pk=endpoint.pk).update(
            last_triggered_at=timezone.now()
        )
    elif delivery.attempt_count >= MAX_DELIVERY_ATTEMPTS:
        delivery.status = WebhookDelivery.Status.DEAD
    else:
        delivery.status = WebhookDelivery.Status.FAILED
    delivery.save(
        update_fields=[
            "attempt_count",
            "last_status_code",
            "last_error",
            "status",
            "delivered_at",
            "updated_at",
        ]
    )
    return succeeded


__all__ = [
    "attempt_delivery",
    "hash_key",
    "issue_api_key",
    "provision_webhook_endpoint",
    "publish_event",
    "sign_payload",
]
