from rest_framework.routers import DefaultRouter

from integrations import views

router = DefaultRouter()
router.register("api-keys", views.APIKeyViewSet)
router.register("webhook-endpoints", views.WebhookEndpointViewSet)
router.register("devices", views.DeviceViewSet)
router.register("sync-operations", views.SyncOperationViewSet)

urlpatterns = router.urls
