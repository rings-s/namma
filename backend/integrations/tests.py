"""Webhook outbox, signed delivery and API key issuance tests."""

import hashlib
import hmac
import json

import httpx
from cryptography.fernet import Fernet
from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APITestCase

from accounts.models import UserRole
from integrations.models import (
    APIKey,
    OutboundEvent,
    WebhookDelivery,
    WebhookEndpoint,
)
from integrations.services import (
    MAX_DELIVERY_ATTEMPTS,
    attempt_delivery,
    hash_key,
    provision_webhook_endpoint,
    publish_event,
)
from organizations.models import Organization

User = get_user_model()

FERNET_KEY = Fernet.generate_key().decode()


@override_settings(ZATCA_KEY_ENCRYPTION_KEY=FERNET_KEY)
class WebhookOutboxTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org = Organization.objects.create(name="Hooked", slug="hooked")
        cls.endpoint = WebhookEndpoint.objects.create(
            organization=cls.org,
            url="https://example.sa/hooks",
            secret_hash="x",
            events=["invoice.paid"],
        )

    def setUp(self):
        provision_webhook_endpoint(self.endpoint)

    def test_publish_fans_out_to_subscribed_endpoints_only(self):
        other = WebhookEndpoint.objects.create(
            organization=self.org,
            url="https://example.sa/other",
            secret_hash="y",
            events=["customer.created"],  # not subscribed to invoice.paid
        )
        catch_all = WebhookEndpoint.objects.create(
            organization=self.org,
            url="https://example.sa/all",
            secret_hash="z",
            events=[],  # empty = everything
        )
        event = publish_event(self.org, "invoice.paid", {"invoice": "INV-1"})
        endpoints = set(
            WebhookDelivery.objects.filter(event=event).values_list(
                "endpoint_id", flat=True
            )
        )
        self.assertEqual(endpoints, {self.endpoint.pk, catch_all.pk})
        self.assertNotIn(other.pk, endpoints)
        self.assertIsNotNone(OutboundEvent.objects.get(pk=event.pk).dispatched_at)

    def test_delivery_is_signed_and_marked_delivered(self):
        event = publish_event(self.org, "invoice.paid", {"invoice": "INV-1"})
        delivery = WebhookDelivery.objects.get(event=event, endpoint=self.endpoint)
        captured = {}

        def handler(request):
            captured["headers"] = dict(request.headers)
            captured["body"] = request.content
            return httpx.Response(200)

        ok = attempt_delivery(delivery, transport=httpx.MockTransport(handler))
        self.assertTrue(ok)
        delivery.refresh_from_db()
        self.endpoint.refresh_from_db()
        self.assertEqual(delivery.status, WebhookDelivery.Status.DELIVERED)
        self.assertEqual(delivery.attempt_count, 1)
        self.assertIsNotNone(self.endpoint.last_triggered_at)
        # The receiver can verify the HMAC with the secret it was handed.
        from core.crypto import decrypt_secret

        secret = decrypt_secret(self.endpoint.signing_secret_encrypted)
        expected = hmac.new(
            secret.encode(), captured["body"], hashlib.sha256
        ).hexdigest()
        self.assertEqual(captured["headers"]["x-namaa-signature"], f"sha256={expected}")
        self.assertEqual(json.loads(captured["body"])["type"], "invoice.paid")

    def test_failures_retry_then_go_dead(self):
        event = publish_event(self.org, "invoice.paid", {})
        delivery = WebhookDelivery.objects.get(event=event, endpoint=self.endpoint)

        def failing(request):
            return httpx.Response(500)

        ok = attempt_delivery(delivery, transport=httpx.MockTransport(failing))
        self.assertFalse(ok)
        delivery.refresh_from_db()
        self.assertEqual(delivery.status, WebhookDelivery.Status.FAILED)
        self.assertEqual(delivery.last_status_code, 500)

        delivery.attempt_count = MAX_DELIVERY_ATTEMPTS - 1
        delivery.save(update_fields=["attempt_count"])
        attempt_delivery(delivery, transport=httpx.MockTransport(failing))
        delivery.refresh_from_db()
        self.assertEqual(delivery.status, WebhookDelivery.Status.DEAD)


@override_settings(ZATCA_KEY_ENCRYPTION_KEY=FERNET_KEY)
class APIKeyIssuanceTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org = Organization.objects.create(name="Keyed", slug="keyed")
        cls.owner = User.objects.create_user(
            email="keys-owner@namaa.sa", password="pass12345"
        )
        UserRole.objects.create(
            user=cls.owner, organization=cls.org, role=UserRole.Role.OWNER
        )
        cls.staff = User.objects.create_user(
            email="keys-staff@namaa.sa", password="pass12345"
        )
        UserRole.objects.create(
            user=cls.staff, organization=cls.org, role=UserRole.Role.STAFF
        )

    def test_plaintext_returned_once_and_only_hash_stored(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post(
            "/api/v1/api-keys/",
            {"organization": str(self.org.id), "name": "Zapier"},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        plaintext = response.data["key"]
        self.assertTrue(plaintext.startswith("nmk_"))
        api_key = APIKey.objects.get(name="Zapier")
        self.assertEqual(api_key.key_hash, hash_key(plaintext))
        self.assertEqual(api_key.key_prefix, plaintext[:8])
        # Subsequent reads never expose the key or its hash.
        detail = self.client.get(f"/api/v1/api-keys/{api_key.id}/")
        self.assertNotIn("key", detail.data)
        self.assertNotIn("key_hash", detail.data)

    def test_staff_cannot_issue_keys(self):
        self.client.force_authenticate(self.staff)
        response = self.client.post(
            "/api/v1/api-keys/",
            {"organization": str(self.org.id), "name": "Nope"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_endpoint_creation_returns_signing_secret_once(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post(
            "/api/v1/webhook-endpoints/",
            {
                "organization": str(self.org.id),
                "url": "https://example.sa/hooks",
                "events": ["invoice.paid"],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        secret = response.data["signing_secret"]
        endpoint = WebhookEndpoint.objects.get(url="https://example.sa/hooks")
        self.assertEqual(endpoint.secret_hash, hash_key(secret))
        detail = self.client.get(f"/api/v1/webhook-endpoints/{endpoint.id}/")
        self.assertNotIn("signing_secret", detail.data)
        self.assertNotIn("secret_hash", detail.data)
