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


class BookingConsistencyTests(APITestCase):
    """Double-booking and overbooking prevention (audit issue #2)."""

    @classmethod
    def setUpTestData(cls):
        from datetime import datetime, timezone as dt_timezone

        from customers.models import Customer
        from operations.models import Appointment, Event

        cls.Appointment = Appointment
        cls.Event = Event
        cls.org = Organization.objects.create(name="Glow Spa", slug="glow-book")
        cls.branch = Branch.objects.create(organization=cls.org, name="Main")
        cls.employee = Employee.objects.create(
            organization=cls.org, branch=cls.branch, job_title="Stylist"
        )
        cls.other_employee = Employee.objects.create(
            organization=cls.org, branch=cls.branch, job_title="Therapist"
        )
        cls.service = Service.objects.create(
            organization=cls.org, name="Haircut", price=Decimal("100.00")
        )
        cls.customer = Customer.objects.create(
            organization=cls.org, first_name="Sara", last_name="A"
        )
        cls.slot = datetime(2026, 7, 1, 10, 0, tzinfo=dt_timezone.utc)

    def _appointment(self, *, employee=None, at=None, minutes=60, status=None):
        return self.Appointment.objects.create(
            organization=self.org,
            branch=self.branch,
            customer=self.customer,
            employee=employee or self.employee,
            service=self.service,
            scheduled_at=at or self.slot,
            duration_minutes=minutes,
            status=status or self.Appointment.Status.SCHEDULED,
        )

    def test_overlapping_appointment_same_employee_is_rejected(self):
        from django.db import transaction
        from operations.services import assert_no_appointment_conflict

        self._appointment(minutes=60)  # 10:00-11:00
        with self.assertRaises(ValidationError), transaction.atomic():
            # 10:30 start overlaps the 10:00-11:00 appointment.
            assert_no_appointment_conflict(
                employee_id=self.employee.id,
                scheduled_at=self.slot.replace(minute=30),
                duration_minutes=30,
            )

    def test_adjacent_appointment_is_allowed(self):
        from datetime import timedelta

        from django.db import transaction
        from operations.services import assert_no_appointment_conflict

        self._appointment(minutes=60)  # 10:00-11:00
        with transaction.atomic():  # 11:00 start is adjacent, not overlapping
            assert_no_appointment_conflict(
                employee_id=self.employee.id,
                scheduled_at=self.slot + timedelta(hours=1),
                duration_minutes=30,
            )

    def test_other_employee_same_slot_is_allowed(self):
        from django.db import transaction
        from operations.services import assert_no_appointment_conflict

        self._appointment(minutes=60)
        with transaction.atomic():
            assert_no_appointment_conflict(
                employee_id=self.other_employee.id,
                scheduled_at=self.slot,
                duration_minutes=60,
            )

    def test_cancelled_appointment_frees_the_slot(self):
        from django.db import transaction
        from operations.services import assert_no_appointment_conflict

        self._appointment(minutes=60, status=self.Appointment.Status.CANCELLED)
        with transaction.atomic():
            assert_no_appointment_conflict(
                employee_id=self.employee.id,
                scheduled_at=self.slot,
                duration_minutes=60,
            )

    def test_reschedule_excludes_self(self):
        from django.db import transaction
        from operations.services import assert_no_appointment_conflict

        appt = self._appointment(minutes=60)
        with transaction.atomic():  # the appointment must not conflict with itself
            assert_no_appointment_conflict(
                employee_id=self.employee.id,
                scheduled_at=self.slot,
                duration_minutes=60,
                exclude_id=appt.pk,
            )

    def test_event_capacity_blocks_overbooking(self):
        from operations.services import reserve_event_capacity

        event = self.Event.objects.create(
            organization=self.org,
            branch=self.branch,
            name="Yoga",
            start_datetime=self.slot,
            end_datetime=self.slot,
            capacity=2,
        )
        reserve_event_capacity(event.id, 2)
        with self.assertRaises(ValidationError):
            reserve_event_capacity(event.id, 1)
        event.refresh_from_db()
        self.assertEqual(event.booked_count, 2)

    def test_zero_capacity_means_unlimited(self):
        from operations.services import reserve_event_capacity

        event = self.Event.objects.create(
            organization=self.org,
            branch=self.branch,
            name="Open House",
            start_datetime=self.slot,
            end_datetime=self.slot,
            capacity=0,
        )
        reserve_event_capacity(event.id, 500)  # must not raise
        event.refresh_from_db()
        self.assertEqual(event.booked_count, 500)

    def test_release_capacity_returns_seats(self):
        from operations.services import release_event_capacity, reserve_event_capacity

        event = self.Event.objects.create(
            organization=self.org,
            branch=self.branch,
            name="Class",
            start_datetime=self.slot,
            end_datetime=self.slot,
            capacity=3,
        )
        reserve_event_capacity(event.id, 3)
        release_event_capacity(event.id, 2)
        event.refresh_from_db()
        self.assertEqual(event.booked_count, 1)
        reserve_event_capacity(event.id, 2)  # seats freed, so this fits
        event.refresh_from_db()
        self.assertEqual(event.booked_count, 3)


class LaborSummaryQueryEfficiencyTests(APITestCase):
    """organization_labor_summary stays O(1) in queries (audit issue #11)."""

    def test_constant_queries_regardless_of_headcount(self):
        from operations.models import EmployeeCostComponent
        from operations.services import organization_labor_summary

        org = Organization.objects.create(name="Big", slug="big-labor")
        branch = Branch.objects.create(organization=org, name="HQ")
        for i in range(8):
            emp = Employee.objects.create(
                organization=org,
                branch=branch,
                job_title=f"E{i}",
                is_saudi=(i % 2 == 0),
                monthly_salary=Decimal("5000.00"),
            )
            # Half also carry an explicit base-salary component.
            if i % 2 == 0:
                EmployeeCostComponent.objects.create(
                    organization=org,
                    employee=emp,
                    component_type=EmployeeCostComponent.ComponentType.BASE_SALARY,
                    monthly_amount=Decimal("6000.00"),
                    effective_from=date(2026, 1, 1),
                )
        # Constant query count (counts + salaries + components), not O(employees).
        with self.assertNumQueries(3):
            summary = organization_labor_summary(org.id, on_date=date(2026, 6, 1))
        self.assertEqual(summary["active_employees"], 8)
        self.assertEqual(summary["saudi_employees"], 4)
        # 4 with base component (6000) + 4 on profile salary (5000) = 44000.
        self.assertEqual(summary["total_loaded_monthly_cost"], Decimal("44000.00"))
