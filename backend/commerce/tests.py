"""Stored value tests: gift cards, store credit and packages."""

from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from accounts.models import UserRole
from commerce.models import (
    CustomerPackage,
    GiftCard,
    GiftCardTransaction,
    Package,
    PackageItem,
    Service,
    StoreCreditAccount,
)
from customers.models import Customer
from organizations.models import Organization

User = get_user_model()


class StoredValueTestCase(APITestCase):
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


class GiftCardTests(StoredValueTestCase):
    def test_issuing_creates_issue_transaction_and_sets_balance(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post(
            "/api/v1/gift-cards/",
            {
                "organization": str(self.org.id),
                "code": "GC-100",
                "initial_value": "250.00",
            },
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["balance"], "250.00")
        card = GiftCard.objects.get(code="GC-100")
        issue = card.transactions.get()
        self.assertEqual(issue.transaction_type, GiftCardTransaction.Type.ISSUE)
        self.assertEqual(issue.balance_after, Decimal("250.00"))

    def test_partial_redemption_decrements_balance_and_appends_ledger_row(self):
        card = GiftCard.objects.create(
            organization=self.org, code="GC-200", initial_value=100, balance=100
        )
        self.client.force_authenticate(self.owner)
        response = self.client.post(
            f"/api/v1/gift-cards/{card.id}/redeem/", {"amount": "40.00"}
        )
        self.assertEqual(response.status_code, 201, response.data)
        card.refresh_from_db()
        self.assertEqual(card.balance, Decimal("60.00"))
        self.assertEqual(card.status, GiftCard.Status.ACTIVE)

    def test_full_redemption_marks_card_depleted(self):
        card = GiftCard.objects.create(
            organization=self.org, code="GC-300", initial_value=50, balance=50
        )
        self.client.force_authenticate(self.owner)
        response = self.client.post(
            f"/api/v1/gift-cards/{card.id}/redeem/", {"amount": "50.00"}
        )
        self.assertEqual(response.status_code, 201)
        card.refresh_from_db()
        self.assertEqual(card.status, GiftCard.Status.DEPLETED)

    def test_over_redemption_is_rejected(self):
        card = GiftCard.objects.create(
            organization=self.org, code="GC-400", initial_value=30, balance=30
        )
        self.client.force_authenticate(self.owner)
        response = self.client.post(
            f"/api/v1/gift-cards/{card.id}/redeem/", {"amount": "31.00"}
        )
        self.assertEqual(response.status_code, 400)
        card.refresh_from_db()
        self.assertEqual(card.balance, Decimal("30.00"))


class StoreCreditTests(StoredValueTestCase):
    def test_staff_cannot_adjust_store_credit(self):
        account = StoreCreditAccount.objects.create(
            organization=self.org, customer=self.customer
        )
        self.client.force_authenticate(self.staff)
        response = self.client.post(
            f"/api/v1/store-credit-accounts/{account.id}/adjust/",
            {"transaction_type": "credit", "amount": "100.00"},
        )
        self.assertEqual(response.status_code, 403)

    def test_credit_then_overdraft_debit_rejected(self):
        account = StoreCreditAccount.objects.create(
            organization=self.org, customer=self.customer
        )
        self.client.force_authenticate(self.owner)
        credit = self.client.post(
            f"/api/v1/store-credit-accounts/{account.id}/adjust/",
            {"transaction_type": "credit", "amount": "100.00"},
        )
        self.assertEqual(credit.status_code, 201, credit.data)
        overdraft = self.client.post(
            f"/api/v1/store-credit-accounts/{account.id}/adjust/",
            {"transaction_type": "debit", "amount": "150.00"},
        )
        self.assertEqual(overdraft.status_code, 400)
        account.refresh_from_db()
        self.assertEqual(account.balance, Decimal("100.00"))


class PackageTests(StoredValueTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.service = Service.objects.create(
            organization=cls.org, name="Haircut", price=80, duration_minutes=30
        )
        cls.package = Package.objects.create(
            organization=cls.org, name="5x Haircut", price=350
        )
        cls.item = PackageItem.objects.create(
            package=cls.package, service=cls.service, quantity=5
        )
        cls.owned = CustomerPackage.objects.create(
            organization=cls.org, customer=cls.customer, package=cls.package
        )

    def test_redemption_decrements_remaining_uses(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post(
            f"/api/v1/customer-packages/{self.owned.id}/redeem/",
            {"package_item": str(self.item.id), "quantity": 2},
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(self.owned.remaining_quantity(self.item), 3)

    def test_over_redemption_is_rejected(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post(
            f"/api/v1/customer-packages/{self.owned.id}/redeem/",
            {"package_item": str(self.item.id), "quantity": 6},
        )
        self.assertEqual(response.status_code, 400)

    def test_consuming_all_uses_marks_package_consumed(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post(
            f"/api/v1/customer-packages/{self.owned.id}/redeem/",
            {"package_item": str(self.item.id), "quantity": 5},
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.owned.refresh_from_db()
        self.assertEqual(self.owned.status, CustomerPackage.Status.CONSUMED)


class DynamicPricingTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        from datetime import time

        from commerce.models import PricingRule

        cls.org = Organization.objects.create(name="Pricing", slug="pricing")
        cls.service = Service.objects.create(
            organization=cls.org, name="Massage", price=Decimal("200.00")
        )
        cls.customer = Customer.objects.create(organization=cls.org, first_name="Vip")
        cls.happy_hour = PricingRule.objects.create(
            organization=cls.org,
            service=cls.service,
            name="Happy hour",
            rule_type=PricingRule.RuleType.TIME_BASED,
            adjustment_type=PricingRule.AdjustmentType.PERCENT,
            adjustment_value=Decimal("-20"),
            start_time=time(14, 0),
            end_time=time(16, 0),
            priority=10,
        )

    def _resolve(self, when, **kwargs):
        from commerce.models import PricingRule
        from commerce.pricing import resolve_price

        rules = PricingRule.objects.filter(organization=self.org, is_active=True)
        return resolve_price(self.service.price, rules, when, **kwargs)

    def test_time_window_rule_applies_only_inside_the_window(self):
        from django.utils import timezone as dj_timezone

        inside = dj_timezone.now().replace(hour=15, minute=0)
        outside = dj_timezone.now().replace(hour=19, minute=0)
        price_inside, rule = self._resolve(inside)
        price_outside, no_rule = self._resolve(outside)
        self.assertEqual(price_inside, Decimal("160.00"))
        self.assertEqual(rule, self.happy_hour)
        self.assertEqual(price_outside, Decimal("200.00"))
        self.assertIsNone(no_rule)

    def test_segment_rule_applies_to_members_only(self):
        from datetime import time

        from commerce.models import PricingRule
        from customers.models import CustomerSegment, CustomerSegmentMembership
        from django.utils import timezone as dj_timezone

        segment = CustomerSegment.objects.create(organization=self.org, name="VIP")
        PricingRule.objects.create(
            organization=self.org,
            service=self.service,
            segment=segment,
            name="VIP surcharge-free peak",
            rule_type=PricingRule.RuleType.SEGMENT_BASED,
            adjustment_type=PricingRule.AdjustmentType.PERCENT,
            adjustment_value=Decimal("-30"),
            priority=99,  # beats happy hour when both match
            start_time=time(14, 0),
            end_time=time(16, 0),
        )
        when = dj_timezone.now().replace(hour=15, minute=0)
        price_non_member, rule = self._resolve(when, customer=self.customer)
        self.assertEqual(price_non_member, Decimal("160.00"))  # happy hour
        CustomerSegmentMembership.objects.create(
            segment=segment, customer=self.customer
        )
        price_member, rule = self._resolve(when, customer=self.customer)
        self.assertEqual(price_member, Decimal("140.00"))
        self.assertEqual(rule.name, "VIP surcharge-free peak")

    def test_price_never_goes_negative(self):
        from commerce.models import PricingRule
        from django.utils import timezone as dj_timezone

        PricingRule.objects.create(
            organization=self.org,
            service=self.service,
            name="Broken discount",
            rule_type=PricingRule.RuleType.TIME_BASED,
            adjustment_type=PricingRule.AdjustmentType.FIXED,
            adjustment_value=Decimal("-500"),
            priority=999,
        )
        price, _ = self._resolve(dj_timezone.now())
        self.assertEqual(price, Decimal("0.00"))
