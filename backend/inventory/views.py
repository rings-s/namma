<<<<<<< HEAD
from django.shortcuts import render

# Create your views here.
=======
from core.api import TenantScopedViewSet
from inventory.models import StockMovement, StockTransfer
from inventory.serializers import StockMovementSerializer, StockTransferSerializer


class StockMovementViewSet(TenantScopedViewSet):
    # Movements are an append-only ledger; edits should go through reversing entries.
    http_method_names = ["get", "post", "head", "options"]
    queryset = StockMovement.objects.select_related("product", "branch")
    serializer_class = StockMovementSerializer
    ordering_fields = ["created_at"]


class StockTransferViewSet(TenantScopedViewSet):
    queryset = StockTransfer.objects.select_related("product", "from_branch", "to_branch")
    serializer_class = StockTransferSerializer
    ordering_fields = ["created_at"]
>>>>>>> a3235b4 (feat(db): initialize core relational schema)
