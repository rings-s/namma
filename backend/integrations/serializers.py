from rest_framework import serializers

from core.api import AUDIT_FIELDS
from integrations.models import (
    APIKey,
    Device,
    IntegrationConnection,
    OutboundEvent,
    SyncOperation,
    WebhookDelivery,
    WebhookEndpoint,
)


class APIKeySerializer(serializers.ModelSerializer):
    class Meta:
        model = APIKey
        # The hash is internal; the plaintext is returned once at issuance.
        exclude = ("key_hash",)
        read_only_fields = (*AUDIT_FIELDS, "key_prefix", "last_used_at", "rotated_at")


class WebhookEndpointSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebhookEndpoint
        exclude = ("secret_hash", "signing_secret_encrypted")
        read_only_fields = (*AUDIT_FIELDS, "last_triggered_at")


class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = "__all__"
        read_only_fields = (*AUDIT_FIELDS, "last_sync_at")


class SyncOperationSerializer(serializers.ModelSerializer):
    class Meta:
        model = SyncOperation
        fields = "__all__"
        read_only_fields = (
            *AUDIT_FIELDS,
            "server_applied_at",
            "conflict_status",
            "conflict_resolution",
        )


class OutboundEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = OutboundEvent
        fields = "__all__"


class WebhookDeliverySerializer(serializers.ModelSerializer):
    class Meta:
        model = WebhookDelivery
        fields = "__all__"


class IntegrationConnectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = IntegrationConnection
        exclude = ("credentials_encrypted",)
        read_only_fields = (
            *AUDIT_FIELDS,
            "status",
            "external_account_id",
            "last_synced_at",
            "last_error",
        )
