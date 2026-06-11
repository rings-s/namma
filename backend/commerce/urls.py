from rest_framework.routers import DefaultRouter

from commerce import views

router = DefaultRouter()
router.register("service-categories", views.ServiceCategoryViewSet)
router.register("services", views.ServiceViewSet)
router.register("products", views.ProductViewSet)
router.register("sales", views.SaleViewSet)
router.register("sale-items", views.SaleItemViewSet)

urlpatterns = router.urls
