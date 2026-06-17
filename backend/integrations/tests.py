"""Webhook outbox, signed delivery and API key issuance/auth tests."""

import hashlib
import hmac
import json
from datetime import timedelta
from decimal import Decimal

import httpx
from cryptography.fernet import Fernet
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import UserRole
from commerce.models import Service
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
    issue_api_key,
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


class APIKeyAuthenticationTests(APITestCase):
    """The verification side of the API-key surface (audit gap V4)."""

    @classmethod
    def setUpTestData(cls):
        cls.org = Organization.objects.create(name="KeyAuth", slug="key-auth")
        cls.other_org = Organization.objects.create(name="Other", slug="other-key")
        cls.svc = Service.objects.create(
            organization=cls.org, name="Haircut", price=Decimal("50")
        )
        Service.objects.create(
            organization=cls.other_org, name="Massage", price=Decimal("120")
        )
        cls.api_key, cls.plaintext = issue_api_key(cls.org, "Integration")

    def test_valid_key_authenticates_and_is_scoped_to_its_org(self):
        response = self.client.get("/api/v1/services/", HTTP_X_API_KEY=self.plaintext)
        self.assertEqual(response.status_code, 200, response.data)
        names = {row["name"] for row in response.data["results"]}
        self.assertEqual(names, {"Haircut"})  # never the other org's service

    def test_authorization_api_key_scheme_also_works(self):
        response = self.client.get(
            "/api/v1/services/", HTTP_AUTHORIZATION=f"Api-Key {self.plaintext}"
        )
        self.assertEqual(response.status_code, 200, response.data)

    def test_missing_credential_is_unauthorized(self):
        self.assertEqual(self.client.get("/api/v1/services/").status_code, 401)

    def test_invalid_key_is_rejected(self):
        response = self.client.get(
            "/api/v1/services/", HTTP_X_API_KEY="nmk_deadbeefdeadbeef"
        )
        self.assertEqual(response.status_code, 401)

    def test_expired_key_is_rejected(self):
        self.api_key.expires_at = timezone.now() - timedelta(minutes=1)
        self.api_key.save(update_fields=["expires_at"])
        response = self.client.get("/api/v1/services/", HTTP_X_API_KEY=self.plaintext)
        self.assertEqual(response.status_code, 401)

    def test_inactive_key_is_rejected(self):
        self.api_key.is_active = False
        self.api_key.save(update_fields=["is_active"])
        response = self.client.get("/api/v1/services/", HTTP_X_API_KEY=self.plaintext)
        self.assertEqual(response.status_code, 401)

    def test_last_used_at_is_recorded_on_use(self):
        self.assertIsNone(self.api_key.last_used_at)
        self.client.get("/api/v1/services/", HTTP_X_API_KEY=self.plaintext)
        self.api_key.refresh_from_db()
        self.assertIsNotNone(self.api_key.last_used_at)

    def test_key_principal_holds_no_role_so_role_gated_actions_denied(self):
        # Issuing a key requires Admin; an API-key principal has rank 0.
        response = self.client.post(
            "/api/v1/api-keys/",
            {"organization": str(self.org.id), "name": "Nope"},
            format="json",
            HTTP_X_API_KEY=self.plaintext,
        )
        self.assertEqual(response.status_code, 403)
