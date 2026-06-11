from rest_framework import serializers

from core.api import AUDIT_FIELDS
from integrations.models import APIKey, Device, SyncOperation, WebhookEndpoint


class APIKeySerializer(serializers.ModelSerializer):
    class Meta:
        model = APIKey
        fields = "__all__"
        read_only_fields = (*AUDIT_FIELDS, "key_hash", "last_used_at", "rotated_at")


class WebhookEndpointSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebhookEndpoint
        fields = "__all__"
        read_only_fields = (*AUDIT_FIELDS, "secret_hash", "last_triggered_at")


class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = "__all__"
        read_only_fields = (*AUDIT_FIELDS, "last_sync_at")


class SyncOperationSerializer(serializers.ModelSerializer):
    class Meta:
        model = SyncOperation
        fields = "__all__"
        read_only_fields = (*AUDIT_FIELDS, "server_applied_at", "conflict_status", "conflict_resolution")
