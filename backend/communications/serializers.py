from rest_framework import serializers

from communications.models import (
    ConsentRecord,
    MessageDispatch,
    MessageTemplate,
    Notification,
    NotificationTemplate,
)
from core.api import AUDIT_FIELDS


class MessageTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageTemplate
        fields = "__all__"
        read_only_fields = (*AUDIT_FIELDS, "approval_status", "approved_at", "rejected_reason")


class MessageDispatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageDispatch
        fields = "__all__"


class ConsentRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsentRecord
        fields = "__all__"
        read_only_fields = AUDIT_FIELDS


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = "__all__"


class NotificationTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationTemplate
        fields = "__all__"
        read_only_fields = AUDIT_FIELDS
