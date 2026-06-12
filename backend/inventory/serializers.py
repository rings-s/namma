from rest_framework import serializers

from core.api import AUDIT_FIELDS
from inventory.models import (
    PurchaseOrder,
    PurchaseOrderLine,
    ReorderRule,
    StockMovement,
    StockTransfer,
    Supplier,
)


class StockMovementSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockMovement
        fields = "__all__"
        read_only_fields = AUDIT_FIELDS


class StockTransferSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockTransfer
        fields = "__all__"
        read_only_fields = AUDIT_FIELDS


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = "__all__"
        read_only_fields = AUDIT_FIELDS


class PurchaseOrderLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchaseOrderLine
        fields = "__all__"
        read_only_fields = (*AUDIT_FIELDS, "quantity_received")


class PurchaseOrderSerializer(serializers.ModelSerializer):
    lines = PurchaseOrderLineSerializer(many=True, read_only=True)

    class Meta:
        model = PurchaseOrder
        fields = "__all__"
        read_only_fields = (
            *AUDIT_FIELDS,
            "status",
            "submitted_at",
            "received_at",
        )


class PurchaseOrderReceiptSerializer(serializers.Serializer):
    class ReceiptLineSerializer(serializers.Serializer):
        line = serializers.UUIDField()
        quantity = serializers.IntegerField(min_value=1)

    receipts = ReceiptLineSerializer(many=True, allow_empty=False)


class ReorderRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReorderRule
        fields = "__all__"
        read_only_fields = AUDIT_FIELDS
