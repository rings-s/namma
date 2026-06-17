"""Daily-metric roll-up correctness (audit P1)."""

import datetime as dt
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from analytics.models import (
    DailyBranchMetric,
    DailyEmployeeMetric,
    DailyMetric,
    Goal,
    GoalMilestone,
)
from analytics.services import roll_up_day
from commerce.models import Sale, Service
from customers.models import Customer
from operations.models import Appointment, Booking, Employee
from organizations.models import Branch, Organization


class RollUpTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org = Organization.objects.create(
            name="Glow", slug="glow", timezone="Asia/Riyadh"
        )
        cls.branch = Branch.objects.create(organization=cls.org, name="Main")
        cls.customer = Customer.objects.create(organization=cls.org, first_name="Sara")
        cls.service = Service.objects.create(
            organization=cls.org, name="Cut", price=Decimal("100")
        )
        cls.employee = Employee.objects.create(
            organization=cls.org, branch=cls.branch, commission_rate=Decimal("10")
        )
        cls.day = dt.date(2026, 3, 10)
        # 09:00 Riyadh == 06:00 UTC on the same calendar day.
        cls.local_dt = timezone.make_aware(
            dt.datetime(2026, 3, 10, 6, 0), dt.timezone.utc
        )

    def _make_appointment(self, status, when=None):
        appt = Appointment.objects.create(
            organization=self.org,
            branch=self.branch,
            customer=self.customer,
            employee=self.employee,
            service=self.service,
            scheduled_at=when or self.local_dt,
            status=status,
        )
        return appt

    def _make_sale(self, number, amount, status=Sale.Status.COMPLETED, when=None):
        sale = Sale.objects.create(
            organization=self.org,
            branch=self.branch,
            employee=self.employee,
            sale_number=number,
            total_amount=Decimal(amount),
            status=status,
        )
        # created_at is auto_now_add; rewrite it to land on the target instant.
        Sale.objects.filter(pk=sale.pk).update(created_at=when or self.local_dt)
        return sale

    def test_organization_metric_counts_and_revenue(self):
        self._make_appointment(Appointment.Status.COMPLETED)
        self._make_appointment(Appointment.Status.CANCELLED)
        self._make_appointment(Appointment.Status.SCHEDULED)
        self._make_sale("S-1", "100")
        self._make_sale("S-2", "50")
        self._make_sale("S-3", "999", status=Sale.Status.DRAFT)  # excluded

        roll_up_day(self.org.id, self.day)

        metric = DailyMetric.objects.get(
            organization=self.org, branch=None, date=self.day
        )
        self.assertEqual(metric.total_appointments, 3)
        self.assertEqual(metric.completed_appointments, 1)
        self.assertEqual(metric.cancelled_appointments, 1)
        self.assertEqual(metric.total_revenue, Decimal("150"))
        self.assertEqual(metric.new_customers, 0)  # customer made in setUp, not on day

    def test_roll_up_is_idempotent(self):
        self._make_sale("S-1", "100")
        roll_up_day(self.org.id, self.day)
        roll_up_day(self.org.id, self.day)
        self.assertEqual(
            DailyMetric.objects.filter(organization=self.org, date=self.day).count(), 1
        )
        self.assertEqual(
            DailyMetric.objects.get(date=self.day).total_revenue, Decimal("100")
        )

    def test_revenue_buckets_by_organization_local_day_not_utc(self):
        # 22:30 UTC on Mar 10 is 01:30 Riyadh on Mar 11 → belongs to Mar 11.
        utc_late = timezone.make_aware(
            dt.datetime(2026, 3, 10, 22, 30), dt.timezone.utc
        )
        self._make_sale("S-late", "200", when=utc_late)

        roll_up_day(self.org.id, dt.date(2026, 3, 10))
        roll_up_day(self.org.id, dt.date(2026, 3, 11))

        mar10 = DailyMetric.objects.filter(date=dt.date(2026, 3, 10)).first()
        mar11 = DailyMetric.objects.get(date=dt.date(2026, 3, 11))
        self.assertIsNone(mar10)  # nothing happened on the local 10th
        self.assertEqual(mar11.total_revenue, Decimal("200"))

    def test_branch_metric_breaks_down_bookings_by_status(self):
        for number, status in [
            ("B-1", Booking.Status.COMPLETED),
            ("B-2", Booking.Status.CANCELLED),
            ("B-3", Booking.Status.NO_SHOW),
            ("B-4", Booking.Status.CONFIRMED),
        ]:
            booking = Booking.objects.create(
                organization=self.org,
                branch=self.branch,
                customer=self.customer,
                booking_number=number,
                status=status,
            )
            Booking.objects.filter(pk=booking.pk).update(booked_at=self.local_dt)

        roll_up_day(self.org.id, self.day)

        bm = DailyBranchMetric.objects.get(branch=self.branch, date=self.day)
        self.assertEqual(bm.total_bookings, 4)
        self.assertEqual(bm.completed_bookings, 1)
        self.assertEqual(bm.cancelled_bookings, 1)
        self.assertEqual(bm.no_shows, 1)

    def test_employee_commission_is_revenue_times_rate(self):
        self._make_appointment(Appointment.Status.COMPLETED)
        self._make_sale("S-1", "300")  # rate 10% -> 30.00 commission

        roll_up_day(self.org.id, self.day)

        em = DailyEmployeeMetric.objects.get(employee=self.employee, date=self.day)
        self.assertEqual(em.total_revenue, Decimal("300"))
        self.assertEqual(em.total_commission, Decimal("30.00"))
        self.assertEqual(em.completed_appointments, 1)

    def test_revenue_goal_is_advanced_achieved_and_milestone_reached(self):
        goal = Goal.objects.create(
            organization=self.org,
            name="March revenue",
            metric=Goal.Metric.REVENUE,
            target_value=Decimal("100"),
            period_start=dt.date(2026, 3, 1),
            period_end=dt.date(2026, 3, 31),
        )
        milestone = GoalMilestone.objects.create(goal=goal, threshold_percent=50)
        self._make_sale("S-1", "120")

        roll_up_day(self.org.id, self.day)

        goal.refresh_from_db()
        milestone.refresh_from_db()
        self.assertEqual(goal.current_value, Decimal("120"))
        self.assertEqual(goal.status, Goal.Status.ACHIEVED)
        self.assertIsNotNone(milestone.reached_at)

    def test_goal_is_missed_after_period_end_without_reaching_target(self):
        goal = Goal.objects.create(
            organization=self.org,
            name="Feb revenue",
            metric=Goal.Metric.REVENUE,
            target_value=Decimal("1000"),
            period_start=dt.date(2026, 2, 1),
            period_end=dt.date(2026, 2, 28),
        )
        # Roll up a day after the period closed; no February sales exist.
        roll_up_day(self.org.id, self.day)
        goal.refresh_from_db()
        self.assertEqual(goal.status, Goal.Status.MISSED)
