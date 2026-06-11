from rest_framework import permissions, viewsets

from core.api import TenantScopedReadOnlyViewSet, TenantScopedViewSet
from core.models import AccessLog, AuditLog, Country, Currency, Translation
from core.serializers import (
    AccessLogSerializer,
    AuditLogSerializer,
    CountrySerializer,
    CurrencySerializer,
    TranslationSerializer,
)


class CountryViewSet(viewsets.ReadOnlyModelViewSet):
    """Global reference data, managed through the Django admin."""

    queryset = Country.objects.all()
    serializer_class = CountrySerializer
    permission_classes = [permissions.IsAuthenticated]
    search_fields = ["name", "code"]


class CurrencyViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Currency.objects.all()
    serializer_class = CurrencySerializer
    permission_classes = [permissions.IsAuthenticated]
    search_fields = ["name", "code"]


class TranslationViewSet(TenantScopedViewSet):
    queryset = Translation.objects.all()
    serializer_class = TranslationSerializer
    search_fields = ["entity_type", "field", "locale"]


class AuditLogViewSet(TenantScopedReadOnlyViewSet):
    queryset = AuditLog.objects.select_related("user")
    serializer_class = AuditLogSerializer
    search_fields = ["action", "entity_type"]
    ordering_fields = ["occurred_at", "created_at"]


class AccessLogViewSet(TenantScopedReadOnlyViewSet):
    queryset = AccessLog.objects.select_related("user")
    serializer_class = AccessLogSerializer
    search_fields = ["action", "entity_type"]
    ordering_fields = ["accessed_at"]
