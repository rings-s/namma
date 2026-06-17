"""Stored value tests: gift cards, store credit and packages."""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APITestCase

from accounts.models import UserRole
from commerce.models import (
    CustomerPackage,
    GiftCard,
    GiftCardTransaction,
    Package,
    PackageItem,
    Product,
    Sale,
    SaleItem,
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


class SaleStockCommitmentTests(TestCase):
    """Stock decrements on completed sales, append-only and idempotent (#7)."""

    @classmethod
    def setUpTestData(cls):
        from organizations.models import Branch, Organization

        cls.org = Organization.objects.create(name="Glow", slug="glow-stock")
        cls.branch = Branch.objects.create(organization=cls.org, name="Main")
        cls.product = Product.objects.create(
            organization=cls.org,
            name="Shampoo",
            price=Decimal("30.00"),
            stock_quantity=10,
        )

    def _sale(self, qty, status):
        sale = Sale.objects.create(
            organization=self.org,
            branch=self.branch,
            sale_number=f"S-{qty}-{status}",
            total_amount=Decimal("30.00"),
            status=status,
        )
        SaleItem.objects.create(
            sale=sale,
            product=self.product,
            description="Shampoo",
            quantity=qty,
            unit_price=Decimal("30.00"),
            total_price=Decimal("30.00"),
        )
        return sale

    def test_completing_sale_decrements_stock_and_writes_movement(self):
        from commerce.services import commit_sale_stock
        from inventory.models import StockMovement

        sale = self._sale(3, Sale.Status.COMPLETED)
        movements = commit_sale_stock(sale)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 7)
        self.assertEqual(len(movements), 1)
        self.assertEqual(movements[0].quantity, -3)
        self.assertEqual(
            StockMovement.objects.filter(
                reference_id=sale.pk,
                movement_type=StockMovement.MovementType.SALE,
            ).count(),
            1,
        )

    def test_commit_is_idempotent(self):
        from commerce.services import commit_sale_stock

        sale = self._sale(2, Sale.Status.COMPLETED)
        commit_sale_stock(sale)
        commit_sale_stock(sale)  # second call must not deduct again
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 8)

    def test_draft_sale_does_not_move_stock(self):
        from commerce.services import commit_sale_stock

        sale = self._sale(5, Sale.Status.DRAFT)
        self.assertEqual(commit_sale_stock(sale), [])
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 10)

    def test_overselling_is_rejected(self):
        from django.core.exceptions import ValidationError

        from commerce.services import commit_sale_stock

        sale = self._sale(99, Sale.Status.COMPLETED)
        with self.assertRaises(ValidationError):
            commit_sale_stock(sale)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 10)


class CatalogOwnerOnlyWriteTests(APITestCase):
    """Service/ServiceCategory/Package/PricingRule writes are Owner-only (P2).

    Reads stay open to any tenant member; the superuser escape hatch holds.
    """

    @classmethod
    def setUpTestData(cls):
        cls.org = Organization.objects.create(name="Cat", slug="cat")
        cls.owner = User.objects.create_user(
            email="cat-owner@namaa.sa", password="pass12345"
        )
        UserRole.objects.create(
            user=cls.owner, organization=cls.org, role=UserRole.Role.OWNER
        )
        cls.manager = User.objects.create_user(
            email="cat-manager@namaa.sa", password="pass12345"
        )
        UserRole.objects.create(
            user=cls.manager, organization=cls.org, role=UserRole.Role.MANAGER
        )
        cls.superuser = User.objects.create_superuser(
            email="root@namaa.sa", password="pass12345"
        )
        cls.service = Service.objects.create(
            organization=cls.org, name="Cut", price=Decimal("100")
        )

    def _create_service(self, user):
        self.client.force_authenticate(user)
        return self.client.post(
            "/api/v1/services/",
            {"organization": str(self.org.id), "name": "Color", "price": "200"},
            format="json",
        )

    def test_owner_can_create_service(self):
        self.assertEqual(self._create_service(self.owner).status_code, 201)

    def test_manager_cannot_create_service(self):
        self.assertEqual(self._create_service(self.manager).status_code, 403)

    def test_superuser_bypasses_the_owner_gate(self):
        self.assertEqual(self._create_service(self.superuser).status_code, 201)

    def test_manager_can_still_read_the_catalog(self):
        self.client.force_authenticate(self.manager)
        response = self.client.get("/api/v1/services/")
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(response.data["count"], 1)

    def test_manager_cannot_update_service(self):
        self.client.force_authenticate(self.manager)
        response = self.client.patch(
            f"/api/v1/services/{self.service.id}/",
            {"price": "999"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.service.refresh_from_db()
        self.assertEqual(self.service.price, Decimal("100"))

    def test_manager_cannot_delete_service(self):
        self.client.force_authenticate(self.manager)
        response = self.client.delete(f"/api/v1/services/{self.service.id}/")
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Service.objects.filter(pk=self.service.id).exists())

    def test_manager_cannot_write_pricing_rule(self):
        self.client.force_authenticate(self.manager)
        response = self.client.post(
            "/api/v1/pricing-rules/",
            {
                "organization": str(self.org.id),
                "name": "Happy hour",
                "rule_type": "time_based",
                "adjustment_type": "percent",
                "adjustment_value": "10",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403, response.data)
