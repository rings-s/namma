"""Gateway tests: Taqnyat SMS and Amazon SES email contracts and flows."""

import base64
import datetime
import json
from decimal import Decimal
from unittest import mock

import httpx
from botocore.exceptions import ClientError, EndpointConnectionError
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.x509.oid import NameOID
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.test import override_settings
from rest_framework.test import APITestCase

from accounts.models import UserRole
from communications.gateways import (
    SESEmailClient,
    SESError,
    TaqnyatClient,
    TaqnyatError,
    normalize_msisdn,
)
from communications.models import ConsentRecord, EmailEvent, MessageDispatch
from communications.services import send_email_dispatch, send_sms_dispatch
from communications.sns import _CERT_CACHE_PREFIX, _SIGNED_FIELDS
from core.models import Channel
from customers.models import Customer
from organizations.models import Organization

User = get_user_model()

SUCCESS_RESPONSE = {
    "statusCode": 201,
    "messageId": "5829452722",
    "cost": "0.1500",
    "currency": "SAR",
    "totalCount": 1,
    "msgLength": 1,
    "accepted": ["966500000001"],
    "rejected": [],
}


def mock_client(handler):
    return TaqnyatClient(
        bearer_token="test-token",
        base_url="https://api.taqnyat.sa",
        transport=httpx.MockTransport(handler),
    )


class NormalizeMsisdnTests(APITestCase):
    def test_strips_plus_zeroes_and_separators(self):
        self.assertEqual(normalize_msisdn("+966 50-000-0001"), "966500000001")
        self.assertEqual(normalize_msisdn("00966500000001"), "966500000001")
        self.assertEqual(normalize_msisdn("966500000001"), "966500000001")


class TaqnyatClientTests(APITestCase):
    def test_send_sms_matches_official_contract(self):
        captured = {}

        def handler(request):
            captured["url"] = str(request.url)
            captured["auth"] = request.headers.get("authorization", "")
            captured["body"] = json.loads(request.content)
            return httpx.Response(201, json=SUCCESS_RESPONSE)

        with mock_client(handler) as client:
            result = client.send_sms(
                ["+966500000001"], "Hello From Namaa!", sender="Namaa"
            )
        self.assertEqual(captured["url"], "https://api.taqnyat.sa/v1/messages")
        self.assertEqual(captured["auth"], "Bearer test-token")
        self.assertEqual(
            captured["body"],
            {
                "recipients": ["966500000001"],
                "body": "Hello From Namaa!",
                "sender": "Namaa",
            },
        )
        self.assertEqual(result["messageId"], "5829452722")

    def test_error_response_raises_taqnyat_error(self):
        def handler(request):
            return httpx.Response(
                400, json={"statusCode": 400, "message": "Sender Name not active"}
            )

        with mock_client(handler) as client:
            with self.assertRaises(TaqnyatError) as ctx:
                client.send_sms(["966500000001"], "hi", sender="Bad")
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("Sender Name not active", str(ctx.exception))


class SmsDispatchTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org = Organization.objects.create(name="Salon A", slug="salon-a")
        cls.owner = User.objects.create_user(
            email="owner@namaa.sa", password="pass12345"
        )
        UserRole.objects.create(
            user=cls.owner, organization=cls.org, role=UserRole.Role.OWNER
        )
        cls.customer = Customer.objects.create(
            organization=cls.org, first_name="Sara", last_name="Ali"
        )

    def _dispatch(self, **overrides):
        defaults = {
            "organization": self.org,
            "customer": self.customer,
            "channel": Channel.SMS,
            "recipient": "+966500000001",
            "content": "Your appointment is tomorrow at 4pm.",
        }
        defaults.update(overrides)
        return MessageDispatch.objects.create(**defaults)

    def test_successful_send_records_message_id_and_cost(self):
        dispatch = self._dispatch()
        with mock_client(
            lambda r: httpx.Response(201, json=SUCCESS_RESPONSE)
        ) as client:
            send_sms_dispatch(dispatch, client=client)
        dispatch.refresh_from_db()
        self.assertEqual(dispatch.status, MessageDispatch.Status.SENT)
        self.assertEqual(dispatch.external_message_id, "5829452722")
        self.assertEqual(dispatch.cost, Decimal("0.15"))
        self.assertIsNotNone(dispatch.sent_at)

    def test_gateway_failure_marks_dispatch_failed_with_reason(self):
        dispatch = self._dispatch()

        def handler(request):
            return httpx.Response(
                400, json={"statusCode": 400, "message": "Sender Name not active"}
            )

        with mock_client(handler) as client:
            with self.assertRaises(TaqnyatError):
                send_sms_dispatch(dispatch, client=client)
        dispatch.refresh_from_db()
        self.assertEqual(dispatch.status, MessageDispatch.Status.FAILED)
        self.assertIn("Sender Name not active", dispatch.failure_reason)
        self.assertIsNotNone(dispatch.failed_at)

    def test_non_sms_channel_is_rejected(self):
        dispatch = self._dispatch(channel=Channel.EMAIL, recipient="a@b.sa")
        with self.assertRaises(ValidationError):
            send_sms_dispatch(dispatch)

    def test_already_sent_dispatch_is_rejected(self):
        dispatch = self._dispatch(status=MessageDispatch.Status.SENT)
        with self.assertRaises(ValidationError):
            send_sms_dispatch(dispatch)

    def test_api_create_then_send_flow_guards_state(self):
        self.client.force_authenticate(self.owner)
        created = self.client.post(
            "/api/v1/message-dispatches/",
            {
                "organization": str(self.org.id),
                "customer": str(self.customer.id),
                "channel": "sms",
                "recipient": "+966500000001",
                "content": "Reminder",
                # Attempted client-side overrides of gateway-owned fields:
                "status": "sent",
                "cost": "9.99",
            },
        )
        self.assertEqual(created.status_code, 201, created.data)
        # Gateway-owned fields stayed server-controlled.
        self.assertEqual(created.data["status"], "queued")
        self.assertEqual(Decimal(created.data["cost"]), Decimal("0"))

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
    def test_api_send_action_queues_and_worker_sends(self):
        dispatch = self._dispatch()
        self.client.force_authenticate(self.owner)
        with mock.patch("communications.services.TaqnyatClient") as factory:
            factory.return_value.send_sms.return_value = SUCCESS_RESPONSE
            response = self.client.post(
                f"/api/v1/message-dispatches/{dispatch.id}/send/"
            )
        self.assertEqual(response.status_code, 202, response.data)
        dispatch.refresh_from_db()
        self.assertEqual(dispatch.status, MessageDispatch.Status.SENT)
        self.assertEqual(dispatch.external_message_id, "5829452722")

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
    def test_send_action_on_already_sent_dispatch_returns_400(self):
        dispatch = self._dispatch(status=MessageDispatch.Status.SENT)
        self.client.force_authenticate(self.owner)
        response = self.client.post(f"/api/v1/message-dispatches/{dispatch.id}/send/")
        self.assertEqual(response.status_code, 400)


class StubSesV2Client:
    """Captures SES v2 ``send_email`` kwargs; raises ``error`` if set."""

    def __init__(self, message_id="ses-msg-1", error=None):
        self.message_id = message_id
        self.error = error
        self.calls = []

    def send_email(self, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return {"MessageId": self.message_id}


def ses_rejection(code="MessageRejected", message="Email address is not verified."):
    return ClientError({"Error": {"Code": code, "Message": message}}, "SendEmail")


@override_settings(
    SES_FROM_EMAIL="no-reply@namaa.sa", AWS_SES_CONFIGURATION_SET="namaa-events"
)
class SesEmailClientTests(APITestCase):
    def test_send_email_builds_sesv2_request(self):
        stub = StubSesV2Client()
        message_id = SESEmailClient(client=stub).send_email(
            ["sara@example.sa"],
            "أهلاً بك في نماء",
            html_body="<p>مرحبا</p>",
            text_body="مرحبا",
            tags={"dispatch_id": "abc-123"},
        )
        self.assertEqual(message_id, "ses-msg-1")
        (call,) = stub.calls
        self.assertEqual(call["FromEmailAddress"], "no-reply@namaa.sa")
        self.assertEqual(call["Destination"], {"ToAddresses": ["sara@example.sa"]})
        simple = call["Content"]["Simple"]
        self.assertEqual(simple["Subject"]["Data"], "أهلاً بك في نماء")
        self.assertEqual(simple["Body"]["Html"]["Data"], "<p>مرحبا</p>")
        self.assertEqual(simple["Body"]["Text"]["Data"], "مرحبا")
        self.assertEqual(call["ConfigurationSetName"], "namaa-events")
        self.assertEqual(
            call["EmailTags"], [{"Name": "dispatch_id", "Value": "abc-123"}]
        )

    def test_rejection_maps_to_final_error(self):
        stub = StubSesV2Client(error=ses_rejection())
        with self.assertRaises(SESError) as ctx:
            SESEmailClient(client=stub).send_email(
                ["sara@example.sa"], "Hi", html_body="<p>x</p>"
            )
        self.assertFalse(ctx.exception.retryable)
        self.assertEqual(ctx.exception.code, "MessageRejected")

    def test_throttling_is_retryable(self):
        stub = StubSesV2Client(
            error=ses_rejection(code="TooManyRequestsException", message="Slow down.")
        )
        with self.assertRaises(SESError) as ctx:
            SESEmailClient(client=stub).send_email(
                ["sara@example.sa"], "Hi", html_body="<p>x</p>"
            )
        self.assertTrue(ctx.exception.retryable)

    def test_connection_error_is_retryable(self):
        stub = StubSesV2Client(
            error=EndpointConnectionError(endpoint_url="https://email.me-south-1")
        )
        with self.assertRaises(SESError) as ctx:
            SESEmailClient(client=stub).send_email(
                ["sara@example.sa"], "Hi", html_body="<p>x</p>"
            )
        self.assertTrue(ctx.exception.retryable)

    def test_body_is_required(self):
        with self.assertRaises(SESError):
            SESEmailClient(client=StubSesV2Client()).send_email(
                ["sara@example.sa"], "Hi"
            )


class EmailDispatchTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org = Organization.objects.create(name="Salon A", slug="salon-a")
        cls.owner = User.objects.create_user(
            email="owner@namaa.sa", password="pass12345"
        )
        UserRole.objects.create(
            user=cls.owner, organization=cls.org, role=UserRole.Role.OWNER
        )
        cls.customer = Customer.objects.create(
            organization=cls.org,
            first_name="Sara",
            last_name="Ali",
            email="sara@example.sa",
        )

    def _dispatch(self, **overrides):
        defaults = {
            "organization": self.org,
            "customer": self.customer,
            "channel": Channel.EMAIL,
            "recipient": "sara@example.sa",
            "subject": "Your appointment",
            "content": "<p>Tomorrow at 4pm.</p>",
        }
        defaults.update(overrides)
        return MessageDispatch.objects.create(**defaults)

    def test_successful_send_records_message_id(self):
        dispatch = self._dispatch()
        stub = StubSesV2Client(message_id="ses-msg-42")
        send_email_dispatch(dispatch, client=SESEmailClient(client=stub))
        dispatch.refresh_from_db()
        self.assertEqual(dispatch.status, MessageDispatch.Status.SENT)
        self.assertEqual(dispatch.external_message_id, "ses-msg-42")
        self.assertIsNotNone(dispatch.sent_at)
        # HTML content also went out with a stripped text alternative.
        (call,) = stub.calls
        self.assertEqual(
            call["Content"]["Simple"]["Body"]["Text"]["Data"], "Tomorrow at 4pm."
        )

    def test_rejection_marks_dispatch_failed_with_reason(self):
        dispatch = self._dispatch()
        client = SESEmailClient(client=StubSesV2Client(error=ses_rejection()))
        with self.assertRaises(SESError):
            send_email_dispatch(dispatch, client=client)
        dispatch.refresh_from_db()
        self.assertEqual(dispatch.status, MessageDispatch.Status.FAILED)
        self.assertIn("not verified", dispatch.failure_reason)
        self.assertIsNotNone(dispatch.failed_at)

    def test_retryable_error_keeps_dispatch_queued(self):
        dispatch = self._dispatch()
        client = SESEmailClient(
            client=StubSesV2Client(
                error=ses_rejection(code="TooManyRequestsException", message="Later.")
            )
        )
        with self.assertRaises(SESError):
            send_email_dispatch(dispatch, client=client)
        dispatch.refresh_from_db()
        self.assertEqual(dispatch.status, MessageDispatch.Status.QUEUED)

    def test_missing_subject_is_rejected(self):
        dispatch = self._dispatch(subject="")
        with self.assertRaises(ValidationError):
            send_email_dispatch(dispatch)

    def test_invalid_recipient_address_is_rejected(self):
        dispatch = self._dispatch(recipient="not-an-email")
        with self.assertRaises(ValidationError):
            send_email_dispatch(dispatch)

    def test_non_email_channel_is_rejected(self):
        dispatch = self._dispatch(channel=Channel.SMS, recipient="+966500000001")
        with self.assertRaises(ValidationError):
            send_email_dispatch(dispatch)

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
    def test_api_send_action_routes_email_channel_to_ses(self):
        dispatch = self._dispatch()
        self.client.force_authenticate(self.owner)
        with mock.patch("communications.services.SESEmailClient") as factory:
            factory.return_value.send_email.return_value = "ses-msg-77"
            response = self.client.post(
                f"/api/v1/message-dispatches/{dispatch.id}/send/"
            )
        self.assertEqual(response.status_code, 202, response.data)
        dispatch.refresh_from_db()
        self.assertEqual(dispatch.status, MessageDispatch.Status.SENT)
        self.assertEqual(dispatch.external_message_id, "ses-msg-77")

    def test_api_send_action_rejects_channels_without_gateway(self):
        dispatch = self._dispatch(channel=Channel.WHATSAPP)
        self.client.force_authenticate(self.owner)
        response = self.client.post(f"/api/v1/message-dispatches/{dispatch.id}/send/")
        self.assertEqual(response.status_code, 400)


WEBHOOK_URL = "/api/v1/webhooks/ses/"
SIGNING_CERT_URL = (
    "https://sns.me-south-1.amazonaws.com/SimpleNotificationService-test.pem"
)


_SIGNING_MATERIAL = {}


def sns_signing_material(common_name="sns.amazonaws.com"):
    """One RSA key + self-signed cert per CN, shared by the whole module."""
    if common_name not in _SIGNING_MATERIAL:
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])
        now = datetime.datetime.now(datetime.timezone.utc)
        certificate = (
            x509.CertificateBuilder()
            .subject_name(name)
            .issuer_name(name)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - datetime.timedelta(days=1))
            .not_valid_after(now + datetime.timedelta(days=1))
            .sign(key, hashes.SHA256())
        )
        pem = certificate.public_bytes(serialization.Encoding.PEM)
        _SIGNING_MATERIAL[common_name] = (key, pem)
    return _SIGNING_MATERIAL[common_name]


def sign_envelope(envelope, cert_url=SIGNING_CERT_URL, common_name="sns.amazonaws.com"):
    """Sign like SNS does: SHA256withRSA over the type's canonical string."""
    key, _ = sns_signing_material(common_name)
    canonical = "".join(
        f"{field}\n{envelope[field]}\n"
        for field in _SIGNED_FIELDS[envelope["Type"]]
        if field in envelope
    ).encode()
    signature = key.sign(canonical, padding.PKCS1v15(), hashes.SHA256())
    return {
        **envelope,
        "SignatureVersion": "2",
        "Signature": base64.b64encode(signature).decode(),
        "SigningCertURL": cert_url,
    }


def sns_envelope(message, sns_message_id="sns-1", sign=True):
    envelope = {
        "Type": "Notification",
        "MessageId": sns_message_id,
        "TopicArn": "arn:aws:sns:me-south-1:123:namaa-ses-events",
        "Timestamp": "2026-06-11T12:00:00.000Z",
        "Message": json.dumps(message),
    }
    return sign_envelope(envelope) if sign else envelope


def ses_event(event_type, ses_message_id="ses-msg-42", **extra):
    return {
        "eventType": event_type,
        "mail": {"messageId": ses_message_id, "destination": ["sara@example.sa"]},
        **extra,
    }


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
    AWS_SES_SNS_TOPIC_ARN="arn:aws:sns:me-south-1:123:namaa-ses-events",
)
class SesWebhookTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org = Organization.objects.create(name="Salon A", slug="salon-a")
        cls.customer = Customer.objects.create(
            organization=cls.org,
            first_name="Sara",
            last_name="Ali",
            email="sara@example.sa",
        )
        cls.dispatch = MessageDispatch.objects.create(
            organization=cls.org,
            customer=cls.customer,
            channel=Channel.EMAIL,
            recipient="sara@example.sa",
            subject="Hi",
            content="<p>x</p>",
            status=MessageDispatch.Status.SENT,
            external_message_id="ses-msg-42",
        )

    def setUp(self):
        # Seed the verifier's certificate cache so no test touches AWS.
        _, pem = sns_signing_material()
        cache.set(f"{_CERT_CACHE_PREFIX}{SIGNING_CERT_URL}", pem, 300)

    def _post(self, envelope):
        return self.client.post(
            WEBHOOK_URL,
            data=json.dumps(envelope),
            content_type="text/plain; charset=UTF-8",
        )

    def test_unsigned_envelope_is_rejected(self):
        response = self._post(sns_envelope(ses_event("Delivery"), sign=False))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(EmailEvent.objects.count(), 0)

    def test_tampered_message_is_rejected(self):
        envelope = sns_envelope(ses_event("Delivery"))
        envelope["Message"] = json.dumps(ses_event("Bounce"))
        self.assertEqual(self._post(envelope).status_code, 403)
        self.assertEqual(EmailEvent.objects.count(), 0)

    def test_validly_signed_envelope_from_foreign_topic_is_rejected(self):
        # An attacker's own SNS topic signs validly too: the pin must hold.
        envelope = sns_envelope(ses_event("Delivery"), sign=False)
        envelope["TopicArn"] = "arn:aws:sns:me-south-1:999:attacker-topic"
        self.assertEqual(self._post(sign_envelope(envelope)).status_code, 403)
        self.assertEqual(EmailEvent.objects.count(), 0)

    @override_settings(AWS_SES_SNS_TOPIC_ARN="")
    def test_unconfigured_topic_pin_fails_closed(self):
        response = self._post(sns_envelope(ses_event("Delivery")))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(EmailEvent.objects.count(), 0)

    def test_certificate_with_wrong_subject_cn_is_rejected(self):
        wrong_cn_cert_url = (
            "https://sns.me-south-1.amazonaws.com/NotReallySns-wrong-cn.pem"
        )
        _, pem = sns_signing_material("attacker.example.com")
        cache.set(f"{_CERT_CACHE_PREFIX}{wrong_cn_cert_url}", pem, 300)
        envelope = sign_envelope(
            sns_envelope(ses_event("Delivery"), sign=False),
            cert_url=wrong_cn_cert_url,
            common_name="attacker.example.com",
        )
        self.assertEqual(self._post(envelope).status_code, 403)
        self.assertEqual(EmailEvent.objects.count(), 0)

    def test_certificate_from_non_aws_host_is_rejected(self):
        envelope = sns_envelope(ses_event("Delivery"), sign=False)
        for cert_url in (
            "https://evil.example.com/cert.pem",
            "https://sns.me-south-1.amazonaws.com.evil.com/cert.pem",
            "http://sns.me-south-1.amazonaws.com/cert.pem",
        ):
            self.assertEqual(
                self._post(sign_envelope(envelope, cert_url=cert_url)).status_code,
                403,
                cert_url,
            )
        self.assertEqual(EmailEvent.objects.count(), 0)

    def test_subscription_confirmation_is_confirmed_on_a_worker(self):
        envelope = sign_envelope(
            {
                "Type": "SubscriptionConfirmation",
                "MessageId": "sns-sub-1",
                "Token": "opaque-confirmation-token",
                "TopicArn": "arn:aws:sns:me-south-1:123:namaa-ses-events",
                "Timestamp": "2026-06-11T12:00:00.000Z",
                "Message": "You have chosen to subscribe...",
                "SubscribeURL": "https://sns.me-south-1.amazonaws.com/?Action=ConfirmSubscription",
            }
        )
        with mock.patch("communications.views.confirm_sns_subscription_task") as task:
            response = self._post(envelope)
        self.assertEqual(response.status_code, 200)
        task.delay.assert_called_once_with(
            "https://sns.me-south-1.amazonaws.com/?Action=ConfirmSubscription"
        )
        self.assertEqual(EmailEvent.objects.count(), 0)

    def test_duplicate_sns_delivery_is_stored_once(self):
        envelope = sns_envelope(ses_event("Delivery"), sns_message_id="sns-dup")
        self.assertEqual(self._post(envelope).status_code, 200)
        self.assertEqual(self._post(envelope).status_code, 200)
        self.assertEqual(EmailEvent.objects.filter(sns_message_id="sns-dup").count(), 1)

    def test_delivery_event_marks_dispatch_delivered(self):
        self._post(sns_envelope(ses_event("Delivery")))
        self.dispatch.refresh_from_db()
        self.assertEqual(self.dispatch.status, MessageDispatch.Status.DELIVERED)
        self.assertIsNotNone(self.dispatch.delivered_at)
        event = EmailEvent.objects.get(sns_message_id="sns-1")
        self.assertEqual(event.processing_status, EmailEvent.ProcessingStatus.PROCESSED)
        self.assertEqual(event.dispatch_id, self.dispatch.id)
        self.assertEqual(event.organization_id, self.org.id)

    def test_permanent_bounce_marks_dispatch_failed(self):
        bounce = {
            "bounce": {
                "bounceType": "Permanent",
                "bouncedRecipients": [{"diagnosticCode": "550 user unknown"}],
            }
        }
        self._post(sns_envelope(ses_event("Bounce", **bounce)))
        self.dispatch.refresh_from_db()
        self.assertEqual(self.dispatch.status, MessageDispatch.Status.FAILED)
        self.assertIn("550 user unknown", self.dispatch.failure_reason)

    def test_open_event_marks_dispatch_read(self):
        self._post(sns_envelope(ses_event("Open")))
        self.dispatch.refresh_from_db()
        self.assertEqual(self.dispatch.status, MessageDispatch.Status.READ)
        self.assertIsNotNone(self.dispatch.read_at)

    def test_complaint_appends_consent_revocation_once(self):
        ConsentRecord.objects.create(
            organization=self.org,
            customer=self.customer,
            channel=Channel.EMAIL,
            purpose=ConsentRecord.Purpose.MARKETING,
            granted_at="2026-01-01T00:00:00Z",
        )
        self._post(sns_envelope(ses_event("Complaint"), sns_message_id="sns-c1"))
        self._post(sns_envelope(ses_event("Complaint"), sns_message_id="sns-c2"))
        revocations = ConsentRecord.objects.filter(
            customer=self.customer,
            channel=Channel.EMAIL,
            purpose=ConsentRecord.Purpose.MARKETING,
            revoked_at__isnull=False,
        )
        # PDPL ledger stays append-only: one revocation entry, no edits.
        self.assertEqual(revocations.count(), 1)
        self.assertEqual(revocations.get().source, "ses_complaint")

    def test_event_for_unknown_message_is_kept_but_ignored(self):
        self._post(
            sns_envelope(
                ses_event("Delivery", ses_message_id="smtp-system-mail"),
                sns_message_id="sns-x",
            )
        )
        event = EmailEvent.objects.get(sns_message_id="sns-x")
        self.assertEqual(event.processing_status, EmailEvent.ProcessingStatus.IGNORED)
        self.assertIsNone(event.dispatch_id)
