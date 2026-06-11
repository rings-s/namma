<<<<<<< HEAD
from django.test import TestCase

# Create your tests here.
=======
"""Tenant isolation tests for the customers API."""

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from accounts.models import UserRole
from customers.models import Customer
from organnizations.models import Organization

User = get_user_model()


class CustomerTenantIsolationTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org_a = Organization.objects.create(name="Salon A", slug="salon-a")
        cls.org_b = Organization.objects.create(name="Spa B", slug="spa-b")

        cls.user_a = User.objects.create_user(email="a@namaa.sa", password="pass12345")
        UserRole.objects.create(user=cls.user_a, organization=cls.org_a, role=UserRole.Role.OWNER)

        cls.customer_a = Customer.objects.create(
            organization=cls.org_a, first_name="Sara", last_name="Ali", phone="+966500000001"
        )
        cls.customer_b = Customer.objects.create(
            organization=cls.org_b, first_name="Nora", last_name="Omar", phone="+966500000002"
        )

    def test_requires_authentication(self):
        response = self.client.get("/api/v1/customers/")
        self.assertEqual(response.status_code, 403)

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
            {"organization": str(self.org_b.id), "first_name": "Mona", "last_name": "X"},
        )
        self.assertEqual(response.status_code, 403)

    def test_can_create_customer_in_own_tenant(self):
        self.client.force_authenticate(self.user_a)
        response = self.client.post(
            "/api/v1/customers/",
            {"organization": str(self.org_a.id), "first_name": "Mona", "last_name": "X"},
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
>>>>>>> a3235b4 (feat(db): initialize core relational schema)
