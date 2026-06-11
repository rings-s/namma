<<<<<<< HEAD
from django.shortcuts import render

# Create your views here.
=======
from core.api import TenantScopedViewSet
from integrations import serializers
from integrations.models import APIKey, Device, SyncOperation, WebhookEndpoint


class APIKeyViewSet(TenantScopedViewSet):
    # Key material is generated server-side; only metadata is writable here.
    queryset = APIKey.objects.all()
    serializer_class = serializers.APIKeySerializer
    search_fields = ["name"]


class WebhookEndpointViewSet(TenantScopedViewSet):
    queryset = WebhookEndpoint.objects.all()
    serializer_class = serializers.WebhookEndpointSerializer


class DeviceViewSet(TenantScopedViewSet):
    queryset = Device.objects.select_related("branch")
    serializer_class = serializers.DeviceSerializer
    search_fields = ["device_name", "device_uuid"]


class SyncOperationViewSet(TenantScopedViewSet):
    # Offline-first POS pushes queued operations; conflict resolution is server-side.
    http_method_names = ["get", "post", "head", "options"]
    queryset = SyncOperation.objects.select_related("device")
    serializer_class = serializers.SyncOperationSerializer
    ordering_fields = ["client_timestamp", "created_at"]
>>>>>>> a3235b4 (feat(db): initialize core relational schema)
