from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from accounts.models import UserRole
from core.api import (
    TenantScopedReadOnlyViewSet,
    TenantScopedViewSet,
    require_org_role,
)
from integrations import serializers
from integrations.models import (
    APIKey,
    Device,
    IntegrationConnection,
    OutboundEvent,
    SyncOperation,
    WebhookDelivery,
    WebhookEndpoint,
)
from integrations.services import issue_api_key, provision_webhook_endpoint
from integrations.tasks import deliver_webhook_task


class APIKeyViewSet(TenantScopedViewSet):
    """API key management. Creation mints the key server-side and returns
    the plaintext exactly once; afterwards only the prefix is visible."""

    queryset = APIKey.objects.all()
    serializer_class = serializers.APIKeySerializer
    search_fields = ["name"]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        organization = serializer.validated_data["organization"]
        require_org_role(request.user, organization.id, UserRole.Role.ADMIN)
        api_key, plaintext = issue_api_key(
            organization,
            serializer.validated_data["name"],
            scopes=serializer.validated_data.get("scopes"),
            expires_at=serializer.validated_data.get("expires_at"),
        )
        data = self.get_serializer(api_key).data
        data["key"] = plaintext  # shown once, never stored in plaintext
        return Response(data, status=status.HTTP_201_CREATED)


class WebhookEndpointViewSet(TenantScopedViewSet):
    queryset = WebhookEndpoint.objects.all()
    serializer_class = serializers.WebhookEndpointSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        require_org_role(
            request.user,
            serializer.validated_data["organization"].id,
            UserRole.Role.ADMIN,
        )
        endpoint = serializer.save()
        secret = provision_webhook_endpoint(endpoint)
        data = self.get_serializer(endpoint).data
        data["signing_secret"] = secret  # shown once for receiver setup
        return Response(data, status=status.HTTP_201_CREATED)


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


class OutboundEventViewSet(TenantScopedReadOnlyViewSet):
    # Written by domain services through the outbox; read-only for audit.
    queryset = OutboundEvent.objects.all()
    serializer_class = serializers.OutboundEventSerializer
    ordering_fields = ["created_at"]


class WebhookDeliveryViewSet(TenantScopedReadOnlyViewSet):
    queryset = WebhookDelivery.objects.select_related("endpoint", "event")
    serializer_class = serializers.WebhookDeliverySerializer
    org_field = "endpoint__organization"
    ordering_fields = ["created_at"]

    @action(detail=True, methods=["post"])
    def replay(self, request, pk=None):
        """Re-queue a dead or failed delivery. Admin+."""
        delivery = self.get_object()
        require_org_role(
            request.user, delivery.endpoint.organization_id, UserRole.Role.ADMIN
        )
        if delivery.status == WebhookDelivery.Status.DELIVERED:
            raise ValidationError("This delivery already succeeded.")
        delivery.status = WebhookDelivery.Status.PENDING
        delivery.save(update_fields=["status", "updated_at"])
        deliver_webhook_task.delay(str(delivery.pk))
        return Response({"detail": "queued"}, status=status.HTTP_202_ACCEPTED)


class IntegrationConnectionViewSet(TenantScopedViewSet):
    queryset = IntegrationConnection.objects.all()
    serializer_class = serializers.IntegrationConnectionSerializer
