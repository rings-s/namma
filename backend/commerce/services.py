"""Commerce services: sale stock commitment.

Selling a product must move inventory. Following the platform's append-only
stock rule, completing a sale writes one immutable ``StockMovement`` per
product line and decrements the product's cached on-hand counter under a row
lock. The operation is idempotent per sale, so re-completing (or a retried
request) never double-deducts.
"""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F

from commerce.models import Product, Sale


@transaction.atomic
def commit_sale_stock(sale, *, created_by=None):
    """Deduct stock for a completed sale's product lines.

    Idempotent: a sale whose stock movements already exist is a no-op, so it is
    safe to call on every transition into COMPLETED. Raises ``ValidationError``
    if any line would drive a product below zero (no overselling). Service-only
    lines (``product`` null) are skipped. Returns the created movements.
    """
    from inventory.models import StockMovement

    if sale.status != Sale.Status.COMPLETED:
        return []
    already_committed = StockMovement.objects.filter(
        reference_type="sale",
        reference_id=sale.pk,
        movement_type=StockMovement.MovementType.SALE,
    ).exists()
    if already_committed:
        return []

    movements = []
    # Lock each product as we touch it so concurrent sales of the same product
    # can't both pass the on-hand check and oversell.
    for item in sale.items.filter(product__isnull=False).select_related("product"):
        product = Product.objects.select_for_update().get(pk=item.product_id)
        if product.stock_quantity < item.quantity:
            raise ValidationError(
                f"Insufficient stock for {product.name}: "
                f"{product.stock_quantity} on hand, {item.quantity} requested."
            )
        movements.append(
            StockMovement.objects.create(
                organization=sale.organization,
                branch=sale.branch,
                product=product,
                movement_type=StockMovement.MovementType.SALE,
                quantity=-item.quantity,  # signed delta: a sale removes stock
                reference_type="sale",
                reference_id=sale.pk,
                created_by=created_by,
            )
        )
        Product.objects.filter(pk=product.pk).update(
            stock_quantity=F("stock_quantity") - item.quantity
        )
    return movements


__all__ = ["commit_sale_stock"]
