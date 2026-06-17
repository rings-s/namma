"""Daily metric roll-up (audit P1: analytics correctness).

The ``Daily*Metric`` tables and ``Goal.current_value`` were declared to be
"computed by the scheduler", but nothing populated them. This module is that
scheduler job. It is:

* **Idempotent** — every write is an ``update_or_create`` keyed on the table's
  unique ``(organization, …, date)`` constraint, so a day can be re-rolled any
  number of times (nightly run + manual back-fill) without double counting.
* **Timezone-correct** — ``TIME_ZONE`` is UTC but tenants live in
  ``Asia/Riyadh`` (and carry a per-org/branch ``timezone``). A naive
  ``created_at__date`` lookup buckets a 01:00 Riyadh sale onto the previous UTC
  day. We therefore aggregate over the *organization-local* day, expressed as a
  half-open UTC range ``[start, end)`` so the underlying datetime indexes are
  still used.

Metrics with no source in the current schema are written as ``0`` and called
out here rather than fabricated:

* ``DailyBranchMetric.avg_wait_time_minutes`` — no queue/wait timestamps are
  recorded anywhere in operations yet.
* ``DailyEmployeeMetric.utilization_percent`` — requires booked-minutes vs
  rostered-capacity; ``EmployeeSchedule`` models weekly availability but no
  realised capacity is tracked.
* ``DailyBranchMetric.new_customers`` — ``Customer`` is org-scoped with no
  branch attribution, so "new at this branch" is undefined.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.db import transaction
from django.db.models import Count, Q, Sum
from django.utils import timezone

from analytics.models import (
    DailyBranchMetric,
    DailyEmployeeMetric,
    DailyMetric,
    Goal,
)
from commerce.models import Sale
from customers.models import Customer
from operations.models import Appointment, Booking, Employee
from organizations.models import Organization

ZERO = Decimal("0")


def _local_day_bounds(tz_name: str, day: dt.date) -> tuple[dt.datetime, dt.datetime]:
    """Return the half-open UTC range covering ``day`` in ``tz_name``."""
    try:
        tz = ZoneInfo(tz_name)
    except Exception:  # pragma: no cover - bad tz string falls back to UTC
        tz = ZoneInfo("UTC")
    start_local = dt.datetime.combine(day, dt.time.min, tzinfo=tz)
    end_local = start_local + dt.timedelta(days=1)
    return start_local.astimezone(dt.timezone.utc), end_local.astimezone(
        dt.timezone.utc
    )


# ---------------------------------------------------------------------------
# Per-day, per-organization roll-up
# ---------------------------------------------------------------------------


def _roll_up_organization(
    org: Organization, day: dt.date, start: dt.datetime, end: dt.datetime
) -> None:
    appts = Appointment.objects.filter(
        organization=org, scheduled_at__gte=start, scheduled_at__lt=end
    )
    appt_agg = appts.aggregate(
        total=Count("id"),
        completed=Count("id", filter=Q(status=Appointment.Status.COMPLETED)),
        cancelled=Count("id", filter=Q(status=Appointment.Status.CANCELLED)),
    )
    revenue = (
        Sale.objects.filter(
            organization=org,
            status=Sale.Status.COMPLETED,
            created_at__gte=start,
            created_at__lt=end,
        ).aggregate(total=Sum("total_amount"))["total"]
        or ZERO
    )
    new_customers = Customer.objects.filter(
        organization=org, created_at__gte=start, created_at__lt=end
    ).count()
    served_customers = appts.values("customer").distinct().count()

    if not (appt_agg["total"] or revenue or new_customers or served_customers):
        # No activity in this org-local day: don't litter the table with a
        # zero row. A re-run after a correction would still upsert real values.
        return

    DailyMetric.objects.update_or_create(
        organization=org,
        branch=None,
        date=day,
        defaults={
            "total_appointments": appt_agg["total"],
            "completed_appointments": appt_agg["completed"],
            "cancelled_appointments": appt_agg["cancelled"],
            "total_revenue": revenue,
            "total_customers": served_customers,
            "new_customers": new_customers,
        },
    )


def _roll_up_branches(
    org: Organization, day: dt.date, start: dt.datetime, end: dt.datetime
) -> None:
    bookings = Booking.objects.filter(
        organization=org, booked_at__gte=start, booked_at__lt=end
    )
    by_branch = {
        row["branch"]: row
        for row in bookings.values("branch").annotate(
            total=Count("id"),
            completed=Count("id", filter=Q(status=Booking.Status.COMPLETED)),
            cancelled=Count("id", filter=Q(status=Booking.Status.CANCELLED)),
            no_shows=Count("id", filter=Q(status=Booking.Status.NO_SHOW)),
            customers=Count("customer", distinct=True),
        )
    }
    revenue_by_branch = {
        row["branch"]: row["rev"]
        for row in Sale.objects.filter(
            organization=org,
            status=Sale.Status.COMPLETED,
            created_at__gte=start,
            created_at__lt=end,
        )
        .values("branch")
        .annotate(rev=Sum("total_amount"))
    }

    branch_ids = set(by_branch) | set(revenue_by_branch)
    branch_ids.discard(None)
    for branch_id in branch_ids:
        agg = by_branch.get(branch_id, {})
        DailyBranchMetric.objects.update_or_create(
            organization=org,
            branch_id=branch_id,
            date=day,
            defaults={
                "total_bookings": agg.get("total", 0),
                "completed_bookings": agg.get("completed", 0),
                "cancelled_bookings": agg.get("cancelled", 0),
                "no_shows": agg.get("no_shows", 0),
                "total_revenue": revenue_by_branch.get(branch_id, ZERO),
                "total_customers": agg.get("customers", 0),
                "new_customers": 0,  # no branch attribution on Customer (see module docstring)
                "avg_wait_time_minutes": ZERO,  # no source (see module docstring)
            },
        )


def _roll_up_employees(
    org: Organization, day: dt.date, start: dt.datetime, end: dt.datetime
) -> None:
    appt_rows = {
        row["employee"]: row
        for row in Appointment.objects.filter(
            organization=org,
            employee__isnull=False,
            scheduled_at__gte=start,
            scheduled_at__lt=end,
        )
        .values("employee")
        .annotate(
            total=Count("id"),
            completed=Count("id", filter=Q(status=Appointment.Status.COMPLETED)),
        )
    }
    revenue_rows = {
        row["employee"]: row["rev"]
        for row in Sale.objects.filter(
            organization=org,
            status=Sale.Status.COMPLETED,
            employee__isnull=False,
            created_at__gte=start,
            created_at__lt=end,
        )
        .values("employee")
        .annotate(rev=Sum("total_amount"))
    }

    employee_ids = set(appt_rows) | set(revenue_rows)
    employee_ids.discard(None)
    if not employee_ids:
        return
    rates = dict(
        Employee.objects.filter(id__in=employee_ids).values_list(
            "id", "commission_rate"
        )
    )
    for employee_id in employee_ids:
        revenue = revenue_rows.get(employee_id, ZERO)
        rate = rates.get(employee_id) or ZERO
        commission = (revenue * rate / Decimal("100")).quantize(Decimal("0.01"))
        agg = appt_rows.get(employee_id, {})
        DailyEmployeeMetric.objects.update_or_create(
            organization=org,
            employee_id=employee_id,
            date=day,
            defaults={
                "total_appointments": agg.get("total", 0),
                "completed_appointments": agg.get("completed", 0),
                "total_revenue": revenue,
                "total_commission": commission,
                "utilization_percent": ZERO,  # no realised-capacity source (see docstring)
            },
        )


# ---------------------------------------------------------------------------
# Goals
# ---------------------------------------------------------------------------


def _goal_value(
    goal: Goal, start: dt.datetime, end: dt.datetime
) -> Decimal | int | None:
    """Recompute a goal's progress from source over its full period.

    Returns ``None`` for metrics with no schema source (retention, NPS,
    custom), leaving ``current_value`` untouched rather than zeroing it.
    """
    if goal.metric == Goal.Metric.REVENUE:
        sales = Sale.objects.filter(
            organization=goal.organization,
            status=Sale.Status.COMPLETED,
            created_at__gte=start,
            created_at__lt=end,
        )
        if goal.employee_id:
            sales = sales.filter(employee_id=goal.employee_id)
        elif goal.branch_id:
            sales = sales.filter(branch_id=goal.branch_id)
        return sales.aggregate(total=Sum("total_amount"))["total"] or ZERO

    if goal.metric == Goal.Metric.BOOKINGS:
        if goal.employee_id:
            # Bookings carry no employee; appointments are the staff-level proxy.
            return Appointment.objects.filter(
                organization=goal.organization,
                employee_id=goal.employee_id,
                scheduled_at__gte=start,
                scheduled_at__lt=end,
            ).count()
        bookings = Booking.objects.filter(
            organization=goal.organization,
            booked_at__gte=start,
            booked_at__lt=end,
        )
        if goal.branch_id:
            bookings = bookings.filter(branch_id=goal.branch_id)
        return bookings.count()

    if goal.metric == Goal.Metric.NEW_CUSTOMERS:
        if goal.branch_id or goal.employee_id:
            return None  # no branch/employee attribution on Customer
        return Customer.objects.filter(
            organization=goal.organization,
            created_at__gte=start,
            created_at__lt=end,
        ).count()

    return None  # retention / nps / custom: no source


def _refresh_goals(org: Organization, as_of: dt.date) -> None:
    tz_name = org.timezone
    goals = Goal.objects.filter(organization=org, status=Goal.Status.ACTIVE)
    now = timezone.now()
    for goal in goals:
        window_end_day = min(as_of, goal.period_end)
        if window_end_day < goal.period_start:
            continue
        start, _ = _local_day_bounds(tz_name, goal.period_start)
        _, end = _local_day_bounds(tz_name, window_end_day)
        value = _goal_value(goal, start, end)

        update_fields = ["updated_at"]
        if value is not None:
            goal.current_value = Decimal(value)
            update_fields.append("current_value")
            for milestone in goal.milestones.filter(reached_at__isnull=True):
                if goal.target_value > 0:
                    pct = goal.current_value / goal.target_value * Decimal("100")
                    if pct >= milestone.threshold_percent:
                        milestone.reached_at = now
                        milestone.save(update_fields=["reached_at", "updated_at"])

        if (
            value is not None
            and goal.target_value > 0
            and goal.current_value >= goal.target_value
        ):
            goal.status = Goal.Status.ACHIEVED
            update_fields.append("status")
        elif as_of > goal.period_end:
            goal.status = Goal.Status.MISSED
            update_fields.append("status")
        goal.save(update_fields=update_fields)


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------


def roll_up_day(organization_id, day: dt.date) -> None:
    """Roll up a single organization's metrics for one local day."""
    org = Organization.objects.get(id=organization_id)
    start, end = _local_day_bounds(org.timezone, day)
    with transaction.atomic():
        _roll_up_organization(org, day, start, end)
        _roll_up_branches(org, day, start, end)
        _roll_up_employees(org, day, start, end)
        _refresh_goals(org, day)


def roll_up_all_organizations(day: dt.date | None = None) -> int:
    """Roll up every active organization for ``day`` (default: yesterday).

    Yesterday is the safe default for a nightly run: by the time the job fires
    just after local midnight, the previous day is closed in every tenant's
    timezone. Returns the number of organizations processed.
    """
    if day is None:
        day = (timezone.now() - dt.timedelta(days=1)).date()
    count = 0
    for organization_id in Organization.objects.values_list("id", flat=True):
        roll_up_day(organization_id, day)
        count += 1
    return count
