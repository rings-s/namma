from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from accounts.models import UserRole
from core.api import TenantScopedViewSet, require_org_role
from financials.models import DocumentSequence
from financials.services import next_document_number
from inventory.models import (
    PurchaseOrder,
    PurchaseOrderLine,
    ReorderRule,
    StockMovement,
    StockTransfer,
    Supplier,
)
from inventory.serializers import (
    PurchaseOrderLineSerializer,
    PurchaseOrderReceiptSerializer,
    PurchaseOrderSerializer,
    ReorderRuleSerializer,
    StockMovementSerializer,
    StockTransferSerializer,
    SupplierSerializer,
)
from inventory.services import low_stock_products, receive_purchase_order_lines


class StockMovementViewSet(TenantScopedViewSet):
    # Movements are an append-only ledger; edits should go through reversing entries.
    http_method_names = ["get", "post", "head", "options"]
    queryset = StockMovement.objects.select_related("product", "branch")
    serializer_class = StockMovementSerializer
    ordering_fields = ["created_at"]


class StockTransferViewSet(TenantScopedViewSet):
    queryset = StockTransfer.objects.select_related(
        "product", "from_branch", "to_branch"
    )
    serializer_class = StockTransferSerializer
    ordering_fields = ["created_at"]


class SupplierViewSet(TenantScopedViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    search_fields = ["name", "contact_name", "email"]


class PurchaseOrderViewSet(TenantScopedViewSet):
    queryset = PurchaseOrder.objects.select_related(
        "supplier", "branch"
    ).prefetch_related("lines__product")
    serializer_class = PurchaseOrderSerializer
    search_fields = ["po_number"]
    ordering_fields = ["created_at", "expected_at"]

    def perform_create(self, serializer):
        """Assign a gap-free PO number server-side; clients never supply one.

        Wrapped in a transaction so ``next_document_number``'s
        ``select_for_update`` always has one, even without an idempotency key.
        """
        self._check_tenant_ownership(serializer)
        organization = serializer.validated_data["organization"]
        with transaction.atomic():
            serializer.save(
                po_number=next_document_number(
                    organization=organization,
                    document_type=DocumentSequence.DocumentType.PURCHASE_ORDER,
                    branch=serializer.validated_data.get("branch"),
                )
            )

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        """Move a draft order to the supplier (draft -> submitted)."""
        purchase_order = self.get_object()
        require_org_role(
            request.user, purchase_order.organization_id, UserRole.Role.MANAGER
        )
        if purchase_order.status != PurchaseOrder.Status.DRAFT:
            raise ValidationError("Only draft purchase orders can be submitted.")
        if not purchase_order.lines.exists():
            raise ValidationError("A purchase order needs at least one line.")
        purchase_order.status = PurchaseOrder.Status.SUBMITTED
        purchase_order.submitted_at = timezone.now()
        purchase_order.save(update_fields=["status", "submitted_at", "updated_at"])
        return Response(self.get_serializer(purchase_order).data)

    @action(detail=True, methods=["post"])
    def receive(self, request, pk=None):
        """Record a (partial) delivery: appends stock movements and
        advances the order state. Manager+."""
        purchase_order = self.get_object()
        require_org_role(
            request.user, purchase_order.organization_id, UserRole.Role.MANAGER
        )
        params = PurchaseOrderReceiptSerializer(data=request.data)
        params.is_valid(raise_exception=True)
        try:
            purchase_order = receive_purchase_order_lines(
                purchase_order,
                params.validated_data["receipts"],
                received_by=request.user,
            )
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages)
        return Response(self.get_serializer(purchase_order).data)


class PurchaseOrderLineViewSet(TenantScopedViewSet):
    queryset = PurchaseOrderLine.objects.select_related("purchase_order", "product")
    serializer_class = PurchaseOrderLineSerializer
    org_field = "purchase_order__organization"


class ReorderRuleViewSet(TenantScopedViewSet):
    queryset = ReorderRule.objects.select_related(
        "product", "branch", "preferred_supplier"
    )
    serializer_class = ReorderRuleSerializer

    @action(detail=False, methods=["get"], url_path="low-stock")
    def low_stock(self, request):
        """Products at/below their reorder point. ?organization=<id> when
        the user belongs to several organizations."""
        organization_id = request.query_params.get("organization")
        if not organization_id:
            org_ids = self.allowed_organization_ids()
            if org_ids is None or len(org_ids) != 1:
                return Response({"detail": "Pass ?organization=<id>."}, status=400)
            organization_id = org_ids[0]
        require_org_role(request.user, organization_id, UserRole.Role.STAFF)
        return Response(low_stock_products(organization_id))
