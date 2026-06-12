"""Financial domain services: Moyasar webhook processing, refunds and the
ZATCA Phase-2 e-invoicing pipeline.

Webhook events are stored first (idempotently, keyed on the gateway event
id) and then processed; processing touches only local rows, inside one
transaction, so a crash can never half-apply an event.

The ZATCA pipeline splits into a local, atomic *generation* step (ICV/PIH
chain advanced under a counter row lock, XML built, stamped and QR-coded)
and a remote *submission* step (reporting or clearance) that a Celery task
retries only on transport faults — Fatoora deduplicates on the invoice
UUID + hash, so at-least-once submission is safe.
"""

import base64
import uuid as uuid_module

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from financials import zatca
from financials.gateways import (
    MoyasarClient,
    MoyasarError,
    ZatcaClient,
    ZatcaError,
    from_halalas,
    to_halalas,
)
from financials.models import (
    EInvoice,
    EInvoiceSubmission,
    Gateway,
    Invoice,
    Payment,
    PaymentIntent,
    PaymentWebhookEvent,
    Refund,
    ZatcaCounter,
    ZatcaDevice,
)

#: Moyasar payment statuses -> local Payment statuses.
MOYASAR_STATUS_MAP = {
    "paid": Payment.Status.COMPLETED,
    "captured": Payment.Status.COMPLETED,
    "failed": Payment.Status.FAILED,
    "voided": Payment.Status.FAILED,
    "refunded": Payment.Status.REFUNDED,
}


def _apply_to_invoice(invoice_id, amount):
    """Add a completed payment's amount to its invoice under a row lock."""
    invoice = Invoice.objects.select_for_update().get(pk=invoice_id)
    invoice.amount_paid += amount
    invoice.amount_due = invoice.total_amount - invoice.amount_paid
    if invoice.amount_due <= 0:
        invoice.status = Invoice.Status.PAID
        invoice.paid_at = timezone.now()
    else:
        invoice.status = Invoice.Status.PARTIALLY_PAID
    invoice.save(
        update_fields=["amount_paid", "amount_due", "status", "paid_at", "updated_at"]
    )


def _payment_from_intent(intent_id, data):
    """Create a Payment for a gateway charge initiated through an intent."""
    intent = PaymentIntent.objects.select_for_update().filter(pk=intent_id).first()
    if intent is None:
        return None
    intent.status = PaymentIntent.Status.SUCCEEDED
    intent.gateway_intent_id = data.get("id", "")
    intent.save(update_fields=["status", "gateway_intent_id", "updated_at"])
    return Payment.objects.create(
        organization=intent.organization,
        invoice=intent.invoice,
        customer=intent.customer,
        payment_method=intent.payment_method or "card",
        gateway=Gateway.MOYASAR,
        gateway_transaction_id=data.get("id", ""),
        amount=from_halalas(data.get("amount", 0)),
        currency=data.get("currency", intent.currency),
        status=Payment.Status.PENDING,
    )


@transaction.atomic
def process_payment_webhook_event(event):
    """Apply one stored webhook event to the payment domain. Idempotent:
    callers only invoke this for newly created event rows."""
    data = event.payload.get("data", {})
    gateway_payment_id = data.get("id", "")
    payment = (
        Payment.objects.select_for_update()
        .filter(gateway=Gateway.MOYASAR, gateway_transaction_id=gateway_payment_id)
        .first()
    )
    if payment is None:
        intent_id = (data.get("metadata") or {}).get("payment_intent_id")
        if intent_id:
            payment = _payment_from_intent(intent_id, data)
    if payment is None:
        event.processing_status = PaymentWebhookEvent.ProcessingStatus.IGNORED
        event.processed_at = timezone.now()
        event.save(update_fields=["processing_status", "processed_at", "updated_at"])
        return event

    new_status = MOYASAR_STATUS_MAP.get(data.get("status", ""))
    if new_status == Payment.Status.COMPLETED and payment.status != new_status:
        payment.status = new_status
        payment.paid_at = timezone.now()
        if payment.invoice_id is not None:
            _apply_to_invoice(payment.invoice_id, payment.amount)
    elif new_status == Payment.Status.REFUNDED:
        refunded = from_halalas(data.get("refunded", 0))
        payment.status = (
            Payment.Status.REFUNDED
            if refunded >= payment.amount
            else Payment.Status.PARTIALLY_REFUNDED
        )
        payment.refunded_at = timezone.now()
    elif new_status is not None:
        payment.status = new_status
    payment.save(update_fields=["status", "paid_at", "refunded_at", "updated_at"])

    event.organization = payment.organization
    event.processing_status = PaymentWebhookEvent.ProcessingStatus.PROCESSED
    event.processed_at = timezone.now()
    event.save(
        update_fields=[
            "organization",
            "processing_status",
            "processed_at",
            "updated_at",
        ]
    )
    return event


def validate_refund_executable(refund):
    """Cheap, local preconditions — safe to run inside a request."""
    payment = refund.payment
    if payment.gateway != Gateway.MOYASAR or not payment.gateway_transaction_id:
        raise ValidationError("This payment was not processed through Moyasar.")
    if refund.status not in (Refund.Status.PENDING, Refund.Status.APPROVED):
        raise ValidationError("This refund has already been processed or rejected.")
    if refund.amount > payment.amount:
        raise ValidationError("Refund amount exceeds the payment amount.")


def execute_moyasar_refund(refund, approver, client=None):
    """Push an approved refund to Moyasar and record the outcome."""
    validate_refund_executable(refund)
    payment = refund.payment

    amount_halalas = (
        None
        if refund.refund_type == Refund.RefundType.FULL
        else to_halalas(refund.amount)
    )
    own_client = client is None
    client = client or MoyasarClient()
    try:
        result = client.refund_payment(payment.gateway_transaction_id, amount_halalas)
    finally:
        if own_client:
            client.close()

    now = timezone.now()
    with transaction.atomic():
        refund.status = Refund.Status.PROCESSED
        refund.refunded_at = now
        refund.approver = approver
        refund.approved_at = now
        refund.save(
            update_fields=[
                "status",
                "refunded_at",
                "approver",
                "approved_at",
                "updated_at",
            ]
        )
        refunded_total = from_halalas(result.get("refunded", 0)) or refund.amount
        payment.status = (
            Payment.Status.REFUNDED
            if refunded_total >= payment.amount
            else Payment.Status.PARTIALLY_REFUNDED
        )
        payment.refunded_at = now
        payment.save(update_fields=["status", "refunded_at", "updated_at"])
    return refund


# ---------------------------------------------------------------------------
# ZATCA device onboarding
# ---------------------------------------------------------------------------


def onboard_zatca_device(device, otp, client=None):
    """Step 1 of onboarding: generate the device key, build the ZATCA CSR
    and trade it (plus the Fatoora portal OTP) for the compliance CSID.

    The private key and the CSID secret are stored Fernet-encrypted; the
    plaintext never leaves this function.
    """
    if device.status not in (ZatcaDevice.Status.PENDING, ZatcaDevice.Status.REVOKED):
        raise ValidationError("This device has already been onboarded.")

    private_key = zatca.generate_private_key()
    csr_b64 = zatca.csr_to_base64(zatca.generate_csr(private_key, device))

    own_client = client is None
    client = client or ZatcaClient()
    try:
        result = client.request_compliance_csid(csr_b64, otp)
    finally:
        if own_client:
            client.close()

    device.private_key_encrypted = zatca.encrypt_secret(
        zatca.private_key_to_pem(private_key)
    )
    device.compliance_csid = result["binarySecurityToken"]
    device.csid_secret_encrypted = zatca.encrypt_secret(result["secret"])
    device.compliance_request_id = str(result["requestID"])
    device.status = ZatcaDevice.Status.ONBOARDED
    device.save(
        update_fields=[
            "private_key_encrypted",
            "compliance_csid",
            "csid_secret_encrypted",
            "compliance_request_id",
            "status",
            "updated_at",
        ]
    )
    return device


def activate_zatca_device(device, client=None):
    """Step 2 of onboarding: trade the compliance CSID for the production
    CSID. (In production ZATCA expects the compliance check documents to
    have been submitted in between; the sandbox issues the CSID directly.)
    """
    if device.status != ZatcaDevice.Status.ONBOARDED:
        raise ValidationError("The device must hold a compliance CSID first.")

    own_client = client is None
    client = client or ZatcaClient(
        csid=device.compliance_csid,
        secret=zatca.decrypt_secret(device.csid_secret_encrypted),
    )
    try:
        result = client.request_production_csid(device.compliance_request_id)
    finally:
        if own_client:
            client.close()

    device.production_csid = result["binarySecurityToken"]
    device.csid_secret_encrypted = zatca.encrypt_secret(result["secret"])
    # The production CSID decodes to the base64-DER device certificate that
    # stamps every simplified invoice and feeds QR tags 8 and 9.
    device.certificate = base64.b64decode(device.production_csid).decode()
    device.status = ZatcaDevice.Status.ACTIVE
    device.onboarded_at = timezone.now()
    device.save(
        update_fields=[
            "production_csid",
            "csid_secret_encrypted",
            "certificate",
            "status",
            "onboarded_at",
            "updated_at",
        ]
    )
    ZatcaCounter.objects.get_or_create(zatca_device=device)
    return device


# ---------------------------------------------------------------------------
# E-invoice generation (local, atomic)
# ---------------------------------------------------------------------------


def validate_e_invoice_generable(invoice, device):
    """Cheap, local preconditions — safe to run inside a request."""
    if invoice.status in (Invoice.Status.DRAFT, Invoice.Status.VOID):
        raise ValidationError("Draft and void invoices cannot be reported to ZATCA.")
    if invoice.organization_id != device.organization_id:
        raise ValidationError("The device belongs to a different organization.")
    if device.status != ZatcaDevice.Status.ACTIVE:
        raise ValidationError("The ZATCA device is not active.")
    if not invoice.organization.vat_number:
        raise ValidationError("The organization has no VAT number configured.")


@transaction.atomic
def generate_e_invoice(invoice, device, invoice_type=None):
    """Create the signed, QR-coded EInvoice for an invoice. Idempotent:
    an existing non-failed e-invoice for the same invoice is returned
    untouched, so the ICV chain never skips or forks on retries.
    """

    def existing_e_invoice():
        return (
            invoice.e_invoices.exclude(status=EInvoice.Status.FAILED)
            .order_by("created_at")
            .first()
        )

    existing = existing_e_invoice()
    if existing is not None:
        return existing

    validate_e_invoice_generable(invoice, device)
    invoice_type = invoice_type or EInvoice.InvoiceType.SIMPLIFIED

    counter, _ = ZatcaCounter.objects.select_for_update().get_or_create(
        zatca_device=device
    )
    # Re-check under the counter lock: a concurrent generation for the same
    # invoice serializes here, and the loser must reuse the winner's row
    # instead of burning a second ICV.
    existing = existing_e_invoice()
    if existing is not None:
        return existing
    icv = counter.current_icv + 1
    previous_hash = counter.last_invoice_hash or zatca.INITIAL_PREVIOUS_INVOICE_HASH

    e_invoice = EInvoice(
        organization=invoice.organization,
        invoice=invoice,
        zatca_device=device,
        uuid=str(uuid_module.uuid4()),
        invoice_type=invoice_type,
        previous_invoice_hash=previous_hash,
        icv=icv,
        status=EInvoice.Status.PENDING,
    )
    xml = zatca.build_invoice_xml(e_invoice)
    invoice_hash = zatca.compute_invoice_hash(xml)
    issued_at = invoice.issued_at or invoice.created_at
    organization = invoice.organization

    signature_b64 = None
    if invoice_type == EInvoice.InvoiceType.SIMPLIFIED:
        private_key = zatca.private_key_from_pem(
            zatca.decrypt_secret(device.private_key_encrypted)
        )
        xml, signature_b64 = zatca.stamp_invoice(
            xml, invoice_hash, device.certificate, private_key, issued_at
        )
        qr_b64 = zatca.build_qr_tlv(
            seller_name=organization.name,
            vat_number=organization.vat_number,
            timestamp=issued_at,
            total_with_vat=invoice.total_amount,
            vat_amount=invoice.tax_amount,
            invoice_hash=invoice_hash,
            signature_b64=signature_b64,
            public_key_der=zatca.certificate_public_key_der(device.certificate),
            certificate_signature=zatca.certificate_signature_bytes(device.certificate),
        )
    else:
        # Standard invoices are cleared (and stamped) by ZATCA; until the
        # cleared XML comes back the QR carries the base tags only.
        qr_b64 = zatca.build_qr_tlv(
            seller_name=organization.name,
            vat_number=organization.vat_number,
            timestamp=issued_at,
            total_with_vat=invoice.total_amount,
            vat_amount=invoice.tax_amount,
            invoice_hash=invoice_hash,
        )
    xml = zatca.embed_qr(xml, qr_b64)

    e_invoice.ubl_xml = xml
    e_invoice.invoice_hash = invoice_hash
    e_invoice.cryptographic_stamp = signature_b64 or ""
    e_invoice.qr_code_tlv = qr_b64
    e_invoice.save()

    counter.current_icv = icv
    counter.last_invoice_hash = invoice_hash
    counter.save(update_fields=["current_icv", "last_invoice_hash", "updated_at"])
    return e_invoice


# ---------------------------------------------------------------------------
# E-invoice submission (remote)
# ---------------------------------------------------------------------------

_SUBMITTABLE_STATUSES = (EInvoice.Status.PENDING, EInvoice.Status.FAILED)


def submit_e_invoice(e_invoice, client=None):
    """Report (simplified) or clear (standard) one generated e-invoice.

    Each attempt is recorded as an EInvoiceSubmission. Transport faults and
    throttling raise a retryable ZatcaError with the e-invoice left
    submittable; definitive rejections finalize it as REJECTED. Fatoora
    deduplicates on UUID + hash, so retried submissions cannot double-report.
    """
    if e_invoice.status not in _SUBMITTABLE_STATUSES:
        return e_invoice

    device = e_invoice.zatca_device
    if device is None or device.status != ZatcaDevice.Status.ACTIVE:
        raise ValidationError("The e-invoice has no active ZATCA device.")

    submission = EInvoiceSubmission.objects.create(
        e_invoice=e_invoice,
        status=EInvoiceSubmission.Status.SUBMITTED,
        retry_count=e_invoice.submissions.count(),
        submitted_at=timezone.now(),
    )
    invoice_b64 = base64.b64encode(e_invoice.ubl_xml.encode()).decode()

    own_client = client is None
    client = client or ZatcaClient(
        csid=device.production_csid,
        secret=zatca.decrypt_secret(device.csid_secret_encrypted),
    )
    try:
        if e_invoice.invoice_type == EInvoice.InvoiceType.SIMPLIFIED:
            result = client.report_invoice(
                e_invoice.invoice_hash, e_invoice.uuid, invoice_b64
            )
        else:
            result = client.clear_invoice(
                e_invoice.invoice_hash, e_invoice.uuid, invoice_b64
            )
    except ZatcaError as exc:
        now = timezone.now()
        submission.status = (
            EInvoiceSubmission.Status.FAILED
            if exc.retryable
            else EInvoiceSubmission.Status.REJECTED
        )
        submission.api_response = exc.payload
        submission.responded_at = now
        submission.save(
            update_fields=["status", "api_response", "responded_at", "updated_at"]
        )
        e_invoice.status = (
            EInvoice.Status.FAILED if exc.retryable else EInvoice.Status.REJECTED
        )
        e_invoice.save(update_fields=["status", "updated_at"])
        raise
    finally:
        if own_client:
            client.close()

    now = timezone.now()
    reporting_status = result.get("reportingStatus") or result.get("clearanceStatus")
    accepted = reporting_status in ("REPORTED", "CLEARED")
    submission.status = (
        EInvoiceSubmission.Status.ACCEPTED
        if accepted
        else EInvoiceSubmission.Status.REJECTED
    )
    submission.api_response = result
    submission.responded_at = now
    submission.save(
        update_fields=["status", "api_response", "responded_at", "updated_at"]
    )

    if accepted:
        if reporting_status == "CLEARED":
            e_invoice.status = EInvoice.Status.CLEARED
            cleared = result.get("clearedInvoice")
            if cleared:
                # The cleared document (ZATCA-stamped) replaces ours as the
                # legal artifact.
                e_invoice.ubl_xml = base64.b64decode(cleared).decode()
        else:
            e_invoice.status = EInvoice.Status.REPORTED
    else:
        e_invoice.status = EInvoice.Status.REJECTED
    e_invoice.save(update_fields=["status", "ubl_xml", "updated_at"])
    return e_invoice


__all__ = [
    "MoyasarError",
    "ZatcaError",
    "activate_zatca_device",
    "execute_moyasar_refund",
    "generate_e_invoice",
    "onboard_zatca_device",
    "process_payment_webhook_event",
    "submit_e_invoice",
    "validate_e_invoice_generable",
]
