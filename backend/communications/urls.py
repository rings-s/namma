from django.urls import path
from rest_framework.routers import DefaultRouter

from communications import views

urlpatterns = [
    path(
        "webhooks/ses/",
        views.SESWebhookView.as_view(),
        name="ses_webhook",
    ),
]

router = DefaultRouter()
router.register("message-templates", views.MessageTemplateViewSet)
router.register("message-dispatches", views.MessageDispatchViewSet)
router.register("consent-records", views.ConsentRecordViewSet)
router.register("email-events", views.EmailEventViewSet)
router.register("notifications", views.NotificationViewSet)
router.register("notification-templates", views.NotificationTemplateViewSet)
router.register("conversations", views.ConversationViewSet)
router.register("conversation-messages", views.ConversationMessageViewSet)

urlpatterns += router.urls
