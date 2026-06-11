<<<<<<< HEAD
from django.shortcuts import render

# Create your views here.
=======
from commerce.models import Product, Sale, SaleItem, Service, ServiceCategory
from commerce.serializers import (
    ProductSerializer,
    SaleItemSerializer,
    SaleSerializer,
    ServiceCategorySerializer,
    ServiceSerializer,
)
from core.api import TenantScopedViewSet


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
    queryset = Sale.objects.select_related("customer", "employee", "branch").prefetch_related("items")
    serializer_class = SaleSerializer
    search_fields = ["sale_number"]
    ordering_fields = ["created_at", "total_amount"]


class SaleItemViewSet(TenantScopedViewSet):
    queryset = SaleItem.objects.select_related("sale", "service", "product")
    serializer_class = SaleItemSerializer
    org_field = "sale__organization"
>>>>>>> a3235b4 (feat(db): initialize core relational schema)
