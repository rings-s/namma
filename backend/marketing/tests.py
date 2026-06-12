"""Campaign send tests: consent gating, fan-out idempotency and RBAC."""

from unittest import mock

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import UserRole
from communications.models import ConsentRecord, MessageDispatch
from core.models import Channel
from customers.models import Customer
from marketing.models import Campaign, CampaignRecipient
from marketing.tasks import send_campaign_task
from organizations.models import Organization

User = get_user_model()


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
class CampaignSendTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org = Organization.objects.create(name="Salon A", slug="salon-a")
        cls.marketer = User.objects.create_user(
            email="marketer@namaa.sa", password="pass12345"
        )
        UserRole.objects.create(
            user=cls.marketer, organization=cls.org, role=UserRole.Role.MARKETER
        )
        cls.staff = User.objects.create_user(
            email="staff@namaa.sa", password="pass12345"
        )
        UserRole.objects.create(
            user=cls.staff, organization=cls.org, role=UserRole.Role.STAFF
        )

        def customer(first_name, email=""):
            return Customer.objects.create(
                organization=cls.org, first_name=first_name, last_name="X", email=email
            )

        def consent(cust, granted=True, revoked=False):
            ConsentRecord.objects.create(
                organization=cls.org,
                customer=cust,
                channel=Channel.EMAIL,
                purpose=ConsentRecord.Purpose.MARKETING,
                granted_at=timezone.now() if granted else None,
                revoked_at=timezone.now() if revoked else None,
            )

        cls.consented = customer("Consented", email="ok@example.sa")
        consent(cls.consented)
        cls.revoked = customer("Revoked", email="revoked@example.sa")
        consent(cls.revoked)
        consent(cls.revoked, granted=False, revoked=True)  # later ledger entry wins
        cls.never_asked = customer("Silent", email="silent@example.sa")
        cls.no_email = customer("NoEmail")
        consent(cls.no_email)

        cls.campaign = Campaign.objects.create(
            organization=cls.org,
            name="Eid offer",
            type=Campaign.CampaignType.PROMOTIONAL,
            channel=Channel.EMAIL,
            subject="عرض العيد",
            content="<p>خصم ٢٠٪</p>",
        )

    def _send(self, user=None):
        self.client.force_authenticate(user or self.marketer)
        with mock.patch("communications.services.SESEmailClient") as factory:
            factory.return_value.send_email.return_value = "ses-msg-1"
            return self.client.post(f"/api/v1/campaigns/{self.campaign.id}/send/")

    def test_fan_out_reaches_only_consented_customers_with_email(self):
        response = self._send()
        self.assertEqual(response.status_code, 202, response.data)
        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.status, Campaign.Status.SENT)
        self.assertIsNotNone(self.campaign.sent_at)
        recipients = CampaignRecipient.objects.filter(campaign=self.campaign)
        self.assertEqual([r.customer_id for r in recipients], [self.consented.id])
        dispatch = MessageDispatch.objects.get(campaign_recipient=recipients.get())
        self.assertEqual(dispatch.channel, Channel.EMAIL)
        self.assertEqual(dispatch.recipient, "ok@example.sa")
        self.assertEqual(dispatch.subject, "عرض العيد")
        self.assertEqual(dispatch.status, MessageDispatch.Status.SENT)
        self.assertEqual(dispatch.external_message_id, "ses-msg-1")
        # Funnel state mirrored back onto the campaign recipient.
        self.assertEqual(recipients.get().status, CampaignRecipient.Status.SENT)

    def test_duplicate_task_delivery_does_not_double_send(self):
        self._send()
        with mock.patch("communications.services.SESEmailClient") as factory:
            factory.return_value.send_email.return_value = "ses-msg-2"
            send_campaign_task(str(self.campaign.id))  # redelivered message
        self.assertEqual(
            MessageDispatch.objects.filter(
                campaign_recipient__campaign=self.campaign
            ).count(),
            1,
        )

    def test_send_requires_marketer_role(self):
        response = self._send(user=self.staff)
        self.assertEqual(response.status_code, 403)
        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.status, Campaign.Status.DRAFT)

    def test_already_sent_campaign_is_rejected(self):
        Campaign.objects.filter(pk=self.campaign.pk).update(status=Campaign.Status.SENT)
        response = self._send()
        self.assertEqual(response.status_code, 400)

    def test_email_campaign_without_subject_is_rejected(self):
        Campaign.objects.filter(pk=self.campaign.pk).update(subject="")
        response = self._send()
        self.assertEqual(response.status_code, 400)

    def test_whatsapp_campaign_has_no_gateway_yet(self):
        Campaign.objects.filter(pk=self.campaign.pk).update(channel=Channel.WHATSAPP)
        response = self._send()
        self.assertEqual(response.status_code, 400)


class ReferralTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        from decimal import Decimal

        from marketing.models import LoyaltyProgram, ReferralProgram

        cls.org = Organization.objects.create(name="Referrals", slug="referrals")
        cls.loyalty = LoyaltyProgram.objects.create(organization=cls.org, name="Points")
        cls.program = ReferralProgram.objects.create(
            organization=cls.org,
            name="Bring a friend",
            referrer_reward_value=Decimal("100"),
            referee_reward_value=Decimal("50"),
            max_referrals_per_customer=2,
        )
        cls.referrer = Customer.objects.create(
            organization=cls.org,
            first_name="Amal",
            phone="+966500000010",
            email="amal@example.sa",
        )

    def _referee(self, **overrides):
        defaults = {
            "organization": self.org,
            "first_name": "Friend",
            "phone": "+966500000011",
            "email": "friend@example.sa",
        }
        defaults.update(overrides)
        return Customer.objects.create(**defaults)

    def test_clean_referral_rewards_both_sides(self):
        from marketing.models import LoyaltyTransaction, Referral
        from marketing.services import create_referral, qualify_referral

        referral = create_referral(self.program, self.referrer)
        referee = self._referee()
        referral = qualify_referral(referral, referee)
        self.assertEqual(referral.status, Referral.Status.REWARDED)
        self.assertIsNotNone(referral.rewarded_at)
        points = {
            (t.customer_id, t.points)
            for t in LoyaltyTransaction.objects.filter(loyalty_program=self.loyalty)
        }
        self.assertEqual(points, {(self.referrer.pk, 100), (referee.pk, 50)})
        self.referrer.refresh_from_db()
        self.assertEqual(self.referrer.loyalty_points, 100)

    def test_self_referral_is_rejected(self):
        from marketing.models import Referral
        from marketing.services import create_referral, qualify_referral

        referral = create_referral(self.program, self.referrer)
        referral = qualify_referral(referral, self.referrer)
        self.assertEqual(referral.status, Referral.Status.REJECTED)
        self.assertIn("Self-referral", referral.rejection_reason)

    def test_shared_phone_is_flagged_as_fraud(self):
        from marketing.models import Referral
        from marketing.services import create_referral, qualify_referral

        referral = create_referral(self.program, self.referrer)
        referee = self._referee(phone=self.referrer.phone, email="")
        referral = qualify_referral(referral, referee)
        self.assertEqual(referral.status, Referral.Status.REJECTED)
        self.assertIn("phone", referral.rejection_reason)

    def test_pre_existing_customer_cannot_be_a_referee(self):
        from marketing.models import Referral
        from marketing.services import create_referral, qualify_referral

        referee = self._referee()  # created BEFORE the referral
        referral = create_referral(self.program, self.referrer)
        referral = qualify_referral(referral, referee)
        self.assertEqual(referral.status, Referral.Status.REJECTED)
        self.assertIn("already a customer", referral.rejection_reason)

    def test_per_customer_referral_cap(self):
        from django.core.exceptions import ValidationError as DjangoValidationError

        from marketing.services import create_referral

        create_referral(self.program, self.referrer)
        create_referral(self.program, self.referrer)
        with self.assertRaises(DjangoValidationError):
            create_referral(self.program, self.referrer)

    def test_settled_referral_cannot_be_reprocessed(self):
        from django.core.exceptions import ValidationError as DjangoValidationError

        from marketing.services import create_referral, qualify_referral

        referral = create_referral(self.program, self.referrer)
        referee = self._referee()
        qualify_referral(referral, referee)
        with self.assertRaises(DjangoValidationError):
            qualify_referral(referral, referee)
