from rest_framework.routers import DefaultRouter

from core import views

router = DefaultRouter()
router.register("countries", views.CountryViewSet)
router.register("currencies", views.CurrencyViewSet)
router.register("translations", views.TranslationViewSet)
router.register("audit-logs", views.AuditLogViewSet)
router.register("access-logs", views.AccessLogViewSet)

urlpatterns = router.urls
