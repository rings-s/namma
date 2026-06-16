"""Operations services: the commission calculator and the Saudi labor
loaded-cost engine.

Commission entries are append-only: the calculator is idempotent per sale
(it refuses to double-write), and corrections happen through explicit
ADJUSTMENT entries, never by editing history.
"""

from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, F, Q, Sum
from django.utils import timezone

from operations.models import (
    Appointment,
    CommissionEntry,
    CommissionRule,
    EmployeeCostComponent,
    Event,
)

TWO_PLACES = Decimal("0.01")

#: Appointment statuses that occupy an employee's calendar. Cancelled and
#: no-show appointments free the slot; completed ones are historical.
OCCUPYING_APPOINTMENT_STATUSES = (
    Appointment.Status.SCHEDULED,
    Appointment.Status.CONFIRMED,
    Appointment.Status.IN_PROGRESS,
)

#: How far back to scan for an overlapping appointment. Bounds the locked row
#: set: an appointment that started more than this before the new slot cannot
#: still be running. Comfortably exceeds any realistic service duration.
_CONFLICT_SCAN_WINDOW = timedelta(days=1)


# ---------------------------------------------------------------------------
# Booking consistency: appointment overlap & event capacity
# ---------------------------------------------------------------------------


def assert_no_appointment_conflict(
    *, employee_id, scheduled_at, duration_minutes, exclude_id=None
):
    """Raise ``ValidationError`` if ``employee_id`` already has an occupying
    appointment overlapping ``[scheduled_at, scheduled_at + duration)``.

    Caller must already hold an open transaction: the candidate rows are
    locked with ``select_for_update`` so two concurrent bookings for the same
    employee serialize here and the second one sees the first.
    """
    if employee_id is None:
        return  # unassigned appointments never conflict on an employee calendar
    new_end = scheduled_at + timedelta(minutes=duration_minutes)
    candidates = Appointment.objects.select_for_update().filter(
        employee_id=employee_id,
        status__in=OCCUPYING_APPOINTMENT_STATUSES,
        scheduled_at__lt=new_end,
        scheduled_at__gte=scheduled_at - _CONFLICT_SCAN_WINDOW,
    )
    if exclude_id is not None:
        candidates = candidates.exclude(pk=exclude_id)
    for existing in candidates:
        existing_end = existing.scheduled_at + timedelta(
            minutes=existing.duration_minutes
        )
        if existing_end > scheduled_at:
            raise ValidationError(
                "This employee already has an appointment in that time slot."
            )


@transaction.atomic
def book_appointment(serializer):
    """Persist an appointment from a validated serializer, rejecting any
    double-booking of the assigned employee. Returns the saved instance."""
    data = serializer.validated_data
    employee = data.get("employee")
    assert_no_appointment_conflict(
        employee_id=employee.id if employee is not None else None,
        scheduled_at=data["scheduled_at"],
        duration_minutes=data.get("duration_minutes", 30),
    )
    return serializer.save()


@transaction.atomic
def reschedule_appointment(serializer):
    """Persist an appointment update, re-checking the employee calendar when
    the slot or assignee changed. Excludes the appointment itself."""
    instance = serializer.instance
    data = serializer.validated_data
    employee = data.get("employee", instance.employee)
    scheduled_at = data.get("scheduled_at", instance.scheduled_at)
    duration_minutes = data.get("duration_minutes", instance.duration_minutes)
    assert_no_appointment_conflict(
        employee_id=employee.id if employee is not None else None,
        scheduled_at=scheduled_at,
        duration_minutes=duration_minutes,
        exclude_id=instance.pk,
    )
    return serializer.save(version=instance.version + 1)


@transaction.atomic
def reserve_event_capacity(event_id, quantity):
    """Atomically reserve ``quantity`` seats on an event under a row lock.

    A capacity of 0 means unlimited (the historical default), so existing
    open-capacity events keep accepting bookings unchanged.
    """
    event = Event.objects.select_for_update().get(pk=event_id)
    if event.capacity and event.booked_count + quantity > event.capacity:
        remaining = event.capacity - event.booked_count
        raise ValidationError(
            f"Only {max(remaining, 0)} seat(s) remain for this event."
        )
    Event.objects.filter(pk=event_id).update(
        booked_count=F("booked_count") + quantity, updated_at=timezone.now()
    )


@transaction.atomic
def release_event_capacity(event_id, quantity):
    """Return ``quantity`` seats to an event when a booking is cancelled.
    Never drives ``booked_count`` below zero."""
    event = Event.objects.select_for_update().get(pk=event_id)
    new_count = max(event.booked_count - quantity, 0)
    Event.objects.filter(pk=event_id).update(
        booked_count=new_count, updated_at=timezone.now()
    )


def _rule_specificity(rule, item):
    """Higher = more specific. Employee+item beats employee, beats item,
    beats org-wide; explicit priority breaks ties at equal specificity."""
    score = 0
    if rule.employee_id is not None:
        score += 4
    if rule.service_id is not None or rule.product_id is not None:
        score += 2
    if rule.branch_id is not None:
        score += 1
    return (score, rule.priority)


def _matching_rules(sale, item):
    item_kind = (
        CommissionRule.AppliesTo.SERVICES
        if item.service_id is not None
        else CommissionRule.AppliesTo.PRODUCTS
    )
    return CommissionRule.objects.filter(
        Q(employee__isnull=True) | Q(employee_id=sale.employee_id),
        Q(branch__isnull=True) | Q(branch_id=sale.branch_id),
        Q(service__isnull=True) | Q(service_id=item.service_id),
        Q(product__isnull=True) | Q(product_id=item.product_id),
        Q(applies_to=CommissionRule.AppliesTo.ALL) | Q(applies_to=item_kind),
        organization_id=sale.organization_id,
        is_active=True,
    )


def _tiered_rate(rule, period_revenue):
    rate = Decimal(0)
    for tier in sorted(rule.tiers, key=lambda t: Decimal(str(t["threshold"]))):
        if period_revenue >= Decimal(str(tier["threshold"])):
            rate = Decimal(str(tier["rate_percent"]))
    return rate


def _item_commission(rule, item, period_revenue):
    line_total = Decimal(item.total_price)
    if rule.basis == CommissionRule.Basis.PERCENT:
        rate = rule.rate_percent or Decimal(0)
        return (line_total * rate / Decimal(100)).quantize(
            TWO_PLACES, rounding=ROUND_HALF_UP
        )
    if rule.basis == CommissionRule.Basis.FIXED:
        return ((rule.fixed_amount or Decimal(0)) * item.quantity).quantize(
            TWO_PLACES, rounding=ROUND_HALF_UP
        )
    rate = _tiered_rate(rule, period_revenue)
    return (line_total * rate / Decimal(100)).quantize(
        TWO_PLACES, rounding=ROUND_HALF_UP
    )


@transaction.atomic
def calculate_sale_commissions(sale):
    """Write CommissionEntry rows for a completed sale. Idempotent: a sale
    that already has commission entries is left untouched."""
    if sale.employee_id is None:
        return []
    if sale.status != sale.Status.COMPLETED:
        raise ValidationError("Commissions are calculated for completed sales only.")
    if CommissionEntry.objects.filter(
        sale=sale, entry_type=CommissionEntry.EntryType.COMMISSION
    ).exists():
        return []

    # Period revenue for tiered rules: this employee's completed sales in
    # the current calendar month.
    now = timezone.now()
    period_revenue = type(sale).objects.filter(
        employee_id=sale.employee_id,
        status=sale.Status.COMPLETED,
        created_at__year=now.year,
        created_at__month=now.month,
    ).aggregate(total=Sum("total_amount"))["total"] or Decimal(0)

    entries = []
    items = sale.items.select_related("service", "product")
    for item in items:
        rules = list(_matching_rules(sale, item))
        if not rules:
            # Legacy fallback: the employee's flat profile rate.
            rate = sale.employee.commission_rate or Decimal(0)
            if rate == 0:
                continue
            amount = (Decimal(item.total_price) * rate / Decimal(100)).quantize(
                TWO_PLACES, rounding=ROUND_HALF_UP
            )
            description = f"Flat profile rate {rate}% on {item}"
        else:
            rule = max(rules, key=lambda candidate: _rule_specificity(candidate, item))
            amount = _item_commission(rule, item, period_revenue)
            description = f"Rule '{rule.name}' on {item}"
        if amount <= 0:
            continue
        entries.append(
            CommissionEntry(
                organization_id=sale.organization_id,
                employee_id=sale.employee_id,
                sale=sale,
                amount=amount,
                entry_type=CommissionEntry.EntryType.COMMISSION,
                description=description,
            )
        )
    return CommissionEntry.objects.bulk_create(entries)


def employee_loaded_cost(employee, on_date=None):
    """Fully loaded monthly cost: active cost components on the date, with
    the profile salary as fallback when no BASE_SALARY component exists."""
    on_date = on_date or timezone.now().date()
    components = EmployeeCostComponent.objects.filter(
        Q(effective_to__isnull=True) | Q(effective_to__gte=on_date),
        employee=employee,
        effective_from__lte=on_date,
    )
    breakdown = {}
    for component in components:
        key = component.component_type
        breakdown[key] = breakdown.get(key, Decimal(0)) + component.monthly_amount
    if EmployeeCostComponent.ComponentType.BASE_SALARY not in breakdown:
        breakdown[EmployeeCostComponent.ComponentType.BASE_SALARY] = (
            employee.monthly_salary or Decimal(0)
        )
    total = sum(breakdown.values(), Decimal(0))
    return {"total_monthly": total, "components": breakdown}


def organization_labor_summary(organization_id, on_date=None):
    """Org-level labor compliance snapshot: saudization ratio (Nitaqat
    input) and the total fully loaded monthly payroll cost.

    Runs in a constant number of queries regardless of headcount: one grouped
    count for the saudization ratio, and one pass over the org's active cost
    components (instead of a per-employee query). Employees without a
    BASE_SALARY component fall back to their profile salary.
    """
    from operations.models import Employee, EmployeeCostComponent

    counts = Employee.objects.filter(
        organization_id=organization_id, is_active=True
    ).aggregate(
        total=Count("id"),
        saudi=Count("id", filter=Q(is_saudi=True)),
    )
    total = counts["total"]
    saudi = counts["saudi"]

    on_date = on_date or timezone.now().date()
    salary_by_employee = dict(
        Employee.objects.filter(
            organization_id=organization_id, is_active=True
        ).values_list("id", "monthly_salary")
    )
    # One query for every active cost component in the org effective on the date.
    components = EmployeeCostComponent.objects.filter(
        Q(effective_to__isnull=True) | Q(effective_to__gte=on_date),
        employee__organization_id=organization_id,
        employee__is_active=True,
        effective_from__lte=on_date,
    ).values_list("employee_id", "component_type", "monthly_amount")

    loaded_total = Decimal(0)
    employees_with_base = set()
    for employee_id, component_type, monthly_amount in components:
        loaded_total += monthly_amount or Decimal(0)
        if component_type == EmployeeCostComponent.ComponentType.BASE_SALARY:
            employees_with_base.add(employee_id)
    # Profile-salary fallback for anyone lacking an explicit BASE_SALARY row.
    for employee_id, monthly_salary in salary_by_employee.items():
        if employee_id not in employees_with_base:
            loaded_total += monthly_salary or Decimal(0)

    return {
        "active_employees": total,
        "saudi_employees": saudi,
        "saudization_percent": round((saudi / total) * 100, 1) if total else None,
        "total_loaded_monthly_cost": loaded_total,
    }


__all__ = [
    "assert_no_appointment_conflict",
    "book_appointment",
    "calculate_sale_commissions",
    "employee_loaded_cost",
    "organization_labor_summary",
    "release_event_capacity",
    "reschedule_appointment",
    "reserve_event_capacity",
]
