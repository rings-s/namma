"""Commission engine and Saudi labor cost engine tests."""

from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from rest_framework.test import APITestCase

from commerce.models import Sale, SaleItem, Service
from operations.models import (
    CommissionEntry,
    CommissionRule,
    Employee,
    EmployeeCostComponent,
)
from operations.services import (
    calculate_sale_commissions,
    employee_loaded_cost,
    organization_labor_summary,
)
from organizations.models import Branch, Organization


class CommissionTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org = Organization.objects.create(name="Glow Spa", slug="glow-spa")
        cls.branch = Branch.objects.create(organization=cls.org, name="Main")
        cls.employee = Employee.objects.create(
            organization=cls.org,
            branch=cls.branch,
            job_title="Stylist",
            commission_rate=Decimal("5.00"),
            is_saudi=True,
            monthly_salary=Decimal("6000.00"),
        )
        cls.service = Service.objects.create(
            organization=cls.org, name="Haircut", price=Decimal("100.00")
        )

    def _sale(self, number="S-COM-1", total=Decimal("100.00")):
        sale = Sale.objects.create(
            organization=self.org,
            branch=self.branch,
            employee=self.employee,
            sale_number=number,
            subtotal=total,
            total_amount=total,
            status=Sale.Status.COMPLETED,
        )
        SaleItem.objects.create(
            sale=sale,
            service=self.service,
            description="Haircut",
            quantity=1,
            unit_price=total,
            total_price=total,
        )
        return sale


class CommissionCalculationTests(CommissionTestCase):
    def test_specific_service_rule_beats_org_wide_rule(self):
        CommissionRule.objects.create(
            organization=self.org,
            name="Org default",
            basis=CommissionRule.Basis.PERCENT,
            rate_percent=Decimal("10.00"),
        )
        CommissionRule.objects.create(
            organization=self.org,
            name="Haircut special",
            service=self.service,
            basis=CommissionRule.Basis.PERCENT,
            rate_percent=Decimal("20.00"),
        )
        entries = calculate_sale_commissions(self._sale())
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].amount, Decimal("20.00"))
        self.assertIn("Haircut special", entries[0].description)

    def test_tiered_rule_uses_period_revenue(self):
        CommissionRule.objects.create(
            organization=self.org,
            name="Tiered",
            basis=CommissionRule.Basis.TIERED,
            tiers=[
                {"threshold": "0", "rate_percent": "5"},
                {"threshold": "100", "rate_percent": "10"},
            ],
        )
        # The sale itself counts toward period revenue (100 >= 100 tier).
        entries = calculate_sale_commissions(self._sale())
        self.assertEqual(entries[0].amount, Decimal("10.00"))

    def test_profile_rate_fallback_when_no_rules_exist(self):
        entries = calculate_sale_commissions(self._sale())
        self.assertEqual(entries[0].amount, Decimal("5.00"))
        self.assertIn("Flat profile rate", entries[0].description)

    def test_recalculation_is_refused(self):
        sale = self._sale()
        calculate_sale_commissions(sale)
        self.assertEqual(calculate_sale_commissions(sale), [])
        self.assertEqual(CommissionEntry.objects.filter(sale=sale).count(), 1)

    def test_draft_sale_is_rejected(self):
        sale = self._sale()
        Sale.objects.filter(pk=sale.pk).update(status=Sale.Status.DRAFT)
        sale.refresh_from_db()
        with self.assertRaises(ValidationError):
            calculate_sale_commissions(sale)


class LaborCostTests(CommissionTestCase):
    def test_loaded_cost_sums_components_with_salary_fallback(self):
        EmployeeCostComponent.objects.create(
            organization=self.org,
            employee=self.employee,
            component_type=EmployeeCostComponent.ComponentType.GOSI_EMPLOYER,
            monthly_amount=Decimal("700.00"),
            effective_from=date(2026, 1, 1),
        )
        EmployeeCostComponent.objects.create(
            organization=self.org,
            employee=self.employee,
            component_type=EmployeeCostComponent.ComponentType.MEDICAL_INSURANCE,
            monthly_amount=Decimal("300.00"),
            effective_from=date(2026, 1, 1),
            effective_to=date(2026, 3, 31),  # ended — must not count today
        )
        cost = employee_loaded_cost(self.employee, on_date=date(2026, 6, 1))
        self.assertEqual(cost["total_monthly"], Decimal("6700.00"))
        self.assertNotIn(
            EmployeeCostComponent.ComponentType.MEDICAL_INSURANCE, cost["components"]
        )

    def test_labor_summary_reports_saudization(self):
        Employee.objects.create(
            organization=self.org,
            branch=self.branch,
            job_title="Therapist",
            is_saudi=False,
            monthly_salary=Decimal("4000.00"),
        )
        summary = organization_labor_summary(self.org.id)
        self.assertEqual(summary["active_employees"], 2)
        self.assertEqual(summary["saudi_employees"], 1)
        self.assertEqual(summary["saudization_percent"], 50.0)
        self.assertEqual(summary["total_loaded_monthly_cost"], Decimal("10000.00"))
