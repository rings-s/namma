"""Purchase-order receiving and low-stock alerting tests."""

from decimal import Decimal

from django.core.exceptions import ValidationError
from rest_framework.test import APITestCase

from commerce.models import Product
from inventory.models import (
    PurchaseOrder,
    PurchaseOrderLine,
    ReorderRule,
    StockMovement,
)
from inventory.services import low_stock_products, receive_purchase_order_lines
from organizations.models import Branch, Organization


class ProcurementTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        from inventory.models import Supplier

        cls.org = Organization.objects.create(name="Shine", slug="shine")
        cls.branch = Branch.objects.create(organization=cls.org, name="Main")
        cls.supplier = Supplier.objects.create(organization=cls.org, name="Beauty Co")
        cls.product = Product.objects.create(
            organization=cls.org,
            name="Shampoo",
            price=Decimal("40.00"),
            stock_quantity=2,
        )
        cls.po = PurchaseOrder.objects.create(
            organization=cls.org,
            branch=cls.branch,
            supplier=cls.supplier,
            po_number="PO-1",
            status=PurchaseOrder.Status.SUBMITTED,
        )
        cls.line = PurchaseOrderLine.objects.create(
            purchase_order=cls.po,
            product=cls.product,
            quantity_ordered=10,
            unit_cost=Decimal("20.00"),
        )


class PurchaseOrderReceivingTests(ProcurementTestCase):
    def test_partial_receipt_moves_stock_and_keeps_po_open(self):
        receive_purchase_order_lines(
            self.po, [{"line": str(self.line.pk), "quantity": 4}]
        )
        self.po.refresh_from_db()
        self.line.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(self.po.status, PurchaseOrder.Status.PARTIALLY_RECEIVED)
        self.assertIsNone(self.po.received_at)
        self.assertEqual(self.line.quantity_received, 4)
        self.assertEqual(self.product.stock_quantity, 6)
        movement = StockMovement.objects.get(reference_id=self.po.pk)
        self.assertEqual(movement.movement_type, StockMovement.MovementType.PURCHASE)
        self.assertEqual(movement.quantity, 4)

    def test_full_receipt_closes_the_order(self):
        receive_purchase_order_lines(
            self.po, [{"line": str(self.line.pk), "quantity": 10}]
        )
        self.po.refresh_from_db()
        self.assertEqual(self.po.status, PurchaseOrder.Status.RECEIVED)
        self.assertIsNotNone(self.po.received_at)

    def test_over_receiving_is_rejected(self):
        receive_purchase_order_lines(
            self.po, [{"line": str(self.line.pk), "quantity": 8}]
        )
        with self.assertRaises(ValidationError):
            receive_purchase_order_lines(
                self.po, [{"line": str(self.line.pk), "quantity": 5}]
            )
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 10)  # 2 + 8, nothing extra

    def test_draft_order_cannot_be_received(self):
        PurchaseOrder.objects.filter(pk=self.po.pk).update(
            status=PurchaseOrder.Status.DRAFT
        )
        self.po.refresh_from_db()
        with self.assertRaises(ValidationError):
            receive_purchase_order_lines(
                self.po, [{"line": str(self.line.pk), "quantity": 1}]
            )

    def test_foreign_line_is_rejected(self):
        other_po = PurchaseOrder.objects.create(
            organization=self.org,
            branch=self.branch,
            supplier=self.supplier,
            po_number="PO-2",
            status=PurchaseOrder.Status.SUBMITTED,
        )
        with self.assertRaises(ValidationError):
            receive_purchase_order_lines(
                other_po, [{"line": str(self.line.pk), "quantity": 1}]
            )


class ReorderAlertTests(ProcurementTestCase):
    def test_low_stock_products_lists_breached_rules_only(self):
        ReorderRule.objects.create(
            organization=self.org,
            product=self.product,
            reorder_point=5,
            reorder_quantity=20,
        )
        healthy = Product.objects.create(
            organization=self.org,
            name="Conditioner",
            price=Decimal("45.00"),
            stock_quantity=50,
        )
        ReorderRule.objects.create(
            organization=self.org,
            product=healthy,
            reorder_point=5,
            reorder_quantity=20,
        )
        alerts = low_stock_products(self.org.id)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["product_name"], "Shampoo")
        self.assertEqual(alerts[0]["reorder_quantity"], 20)
