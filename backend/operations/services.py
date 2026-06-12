"""Operations services: the commission calculator and the Saudi labor
loaded-cost engine.

Commission entries are append-only: the calculator is idempotent per sale
(it refuses to double-write), and corrections happen through explicit
ADJUSTMENT entries, never by editing history.
"""

from decimal import ROUND_HALF_UP, Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone

from operations.models import (
    CommissionEntry,
    CommissionRule,
    EmployeeCostComponent,
)

TWO_PLACES = Decimal("0.01")


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
    input) and the total fully loaded monthly payroll cost."""
    from operations.models import Employee

    employees = Employee.objects.filter(organization_id=organization_id, is_active=True)
    total = employees.count()
    saudi = employees.filter(is_saudi=True).count()
    loaded_total = Decimal(0)
    for employee in employees:
        loaded_total += employee_loaded_cost(employee, on_date)["total_monthly"]
    return {
        "active_employees": total,
        "saudi_employees": saudi,
        "saudization_percent": round((saudi / total) * 100, 1) if total else None,
        "total_loaded_monthly_cost": loaded_total,
    }


__all__ = [
    "calculate_sale_commissions",
    "employee_loaded_cost",
    "organization_labor_summary",
]
