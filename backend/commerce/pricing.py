"""Dynamic price resolution.

The resolver applies the single best (highest-priority) active rule that
matches the context. Rules never stack — stacking makes prices impossible
to explain to a cashier or an auditor; a deliberate single-winner design.
"""

from decimal import ROUND_HALF_UP, Decimal


def _matches(rule, when, segment_ids, utilization_percent):
    if rule.valid_from and when < rule.valid_from:
        return False
    if rule.valid_until and when > rule.valid_until:
        return False
    if rule.days_of_week and when.isoweekday() not in rule.days_of_week:
        return False
    local_time = when.time()
    if rule.start_time and rule.end_time:
        if rule.start_time <= rule.end_time:
            if not (rule.start_time <= local_time <= rule.end_time):
                return False
        elif not (local_time >= rule.start_time or local_time <= rule.end_time):
            return False  # overnight window (e.g. 22:00-02:00)
    if rule.segment_id is not None and rule.segment_id not in segment_ids:
        return False
    if rule.min_utilization_percent is not None and (
        utilization_percent is None
        or utilization_percent < rule.min_utilization_percent
    ):
        return False
    if rule.max_utilization_percent is not None and (
        utilization_percent is None
        or utilization_percent > rule.max_utilization_percent
    ):
        return False
    return True


def resolve_price(
    base_price,
    rules,
    when,
    customer=None,
    utilization_percent=None,
):
    """(final_price, applied_rule) for a base price under the given rules.

    ``rules`` should already be filtered to the org + item (service/product/
    catalog-wide) and ``is_active=True``, ordered by ``-priority`` —
    ``PricingRule.objects`` default ordering does this.
    """
    segment_ids = set()
    if customer is not None:
        segment_ids = set(
            customer.segment_memberships.values_list("segment_id", flat=True)
        )
    base_price = Decimal(base_price)
    for rule in rules:
        if not _matches(rule, when, segment_ids, utilization_percent):
            continue
        if rule.adjustment_type == rule.AdjustmentType.PERCENT:
            adjusted = base_price * (1 + rule.adjustment_value / Decimal(100))
        else:
            adjusted = base_price + rule.adjustment_value
        adjusted = max(adjusted, Decimal(0)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        return adjusted, rule
    return base_price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), None


__all__ = ["resolve_price"]
