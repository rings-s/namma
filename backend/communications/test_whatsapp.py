"""WhatsApp Cloud API gateway: send contract, signature verification, delivery
receipts and the webhook receiver. The provider is faked with
``httpx.MockTransport`` so nothing hits the network or needs a real token.
"""

import hashlib
import hmac
import json

import httpx
from django.test import override_settings
from rest_framework.test import APITestCase

from communications.gateways import (
    WhatsAppCloudClient,
    WhatsAppError,
    verify_whatsapp_signature,
)
from communications.models import MessageDispatch
from communications.services import (
    process_whatsapp_webhook,
    send_whatsapp_dispatch,
)
from core.models import Channel
from organizations.models import Organization

SEND_OK = {
    "messaging_product": "whatsapp",
    "contacts": [{"input": "966500000001", "wa_id": "966500000001"}],
    "messages": [{"id": "wamid.HBgABC"}],
}


def whatsapp_client(handler):
    return WhatsAppCloudClient(
        access_token="test-token",
        phone_number_id="PNID123",
        base_url="http://fake",
        api_version="v21.0",
        transport=httpx.MockTransport(handler),
    )


def ok_handler(request):
    return httpx.Response(200, json=SEND_OK)


def error_handler(status_code, code=131026):
    def handler(request):
        return httpx.Response(
            status_code,
            json={"error": {"message": "Message undeliverable", "code": code}},
        )

    return handler


class WhatsAppClientTests(APITestCase):
    def test_send_text_posts_to_phone_number_id_and_returns_message_id(self):
        captured = {}

        def handler(request):
            captured["url"] = str(request.url)
            captured["body"] = json.loads(request.content)
            return httpx.Response(200, json=SEND_OK)

        result = whatsapp_client(handler).send_text("+966 50 000 0001", "Hello")
        self.assertTrue(captured["url"].endswith("/v21.0/PNID123/messages"))
        self.assertEqual(captured["body"]["to"], "966500000001")  # normalized
        self.assertEqual(captured["body"]["type"], "text")
        self.assertEqual(WhatsAppCloudClient.first_message_id(result), "wamid.HBgABC")

    def test_send_template_includes_name_and_language(self):
        captured = {}

        def handler(request):
            captured["body"] = json.loads(request.content)
            return httpx.Response(200, json=SEND_OK)

        whatsapp_client(handler).send_template("966500000001", "reminder", "ar")
        self.assertEqual(captured["body"]["type"], "template")
        self.assertEqual(captured["body"]["template"]["name"], "reminder")
        self.assertEqual(captured["body"]["template"]["language"], {"code": "ar"})

    def test_client_error_is_final(self):
        with self.assertRaises(WhatsAppError) as ctx:
            whatsapp_client(error_handler(400)).send_text("966500000001", "hi")
        self.assertFalse(ctx.exception.retryable)

    def test_rate_limit_and_server_errors_are_retryable(self):
        for code in (429, 500, 503):
            with self.assertRaises(WhatsAppError) as ctx:
                whatsapp_client(error_handler(code)).send_text("966500000001", "hi")
            self.assertTrue(ctx.exception.retryable, code)


@override_settings(WHATSAPP_APP_SECRET="topsecret")
class SignatureVerificationTests(APITestCase):
    def _sign(self, body, secret="topsecret"):
        digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        return f"sha256={digest}"

    def test_valid_signature_passes(self):
        body = b'{"a":1}'
        self.assertTrue(verify_whatsapp_signature(body, self._sign(body)))

    def test_tampered_body_fails(self):
        self.assertFalse(verify_whatsapp_signature(b'{"a":2}', self._sign(b'{"a":1}')))

    def test_missing_header_fails(self):
        self.assertFalse(verify_whatsapp_signature(b"{}", ""))

    @override_settings(WHATSAPP_APP_SECRET="")
    def test_fails_closed_without_secret(self):
        body = b"{}"
        digest = hmac.new(b"anything", body, hashlib.sha256).hexdigest()
        self.assertFalse(verify_whatsapp_signature(body, f"sha256={digest}"))


class SendDispatchTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org = Organization.objects.create(name="Glow Spa", slug="glow")

    def _dispatch(self):
        return MessageDispatch.objects.create(
            organization=self.org,
            channel=Channel.WHATSAPP,
            recipient="966500000001",
            content="Your appointment is tomorrow at 5pm.",
        )

    def test_successful_send_records_message_id(self):
        dispatch = self._dispatch()
        send_whatsapp_dispatch(dispatch, client=whatsapp_client(ok_handler))
        dispatch.refresh_from_db()
        self.assertEqual(dispatch.status, MessageDispatch.Status.SENT)
        self.assertEqual(dispatch.external_message_id, "wamid.HBgABC")
        self.assertIsNotNone(dispatch.sent_at)

    def test_final_rejection_marks_failed(self):
        dispatch = self._dispatch()
        with self.assertRaises(WhatsAppError):
            send_whatsapp_dispatch(dispatch, client=whatsapp_client(error_handler(400)))
        dispatch.refresh_from_db()
        self.assertEqual(dispatch.status, MessageDispatch.Status.FAILED)
        self.assertTrue(dispatch.failure_reason)

    def test_transient_failure_keeps_queued_for_retry(self):
        dispatch = self._dispatch()
        with self.assertRaises(WhatsAppError):
            send_whatsapp_dispatch(dispatch, client=whatsapp_client(error_handler(503)))
        dispatch.refresh_from_db()
        self.assertEqual(dispatch.status, MessageDispatch.Status.QUEUED)


class DeliveryReceiptTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org = Organization.objects.create(name="Glow Spa", slug="glow")

    def _dispatch(self, message_id="wamid.HBgABC"):
        return MessageDispatch.objects.create(
            organization=self.org,
            channel=Channel.WHATSAPP,
            recipient="966500000001",
            content="hi",
            status=MessageDispatch.Status.SENT,
            external_message_id=message_id,
        )

    def _payload(self, statuses):
        return {"entry": [{"changes": [{"value": {"statuses": statuses}}]}]}

    def test_delivered_then_read_moves_status_forward(self):
        dispatch = self._dispatch()
        process_whatsapp_webhook(
            self._payload([{"id": "wamid.HBgABC", "status": "delivered"}])
        )
        dispatch.refresh_from_db()
        self.assertEqual(dispatch.status, MessageDispatch.Status.DELIVERED)
        self.assertIsNotNone(dispatch.delivered_at)

        process_whatsapp_webhook(
            self._payload([{"id": "wamid.HBgABC", "status": "read"}])
        )
        dispatch.refresh_from_db()
        self.assertEqual(dispatch.status, MessageDispatch.Status.READ)
        self.assertIsNotNone(dispatch.read_at)

    def test_failed_status_records_reason(self):
        dispatch = self._dispatch()
        applied = process_whatsapp_webhook(
            self._payload(
                [
                    {
                        "id": "wamid.HBgABC",
                        "status": "failed",
                        "errors": [{"code": 131026, "title": "Message undeliverable"}],
                    }
                ]
            )
        )
        self.assertEqual(applied, 1)
        dispatch.refresh_from_db()
        self.assertEqual(dispatch.status, MessageDispatch.Status.FAILED)
        self.assertIn("131026", dispatch.failure_reason)

    def test_unknown_message_id_is_ignored(self):
        applied = process_whatsapp_webhook(
            self._payload([{"id": "wamid.UNKNOWN", "status": "delivered"}])
        )
        self.assertEqual(applied, 0)


@override_settings(
    WHATSAPP_APP_SECRET="topsecret",
    WHATSAPP_WEBHOOK_VERIFY_TOKEN="verify-me",
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
)
class WebhookEndpointTests(APITestCase):
    url = "/api/v1/webhooks/whatsapp/"

    @classmethod
    def setUpTestData(cls):
        cls.org = Organization.objects.create(name="Glow Spa", slug="glow")

    def test_get_verification_echoes_challenge(self):
        response = self.client.get(
            self.url,
            {
                "hub.mode": "subscribe",
                "hub.verify_token": "verify-me",
                "hub.challenge": "1234567890",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"1234567890")

    def test_get_verification_rejects_wrong_token(self):
        response = self.client.get(
            self.url,
            {"hub.mode": "subscribe", "hub.verify_token": "nope", "hub.challenge": "x"},
        )
        self.assertEqual(response.status_code, 403)

    def test_post_rejects_invalid_signature(self):
        response = self.client.post(
            self.url,
            data=b"{}",
            content_type="application/json",
            HTTP_X_HUB_SIGNATURE_256="sha256=deadbeef",
        )
        self.assertEqual(response.status_code, 403)

    def test_post_with_valid_signature_applies_status(self):
        dispatch = MessageDispatch.objects.create(
            organization=self.org,
            channel=Channel.WHATSAPP,
            recipient="966500000001",
            content="hi",
            status=MessageDispatch.Status.SENT,
            external_message_id="wamid.HBgABC",
        )
        payload = {
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "statuses": [
                                    {"id": "wamid.HBgABC", "status": "delivered"}
                                ]
                            }
                        }
                    ]
                }
            ]
        }
        raw = json.dumps(payload).encode()
        digest = hmac.new(b"topsecret", raw, hashlib.sha256).hexdigest()
        response = self.client.post(
            self.url,
            data=raw,
            content_type="application/json",
            HTTP_X_HUB_SIGNATURE_256=f"sha256={digest}",
        )
        self.assertEqual(response.status_code, 200)
        dispatch.refresh_from_db()
        self.assertEqual(dispatch.status, MessageDispatch.Status.DELIVERED)

    def test_post_persists_event_and_dedupes_retries(self):
        from communications.models import WhatsAppWebhookEvent

        dispatch = MessageDispatch.objects.create(
            organization=self.org,
            channel=Channel.WHATSAPP,
            recipient="966500000002",
            content="hi",
            status=MessageDispatch.Status.SENT,
            external_message_id="wamid.DEDUPE",
        )
        payload = {
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "statuses": [{"id": "wamid.DEDUPE", "status": "read"}]
                            }
                        }
                    ]
                }
            ]
        }
        raw = json.dumps(payload).encode()
        digest = hmac.new(b"topsecret", raw, hashlib.sha256).hexdigest()
        headers = {"HTTP_X_HUB_SIGNATURE_256": f"sha256={digest}"}

        first = self.client.post(
            self.url, data=raw, content_type="application/json", **headers
        )
        # Meta re-delivers the identical body; the body-hash dedupe collapses it.
        second = self.client.post(
            self.url, data=raw, content_type="application/json", **headers
        )
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(WhatsAppWebhookEvent.objects.count(), 1)
        event = WhatsAppWebhookEvent.objects.get()
        self.assertEqual(
            event.processing_status,
            WhatsAppWebhookEvent.ProcessingStatus.PROCESSED,
        )
        self.assertEqual(event.statuses_applied, 1)
        dispatch.refresh_from_db()
        self.assertEqual(dispatch.status, MessageDispatch.Status.READ)
