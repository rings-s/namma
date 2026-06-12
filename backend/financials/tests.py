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
