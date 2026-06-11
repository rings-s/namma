from rest_framework import serializers

from core.api import AUDIT_FIELDS
from inventory.models import StockMovement, StockTransfer


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
