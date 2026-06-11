from rest_framework.routers import DefaultRouter

from communications import views

router = DefaultRouter()
router.register("message-templates", views.MessageTemplateViewSet)
router.register("message-dispatches", views.MessageDispatchViewSet)
router.register("consent-records", views.ConsentRecordViewSet)
router.register("notifications", views.NotificationViewSet)
router.register("notification-templates", views.NotificationTemplateViewSet)

urlpatterns = router.urls
