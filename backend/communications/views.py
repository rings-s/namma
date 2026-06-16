import hashlib
import json

from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import HttpResponse
from rest_framework import generics, permissions, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from communications import serializers
from communications.models import (
    ConsentRecord,
    Conversation,
    ConversationMessage,
    EmailEvent,
    MessageDispatch,
    MessageTemplate,
    Notification,
    NotificationTemplate,
    WhatsAppWebhookEvent,
)
from communications.gateways import verify_whatsapp_signature
from communications.services import (
    validate_email_dispatch,
    validate_sms_dispatch,
    validate_whatsapp_dispatch,
)
from communications.sns import SNSVerificationError, verify_sns_message
from communications.tasks import (
    confirm_sns_subscription_task,
    process_ses_event_task,
    process_whatsapp_webhook_task,
    send_email_dispatch_task,
    send_sms_dispatch_task,
    send_whatsapp_dispatch_task,
)
from core.api import TenantScopedReadOnlyViewSet, TenantScopedViewSet
from core.models import Channel


class MessageTemplateViewSet(TenantScopedViewSet):
    queryset = MessageTemplate.objects.all()
    serializer_class = serializers.MessageTemplateSerializer
    search_fields = ["name", "channel"]


class MessageDispatchViewSet(TenantScopedViewSet):
    """Outbound messages. Created as ``queued``; pushed via the send action."""

    queryset = MessageDispatch.objects.select_related("customer", "template")
    serializer_class = serializers.MessageDispatchSerializer
    ordering_fields = ["sent_at", "created_at"]
    # Dispatch history is immutable: no edits or deletes once created.
    http_method_names = ["get", "post", "head", "options"]

    @action(detail=True, methods=["post"])
    def send(self, request, pk=None):
        """Queue a dispatch for its channel gateway (Taqnyat or SES)."""
        dispatch = self.get_object()
        routes = {
            Channel.SMS: (validate_sms_dispatch, send_sms_dispatch_task),
            Channel.EMAIL: (validate_email_dispatch, send_email_dispatch_task),
            Channel.WHATSAPP: (validate_whatsapp_dispatch, send_whatsapp_dispatch_task),
        }
        if dispatch.channel not in routes:
            raise ValidationError(
                f"No sending gateway for the {dispatch.get_channel_display()} channel."
            )
        validate, task = routes[dispatch.channel]
        try:
            validate(dispatch)
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages)
        task.delay(str(dispatch.pk))
        dispatch.refresh_from_db()
        return Response(
            serializers.MessageDispatchSerializer(dispatch).data,
            status=status.HTTP_202_ACCEPTED,
        )


class ConsentRecordViewSet(TenantScopedViewSet):
    # PDPL consent ledger: grant/revoke via create; no edits of history.
    http_method_names = ["get", "post", "head", "options"]
    queryset = ConsentRecord.objects.select_related("customer")
    serializer_class = serializers.ConsentRecordSerializer
    ordering_fields = ["granted_at", "created_at"]


class SESWebhookView(generics.GenericAPIView):
    """Receiver for SES delivery events pushed by Amazon SNS.

    Every envelope is authenticated against AWS's embedded signature before
    anything is stored or acted on. Subscription confirmations are visited
    by a worker; notifications are stored idempotently on the SNS message id
    and applied by a worker — the receiver answers 200 fast so SNS stops
    retrying.
    """

    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        try:
            # SNS posts JSON with a text/plain content type, so DRF's
            # parsers never see it — read the raw body.
            envelope = json.loads(request.body)
        except ValueError:
            return Response(
                {"detail": "Malformed SNS payload."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            verify_sns_message(envelope)
        except SNSVerificationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        sns_type = envelope.get("Type", "")
        sns_message_id = str(envelope.get("MessageId", ""))

        if sns_type == "SubscriptionConfirmation":
            subscribe_url = str(envelope.get("SubscribeURL", ""))
            if subscribe_url:
                confirm_sns_subscription_task.delay(subscribe_url)
            return Response({"detail": "ok"})
        if sns_type != "Notification" or not sns_message_id:
            return Response({"detail": "ok"})

        try:
            message = json.loads(envelope.get("Message", "{}"))
        except ValueError:
            message = {}
        event, created = EmailEvent.objects.get_or_create(
            sns_message_id=sns_message_id,
            defaults={
                "event_type": str(message.get("eventType", "")),
                "ses_message_id": str(message.get("mail", {}).get("messageId", "")),
                "payload": message,
            },
        )
        if created:
            process_ses_event_task.delay(str(event.pk))
        return Response({"detail": "ok"})


class WhatsAppWebhookView(generics.GenericAPIView):
    """Receiver for the Meta WhatsApp Cloud API webhook.

    GET performs Meta's subscription handshake — it echoes ``hub.challenge`` only
    when ``hub.verify_token`` matches the configured token. POST authenticates
    every payload against the app secret (``X-Hub-Signature-256``) before handing
    delivery statuses to a worker, so the receiver answers 200 fast and Meta
    stops retrying.
    """

    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        verify_token = settings.WHATSAPP_WEBHOOK_VERIFY_TOKEN
        mode = request.query_params.get("hub.mode")
        token = request.query_params.get("hub.verify_token")
        challenge = request.query_params.get("hub.challenge", "")
        if mode == "subscribe" and verify_token and token == verify_token:
            # Meta expects the raw challenge string echoed back, not JSON.
            return HttpResponse(challenge, content_type="text/plain")
        return HttpResponse("Verification failed", status=403)

    def post(self, request):
        if not verify_whatsapp_signature(
            request.body, request.headers.get("X-Hub-Signature-256", "")
        ):
            return Response(
                {"detail": "Invalid signature."}, status=status.HTTP_403_FORBIDDEN
            )
        try:
            payload = json.loads(request.body)
        except ValueError:
            return Response(
                {"detail": "Malformed payload."}, status=status.HTTP_400_BAD_REQUEST
            )
        # Store fast, return fast: persist the raw delivery (deduped on a body
        # hash so Meta's retries collapse), then a worker applies it by id — the
        # full payload never travels through the broker.
        signature = hashlib.sha256(request.body).hexdigest()
        event, created = WhatsAppWebhookEvent.objects.get_or_create(
            body_signature=signature,
            defaults={"payload": payload},
        )
        if created:
            process_whatsapp_webhook_task.delay(str(event.pk))
        return Response({"detail": "ok"})


class EmailEventViewSet(TenantScopedReadOnlyViewSet):
    # Written exclusively by the SES webhook receiver.
    queryset = EmailEvent.objects.select_related("dispatch")
    serializer_class = serializers.EmailEventSerializer
    ordering_fields = ["created_at"]


class NotificationViewSet(TenantScopedReadOnlyViewSet):
    queryset = Notification.objects.select_related("user", "customer")
    serializer_class = serializers.NotificationSerializer
    ordering_fields = ["created_at"]


class NotificationTemplateViewSet(TenantScopedViewSet):
    queryset = NotificationTemplate.objects.all()
    serializer_class = serializers.NotificationTemplateSerializer
    search_fields = ["name", "type"]


class ConversationViewSet(TenantScopedViewSet):
    """Omni-channel inbox threads with explicit routing transitions:
    open -> assigned -> resolved -> closed (resolve can reopen via assign)."""

    queryset = Conversation.objects.select_related("customer", "branch", "assigned_to")
    serializer_class = serializers.ConversationSerializer
    search_fields = ["subject", "customer__first_name", "customer__phone"]
    ordering_fields = ["last_message_at", "created_at"]

    @action(detail=True, methods=["post"])
    def assign(self, request, pk=None):
        """Route the thread to a staff user holding a role in the org."""
        from accounts.models import UserRole

        conversation = self.get_object()
        params = serializers.ConversationAssignSerializer(data=request.data)
        params.is_valid(raise_exception=True)
        assignee_role = UserRole.objects.filter(
            user_id=params.validated_data["assigned_to"],
            organization_id=conversation.organization_id,
        ).first()
        if assignee_role is None:
            raise ValidationError("The assignee has no role in this organization.")
        conversation.assigned_to_id = assignee_role.user_id
        conversation.status = Conversation.Status.ASSIGNED
        conversation.resolved_at = None
        conversation.save(
            update_fields=["assigned_to", "status", "resolved_at", "updated_at"]
        )
        return Response(self.get_serializer(conversation).data)

    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        from django.utils import timezone

        conversation = self.get_object()
        if conversation.status in (
            Conversation.Status.RESOLVED,
            Conversation.Status.CLOSED,
        ):
            raise ValidationError("The conversation is already resolved or closed.")
        conversation.status = Conversation.Status.RESOLVED
        conversation.resolved_at = timezone.now()
        conversation.save(update_fields=["status", "resolved_at", "updated_at"])
        return Response(self.get_serializer(conversation).data)

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        conversation = self.get_object()
        if conversation.status == Conversation.Status.CLOSED:
            raise ValidationError("The conversation is already closed.")
        conversation.status = Conversation.Status.CLOSED
        conversation.save(update_fields=["status", "updated_at"])
        return Response(self.get_serializer(conversation).data)


class ConversationMessageViewSet(TenantScopedViewSet):
    queryset = ConversationMessage.objects.select_related(
        "conversation", "sender_user", "dispatch"
    )
    serializer_class = serializers.ConversationMessageSerializer
    org_field = "conversation__organization"
    http_method_names = ["get", "post", "head", "options"]  # immutable history

    def perform_create(self, serializer):
        from django.utils import timezone

        self._check_tenant_ownership(serializer)
        message = serializer.save(sender_user=self.request.user)
        Conversation.objects.filter(pk=message.conversation_id).update(
            last_message_at=timezone.now()
        )
