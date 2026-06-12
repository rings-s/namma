"""Celery tasks for campaign fan-out."""

from celery import shared_task
from celery.utils.log import get_task_logger
from django.utils import timezone

from communications.models import MessageDispatch
from communications.tasks import send_email_dispatch_task, send_sms_dispatch_task
from core.models import Channel
from marketing.models import Campaign, CampaignRecipient
from marketing.services import consented_campaign_audience

logger = get_task_logger(__name__)


@shared_task
def send_campaign_task(campaign_id):
    """Fan a campaign out to its consented audience as queued dispatches.

    The draft/scheduled → sending transition is claimed with a conditional
    UPDATE so a duplicate delivery of this task is a no-op, and recipients
    are ``get_or_create``d so a crash mid-fan-out never double-sends on
    the retry.
    """
    claimed = Campaign.objects.filter(
        pk=campaign_id,
        status__in=[Campaign.Status.DRAFT, Campaign.Status.SCHEDULED],
    ).update(status=Campaign.Status.SENDING)
    if not claimed:
        logger.info("Campaign %s gone or already sending; nothing to do.", campaign_id)
        return
    campaign = Campaign.objects.get(pk=campaign_id)
    contact_field = "email" if campaign.channel == Channel.EMAIL else "phone"
    send_task = (
        send_email_dispatch_task
        if campaign.channel == Channel.EMAIL
        else send_sms_dispatch_task
    )
    queued = 0
    for customer in consented_campaign_audience(campaign).iterator():
        recipient, created = CampaignRecipient.objects.get_or_create(
            campaign=campaign, customer=customer
        )
        if not created:
            continue
        dispatch = MessageDispatch.objects.create(
            organization_id=campaign.organization_id,
            customer=customer,
            campaign_recipient=recipient,
            channel=campaign.channel,
            recipient=getattr(customer, contact_field),
            subject=campaign.subject,
            content=campaign.content,
        )
        send_task.delay(str(dispatch.pk))
        queued += 1
    campaign.status = Campaign.Status.SENT
    campaign.sent_at = timezone.now()
    campaign.save(update_fields=["status", "sent_at", "updated_at"])
    logger.info("Campaign %s fanned out to %s recipients.", campaign_id, queued)
