<<<<<<< HEAD
from django.shortcuts import render

# Create your views here.
=======
from communications import serializers
from communications.models import (
    ConsentRecord,
    MessageDispatch,
    MessageTemplate,
    Notification,
    NotificationTemplate,
)
from core.api import TenantScopedReadOnlyViewSet, TenantScopedViewSet


class MessageTemplateViewSet(TenantScopedViewSet):
    queryset = MessageTemplate.objects.all()
    serializer_class = serializers.MessageTemplateSerializer
    search_fields = ["name", "channel"]


class MessageDispatchViewSet(TenantScopedReadOnlyViewSet):
    # Dispatches are created by the messaging worker, not by API clients.
    queryset = MessageDispatch.objects.select_related("customer", "template")
    serializer_class = serializers.MessageDispatchSerializer
    ordering_fields = ["sent_at", "created_at"]


class ConsentRecordViewSet(TenantScopedViewSet):
    # PDPL consent ledger: grant/revoke via create; no edits of history.
    http_method_names = ["get", "post", "head", "options"]
    queryset = ConsentRecord.objects.select_related("customer")
    serializer_class = serializers.ConsentRecordSerializer
    ordering_fields = ["granted_at", "created_at"]


class NotificationViewSet(TenantScopedReadOnlyViewSet):
    queryset = Notification.objects.select_related("user", "customer")
    serializer_class = serializers.NotificationSerializer
    ordering_fields = ["created_at"]


class NotificationTemplateViewSet(TenantScopedViewSet):
    queryset = NotificationTemplate.objects.all()
    serializer_class = serializers.NotificationTemplateSerializer
    search_fields = ["name", "type"]
>>>>>>> a3235b4 (feat(db): initialize core relational schema)
