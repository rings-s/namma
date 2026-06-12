from rest_framework import serializers

from communications.models import (
    ConsentRecord,
    Conversation,
    ConversationMessage,
    EmailEvent,
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
        read_only_fields = (
            *AUDIT_FIELDS,
            "approval_status",
            "approved_at",
            "rejected_reason",
        )


class MessageDispatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageDispatch
        fields = "__all__"
        # Outcome fields are written by the gateway send path, never by clients.
        read_only_fields = (
            *AUDIT_FIELDS,
            "status",
            "external_message_id",
            "cost",
            "sent_at",
            "delivered_at",
            "read_at",
            "failed_at",
            "failure_reason",
        )


class EmailEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailEvent
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


class ConversationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Conversation
        fields = "__all__"
        read_only_fields = (
            *AUDIT_FIELDS,
            "status",
            "assigned_to",
            "last_message_at",
            "resolved_at",
        )


class ConversationMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConversationMessage
        fields = "__all__"
        read_only_fields = (*AUDIT_FIELDS, "sender_user", "dispatch", "read_at")


class ConversationAssignSerializer(serializers.Serializer):
    assigned_to = serializers.UUIDField()
