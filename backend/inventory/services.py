"""Inventory services: purchase-order receiving.

Receiving is the only path that turns a PO into stock: each receipt
appends an immutable StockMovement, bumps the product counter under a row
lock, and advances the PO state machine (submitted -> partially_received
-> received). Over-receiving is rejected at both the service and the
database (check constraint) layers.
"""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from inventory.models import PurchaseOrder, PurchaseOrderLine, StockMovement

RECEIVABLE_STATUSES = (
    PurchaseOrder.Status.SUBMITTED,
    PurchaseOrder.Status.PARTIALLY_RECEIVED,
)


@transaction.atomic
def receive_purchase_order_lines(purchase_order, receipts, received_by=None):
    """Receive quantities against a PO.

    ``receipts`` is ``[{"line": <PurchaseOrderLine id>, "quantity": int}]``.
    Returns the updated PurchaseOrder. Partial receipts are first-class:
    the PO closes only when every line is fully received.
    """
    purchase_order = PurchaseOrder.objects.select_for_update().get(pk=purchase_order.pk)
    if purchase_order.status not in RECEIVABLE_STATUSES:
        raise ValidationError(
            "Only submitted or partially received purchase orders accept receipts."
        )
    if not receipts:
        raise ValidationError("No receipt lines provided.")

    lines = {
        str(line.pk): line
        for line in PurchaseOrderLine.objects.select_for_update()
        .filter(purchase_order=purchase_order)
        .select_related("product")
    }
    for receipt in receipts:
        line = lines.get(str(receipt.get("line")))
        quantity = int(receipt.get("quantity", 0))
        if line is None:
            raise ValidationError("A receipt references a line not on this order.")
        if quantity <= 0:
            raise ValidationError("Receipt quantities must be positive.")
        if line.quantity_received + quantity > line.quantity_ordered:
            raise ValidationError(
                f"Receiving {quantity} would exceed the ordered quantity "
                f"for {line.product}."
            )
        line.quantity_received += quantity
        line.save(update_fields=["quantity_received", "updated_at"])
        StockMovement.objects.create(
            organization=purchase_order.organization,
            branch=purchase_order.branch,
            product=line.product,
            movement_type=StockMovement.MovementType.PURCHASE,
            quantity=quantity,
            reference_type="purchase_order",
            reference_id=purchase_order.pk,
            created_by=received_by,
        )
        # Counter cache on the product; the movement ledger stays the truth.
        type(line.product).objects.filter(pk=line.product_id).update(
            stock_quantity=F("stock_quantity") + quantity
        )

    fully_received = all(
        line.quantity_received >= line.quantity_ordered for line in lines.values()
    )
    purchase_order.status = (
        PurchaseOrder.Status.RECEIVED
        if fully_received
        else PurchaseOrder.Status.PARTIALLY_RECEIVED
    )
    if fully_received:
        purchase_order.received_at = timezone.now()
    purchase_order.save(update_fields=["status", "received_at", "updated_at"])
    return purchase_order


def low_stock_products(organization_id):
    """Products at/below their reorder point — feeds alerts and PO drafts."""
    from inventory.models import ReorderRule

    alerts = []
    rules = ReorderRule.objects.filter(
        organization_id=organization_id, is_active=True
    ).select_related("product", "preferred_supplier", "branch")
    for rule in rules:
        if rule.product.stock_quantity <= rule.reorder_point:
            alerts.append(
                {
                    "product": str(rule.product_id),
                    "product_name": rule.product.name,
                    "stock_quantity": rule.product.stock_quantity,
                    "reorder_point": rule.reorder_point,
                    "reorder_quantity": rule.reorder_quantity,
                    "preferred_supplier": str(rule.preferred_supplier_id)
                    if rule.preferred_supplier_id
                    else None,
                }
            )
    return alerts


__all__ = ["low_stock_products", "receive_purchase_order_lines"]
