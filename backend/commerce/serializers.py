from decimal import Decimal

from rest_framework import serializers

from commerce.models import (
    PricingRule,
    CustomerPackage,
    GiftCard,
    GiftCardTransaction,
    Package,
    PackageItem,
    PackageRedemption,
    Product,
    Sale,
    SaleItem,
    Service,
    ServiceCategory,
    StoreCreditAccount,
    StoreCreditTransaction,
)
from core.api import AUDIT_FIELDS
from operations.models import Appointment


class ServiceCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceCategory
        fields = "__all__"
        read_only_fields = AUDIT_FIELDS


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = "__all__"
        read_only_fields = AUDIT_FIELDS


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = "__all__"
        read_only_fields = (*AUDIT_FIELDS, "deleted_at")


class SaleItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = SaleItem
        fields = "__all__"
        read_only_fields = AUDIT_FIELDS


class SaleSerializer(serializers.ModelSerializer):
    items = SaleItemSerializer(many=True, read_only=True)

    class Meta:
        model = Sale
        fields = "__all__"
        read_only_fields = AUDIT_FIELDS


class GiftCardSerializer(serializers.ModelSerializer):
    class Meta:
        model = GiftCard
        fields = "__all__"
        # Balance and status only ever change through the transaction ledger.
        read_only_fields = (*AUDIT_FIELDS, "balance", "status")

    def validate_initial_value(self, value):
        if value <= 0:
            raise serializers.ValidationError("Initial value must be positive.")
        return value


class GiftCardRedeemSerializer(serializers.Serializer):
    amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal("0.01")
    )
    sale = serializers.PrimaryKeyRelatedField(
        queryset=Sale.objects.all(), required=False, allow_null=True
    )


class GiftCardTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = GiftCardTransaction
        fields = "__all__"


class StoreCreditAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoreCreditAccount
        fields = "__all__"
        read_only_fields = (*AUDIT_FIELDS, "balance")


class StoreCreditAdjustSerializer(serializers.Serializer):
    transaction_type = serializers.ChoiceField(
        choices=StoreCreditTransaction.Type.choices
    )
    amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal("0.01")
    )
    description = serializers.CharField(max_length=255, required=False, default="")
    sale = serializers.PrimaryKeyRelatedField(
        queryset=Sale.objects.all(), required=False, allow_null=True
    )


class StoreCreditTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoreCreditTransaction
        fields = "__all__"


class PackageItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PackageItem
        fields = "__all__"
        read_only_fields = AUDIT_FIELDS


class PackageSerializer(serializers.ModelSerializer):
    items = PackageItemSerializer(many=True, read_only=True)

    class Meta:
        model = Package
        fields = "__all__"
        read_only_fields = AUDIT_FIELDS


class CustomerPackageSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerPackage
        fields = "__all__"
        # Status transitions happen through redemption/expiry, not direct writes.
        read_only_fields = (*AUDIT_FIELDS, "status")


class CustomerPackageRedeemSerializer(serializers.Serializer):
    package_item = serializers.PrimaryKeyRelatedField(
        queryset=PackageItem.objects.all()
    )
    quantity = serializers.IntegerField(min_value=1, default=1)
    appointment = serializers.PrimaryKeyRelatedField(
        queryset=Appointment.objects.all(), required=False, allow_null=True
    )


class PackageRedemptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PackageRedemption
        fields = "__all__"


class PricingRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = PricingRule
        fields = "__all__"
        read_only_fields = AUDIT_FIELDS

    def validate(self, attrs):
        targets = [attrs.get("service"), attrs.get("product")]
        if all(target is not None for target in targets):
            raise serializers.ValidationError(
                "A rule targets a service or a product, not both."
            )
        return attrs


class PriceQuoteSerializer(serializers.Serializer):
    service = serializers.UUIDField(required=False)
    product = serializers.UUIDField(required=False)
    customer = serializers.UUIDField(required=False)
    at = serializers.DateTimeField(required=False)
    utilization_percent = serializers.IntegerField(
        required=False, min_value=0, max_value=100
    )

    def validate(self, attrs):
        if ("service" in attrs) == ("product" in attrs):
            raise serializers.ValidationError(
                "Provide exactly one of service or product."
            )
        return attrs
