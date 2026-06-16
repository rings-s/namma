from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from accounts.models import UserRole
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
from commerce.serializers import (
    PriceQuoteSerializer,
    PricingRuleSerializer,
    CustomerPackageRedeemSerializer,
    CustomerPackageSerializer,
    GiftCardRedeemSerializer,
    GiftCardSerializer,
    GiftCardTransactionSerializer,
    PackageItemSerializer,
    PackageRedemptionSerializer,
    PackageSerializer,
    ProductSerializer,
    SaleItemSerializer,
    SaleSerializer,
    ServiceCategorySerializer,
    ServiceSerializer,
    StoreCreditAccountSerializer,
    StoreCreditAdjustSerializer,
    StoreCreditTransactionSerializer,
)
from core.api import TenantScopedReadOnlyViewSet, TenantScopedViewSet, require_org_role


class ServiceCategoryViewSet(TenantScopedViewSet):
    queryset = ServiceCategory.objects.all()
    serializer_class = ServiceCategorySerializer
    search_fields = ["name"]


class ServiceViewSet(TenantScopedViewSet):
    queryset = Service.objects.select_related("category")
    serializer_class = ServiceSerializer
    search_fields = ["name"]
    ordering_fields = ["price", "duration_minutes", "created_at"]


class ProductViewSet(TenantScopedViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    search_fields = ["name", "sku"]
    ordering_fields = ["price", "stock_quantity", "created_at"]


class SaleViewSet(TenantScopedViewSet):
    queryset = Sale.objects.select_related(
        "customer", "employee", "branch"
    ).prefetch_related("items")
    serializer_class = SaleSerializer
    search_fields = ["sale_number"]
    ordering_fields = ["created_at", "total_amount"]

    def perform_create(self, serializer):
        from django.db import transaction

        from commerce.services import commit_sale_stock
        from financials.models import DocumentSequence
        from financials.services import next_document_number

        self._check_tenant_ownership(serializer)
        data = serializer.validated_data
        try:
            with transaction.atomic():
                sale = serializer.save(
                    sale_number=next_document_number(
                        organization=data["organization"],
                        document_type=DocumentSequence.DocumentType.SALE,
                        branch=data.get("branch"),
                    )
                )
                # A sale created already-completed commits its stock now (any
                # lines added later complete via the update path).
                commit_sale_stock(sale, created_by=self.request.user)
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages)

    def perform_update(self, serializer):
        """Commit stock when a sale transitions into COMPLETED. Idempotent, so
        edits to an already-completed sale never double-deduct."""
        from django.db import transaction

        from commerce.services import commit_sale_stock

        self._check_tenant_ownership(serializer)
        try:
            with transaction.atomic():
                sale = serializer.save()
                commit_sale_stock(sale, created_by=self.request.user)
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages)

    @action(detail=True, methods=["post"])
    def commissions(self, request, pk=None):
        """Queue commission calculation for a completed sale. Manager+.
        Idempotent — already-commissioned sales are left untouched."""
        from operations.tasks import calculate_sale_commissions_task

        sale = self.get_object()
        require_org_role(request.user, sale.organization_id, UserRole.Role.MANAGER)
        if sale.status != Sale.Status.COMPLETED:
            raise ValidationError("Commissions apply to completed sales only.")
        calculate_sale_commissions_task.delay(str(sale.pk))
        return Response({"detail": "queued"}, status=status.HTTP_202_ACCEPTED)


class SaleItemViewSet(TenantScopedViewSet):
    queryset = SaleItem.objects.select_related("sale", "service", "product")
    serializer_class = SaleItemSerializer
    org_field = "sale__organization"


class GiftCardViewSet(TenantScopedViewSet):
    queryset = GiftCard.objects.select_related("purchased_by", "sale")
    serializer_class = GiftCardSerializer
    search_fields = ["code"]
    # No DELETE: cards are cancelled (status), never erased from the ledger.
    http_method_names = ["get", "post", "patch", "head", "options"]

    def perform_create(self, serializer):
        self._check_tenant_ownership(serializer)
        gift_card = serializer.save(
            balance=serializer.validated_data["initial_value"],
            status=GiftCard.Status.ACTIVE,
        )
        GiftCardTransaction.objects.create(
            gift_card=gift_card,
            transaction_type=GiftCardTransaction.Type.ISSUE,
            amount=gift_card.initial_value,
            balance_after=gift_card.balance,
            sale=gift_card.sale,
            created_by=self.request.user,
        )

    @action(detail=True, methods=["post"])
    def redeem(self, request, pk=None):
        gift_card = self.get_object()
        serializer = GiftCardRedeemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        sale = serializer.validated_data.get("sale")
        if sale is not None and sale.organization_id != gift_card.organization_id:
            raise PermissionDenied("Sale belongs to a different organization.")
        try:
            txn = gift_card.redeem(
                amount=serializer.validated_data["amount"],
                sale=sale,
                created_by=request.user,
            )
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages)
        return Response(
            GiftCardTransactionSerializer(txn).data, status=status.HTTP_201_CREATED
        )


class GiftCardTransactionViewSet(TenantScopedReadOnlyViewSet):
    queryset = GiftCardTransaction.objects.select_related("gift_card", "sale")
    serializer_class = GiftCardTransactionSerializer
    org_field = "gift_card__organization"


class StoreCreditAccountViewSet(TenantScopedViewSet):
    queryset = StoreCreditAccount.objects.select_related("customer")
    serializer_class = StoreCreditAccountSerializer
    # Balances move only through the adjust action's ledger writes.
    http_method_names = ["get", "post", "head", "options"]

    @action(detail=True, methods=["post"])
    def adjust(self, request, pk=None):
        account = self.get_object()
        # Manual credit/debit is a money operation: manager and above only.
        require_org_role(request.user, account.organization_id, UserRole.Role.MANAGER)
        serializer = StoreCreditAdjustSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        sale = serializer.validated_data.get("sale")
        if sale is not None and sale.organization_id != account.organization_id:
            raise PermissionDenied("Sale belongs to a different organization.")
        try:
            txn = account.apply(
                transaction_type=serializer.validated_data["transaction_type"],
                amount=serializer.validated_data["amount"],
                sale=sale,
                created_by=request.user,
                description=serializer.validated_data["description"],
            )
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages)
        return Response(
            StoreCreditTransactionSerializer(txn).data, status=status.HTTP_201_CREATED
        )


class StoreCreditTransactionViewSet(TenantScopedReadOnlyViewSet):
    queryset = StoreCreditTransaction.objects.select_related("account", "sale")
    serializer_class = StoreCreditTransactionSerializer
    org_field = "account__organization"


class PackageViewSet(TenantScopedViewSet):
    queryset = Package.objects.prefetch_related("items__service")
    serializer_class = PackageSerializer
    search_fields = ["name"]


class PackageItemViewSet(TenantScopedViewSet):
    queryset = PackageItem.objects.select_related("package", "service")
    serializer_class = PackageItemSerializer
    org_field = "package__organization"


class CustomerPackageViewSet(TenantScopedViewSet):
    queryset = CustomerPackage.objects.select_related("customer", "package", "sale")
    serializer_class = CustomerPackageSerializer
    # Lifecycle moves through redemptions; no direct edits or deletes.
    http_method_names = ["get", "post", "head", "options"]

    @action(detail=True, methods=["post"])
    def redeem(self, request, pk=None):
        customer_package = self.get_object()
        serializer = CustomerPackageRedeemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        appointment = serializer.validated_data.get("appointment")
        if (
            appointment is not None
            and appointment.organization_id != customer_package.organization_id
        ):
            raise PermissionDenied("Appointment belongs to a different organization.")
        try:
            redemption = customer_package.redeem(
                package_item=serializer.validated_data["package_item"],
                quantity=serializer.validated_data["quantity"],
                appointment=appointment,
                created_by=request.user,
            )
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages)
        return Response(
            PackageRedemptionSerializer(redemption).data,
            status=status.HTTP_201_CREATED,
        )


class PackageRedemptionViewSet(TenantScopedReadOnlyViewSet):
    queryset = PackageRedemption.objects.select_related(
        "customer_package", "package_item", "appointment"
    )
    serializer_class = PackageRedemptionSerializer
    org_field = "customer_package__organization"


class PricingRuleViewSet(TenantScopedViewSet):
    queryset = PricingRule.objects.select_related(
        "branch", "service", "product", "segment"
    )
    serializer_class = PricingRuleSerializer
    search_fields = ["name"]

    @action(detail=False, methods=["post"])
    def quote(self, request):
        """Resolve the effective price for a service/product right now (or
        at ``at``), optionally for a specific customer and measured
        utilization. Read-only: nothing is persisted."""
        from django.db.models import Q
        from django.utils import timezone as dj_timezone

        from commerce.pricing import resolve_price
        from customers.models import Customer

        params = PriceQuoteSerializer(data=request.data)
        params.is_valid(raise_exception=True)
        data = params.validated_data

        org_ids = self.allowed_organization_ids()
        if "service" in data:
            items = Service.objects.filter(pk=data["service"])
            item_filter = {"service": data["service"]}
        else:
            items = Product.objects.filter(pk=data["product"])
            item_filter = {"product": data["product"]}
        if org_ids is not None:
            items = items.filter(organization_id__in=org_ids)
        item = items.first()
        if item is None:
            raise ValidationError("Unknown service or product.")

        customer = None
        if "customer" in data:
            customer = Customer.objects.filter(
                pk=data["customer"], organization_id=item.organization_id
            ).first()

        rules = PricingRule.objects.filter(
            Q(**item_filter) | Q(service__isnull=True, product__isnull=True),
            organization_id=item.organization_id,
            is_active=True,
        )
        price, rule = resolve_price(
            item.price,
            rules,
            when=data.get("at") or dj_timezone.now(),
            customer=customer,
            utilization_percent=data.get("utilization_percent"),
        )
        return Response(
            {
                "base_price": str(item.price),
                "final_price": str(price),
                "applied_rule": str(rule.pk) if rule else None,
                "applied_rule_name": rule.name if rule else None,
            }
        )
