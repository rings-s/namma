from rest_framework.routers import DefaultRouter

from inventory import views

router = DefaultRouter()
router.register("stock-movements", views.StockMovementViewSet)
router.register("stock-transfers", views.StockTransferViewSet)

urlpatterns = router.urls
