"""Inventory: stock movements, inter-branch transfers, suppliers,
purchase orders and reorder rules."""

from django.conf import settings
from django.db import models

from core.models import BaseModel


class StockMovement(BaseModel):
    class MovementType(models.TextChoices):
        PURCHASE = "purchase", "Purchase"
        SALE = "sale", "Sale"
        ADJUSTMENT = "adjustment", "Adjustment"
        TRANSFER_IN = "transfer_in", "Transfer In"
        TRANSFER_OUT = "transfer_out", "Transfer Out"
        RETURN = "return", "Return"

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="stock_movements",
    )
    branch = models.ForeignKey(
        "organizations.Branch",
        on_delete=models.CASCADE,
        related_name="stock_movements",
    )
    product = models.ForeignKey(
        "commerce.Product",
        on_delete=models.CASCADE,
        related_name="stock_movements",
    )
    movement_type = models.CharField(max_length=20, choices=MovementType.choices)
    quantity = models.IntegerField(help_text="Signed quantity delta.")
    reference_type = models.CharField(max_length=100, blank=True)
    reference_id = models.UUIDField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="+",
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "created_at"]),
            models.Index(fields=["product", "created_at"]),
        ]

    def __str__(self):
        return f"{self.get_movement_type_display()} {self.quantity} x {self.product}"


class StockTransfer(BaseModel):
    class Status(models.TextChoices):
        REQUESTED = "requested", "Requested"
        APPROVED = "approved", "Approved"
        IN_TRANSIT = "in_transit", "In Transit"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="stock_transfers",
    )
    from_branch = models.ForeignKey(
        "organizations.Branch",
        on_delete=models.CASCADE,
        related_name="stock_transfers_out",
    )
    to_branch = models.ForeignKey(
        "organizations.Branch",
        on_delete=models.CASCADE,
        related_name="stock_transfers_in",
    )
    product = models.ForeignKey(
        "commerce.Product",
        on_delete=models.CASCADE,
        related_name="stock_transfers",
    )
    quantity = models.PositiveIntegerField()
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.REQUESTED
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="+",
        null=True,
        blank=True,
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="+",
        null=True,
        blank=True,
    )
    transferred_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "status"]),
        ]

    def __str__(self):
        return (
            f"{self.product} x {self.quantity}: {self.from_branch} -> {self.to_branch}"
        )


# ---------------------------------------------------------------------------
# Suppliers & procurement
# ---------------------------------------------------------------------------


class Supplier(BaseModel):
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="suppliers",
    )
    name = models.CharField(max_length=255)
    contact_name = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=32, blank=True)
    email = models.EmailField(blank=True)
    vat_number = models.CharField(max_length=15, blank=True)
    address = models.CharField(max_length=500, blank=True)
    payment_terms = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["organization", "is_active"]),
        ]

    def __str__(self):
        return self.name


class PurchaseOrder(BaseModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        PARTIALLY_RECEIVED = "partially_received", "Partially Received"
        RECEIVED = "received", "Received"
        CANCELLED = "cancelled", "Cancelled"

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="purchase_orders",
    )
    branch = models.ForeignKey(
        "organizations.Branch",
        on_delete=models.CASCADE,
        related_name="purchase_orders",
    )
    supplier = models.ForeignKey(
        Supplier, on_delete=models.PROTECT, related_name="purchase_orders"
    )
    # Unique per tenant, not globally: next_document_number mints org-scoped
    # sequences (PO-2026-00001 restarts for each organization).
    po_number = models.CharField(max_length=50)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    expected_at = models.DateField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    received_at = models.DateTimeField(null=True, blank=True)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "po_number"],
                name="uniq_po_number_per_org",
            ),
        ]
        indexes = [
            models.Index(fields=["organization", "status"]),
        ]

    def __str__(self):
        return self.po_number


class PurchaseOrderLine(BaseModel):
    purchase_order = models.ForeignKey(
        PurchaseOrder, on_delete=models.CASCADE, related_name="lines"
    )
    product = models.ForeignKey(
        "commerce.Product",
        on_delete=models.PROTECT,
        related_name="purchase_order_lines",
    )
    quantity_ordered = models.PositiveIntegerField()
    quantity_received = models.PositiveIntegerField(default=0)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity_received__lte=models.F("quantity_ordered")),
                name="po_line_received_lte_ordered",
            )
        ]

    def __str__(self):
        return f"{self.product} x {self.quantity_ordered} on {self.purchase_order}"


class ReorderRule(BaseModel):
    """Low-stock alerting: when a product's on-hand quantity drops to the
    reorder point, the daily sweep raises an alert/draft PO suggestion."""

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="reorder_rules",
    )
    branch = models.ForeignKey(
        "organizations.Branch",
        on_delete=models.CASCADE,
        related_name="reorder_rules",
        null=True,
        blank=True,
    )
    product = models.ForeignKey(
        "commerce.Product",
        on_delete=models.CASCADE,
        related_name="reorder_rules",
    )
    preferred_supplier = models.ForeignKey(
        Supplier,
        on_delete=models.SET_NULL,
        related_name="reorder_rules",
        null=True,
        blank=True,
    )
    reorder_point = models.PositiveIntegerField()
    reorder_quantity = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "branch", "product"],
                name="uniq_reorder_rule_per_product_branch",
            )
        ]

    def __str__(self):
        return f"Reorder {self.product} at {self.reorder_point}"
