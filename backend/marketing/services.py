"""Marketing services: campaign validation, PDPL consent-gated audience
selection, and the dual-sided referral lifecycle.

A campaign never reaches a customer who hasn't granted consent for its
channel and purpose. Consent state comes from the append-only ledger in
``communications.ConsentRecord``: the latest entry per (customer, channel,
purpose) decides — granted and not revoked means sendable.

Referrals carry money-like rewards, so qualification runs every fraud
guard before any reward is issued, and reward issuance goes through the
existing append-only ledgers (loyalty transactions / store credit).
"""

import secrets

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F, OuterRef, Subquery
from django.utils import timezone

from communications.models import ConsentRecord
from core.models import Channel
from customers.models import Customer
from marketing.models import Campaign, Referral, ReferralProgram

#: Campaign type → the consent purpose its recipients must have granted.
CONSENT_PURPOSE_BY_CAMPAIGN_TYPE = {
    Campaign.CampaignType.PROMOTIONAL: ConsentRecord.Purpose.MARKETING,
    Campaign.CampaignType.ANNOUNCEMENT: ConsentRecord.Purpose.MARKETING,
    Campaign.CampaignType.REMINDER: ConsentRecord.Purpose.REMINDERS,
    Campaign.CampaignType.TRANSACTIONAL: ConsentRecord.Purpose.TRANSACTIONAL,
}

#: Channels with a sending gateway wired up (Taqnyat, SES).
SENDABLE_CHANNELS = (Channel.SMS, Channel.EMAIL)


def validate_campaign_sendable(campaign):
    """Cheap, local preconditions — safe to run inside a request."""
    if campaign.status not in (Campaign.Status.DRAFT, Campaign.Status.SCHEDULED):
        raise ValidationError("Only draft or scheduled campaigns can be sent.")
    if campaign.channel not in SENDABLE_CHANNELS:
        raise ValidationError("Campaigns can only be sent over SMS or email.")
    if not campaign.content:
        raise ValidationError("The campaign has no content.")
    if campaign.channel == Channel.EMAIL and not campaign.subject:
        raise ValidationError("An email campaign needs a subject.")


def consented_campaign_audience(campaign):
    """Customers in the campaign's organization holding an active consent
    for its channel/purpose, with a usable contact handle for the channel."""
    purpose = CONSENT_PURPOSE_BY_CAMPAIGN_TYPE[campaign.type]
    latest_consent = ConsentRecord.objects.filter(
        customer=OuterRef("pk"), channel=campaign.channel, purpose=purpose
    ).order_by("-created_at")
    contact_field = "email" if campaign.channel == Channel.EMAIL else "phone"
    return (
        Customer.objects.filter(organization_id=campaign.organization_id)
        .exclude(**{contact_field: ""})
        .annotate(
            latest_consent_granted=Subquery(latest_consent.values("granted_at")[:1]),
            latest_consent_revoked=Subquery(latest_consent.values("revoked_at")[:1]),
        )
        .filter(
            latest_consent_granted__isnull=False,
            latest_consent_revoked__isnull=True,
        )
    )


# ---------------------------------------------------------------------------
# Referrals
# ---------------------------------------------------------------------------


def create_referral(program, referrer):
    """Open a referral and mint its share code. Enforces the per-customer
    cap up front so codes can't be farmed."""
    if not program.is_active:
        raise ValidationError("This referral program is not active.")
    active = Referral.objects.filter(
        program=program,
        referrer=referrer,
    ).exclude(status=Referral.Status.REJECTED)
    if active.count() >= program.max_referrals_per_customer:
        raise ValidationError("This customer reached the referral limit.")
    return Referral.objects.create(
        program=program,
        organization=program.organization,
        referrer=referrer,
        code=secrets.token_urlsafe(8)[:12].upper(),
    )


def _referral_fraud_reason(referral, referee):
    """First fraud guard that trips, or None when the referral is clean."""
    referrer = referral.referrer
    if referee.pk == referrer.pk:
        return "Self-referral."
    if referee.organization_id != referral.organization_id:
        return "Referee belongs to a different organization."
    if referee.created_at < referral.created_at:
        return "Referee was already a customer before the referral."
    if referee.phone and referee.phone == referrer.phone:
        return "Referee shares the referrer's phone number."
    if referee.email and referee.email == referrer.email:
        return "Referee shares the referrer's email address."
    if (
        Referral.objects.filter(referee=referee)
        .exclude(pk=referral.pk)
        .exclude(status=Referral.Status.REJECTED)
        .exists()
    ):
        return "Referee was already claimed by another referral."
    return None


def _issue_referral_reward(program, customer, reward_type, value, description):
    if reward_type == ReferralProgram.RewardType.LOYALTY_POINTS:
        from marketing.models import LoyaltyProgram, LoyaltyTransaction

        loyalty_program = LoyaltyProgram.objects.filter(
            organization_id=program.organization_id, is_active=True
        ).first()
        if loyalty_program is None:
            raise ValidationError(
                "No active loyalty program to issue referral points into."
            )
        points = int(value)
        LoyaltyTransaction.objects.create(
            loyalty_program=loyalty_program,
            customer=customer,
            points=points,
            type=LoyaltyTransaction.TransactionType.EARN,
            description=description,
        )
        Customer.objects.filter(pk=customer.pk).update(
            loyalty_points=F("loyalty_points") + points
        )
    else:
        from commerce.models import StoreCreditAccount, StoreCreditTransaction

        account, _ = StoreCreditAccount.objects.get_or_create(
            organization_id=program.organization_id, customer=customer
        )
        account.apply(
            StoreCreditTransaction.Type.CREDIT, value, description=description
        )


@transaction.atomic
def qualify_referral(referral, referee):
    """Attach the referee, run the fraud guards, and on success reward
    both sides through the append-only ledgers. One-shot: anything other
    than PENDING is final."""
    referral = Referral.objects.select_for_update().get(pk=referral.pk)
    if referral.status != Referral.Status.PENDING:
        raise ValidationError("This referral has already been processed.")

    program = referral.program
    referral.referee = referee
    reason = _referral_fraud_reason(referral, referee)
    if reason is None and referee.total_spent < program.min_referee_spend:
        reason = "Referee has not reached the minimum qualifying spend."
    if reason is not None:
        referral.status = Referral.Status.REJECTED
        referral.rejection_reason = reason
        referral.save(
            update_fields=["referee", "status", "rejection_reason", "updated_at"]
        )
        return referral

    now = timezone.now()
    _issue_referral_reward(
        program,
        referral.referrer,
        program.referrer_reward_type,
        program.referrer_reward_value,
        f"Referral reward ({referral.code})",
    )
    _issue_referral_reward(
        program,
        referee,
        program.referee_reward_type,
        program.referee_reward_value,
        f"Welcome referral reward ({referral.code})",
    )
    referral.status = Referral.Status.REWARDED
    referral.qualified_at = now
    referral.rewarded_at = now
    referral.save(
        update_fields=[
            "referee",
            "status",
            "qualified_at",
            "rewarded_at",
            "updated_at",
        ]
    )
    return referral
