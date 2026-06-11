<<<<<<< HEAD
from django.db import models

# Create your models here.
=======
"""Inventory: stock movements and inter-branch transfers."""

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
        "organnizations.Organization",
        on_delete=models.CASCADE,
        related_name="stock_movements",
    )
    branch = models.ForeignKey(
        "organnizations.Branch",
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
        "organnizations.Organization",
        on_delete=models.CASCADE,
        related_name="stock_transfers",
    )
    from_branch = models.ForeignKey(
        "organnizations.Branch",
        on_delete=models.CASCADE,
        related_name="stock_transfers_out",
    )
    to_branch = models.ForeignKey(
        "organnizations.Branch",
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
        return f"{self.product} x {self.quantity}: {self.from_branch} -> {self.to_branch}"
>>>>>>> a3235b4 (feat(db): initialize core relational schema)
