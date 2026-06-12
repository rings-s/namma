from rest_framework.routers import DefaultRouter

from inventory import views

router = DefaultRouter()
router.register("stock-movements", views.StockMovementViewSet)
router.register("stock-transfers", views.StockTransferViewSet)
router.register("suppliers", views.SupplierViewSet)
router.register("purchase-orders", views.PurchaseOrderViewSet)
router.register("purchase-order-lines", views.PurchaseOrderLineViewSet)
router.register("reorder-rules", views.ReorderRuleViewSet)

urlpatterns = router.urls
