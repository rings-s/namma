"""Tenant isolation tests for the customers API."""

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from accounts.models import UserRole
from customers.models import Customer
from organizations.models import Organization

User = get_user_model()


class CustomerTenantIsolationTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org_a = Organization.objects.create(name="Salon A", slug="salon-a")
        cls.org_b = Organization.objects.create(name="Spa B", slug="spa-b")

        cls.user_a = User.objects.create_user(email="a@namaa.sa", password="pass12345")
        UserRole.objects.create(
            user=cls.user_a, organization=cls.org_a, role=UserRole.Role.OWNER
        )

        cls.customer_a = Customer.objects.create(
            organization=cls.org_a,
            first_name="Sara",
            last_name="Ali",
            phone="+966500000001",
        )
        cls.customer_b = Customer.objects.create(
            organization=cls.org_b,
            first_name="Nora",
            last_name="Omar",
            phone="+966500000002",
        )

    def test_requires_authentication(self):
        # 401 (not 403): JWTAuthentication is the primary scheme and
        # challenges anonymous requests with WWW-Authenticate.
        response = self.client.get("/api/v1/customers/")
        self.assertEqual(response.status_code, 401)

    def test_list_only_returns_own_organizations_customers(self):
        self.client.force_authenticate(self.user_a)
        response = self.client.get("/api/v1/customers/")
        self.assertEqual(response.status_code, 200)
        ids = [row["id"] for row in response.data["results"]]
        self.assertEqual(ids, [str(self.customer_a.id)])

    def test_cannot_read_other_tenants_customer(self):
        self.client.force_authenticate(self.user_a)
        response = self.client.get(f"/api/v1/customers/{self.customer_b.id}/")
        self.assertEqual(response.status_code, 404)

    def test_cannot_create_customer_in_other_tenant(self):
        self.client.force_authenticate(self.user_a)
        response = self.client.post(
            "/api/v1/customers/",
            {
                "organization": str(self.org_b.id),
                "first_name": "Mona",
                "last_name": "X",
            },
        )
        self.assertEqual(response.status_code, 403)

    def test_can_create_customer_in_own_tenant(self):
        self.client.force_authenticate(self.user_a)
        response = self.client.post(
            "/api/v1/customers/",
            {
                "organization": str(self.org_a.id),
                "first_name": "Mona",
                "last_name": "X",
            },
        )
        self.assertEqual(response.status_code, 201, response.data)

    def test_soft_delete_hides_customer(self):
        self.client.force_authenticate(self.user_a)
        response = self.client.delete(f"/api/v1/customers/{self.customer_a.id}/")
        self.assertEqual(response.status_code, 204)
        self.customer_a.refresh_from_db()
        self.assertIsNotNone(self.customer_a.deleted_at)
        self.assertFalse(Customer.objects.filter(pk=self.customer_a.pk).exists())
        self.assertTrue(Customer.all_objects.filter(pk=self.customer_a.pk).exists())


class DynamicSegmentTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        from customers.models import CustomerSegment

        cls.org = Organization.objects.create(name="Segments", slug="segments")
        cls.loyal = Customer.objects.create(
            organization=cls.org, first_name="Loyal", visit_count=12
        )
        cls.casual = Customer.objects.create(
            organization=cls.org, first_name="Casual", visit_count=2
        )
        cls.segment = CustomerSegment.objects.create(
            organization=cls.org,
            name="Regulars",
            segment_type=CustomerSegment.SegmentType.DYNAMIC,
            criteria={"min_visits": 10},
        )

    def test_refresh_converges_membership_to_current_criteria_match(self):
        from customers.services import refresh_segment

        refresh_segment(self.segment)
        members = set(self.segment.memberships.values_list("customer_id", flat=True))
        self.assertEqual(members, {self.loyal.pk})

        # The loyal customer lapses; refresh must drop them and is
        # idempotent for everyone else.
        Customer.objects.filter(pk=self.loyal.pk).update(visit_count=1)
        Customer.objects.filter(pk=self.casual.pk).update(visit_count=15)
        refresh_segment(self.segment)
        members = set(self.segment.memberships.values_list("customer_id", flat=True))
        self.assertEqual(members, {self.casual.pk})
        self.assertIsNotNone(self.segment.last_refreshed_at)

    def test_manual_segments_cannot_be_refreshed_via_api(self):
        from customers.models import CustomerSegment

        manual = CustomerSegment.objects.create(
            organization=self.org,
            name="Hand-picked",
            segment_type=CustomerSegment.SegmentType.MANUAL,
        )
        owner = User.objects.create_user(
            email="segments-owner@namaa.sa", password="pass12345"
        )
        UserRole.objects.create(
            user=owner, organization=self.org, role=UserRole.Role.OWNER
        )
        self.client.force_authenticate(owner)
        response = self.client.post(f"/api/v1/customer-segments/{manual.id}/refresh/")
        self.assertEqual(response.status_code, 400)


class PdplTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        from decimal import Decimal

        from financials.models import Invoice

        cls.org = Organization.objects.create(name="PDPL Org", slug="pdpl-org")
        cls.admin = User.objects.create_user(
            email="pdpl-admin@namaa.sa", password="pass12345"
        )
        UserRole.objects.create(
            user=cls.admin, organization=cls.org, role=UserRole.Role.ADMIN
        )
        cls.staff = User.objects.create_user(
            email="pdpl-staff@namaa.sa", password="pass12345"
        )
        UserRole.objects.create(
            user=cls.staff, organization=cls.org, role=UserRole.Role.STAFF
        )
        cls.customer = Customer.objects.create(
            organization=cls.org,
            first_name="Noura",
            last_name="Saleh",
            email="noura@example.sa",
            phone="+966500000001",
        )
        cls.invoice = Invoice.objects.create(
            organization=cls.org,
            customer=cls.customer,
            invoice_number="INV-PDPL-1",
            total_amount=Decimal("100.00"),
        )

    def test_export_includes_profile_and_financial_history(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get(f"/api/v1/customers/{self.customer.id}/pdpl-export/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["profile"]["email"], "noura@example.sa")
        self.assertEqual(response.data["invoices"][0]["invoice_number"], "INV-PDPL-1")

    def test_staff_cannot_export_or_erase(self):
        self.client.force_authenticate(self.staff)
        export = self.client.get(f"/api/v1/customers/{self.customer.id}/pdpl-export/")
        erase = self.client.post(f"/api/v1/customers/{self.customer.id}/pdpl-erase/")
        self.assertEqual(export.status_code, 403)
        self.assertEqual(erase.status_code, 403)

    def test_erasure_blanks_pii_but_keeps_statutory_invoices(self):
        from communications.models import ConsentRecord
        from financials.models import Invoice

        self.client.force_authenticate(self.admin)
        response = self.client.post(f"/api/v1/customers/{self.customer.id}/pdpl-erase/")
        self.assertEqual(response.status_code, 200)
        erased = Customer.all_objects.get(pk=self.customer.pk)
        self.assertEqual(erased.email, "")
        self.assertEqual(erased.phone, "")
        self.assertNotIn("Noura", erased.first_name)
        self.assertIsNotNone(erased.deleted_at)
        # The invoice survives, still pointing at the anonymized row.
        invoice = Invoice.objects.get(pk=self.invoice.pk)
        self.assertEqual(invoice.customer_id, self.customer.pk)
        # The erasure is recorded in the consent ledger.
        self.assertTrue(
            ConsentRecord.objects.filter(
                customer_id=self.customer.pk, source="pdpl_erasure"
            ).exists()
        )
