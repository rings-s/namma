"""Celery tasks for the financial domain: payments and ZATCA e-invoicing."""

from celery import shared_task
from celery.utils.log import get_task_logger
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone

from financials.gateways import MoyasarError, ZatcaError
from financials.models import (
    EInvoice,
    Invoice,
    PaymentWebhookEvent,
    Refund,
    ZatcaDevice,
)
from financials.services import (
    activate_zatca_device,
    execute_moyasar_refund,
    generate_e_invoice,
    onboard_zatca_device,
    process_payment_webhook_event,
    submit_e_invoice,
)

logger = get_task_logger(__name__)


@shared_task(bind=True, max_retries=3)
def process_payment_webhook_event_task(self, event_id):
    """Process one stored, still-pending webhook event."""
    event = PaymentWebhookEvent.objects.filter(
        pk=event_id,
        processing_status=PaymentWebhookEvent.ProcessingStatus.PENDING,
    ).first()
    if event is None:
        logger.info("Webhook event %s gone or already handled.", event_id)
        return
    try:
        process_payment_webhook_event(event)
    except Exception as exc:
        PaymentWebhookEvent.objects.filter(pk=event.pk).update(
            processing_status=PaymentWebhookEvent.ProcessingStatus.FAILED,
            processed_at=timezone.now(),
        )
        logger.exception("Webhook event %s failed: %s", event_id, exc)
        raise


@shared_task
def execute_moyasar_refund_task(refund_id, approver_id):
    """Execute one pending refund.

    Deliberately no automatic retry: re-POSTing a refund after a timeout
    could refund twice. A failed attempt leaves the refund pending for an
    explicit re-execution by a manager.
    """
    refund = Refund.objects.select_related("payment").filter(pk=refund_id).first()
    approver = get_user_model().objects.filter(pk=approver_id).first()
    if refund is None or approver is None:
        logger.info("Refund %s or approver %s gone.", refund_id, approver_id)
        return
    try:
        execute_moyasar_refund(refund, approver)
    except ValidationError as exc:
        logger.warning("Refund %s no longer executable: %s", refund_id, exc)
    except MoyasarError as exc:
        logger.error("Refund %s rejected/failed at Moyasar: %s", refund_id, exc)


@shared_task
def onboard_zatca_device_task(device_id, otp):
    """Request the compliance CSID for a pending device.

    Deliberately no automatic retry: the portal OTP is short-lived and a
    failed exchange needs a fresh OTP from an operator, not a blind retry.
    """
    device = (
        ZatcaDevice.objects.select_related("organization", "branch")
        .filter(pk=device_id)
        .first()
    )
    if device is None:
        logger.info("ZATCA device %s gone.", device_id)
        return
    try:
        onboard_zatca_device(device, otp)
    except ValidationError as exc:
        logger.warning("ZATCA device %s not onboardable: %s", device_id, exc)
    except ZatcaError as exc:
        logger.error("ZATCA compliance CSID for device %s failed: %s", device_id, exc)


@shared_task
def activate_zatca_device_task(device_id):
    """Trade the compliance CSID for the production CSID. No automatic
    retry — a rejection here means the compliance steps are incomplete."""
    device = ZatcaDevice.objects.filter(pk=device_id).first()
    if device is None:
        logger.info("ZATCA device %s gone.", device_id)
        return
    try:
        activate_zatca_device(device)
    except ValidationError as exc:
        logger.warning("ZATCA device %s not activatable: %s", device_id, exc)
    except ZatcaError as exc:
        logger.error("ZATCA production CSID for device %s failed: %s", device_id, exc)


@shared_task(bind=True, max_retries=5)
def submit_e_invoice_task(self, e_invoice_id):
    """Submit one generated e-invoice to Fatoora.

    Retries with backoff on transport faults and throttling only — Fatoora
    deduplicates on UUID + invoice hash, so at-least-once delivery cannot
    double-report. Definitive rejections are final and logged.
    """
    e_invoice = (
        EInvoice.objects.select_related("zatca_device", "organization")
        .filter(pk=e_invoice_id)
        .first()
    )
    if e_invoice is None:
        logger.info("E-invoice %s gone.", e_invoice_id)
        return
    try:
        submit_e_invoice(e_invoice)
    except ValidationError as exc:
        logger.warning("E-invoice %s not submittable: %s", e_invoice_id, exc)
    except ZatcaError as exc:
        if exc.retryable:
            raise self.retry(exc=exc, countdown=min(60 * 2**self.request.retries, 900))
        logger.error("E-invoice %s rejected by ZATCA: %s", e_invoice_id, exc)


@shared_task
def generate_and_submit_e_invoice_task(invoice_id, device_id):
    """Generate the e-invoice locally (atomic, idempotent) and hand it to
    the submission task."""
    invoice = (
        Invoice.objects.select_related("organization", "customer", "sale")
        .filter(pk=invoice_id)
        .first()
    )
    device = (
        ZatcaDevice.objects.select_related("organization").filter(pk=device_id).first()
    )
    if invoice is None or device is None:
        logger.info("Invoice %s or ZATCA device %s gone.", invoice_id, device_id)
        return
    try:
        e_invoice = generate_e_invoice(invoice, device)
    except ValidationError as exc:
        logger.warning("Invoice %s not e-invoiceable: %s", invoice_id, exc)
        return
    submit_e_invoice_task.delay(str(e_invoice.pk))
