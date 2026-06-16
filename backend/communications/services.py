"""Messaging services: SMS through Taqnyat, email through Amazon SES.

A dispatch is created as ``queued`` and pushed by a Celery task; the
outcome (sent/failed, gateway message id, metered cost) is recorded on the
row either way, so the per-message cost accounting the platform re-bills
is never lost. Transport-level failures leave the row ``queued`` so the
task can retry; definitive gateway rejections mark it ``failed``.

Email outcomes keep moving after the send: SES pushes delivery, bounce,
complaint, open and click events through SNS, which ``process_ses_event``
applies back onto the dispatch, its campaign recipient, and — for
complaints — the PDPL consent ledger.
"""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.utils import timezone
from django.utils.html import strip_tags

from communications.gateways import (
    SESEmailClient,
    SESError,
    TaqnyatClient,
    TaqnyatError,
    WhatsAppCloudClient,
    WhatsAppError,
)
from communications.models import ConsentRecord, EmailEvent, MessageDispatch
from core.models import Channel
from marketing.models import CampaignRecipient


def validate_sms_dispatch(dispatch):
    """Cheap, local preconditions — safe to run inside a request."""
    if dispatch.channel != Channel.SMS:
        raise ValidationError("Only SMS dispatches are sent through Taqnyat.")
    if dispatch.status != MessageDispatch.Status.QUEUED:
        raise ValidationError("This dispatch has already been sent or failed.")
    if not dispatch.recipient:
        raise ValidationError("The dispatch has no recipient number.")
    if not dispatch.content:
        raise ValidationError("The dispatch has no message content.")


def send_sms_dispatch(dispatch, client=None):
    """Send one queued SMS dispatch via Taqnyat and record the outcome."""
    validate_sms_dispatch(dispatch)

    own_client = client is None
    client = client or TaqnyatClient()
    try:
        result = client.send_sms([dispatch.recipient], dispatch.content)
    except TaqnyatError as exc:
        if exc.status_code is not None:
            # The gateway rejected the message: final, record and stop.
            dispatch.status = MessageDispatch.Status.FAILED
            dispatch.failed_at = timezone.now()
            dispatch.failure_reason = str(exc)
            dispatch.save(
                update_fields=["status", "failed_at", "failure_reason", "updated_at"]
            )
        # Transport errors keep the row queued so the task may retry.
        raise
    finally:
        if own_client:
            client.close()

    dispatch.status = MessageDispatch.Status.SENT
    dispatch.sent_at = timezone.now()
    dispatch.external_message_id = str(result.get("messageId", ""))
    dispatch.cost = Decimal(str(result.get("cost", "0") or "0"))
    dispatch.save(
        update_fields=["status", "sent_at", "external_message_id", "cost", "updated_at"]
    )
    _sync_campaign_recipient(dispatch)
    return dispatch


def validate_whatsapp_dispatch(dispatch):
    """Cheap, local preconditions — safe to run inside a request."""
    if dispatch.channel != Channel.WHATSAPP:
        raise ValidationError(
            "Only WhatsApp dispatches are sent through the WhatsApp Cloud API."
        )
    if dispatch.status != MessageDispatch.Status.QUEUED:
        raise ValidationError("This dispatch has already been sent or failed.")
    if not dispatch.recipient:
        raise ValidationError("The dispatch has no recipient number.")
    if not dispatch.content:
        raise ValidationError("The dispatch has no message content.")


def send_whatsapp_dispatch(dispatch, client=None):
    """Send one queued WhatsApp dispatch via the Cloud API and record the
    outcome. Sends free-form text, which the Cloud API delivers only inside the
    24h customer-service window; template-initiated sends are a future addition."""
    validate_whatsapp_dispatch(dispatch)

    own_client = client is None
    client = client or WhatsAppCloudClient()
    try:
        result = client.send_text(dispatch.recipient, dispatch.content)
    except WhatsAppError as exc:
        if not exc.retryable:
            # The Cloud API rejected the message: final, record and stop.
            dispatch.status = MessageDispatch.Status.FAILED
            dispatch.failed_at = timezone.now()
            dispatch.failure_reason = str(exc)
            dispatch.save(
                update_fields=["status", "failed_at", "failure_reason", "updated_at"]
            )
            _sync_campaign_recipient(dispatch)
        # Retryable errors keep the row queued so the task may retry.
        raise
    finally:
        if own_client:
            client.close()

    dispatch.status = MessageDispatch.Status.SENT
    dispatch.sent_at = timezone.now()
    dispatch.external_message_id = WhatsAppCloudClient.first_message_id(result)
    dispatch.save(
        update_fields=["status", "sent_at", "external_message_id", "updated_at"]
    )
    _sync_campaign_recipient(dispatch)
    return dispatch


def validate_email_dispatch(dispatch):
    """Cheap, local preconditions — safe to run inside a request."""
    if dispatch.channel != Channel.EMAIL:
        raise ValidationError("Only email dispatches are sent through Amazon SES.")
    if dispatch.status != MessageDispatch.Status.QUEUED:
        raise ValidationError("This dispatch has already been sent or failed.")
    if not dispatch.recipient:
        raise ValidationError("The dispatch has no recipient address.")
    validate_email(dispatch.recipient)
    if not dispatch.subject:
        raise ValidationError("An email dispatch needs a subject.")
    if not dispatch.content:
        raise ValidationError("The dispatch has no message content.")


def send_email_dispatch(dispatch, client=None):
    """Send one queued email dispatch via SES and record the outcome."""
    validate_email_dispatch(dispatch)

    client = client or SESEmailClient()
    try:
        message_id = client.send_email(
            [dispatch.recipient],
            dispatch.subject,
            # Content is authored as HTML; the stripped text part keeps
            # plain-text clients and spam filters happy.
            html_body=dispatch.content,
            text_body=strip_tags(dispatch.content),
            tags={
                "dispatch_id": str(dispatch.pk),
                "organization_id": str(dispatch.organization_id),
            },
        )
    except SESError as exc:
        if not exc.retryable:
            # SES rejected the message: final, record and stop.
            dispatch.status = MessageDispatch.Status.FAILED
            dispatch.failed_at = timezone.now()
            dispatch.failure_reason = str(exc)
            dispatch.save(
                update_fields=["status", "failed_at", "failure_reason", "updated_at"]
            )
            _sync_campaign_recipient(dispatch)
        # Retryable errors keep the row queued so the task may retry.
        raise

    dispatch.status = MessageDispatch.Status.SENT
    dispatch.sent_at = timezone.now()
    dispatch.external_message_id = message_id
    dispatch.save(
        update_fields=["status", "sent_at", "external_message_id", "updated_at"]
    )
    _sync_campaign_recipient(dispatch)
    return dispatch


#: MessageDispatch.Status → CampaignRecipient.Status for funnel reporting.
_RECIPIENT_STATUS_BY_DISPATCH_STATUS = {
    MessageDispatch.Status.SENT: CampaignRecipient.Status.SENT,
    MessageDispatch.Status.DELIVERED: CampaignRecipient.Status.DELIVERED,
    MessageDispatch.Status.READ: CampaignRecipient.Status.OPENED,
    MessageDispatch.Status.FAILED: CampaignRecipient.Status.FAILED,
}

#: Funnel order — a recipient's status never moves backwards (a late
#: "delivered" event must not erase an already-recorded open or click).
_RECIPIENT_FUNNEL_RANK = {
    CampaignRecipient.Status.PENDING: 0,
    CampaignRecipient.Status.SENT: 1,
    CampaignRecipient.Status.DELIVERED: 2,
    CampaignRecipient.Status.OPENED: 3,
    CampaignRecipient.Status.CLICKED: 4,
    CampaignRecipient.Status.FAILED: 5,
}


def _sync_campaign_recipient(dispatch, clicked=False):
    """Mirror a dispatch outcome onto its campaign recipient, if any.

    The recipient row is locked for the read-modify-write so concurrent
    outcomes (a send-path write racing a webhook receipt, or two receipts for
    the same campaign) can't lose the monotonic funnel rank. Opens its own
    atomic block; nests harmlessly as a savepoint when the caller already holds
    a transaction (the webhook appliers)."""
    if dispatch.campaign_recipient_id is None:
        return
    with transaction.atomic():
        recipient = (
            CampaignRecipient.objects.select_for_update(of=("self",))
            .filter(pk=dispatch.campaign_recipient_id)
            .first()
        )
        if recipient is None:
            return
        update_fields = []
        if clicked:
            target = CampaignRecipient.Status.CLICKED
            if recipient.clicked_at is None:
                recipient.clicked_at = timezone.now()
                update_fields.append("clicked_at")
        else:
            target = _RECIPIENT_STATUS_BY_DISPATCH_STATUS.get(dispatch.status)
            if target is None:
                return
        if dispatch.sent_at and recipient.sent_at is None:
            recipient.sent_at = dispatch.sent_at
            update_fields.append("sent_at")
        if dispatch.read_at and recipient.opened_at is None:
            recipient.opened_at = dispatch.read_at
            update_fields.append("opened_at")
        moves_forward = (
            _RECIPIENT_FUNNEL_RANK[target] > _RECIPIENT_FUNNEL_RANK[recipient.status]
        )
        if moves_forward:
            recipient.status = target
            update_fields.append("status")
        if update_fields:
            recipient.save(update_fields=[*update_fields, "updated_at"])


@transaction.atomic
def process_ses_event(event):
    """Apply one stored SES event to the messaging domain. Idempotent:
    re-processing converges on the same dispatch/recipient state. The dispatch
    row is locked for the read-modify-write so bursts of SES events for the same
    message (delivery/open/click arriving together) can't lose an update."""
    payload = event.payload or {}
    detail = payload if "eventType" in payload else {}
    event_type = event.event_type
    ses_message_id = event.ses_message_id or str(
        detail.get("mail", {}).get("messageId", "")
    )

    dispatch = (
        MessageDispatch.objects.select_for_update(of=("self",))
        .select_related("campaign_recipient", "customer")
        .filter(channel=Channel.EMAIL, external_message_id=ses_message_id)
        .first()
        if ses_message_id
        else None
    )
    if dispatch is None:
        # Mail sent outside the dispatch pipeline (e.g. framework SMTP mail):
        # keep the event for the audit trail, nothing to update.
        event.processing_status = EmailEvent.ProcessingStatus.IGNORED
        event.processed_at = timezone.now()
        event.save(update_fields=["processing_status", "processed_at", "updated_at"])
        return event

    now = timezone.now()
    clicked = False
    if event_type == "Delivery":
        if dispatch.status in (
            MessageDispatch.Status.QUEUED,
            MessageDispatch.Status.SENT,
        ):
            dispatch.status = MessageDispatch.Status.DELIVERED
        if dispatch.delivered_at is None:
            dispatch.delivered_at = now
    elif event_type == "Open":
        if dispatch.read_at is None:
            dispatch.read_at = now
        if dispatch.status != MessageDispatch.Status.FAILED:
            dispatch.status = MessageDispatch.Status.READ
    elif event_type == "Click":
        clicked = True
        if dispatch.read_at is None:
            dispatch.read_at = now
        if dispatch.status != MessageDispatch.Status.FAILED:
            dispatch.status = MessageDispatch.Status.READ
    elif event_type == "Bounce":
        bounce = detail.get("bounce", {})
        reason = f"Bounce ({bounce.get('bounceType', 'Unknown')}): " + "; ".join(
            str(r.get("diagnosticCode") or r.get("status") or "no diagnostic")
            for r in bounce.get("bouncedRecipients", [{}])
        )
        if bounce.get("bounceType") == "Permanent":
            dispatch.status = MessageDispatch.Status.FAILED
            dispatch.failed_at = now
        # Transient bounces keep the "sent" status — SES may still deliver
        # on its own retries — but the reason is recorded for support.
        dispatch.failure_reason = reason
    elif event_type in ("Reject", "Rendering Failure", "DeliveryDelay"):
        if event_type != "DeliveryDelay":
            dispatch.status = MessageDispatch.Status.FAILED
            dispatch.failed_at = now
        dispatch.failure_reason = f"SES {event_type}"
    elif event_type == "Complaint":
        _revoke_email_marketing_consent(dispatch)
    elif event_type != "Send":
        event.processing_status = EmailEvent.ProcessingStatus.IGNORED
        event.processed_at = now
        event.organization_id = dispatch.organization_id
        event.dispatch = dispatch
        event.save(
            update_fields=[
                "processing_status",
                "processed_at",
                "organization",
                "dispatch",
                "updated_at",
            ]
        )
        return event

    dispatch.save()
    _sync_campaign_recipient(dispatch, clicked=clicked)

    event.organization_id = dispatch.organization_id
    event.dispatch = dispatch
    event.processing_status = EmailEvent.ProcessingStatus.PROCESSED
    event.processed_at = now
    event.save(
        update_fields=[
            "organization",
            "dispatch",
            "processing_status",
            "processed_at",
            "updated_at",
        ]
    )
    return event


def _revoke_email_marketing_consent(dispatch):
    """A spam complaint is a PDPL opt-out: append a revocation to the
    consent ledger (never mutate history) unless one is already on file."""
    if dispatch.customer_id is None:
        return
    already_revoked = (
        ConsentRecord.objects.filter(
            organization_id=dispatch.organization_id,
            customer_id=dispatch.customer_id,
            channel=Channel.EMAIL,
            purpose=ConsentRecord.Purpose.MARKETING,
        )
        .order_by("-created_at")
        .values_list("revoked_at", flat=True)
        .first()
    )
    if already_revoked is not None:
        return
    ConsentRecord.objects.create(
        organization_id=dispatch.organization_id,
        customer_id=dispatch.customer_id,
        channel=Channel.EMAIL,
        purpose=ConsentRecord.Purpose.MARKETING,
        revoked_at=timezone.now(),
        source="ses_complaint",
    )


# ---------------------------------------------------------------------------
# WhatsApp delivery receipts
# ---------------------------------------------------------------------------


@transaction.atomic
def _apply_whatsapp_status(status_obj):
    """Apply one WhatsApp status object to its dispatch. Idempotent: timestamps
    are set once and the dispatch status only ever moves forward. The dispatch
    row is locked for the read-modify-write so concurrent receipts (sent /
    delivered / read for the same message) can't lose an update."""
    message_id = str(status_obj.get("id", ""))
    state = status_obj.get("status", "")
    if not message_id:
        return None
    dispatch = (
        MessageDispatch.objects.select_for_update(of=("self",))
        .select_related("campaign_recipient", "customer")
        .filter(channel=Channel.WHATSAPP, external_message_id=message_id)
        .first()
    )
    if dispatch is None:
        return None

    now = timezone.now()
    fields = []
    if state == "sent":
        if dispatch.status == MessageDispatch.Status.QUEUED:
            dispatch.status = MessageDispatch.Status.SENT
            fields.append("status")
        if dispatch.sent_at is None:
            dispatch.sent_at = now
            fields.append("sent_at")
    elif state == "delivered":
        if dispatch.status in (
            MessageDispatch.Status.QUEUED,
            MessageDispatch.Status.SENT,
        ):
            dispatch.status = MessageDispatch.Status.DELIVERED
            fields.append("status")
        if dispatch.delivered_at is None:
            dispatch.delivered_at = now
            fields.append("delivered_at")
    elif state == "read":
        if dispatch.status != MessageDispatch.Status.FAILED:
            dispatch.status = MessageDispatch.Status.READ
            fields.append("status")
        if dispatch.read_at is None:
            dispatch.read_at = now
            fields.append("read_at")
    elif state == "failed":
        dispatch.status = MessageDispatch.Status.FAILED
        fields.append("status")
        if dispatch.failed_at is None:
            dispatch.failed_at = now
            fields.append("failed_at")
        errors = status_obj.get("errors") or []
        if errors:
            err = errors[0]
            reason = (
                err.get("title") or err.get("message") or "WhatsApp delivery failed"
            )
            code = err.get("code")
            dispatch.failure_reason = (
                f"[{code}] {reason}" if code is not None else reason
            )
            fields.append("failure_reason")
    else:
        return None

    if fields:
        dispatch.save(update_fields=[*fields, "updated_at"])
        _sync_campaign_recipient(dispatch)
    return dispatch


def process_whatsapp_webhook(payload):
    """Walk a WhatsApp Cloud API webhook payload and apply every delivery
    status to its dispatch. Returns the count applied. Inbound customer
    messages are ignored here (two-way routing needs per-org number mapping)."""
    processed = 0
    for entry in payload.get("entry") or []:
        for change in entry.get("changes") or []:
            value = change.get("value") or {}
            for status_obj in value.get("statuses") or []:
                if _apply_whatsapp_status(status_obj) is not None:
                    processed += 1
    return processed
