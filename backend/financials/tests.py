"""Moyasar gateway tests: webhook intake, processing and refunds."""

import json
from decimal import Decimal
from unittest import mock

import httpx
from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APITestCase

from accounts.models import UserRole
from customers.models import Customer
from financials.gateways import MoyasarClient, from_halalas, to_halalas
from financials.models import Gateway, Invoice, Payment, PaymentWebhookEvent, Refund
from financials.services import execute_moyasar_refund
from organizations.models import Organization

User = get_user_model()

WEBHOOK_SECRET = "whsec_test_token"


class MoyasarTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org = Organization.objects.create(name="Salon A", slug="salon-a")
        cls.owner = User.objects.create_user(
            email="owner@namaa.sa", password="pass12345"
        )
        UserRole.objects.create(
            user=cls.owner, organization=cls.org, role=UserRole.Role.OWNER
        )
        cls.staff = User.objects.create_user(
            email="staff@namaa.sa", password="pass12345"
        )
        UserRole.objects.create(
            user=cls.staff, organization=cls.org, role=UserRole.Role.STAFF
        )
        cls.customer = Customer.objects.create(
            organization=cls.org, first_name="Sara", last_name="Ali"
        )
        cls.invoice = Invoice.objects.create(
            organization=cls.org,
            customer=cls.customer,
            invoice_number="INV-1",
            subtotal=Decimal("200.00"),
            total_amount=Decimal("200.00"),
            amount_due=Decimal("200.00"),
            status=Invoice.Status.ISSUED,
        )
        cls.payment = Payment.objects.create(
            organization=cls.org,
            invoice=cls.invoice,
            customer=cls.customer,
            payment_method="card",
            gateway=Gateway.MOYASAR,
            gateway_transaction_id="pay_123",
            amount=Decimal("200.00"),
        )

    def _event(self, event_id="evt_1", event_type="payment_paid", **data):
        payload = {
            "id": event_id,
            "type": event_type,
            "secret_token": WEBHOOK_SECRET,
            "data": {"id": "pay_123", "status": "paid", "amount": 20000, **data},
        }
        return self.client.post("/api/v1/webhooks/moyasar/", payload, format="json")


@override_settings(
    MOYASAR_WEBHOOK_SECRET=WEBHOOK_SECRET,
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
)
class MoyasarWebhookTests(MoyasarTestCase):
    def test_invalid_secret_token_is_rejected(self):
        response = self.client.post(
            "/api/v1/webhooks/moyasar/",
            {"id": "evt_x", "type": "payment_paid", "secret_token": "wrong"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(PaymentWebhookEvent.objects.count(), 0)

    def test_payment_paid_marks_payment_and_invoice(self):
        response = self._event()
        self.assertEqual(response.status_code, 200)
        self.payment.refresh_from_db()
        self.invoice.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.COMPLETED)
        self.assertIsNotNone(self.payment.paid_at)
        self.assertEqual(self.invoice.status, Invoice.Status.PAID)
        self.assertEqual(self.invoice.amount_paid, Decimal("200.00"))
        event = PaymentWebhookEvent.objects.get(gateway_event_id="evt_1")
        self.assertEqual(
            event.processing_status, PaymentWebhookEvent.ProcessingStatus.PROCESSED
        )
        self.assertEqual(event.organization_id, self.org.id)

    def test_duplicate_delivery_is_idempotent(self):
        self._event()
        self._event()  # Moyasar retry of the same event id
        self.assertEqual(PaymentWebhookEvent.objects.count(), 1)
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.amount_paid, Decimal("200.00"))

    def test_unknown_payment_is_stored_but_ignored(self):
        response = self._event(event_id="evt_2", id="pay_unknown")
        self.assertEqual(response.status_code, 200)
        event = PaymentWebhookEvent.objects.get(gateway_event_id="evt_2")
        self.assertEqual(
            event.processing_status, PaymentWebhookEvent.ProcessingStatus.IGNORED
        )

    def test_secret_token_is_never_persisted(self):
        self._event()
        event = PaymentWebhookEvent.objects.get(gateway_event_id="evt_1")
        self.assertNotIn("secret_token", event.payload)


class MoyasarRefundTests(MoyasarTestCase):
    def _mock_client(self, captured):
        def handler(request):
            captured["url"] = str(request.url)
            captured["body"] = json.loads(request.content) if request.content else None
            captured["auth"] = request.headers.get("authorization", "")
            return httpx.Response(
                200, json={"id": "pay_123", "status": "refunded", "refunded": 20000}
            )

        return MoyasarClient(
            secret_key="sk_test_key",
            base_url="https://api.moyasar.com/v1",
            transport=httpx.MockTransport(handler),
        )

    def test_full_refund_hits_refund_endpoint_without_amount(self):
        refund = Refund.objects.create(
            organization=self.org, payment=self.payment, amount=Decimal("200.00")
        )
        captured = {}
        with self._mock_client(captured) as client:
            execute_moyasar_refund(refund, approver=self.owner, client=client)
        self.assertTrue(captured["url"].endswith("/payments/pay_123/refund"))
        self.assertIsNone(captured["body"])  # full refund omits amount
        self.assertTrue(captured["auth"].startswith("Basic "))
        refund.refresh_from_db()
        self.payment.refresh_from_db()
        self.assertEqual(refund.status, Refund.Status.PROCESSED)
        self.assertEqual(refund.approver, self.owner)
        self.assertEqual(self.payment.status, Payment.Status.REFUNDED)

    def test_partial_refund_sends_amount_in_halalas(self):
        refund = Refund.objects.create(
            organization=self.org,
            payment=self.payment,
            amount=Decimal("50.00"),
            refund_type=Refund.RefundType.PARTIAL,
        )
        captured = {}

        def handler(request):
            captured["body"] = json.loads(request.content)
            return httpx.Response(
                200, json={"id": "pay_123", "status": "refunded", "refunded": 5000}
            )

        client = MoyasarClient(
            secret_key="sk_test_key", transport=httpx.MockTransport(handler)
        )
        with client:
            execute_moyasar_refund(refund, approver=self.owner, client=client)
        self.assertEqual(captured["body"], {"amount": 5000})
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.PARTIALLY_REFUNDED)

    def test_staff_cannot_execute_refund_via_api(self):
        refund = Refund.objects.create(
            organization=self.org, payment=self.payment, amount=Decimal("200.00")
        )
        self.client.force_authenticate(self.staff)
        response = self.client.post(f"/api/v1/refunds/{refund.id}/execute/")
        self.assertEqual(response.status_code, 403)

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
    def test_api_execute_queues_and_worker_processes_refund(self):
        refund = Refund.objects.create(
            organization=self.org, payment=self.payment, amount=Decimal("200.00")
        )
        self.client.force_authenticate(self.owner)
        with mock.patch("financials.services.MoyasarClient") as factory:
            factory.return_value.refund_payment.return_value = {
                "id": "pay_123",
                "status": "refunded",
                "refunded": 20000,
            }
            response = self.client.post(f"/api/v1/refunds/{refund.id}/execute/")
        self.assertEqual(response.status_code, 202, response.data)
        refund.refresh_from_db()
        self.payment.refresh_from_db()
        self.assertEqual(refund.status, Refund.Status.PROCESSED)
        self.assertEqual(self.payment.status, Payment.Status.REFUNDED)

    def test_non_moyasar_payment_is_rejected_before_any_network_call(self):
        manual = Payment.objects.create(
            organization=self.org,
            payment_method="cash",
            gateway=Gateway.MANUAL,
            amount=Decimal("80.00"),
        )
        refund = Refund.objects.create(
            organization=self.org, payment=manual, amount=Decimal("80.00")
        )
        self.client.force_authenticate(self.owner)
        response = self.client.post(f"/api/v1/refunds/{refund.id}/execute/")
        self.assertEqual(response.status_code, 400)

    def test_full_refund_reconciles_paid_invoice(self):
        # The invoice has been fully paid; a full refund must un-pay it.
        self.invoice.amount_paid = Decimal("200.00")
        self.invoice.amount_due = Decimal("0.00")
        self.invoice.status = Invoice.Status.PAID
        self.invoice.save()
        refund = Refund.objects.create(
            organization=self.org, payment=self.payment, amount=Decimal("200.00")
        )
        captured = {}
        with self._mock_client(captured) as client:
            execute_moyasar_refund(refund, approver=self.owner, client=client)
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.amount_paid, Decimal("0.00"))
        self.assertEqual(self.invoice.amount_due, Decimal("200.00"))
        self.assertEqual(self.invoice.status, Invoice.Status.ISSUED)
        self.assertIsNone(self.invoice.paid_at)

    def test_partial_refund_reconciles_to_partially_paid(self):
        self.invoice.amount_paid = Decimal("200.00")
        self.invoice.amount_due = Decimal("0.00")
        self.invoice.status = Invoice.Status.PAID
        self.invoice.save()
        refund = Refund.objects.create(
            organization=self.org,
            payment=self.payment,
            amount=Decimal("50.00"),
            refund_type=Refund.RefundType.PARTIAL,
        )

        def handler(request):
            return httpx.Response(
                200, json={"id": "pay_123", "status": "refunded", "refunded": 5000}
            )

        with MoyasarClient(
            secret_key="sk", transport=httpx.MockTransport(handler)
        ) as client:
            execute_moyasar_refund(refund, approver=self.owner, client=client)
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.amount_paid, Decimal("150.00"))
        self.assertEqual(self.invoice.amount_due, Decimal("50.00"))
        self.assertEqual(self.invoice.status, Invoice.Status.PARTIALLY_PAID)

    def test_cumulative_refunds_cannot_exceed_payment(self):
        from django.core.exceptions import ValidationError as DjangoValidationError

        from financials.services import validate_refund_executable

        # 150 already refunded; a further 100 would over-refund the 200 payment.
        Refund.objects.create(
            organization=self.org,
            payment=self.payment,
            amount=Decimal("150.00"),
            status=Refund.Status.PROCESSED,
            refund_type=Refund.RefundType.PARTIAL,
        )
        second = Refund.objects.create(
            organization=self.org,
            payment=self.payment,
            amount=Decimal("100.00"),
            refund_type=Refund.RefundType.PARTIAL,
        )
        with self.assertRaises(DjangoValidationError):
            validate_refund_executable(second)


class WebhookRecoveryTests(MoyasarTestCase):
    """Dead-letter + recovery sweep for payment webhook events (issue #5)."""

    def test_failed_processing_is_dead_lettered_then_replayable(self):
        from unittest.mock import patch

        from financials.models import PaymentWebhookEvent
        from financials.tasks import (
            process_payment_webhook_event_task,
            reprocess_stuck_payment_webhook_events,
        )

        event = PaymentWebhookEvent.objects.create(
            gateway=Gateway.MOYASAR,
            gateway_event_id="evt_fail",
            event_type="payment_paid",
            payload={"data": {"id": "pay_123", "status": "paid", "amount": 20000}},
        )

        # Force every processing attempt to blow up; with retries disabled the
        # final attempt dead-letters the event as FAILED rather than losing it.
        with patch(
            "financials.tasks.process_payment_webhook_event",
            side_effect=RuntimeError("boom"),
        ):
            with patch.object(process_payment_webhook_event_task, "max_retries", 0):
                with self.assertRaises(RuntimeError):
                    process_payment_webhook_event_task.run(str(event.pk))
        event.refresh_from_db()
        self.assertEqual(
            event.processing_status, PaymentWebhookEvent.ProcessingStatus.FAILED
        )

        # The recovery sweep re-enqueues the dead-lettered event; this time
        # processing succeeds and the event reaches a terminal good state.
        with patch(
            "financials.tasks.process_payment_webhook_event_task.delay"
        ) as delay:
            count = reprocess_stuck_payment_webhook_events(older_than_minutes=0)
        self.assertEqual(count, 1)
        delay.assert_called_once_with(str(event.pk))

    def test_sweep_ignores_terminal_events(self):
        from financials.models import PaymentWebhookEvent
        from financials.tasks import reprocess_stuck_payment_webhook_events

        PaymentWebhookEvent.objects.create(
            gateway=Gateway.MOYASAR,
            gateway_event_id="evt_done",
            event_type="payment_paid",
            payload={},
            processing_status=PaymentWebhookEvent.ProcessingStatus.PROCESSED,
        )
        self.assertEqual(
            reprocess_stuck_payment_webhook_events(older_than_minutes=0), 0
        )


class HalalasConversionTests(APITestCase):
    def test_round_trip(self):
        self.assertEqual(to_halalas(Decimal("199.99")), 19999)
        self.assertEqual(from_halalas(19999), Decimal("199.99"))


# ---------------------------------------------------------------------------
# ZATCA e-invoicing
# ---------------------------------------------------------------------------


def _self_signed_device_credentials():
    """A secp256k1 key + self-signed DER certificate standing in for the
    CSID certificate ZATCA issues; lets stamping/QR run without network."""
    import base64
    import datetime

    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import NameOID

    key = ec.generate_private_key(ec.SECP256K1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Namaa Test Device")])
    now = datetime.datetime.now(datetime.timezone.utc)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=365))
        .sign(key, hashes.SHA256())
    )
    cert_b64 = base64.b64encode(
        certificate.public_bytes(serialization.Encoding.DER)
    ).decode()
    return key, cert_b64


ZATCA_TEST_FERNET_KEY = None


def _zatca_test_key():
    global ZATCA_TEST_FERNET_KEY
    if ZATCA_TEST_FERNET_KEY is None:
        from cryptography.fernet import Fernet

        ZATCA_TEST_FERNET_KEY = Fernet.generate_key().decode()
    return ZATCA_TEST_FERNET_KEY


class ZatcaTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        from financials.models import ZatcaDevice

        cls.org = Organization.objects.create(
            name="Namaa Spa",
            slug="namaa-spa",
            vat_number="310000000000003",
            commercial_registration_number="1010101010",
            street_name="King Fahd Rd",
            building_number="1234",
            district="Al Olaya",
            city="Riyadh",
            postal_code="12211",
        )
        cls.owner = User.objects.create_user(
            email="zatca-owner@namaa.sa", password="pass12345"
        )
        UserRole.objects.create(
            user=cls.owner, organization=cls.org, role=UserRole.Role.OWNER
        )
        cls.staff = User.objects.create_user(
            email="zatca-staff@namaa.sa", password="pass12345"
        )
        UserRole.objects.create(
            user=cls.staff, organization=cls.org, role=UserRole.Role.STAFF
        )
        cls.invoice = Invoice.objects.create(
            organization=cls.org,
            invoice_number="INV-Z-1",
            subtotal=Decimal("200.00"),
            tax_amount=Decimal("30.00"),
            total_amount=Decimal("230.00"),
            amount_due=Decimal("230.00"),
            status=Invoice.Status.ISSUED,
        )
        cls.device = ZatcaDevice.objects.create(
            organization=cls.org, device_name="POS-1"
        )

    def setUp(self):
        from django.test import override_settings

        self._settings = override_settings(ZATCA_KEY_ENCRYPTION_KEY=_zatca_test_key())
        self._settings.enable()
        self.addCleanup(self._settings.disable)

    def activate_device(self, device=None):
        """Put a device into ACTIVE state with usable local credentials."""
        from financials import zatca
        from financials.models import ZatcaCounter, ZatcaDevice
        from django.utils import timezone as dj_timezone

        device = device or self.device
        key, cert_b64 = _self_signed_device_credentials()
        device.certificate = cert_b64
        device.private_key_encrypted = zatca.encrypt_secret(
            zatca.private_key_to_pem(key)
        )
        device.production_csid = "prod-csid-token"
        device.csid_secret_encrypted = zatca.encrypt_secret("prod-secret")
        device.status = ZatcaDevice.Status.ACTIVE
        device.onboarded_at = dj_timezone.now()
        device.save()
        ZatcaCounter.objects.get_or_create(zatca_device=device)
        return device


class ZatcaQrTlvTests(APITestCase):
    def test_round_trip_carries_seller_vat_amounts_and_hash(self):
        from django.utils import timezone as dj_timezone

        from financials import zatca

        encoded = zatca.build_qr_tlv(
            seller_name="Namaa Spa",
            vat_number="310000000000003",
            timestamp=dj_timezone.now(),
            total_with_vat=Decimal("230.00"),
            vat_amount=Decimal("30.00"),
            invoice_hash="aGFzaA==",
        )
        fields = zatca.decode_qr_tlv(encoded)
        self.assertEqual(fields[1].decode(), "Namaa Spa")
        self.assertEqual(fields[2].decode(), "310000000000003")
        self.assertEqual(fields[4].decode(), "230.00")
        self.assertEqual(fields[5].decode(), "30.00")
        self.assertEqual(fields[6].decode(), "aGFzaA==")
        self.assertNotIn(7, fields)  # no stamp tags without a signature

    def test_arabic_seller_name_survives_utf8_round_trip(self):
        from django.utils import timezone as dj_timezone

        from financials import zatca

        encoded = zatca.build_qr_tlv(
            seller_name="مشغل نماء",
            vat_number="310000000000003",
            timestamp=dj_timezone.now(),
            total_with_vat=Decimal("115.00"),
            vat_amount=Decimal("15.00"),
            invoice_hash="aGFzaA==",
        )
        self.assertEqual(zatca.decode_qr_tlv(encoded)[1].decode(), "مشغل نماء")


class ZatcaCsrTests(ZatcaTestCase):
    def test_csr_carries_zatca_subject_and_san(self):
        from cryptography import x509
        from cryptography.x509.oid import ExtensionOID, NameOID

        from financials import zatca

        key = zatca.generate_private_key()
        csr_pem = zatca.generate_csr(key, self.device, environment="sandbox")
        csr = x509.load_pem_x509_csr(csr_pem.encode())
        subject = {attr.oid: attr.value for attr in csr.subject}
        self.assertEqual(subject[NameOID.COUNTRY_NAME], "SA")
        self.assertEqual(subject[NameOID.COMMON_NAME], "POS-1")
        san = csr.extensions.get_extension_for_oid(
            ExtensionOID.SUBJECT_ALTERNATIVE_NAME
        ).value
        directory = san.get_values_for_type(x509.DirectoryName)[0]
        san_attrs = {attr.oid.dotted_string: attr.value for attr in directory}
        self.assertEqual(san_attrs["0.9.2342.19200300.100.1.1"], "310000000000003")
        self.assertEqual(san_attrs["2.5.4.12"], "1100")
        self.assertIn(str(self.device.pk), san_attrs["2.5.4.5"])

    def test_csr_requires_vat_number(self):
        from financials import zatca

        self.org.vat_number = ""
        self.org.save(update_fields=["vat_number"])
        self.device.refresh_from_db()
        with self.assertRaises(zatca.ZatcaCryptoError):
            zatca.generate_csr(zatca.generate_private_key(), self.device)


class ZatcaGenerationTests(ZatcaTestCase):
    def test_generation_signs_chains_and_advances_counter(self):
        from financials import zatca
        from financials.models import EInvoice, ZatcaCounter
        from financials.services import generate_e_invoice

        self.activate_device()
        e_invoice = generate_e_invoice(self.invoice, self.device)

        self.assertEqual(e_invoice.icv, 1)
        self.assertEqual(
            e_invoice.previous_invoice_hash, zatca.INITIAL_PREVIOUS_INVOICE_HASH
        )
        self.assertEqual(e_invoice.status, EInvoice.Status.PENDING)
        self.assertTrue(e_invoice.cryptographic_stamp)
        # The stored hash matches a recomputation over the signed document —
        # stamping and QR embedding must not move the hash.
        self.assertEqual(
            e_invoice.invoice_hash, zatca.compute_invoice_hash(e_invoice.ubl_xml)
        )
        fields = zatca.decode_qr_tlv(e_invoice.qr_code_tlv)
        self.assertEqual(fields[2].decode(), "310000000000003")
        self.assertIn(7, fields)  # stamp signature
        self.assertIn(8, fields)  # public key
        self.assertIn(9, fields)  # certificate signature
        self.assertIn("INV-Z-1", e_invoice.ubl_xml)

        counter = ZatcaCounter.objects.get(zatca_device=self.device)
        self.assertEqual(counter.current_icv, 1)
        self.assertEqual(counter.last_invoice_hash, e_invoice.invoice_hash)

        second_invoice = Invoice.objects.create(
            organization=self.org,
            invoice_number="INV-Z-2",
            subtotal=Decimal("100.00"),
            tax_amount=Decimal("15.00"),
            total_amount=Decimal("115.00"),
            amount_due=Decimal("115.00"),
            status=Invoice.Status.ISSUED,
        )
        second = generate_e_invoice(second_invoice, self.device)
        self.assertEqual(second.icv, 2)
        self.assertEqual(second.previous_invoice_hash, e_invoice.invoice_hash)

    def test_generation_is_idempotent_per_invoice(self):
        from financials.models import ZatcaCounter
        from financials.services import generate_e_invoice

        self.activate_device()
        first = generate_e_invoice(self.invoice, self.device)
        again = generate_e_invoice(self.invoice, self.device)
        self.assertEqual(first.pk, again.pk)
        counter = ZatcaCounter.objects.get(zatca_device=self.device)
        self.assertEqual(counter.current_icv, 1)

    def test_draft_invoice_is_rejected(self):
        from django.core.exceptions import ValidationError as DjangoValidationError

        from financials.services import generate_e_invoice

        self.activate_device()
        draft = Invoice.objects.create(
            organization=self.org,
            invoice_number="INV-Z-DRAFT",
            subtotal=Decimal("10.00"),
            total_amount=Decimal("11.50"),
            status=Invoice.Status.DRAFT,
        )
        with self.assertRaises(DjangoValidationError):
            generate_e_invoice(draft, self.device)

    def test_inactive_device_is_rejected(self):
        from django.core.exceptions import ValidationError as DjangoValidationError

        from financials.services import generate_e_invoice

        with self.assertRaises(DjangoValidationError):
            generate_e_invoice(self.invoice, self.device)

    def test_sale_items_become_invoice_lines(self):
        from commerce.models import Sale, SaleItem
        from organizations.models import Branch

        from financials.services import generate_e_invoice

        self.activate_device()
        branch = Branch.objects.create(organization=self.org, name="Main")
        sale = Sale.objects.create(
            organization=self.org,
            branch=branch,
            sale_number="S-1",
            subtotal=Decimal("200.00"),
            tax_amount=Decimal("30.00"),
            total_amount=Decimal("230.00"),
        )
        SaleItem.objects.create(
            sale=sale,
            description="Haircut",
            quantity=1,
            unit_price=Decimal("120.00"),
            total_price=Decimal("120.00"),
        )
        SaleItem.objects.create(
            sale=sale,
            description="Hair mask",
            quantity=2,
            unit_price=Decimal("40.00"),
            total_price=Decimal("80.00"),
        )
        invoice = Invoice.objects.create(
            organization=self.org,
            sale=sale,
            invoice_number="INV-Z-SALE",
            subtotal=Decimal("200.00"),
            tax_amount=Decimal("30.00"),
            total_amount=Decimal("230.00"),
            status=Invoice.Status.ISSUED,
        )
        e_invoice = generate_e_invoice(invoice, self.device)
        self.assertIn("Haircut", e_invoice.ubl_xml)
        self.assertIn("Hair mask", e_invoice.ubl_xml)


class ZatcaOnboardingTests(ZatcaTestCase):
    def _client(self, captured, response_json, status_code=200):
        from financials.gateways import ZatcaClient

        def handler(request):
            captured["url"] = str(request.url)
            captured["headers"] = dict(request.headers)
            captured["body"] = json.loads(request.content) if request.content else None
            return httpx.Response(status_code, json=response_json)

        return ZatcaClient(
            base_url="https://gw-fatoora.zatca.gov.sa/e-invoicing/developer-portal",
            transport=httpx.MockTransport(handler),
        )

    def test_onboarding_stores_encrypted_credentials(self):
        from financials import zatca
        from financials.models import ZatcaDevice
        from financials.services import onboard_zatca_device

        captured = {}
        client = self._client(
            captured,
            {
                "requestID": 1234,
                "binarySecurityToken": "compliance-token",
                "secret": "compliance-secret",
            },
        )
        with client:
            onboard_zatca_device(self.device, otp="123456", client=client)

        self.assertTrue(captured["url"].endswith("/compliance"))
        self.assertEqual(captured["headers"]["otp"], "123456")
        self.assertIn("csr", captured["body"])
        self.device.refresh_from_db()
        self.assertEqual(self.device.status, ZatcaDevice.Status.ONBOARDED)
        self.assertEqual(self.device.compliance_csid, "compliance-token")
        self.assertEqual(self.device.compliance_request_id, "1234")
        # Secrets land encrypted and decrypt back to the originals.
        self.assertNotIn("compliance-secret", self.device.csid_secret_encrypted)
        self.assertEqual(
            zatca.decrypt_secret(self.device.csid_secret_encrypted),
            "compliance-secret",
        )
        self.assertIn(
            "BEGIN PRIVATE KEY",
            zatca.decrypt_secret(self.device.private_key_encrypted),
        )

    def test_activation_decodes_certificate_and_creates_counter(self):
        import base64

        from financials import zatca
        from financials.models import ZatcaCounter, ZatcaDevice
        from financials.services import activate_zatca_device

        _, cert_b64 = _self_signed_device_credentials()
        self.device.status = ZatcaDevice.Status.ONBOARDED
        self.device.compliance_csid = "compliance-token"
        self.device.csid_secret_encrypted = zatca.encrypt_secret("compliance-secret")
        self.device.compliance_request_id = "1234"
        self.device.save()

        captured = {}
        client = self._client(
            captured,
            {
                "binarySecurityToken": base64.b64encode(cert_b64.encode()).decode(),
                "secret": "production-secret",
            },
        )
        with client:
            activate_zatca_device(self.device, client=client)

        self.assertTrue(captured["url"].endswith("/production/csids"))
        self.assertEqual(captured["body"], {"compliance_request_id": "1234"})
        self.device.refresh_from_db()
        self.assertEqual(self.device.status, ZatcaDevice.Status.ACTIVE)
        self.assertEqual(self.device.certificate, cert_b64)
        self.assertTrue(ZatcaCounter.objects.filter(zatca_device=self.device).exists())

    def test_onboarding_twice_is_rejected(self):
        from django.core.exceptions import ValidationError as DjangoValidationError

        from financials.services import onboard_zatca_device

        self.activate_device()
        with self.assertRaises(DjangoValidationError):
            onboard_zatca_device(self.device, otp="123456")


class ZatcaSubmissionTests(ZatcaTestCase):
    def _submit(self, response_json, status_code=200, captured=None):
        from financials.gateways import ZatcaClient
        from financials.services import generate_e_invoice, submit_e_invoice

        self.activate_device()
        e_invoice = generate_e_invoice(self.invoice, self.device)
        captured = captured if captured is not None else {}

        def handler(request):
            captured["url"] = str(request.url)
            captured["headers"] = dict(request.headers)
            captured["body"] = json.loads(request.content)
            return httpx.Response(status_code, json=response_json)

        client = ZatcaClient(
            csid="prod-csid-token",
            secret="prod-secret",
            base_url="https://gw-fatoora.zatca.gov.sa/e-invoicing/developer-portal",
            transport=httpx.MockTransport(handler),
        )
        with client:
            submit_e_invoice(e_invoice, client=client)
        e_invoice.refresh_from_db()
        return e_invoice, captured

    def test_reported_invoice_is_accepted_and_logged(self):
        from financials.models import EInvoice, EInvoiceSubmission

        e_invoice, captured = self._submit({"reportingStatus": "REPORTED"})
        self.assertTrue(captured["url"].endswith("/invoices/reporting/single"))
        self.assertEqual(captured["headers"]["clearance-status"], "0")
        self.assertTrue(captured["headers"]["authorization"].startswith("Basic "))
        self.assertEqual(captured["body"]["uuid"], e_invoice.uuid)
        self.assertEqual(captured["body"]["invoiceHash"], e_invoice.invoice_hash)
        self.assertEqual(e_invoice.status, EInvoice.Status.REPORTED)
        submission = e_invoice.submissions.get()
        self.assertEqual(submission.status, EInvoiceSubmission.Status.ACCEPTED)
        self.assertIsNotNone(submission.responded_at)

    def test_validation_rejection_is_final(self):
        from financials.gateways import ZatcaError
        from financials.models import EInvoice, EInvoiceSubmission

        with self.assertRaises(ZatcaError) as ctx:
            self._submit(
                {
                    "validationResults": {
                        "errorMessages": [{"message": "invalid invoice"}]
                    }
                },
                status_code=400,
            )
        self.assertFalse(ctx.exception.retryable)
        e_invoice = EInvoice.objects.get(invoice=self.invoice)
        self.assertEqual(e_invoice.status, EInvoice.Status.REJECTED)
        submission = e_invoice.submissions.get()
        self.assertEqual(submission.status, EInvoiceSubmission.Status.REJECTED)

    def test_server_fault_keeps_invoice_submittable(self):
        from financials.gateways import ZatcaError
        from financials.models import EInvoice, EInvoiceSubmission

        with self.assertRaises(ZatcaError) as ctx:
            self._submit({"message": "boom"}, status_code=500)
        self.assertTrue(ctx.exception.retryable)
        e_invoice = EInvoice.objects.get(invoice=self.invoice)
        self.assertEqual(e_invoice.status, EInvoice.Status.FAILED)
        submission = e_invoice.submissions.get()
        self.assertEqual(submission.status, EInvoiceSubmission.Status.FAILED)

    def test_already_reported_invoice_is_not_resubmitted(self):
        from financials.models import EInvoice
        from financials.services import generate_e_invoice, submit_e_invoice

        self.activate_device()
        e_invoice = generate_e_invoice(self.invoice, self.device)
        EInvoice.objects.filter(pk=e_invoice.pk).update(status=EInvoice.Status.REPORTED)
        e_invoice.refresh_from_db()
        # No client/transport — a network call would crash the test.
        submit_e_invoice(e_invoice)
        self.assertEqual(e_invoice.submissions.count(), 0)


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
class ZatcaApiTests(ZatcaTestCase):
    def test_staff_cannot_onboard_device(self):
        self.client.force_authenticate(self.staff)
        response = self.client.post(
            f"/api/v1/zatca-devices/{self.device.id}/onboard/", {"otp": "123456"}
        )
        self.assertEqual(response.status_code, 403)

    def test_onboard_requires_otp(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post(
            f"/api/v1/zatca-devices/{self.device.id}/onboard/", {}
        )
        self.assertEqual(response.status_code, 400)

    def test_owner_onboard_queues_and_worker_stores_csid(self):
        from financials.models import ZatcaDevice

        self.client.force_authenticate(self.owner)
        with mock.patch("financials.services.ZatcaClient") as factory:
            factory.return_value.request_compliance_csid.return_value = {
                "requestID": 99,
                "binarySecurityToken": "compliance-token",
                "secret": "compliance-secret",
            }
            response = self.client.post(
                f"/api/v1/zatca-devices/{self.device.id}/onboard/", {"otp": "654321"}
            )
        self.assertEqual(response.status_code, 202, response.data)
        self.device.refresh_from_db()
        self.assertEqual(self.device.status, ZatcaDevice.Status.ONBOARDED)

    def test_einvoice_action_generates_and_reports(self):
        from financials.models import EInvoice

        self.activate_device()
        self.client.force_authenticate(self.owner)
        with mock.patch("financials.services.ZatcaClient") as factory:
            factory.return_value.report_invoice.return_value = {
                "reportingStatus": "REPORTED"
            }
            response = self.client.post(f"/api/v1/invoices/{self.invoice.id}/einvoice/")
        self.assertEqual(response.status_code, 202, response.data)
        e_invoice = EInvoice.objects.get(invoice=self.invoice)
        self.assertEqual(e_invoice.status, EInvoice.Status.REPORTED)
        self.assertEqual(e_invoice.icv, 1)

    def test_einvoice_action_requires_active_device(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post(f"/api/v1/invoices/{self.invoice.id}/einvoice/")
        self.assertEqual(response.status_code, 400)

    def test_device_api_never_exposes_key_material(self):
        device = self.activate_device()
        self.client.force_authenticate(self.owner)
        response = self.client.get(f"/api/v1/zatca-devices/{device.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("private_key_encrypted", response.data)
        self.assertNotIn("csid_secret_encrypted", response.data)


class DocumentNumberingTests(APITestCase):
    """Server-side, gap-free, org-scoped document numbering (audit issue #3)."""

    @classmethod
    def setUpTestData(cls):
        from organizations.models import Branch, Organization

        cls.org = Organization.objects.create(name="Glow Spa", slug="glow-num")
        cls.org2 = Organization.objects.create(name="Rival", slug="rival-num")
        cls.branch = Branch.objects.create(organization=cls.org, name="Main")

    def test_sequential_per_organization_and_type(self):
        from datetime import datetime, timezone as dt_tz

        from financials.models import DocumentSequence
        from financials.services import next_document_number

        when = datetime(2026, 1, 5, tzinfo=dt_tz.utc)
        n1 = next_document_number(
            organization=self.org,
            document_type=DocumentSequence.DocumentType.INVOICE,
            when=when,
        )
        n2 = next_document_number(
            organization=self.org,
            document_type=DocumentSequence.DocumentType.INVOICE,
            when=when,
        )
        self.assertEqual(n1, "INV-2026-00001")
        self.assertEqual(n2, "INV-2026-00002")

    def test_scopes_are_independent(self):
        from financials.models import DocumentSequence
        from financials.services import next_document_number

        # Different org, different type, and different branch each get their own
        # counter starting at 1.
        a = next_document_number(
            organization=self.org,
            document_type=DocumentSequence.DocumentType.SALE,
        )
        b = next_document_number(
            organization=self.org2,
            document_type=DocumentSequence.DocumentType.SALE,
        )
        c = next_document_number(
            organization=self.org,
            document_type=DocumentSequence.DocumentType.SALE,
            branch=self.branch,
        )
        self.assertTrue(a.endswith("00001"))
        self.assertTrue(b.endswith("00001"))
        self.assertTrue(c.endswith("00001"))
        # Only one org-wide (branch-less) sequence row exists for the scope.
        self.assertEqual(
            DocumentSequence.objects.filter(
                organization=self.org,
                document_type=DocumentSequence.DocumentType.SALE,
                branch__isnull=True,
            ).count(),
            1,
        )

    def test_invoice_endpoint_assigns_number_and_ignores_client_value(self):
        from accounts.models import UserRole

        user = User.objects.create_user(email="num@namaa.sa", password="pass12345")
        UserRole.objects.create(
            user=user, organization=self.org, role=UserRole.Role.OWNER
        )
        self.client.force_authenticate(user)
        response = self.client.post(
            "/api/v1/invoices/",
            {
                "organization": str(self.org.id),
                "invoice_number": "CLIENT-CHOSEN",  # must be ignored
                "total_amount": "100.00",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertNotEqual(response.data["invoice_number"], "CLIENT-CHOSEN")
        self.assertTrue(response.data["invoice_number"].startswith("INV-"))


class LedgerPostingTests(APITestCase):
    """Double-entry enforcement: balanced, multi-line, immutable (issue #8)."""

    @classmethod
    def setUpTestData(cls):
        from financials.models import LedgerAccount

        cls.org = Organization.objects.create(name="Books Inc", slug="books")
        cls.other = Organization.objects.create(name="Other", slug="other-led")
        cls.owner = User.objects.create_user(email="led@namaa.sa", password="pass12345")
        UserRole.objects.create(
            user=cls.owner, organization=cls.org, role=UserRole.Role.OWNER
        )
        cls.cash = LedgerAccount.objects.create(
            organization=cls.org,
            code="1000",
            name="Cash",
            account_type=LedgerAccount.AccountType.ASSET,
        )
        cls.revenue = LedgerAccount.objects.create(
            organization=cls.org,
            code="4000",
            name="Revenue",
            account_type=LedgerAccount.AccountType.REVENUE,
        )
        cls.foreign = LedgerAccount.objects.create(
            organization=cls.other,
            code="1000",
            name="Cash",
            account_type=LedgerAccount.AccountType.ASSET,
        )

    def test_balanced_transaction_posts_with_shared_id(self):
        from financials.services import post_journal_entry

        entries = post_journal_entry(
            organization=self.org,
            lines=[
                {"account": self.cash, "debit": Decimal("100"), "credit": Decimal("0")},
                {
                    "account": self.revenue,
                    "debit": Decimal("0"),
                    "credit": Decimal("100"),
                },
            ],
        )
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0].transaction_id, entries[1].transaction_id)

    def test_unbalanced_transaction_is_rejected(self):
        from django.core.exceptions import ValidationError as DjangoValidationError

        from financials.services import post_journal_entry

        with self.assertRaises(DjangoValidationError):
            post_journal_entry(
                organization=self.org,
                lines=[
                    {"account": self.cash, "debit": Decimal("100")},
                    {"account": self.revenue, "credit": Decimal("90")},
                ],
            )

    def test_single_line_is_rejected(self):
        from django.core.exceptions import ValidationError as DjangoValidationError

        from financials.services import post_journal_entry

        with self.assertRaises(DjangoValidationError):
            post_journal_entry(
                organization=self.org,
                lines=[{"account": self.cash, "debit": Decimal("100")}],
            )

    def test_two_sided_line_is_rejected(self):
        from django.core.exceptions import ValidationError as DjangoValidationError

        from financials.services import post_journal_entry

        with self.assertRaises(DjangoValidationError):
            post_journal_entry(
                organization=self.org,
                lines=[
                    {
                        "account": self.cash,
                        "debit": Decimal("100"),
                        "credit": Decimal("100"),
                    },
                    {"account": self.revenue, "credit": Decimal("100")},
                ],
            )

    def test_foreign_account_is_rejected(self):
        from django.core.exceptions import ValidationError as DjangoValidationError

        from financials.services import post_journal_entry

        with self.assertRaises(DjangoValidationError):
            post_journal_entry(
                organization=self.org,
                lines=[
                    {"account": self.cash, "debit": Decimal("100")},
                    {"account": self.foreign, "credit": Decimal("100")},
                ],
            )

    def test_api_posts_balanced_batch_and_rejects_single_line(self):
        self.client.force_authenticate(self.owner)
        ok = self.client.post(
            "/api/v1/ledger-entries/",
            [
                {
                    "organization": str(self.org.id),
                    "account": str(self.cash.id),
                    "debit": "100.00",
                    "credit": "0.00",
                },
                {
                    "organization": str(self.org.id),
                    "account": str(self.revenue.id),
                    "debit": "0.00",
                    "credit": "100.00",
                },
            ],
            format="json",
        )
        self.assertEqual(ok.status_code, 201, ok.data)
        self.assertEqual(len(ok.data), 2)

        bad = self.client.post(
            "/api/v1/ledger-entries/",
            {
                "organization": str(self.org.id),
                "account": str(self.cash.id),
                "debit": "100.00",
                "credit": "0.00",
            },
            format="json",
        )
        self.assertEqual(bad.status_code, 400)


class AuditTrailTests(MoyasarTestCase):
    """Audit records are written for sensitive operations (issue #9)."""

    def test_completed_payment_writes_audit(self):
        from core.models import AuditLog
        from financials.services import process_payment_webhook_event

        event = PaymentWebhookEvent.objects.create(
            gateway=Gateway.MOYASAR,
            gateway_event_id="evt_audit",
            event_type="payment_paid",
            payload={"data": {"id": "pay_123", "status": "paid", "amount": 20000}},
        )
        process_payment_webhook_event(event)
        self.assertTrue(
            AuditLog.objects.filter(
                action="payment.completed", entity_id=self.payment.id
            ).exists()
        )

    def test_refund_writes_audit_with_actor(self):
        from core.models import AuditLog

        refund = Refund.objects.create(
            organization=self.org, payment=self.payment, amount=Decimal("200.00")
        )

        def handler(request):
            return httpx.Response(
                200, json={"id": "pay_123", "status": "refunded", "refunded": 20000}
            )

        with MoyasarClient(
            secret_key="sk", transport=httpx.MockTransport(handler)
        ) as client:
            execute_moyasar_refund(refund, approver=self.owner, client=client)
        entry = AuditLog.objects.get(action="payment.refund_processed")
        self.assertEqual(entry.user_id, self.owner.id)
        self.assertEqual(entry.entity_id, refund.id)


class ZatcaReversalAndImmutabilityTests(ZatcaTestCase):
    """ZATCA immutability + the credit/debit-note reversal pipeline (P3)."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        from organizations.models import Branch

        cls.accountant = User.objects.create_user(
            email="zatca-acct@namaa.sa", password="pass12345"
        )
        UserRole.objects.create(
            user=cls.accountant, organization=cls.org, role=UserRole.Role.ACCOUNTANT
        )
        cls.marketer = User.objects.create_user(
            email="zatca-mkt@namaa.sa", password="pass12345"
        )
        UserRole.objects.create(
            user=cls.marketer, organization=cls.org, role=UserRole.Role.MARKETER
        )
        cls.branch = Branch.objects.create(organization=cls.org, name="Main")

    def _report_invoice(self):
        """Generate the invoice's e-invoice so it becomes ZATCA-locked."""
        from financials.services import generate_e_invoice

        self.activate_device()
        return generate_e_invoice(self.invoice, self.device)

    # --- Immutability -----------------------------------------------------

    def test_invoice_patch_rejected_once_reported(self):
        self._report_invoice()
        self.client.force_authenticate(self.owner)
        response = self.client.patch(
            f"/api/v1/invoices/{self.invoice.id}/",
            {"due_date": "2026-12-31"},
            format="json",
        )
        self.assertEqual(response.status_code, 409, response.data)

    def test_invoice_editable_before_it_is_reported(self):
        self.client.force_authenticate(self.owner)
        response = self.client.patch(
            f"/api/v1/invoices/{self.invoice.id}/",
            {"due_date": "2026-12-31"},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)

    def test_sale_patch_rejected_when_its_invoice_is_reported(self):
        from commerce.models import Sale

        sale = Sale.objects.create(
            organization=self.org,
            branch=self.branch,
            sale_number="SALE-Z-1",
            total_amount=Decimal("230.00"),
            status=Sale.Status.COMPLETED,
        )
        self.invoice.sale = sale
        self.invoice.save(update_fields=["sale"])
        self._report_invoice()

        self.client.force_authenticate(self.owner)
        response = self.client.patch(
            f"/api/v1/sales/{sale.id}/",
            {"notes": "tampering"},
            format="json",
        )
        self.assertEqual(response.status_code, 409, response.data)

    # --- Credit-note pipeline --------------------------------------------

    def test_full_credit_note_builds_381_with_billing_reference(self):
        from financials.models import EInvoice
        from financials.services import generate_note_e_invoice, issue_credit_note

        invoice_e = self._report_invoice()
        note = issue_credit_note(invoice=self.invoice, full=True, reason_text="Refund")
        self.assertEqual(note.amount, Decimal("230.00"))

        note_e = generate_note_e_invoice(
            note, self.device, document_type=EInvoice.DocumentType.CREDIT_NOTE
        )
        self.assertEqual(note_e.document_type, EInvoice.DocumentType.CREDIT_NOTE)
        # Same chain as the invoice: next ICV, PIH = the invoice's hash.
        self.assertEqual(note_e.icv, invoice_e.icv + 1)
        self.assertEqual(note_e.previous_invoice_hash, invoice_e.invoice_hash)
        self.assertTrue(note_e.invoice_hash)
        self.assertIn("InvoiceTypeCode", note_e.ubl_xml)
        self.assertIn(">381<", note_e.ubl_xml)
        self.assertIn("BillingReference", note_e.ubl_xml)
        self.assertIn(self.invoice.invoice_number, note_e.ubl_xml)

    def test_debit_note_builds_383(self):
        from financials.models import EInvoice
        from financials.services import generate_note_e_invoice, issue_debit_note

        self._report_invoice()
        note = issue_debit_note(
            invoice=self.invoice, amount=Decimal("57.50"), reason_text="Extra"
        )
        note_e = generate_note_e_invoice(
            note, self.device, document_type=EInvoice.DocumentType.DEBIT_NOTE
        )
        self.assertEqual(note_e.document_type, EInvoice.DocumentType.DEBIT_NOTE)
        self.assertIn(">383<", note_e.ubl_xml)

    def test_credit_notes_cannot_exceed_invoice_total(self):
        from django.core.exceptions import ValidationError

        from financials.services import issue_credit_note

        self._report_invoice()
        issue_credit_note(invoice=self.invoice, full=True)  # credits the whole 230
        with self.assertRaises(ValidationError):
            issue_credit_note(invoice=self.invoice, amount=Decimal("0.01"))

    def test_credit_note_requires_a_reported_invoice(self):
        from django.core.exceptions import ValidationError

        from financials.services import issue_credit_note

        # No e-invoice generated yet -> nothing to reverse.
        with self.assertRaises(ValidationError):
            issue_credit_note(invoice=self.invoice, full=True)

    # --- Authorization (explicit role set, not rank) ----------------------

    def test_accountant_can_issue_credit_note(self):
        self._report_invoice()
        self.client.force_authenticate(self.accountant)
        response = self.client.post(
            f"/api/v1/invoices/{self.invoice.id}/credit-note/",
            {"full": True, "reason_text": "Refund"},
            format="json",
        )
        self.assertEqual(response.status_code, 202, response.data)
        self.assertEqual(self.invoice.credit_notes.count(), 1)

    def test_marketer_cannot_issue_credit_note_despite_same_rank(self):
        # Marketer shares rank 40 with Accountant; the explicit role set must
        # still exclude them.
        self._report_invoice()
        self.client.force_authenticate(self.marketer)
        response = self.client.post(
            f"/api/v1/invoices/{self.invoice.id}/credit-note/",
            {"full": True},
            format="json",
        )
        self.assertEqual(response.status_code, 403, response.data)
        self.assertEqual(self.invoice.credit_notes.count(), 0)
