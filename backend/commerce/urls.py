from rest_framework.routers import DefaultRouter

from commerce import views

router = DefaultRouter()
router.register("service-categories", views.ServiceCategoryViewSet)
router.register("services", views.ServiceViewSet)
router.register("products", views.ProductViewSet)
router.register("sales", views.SaleViewSet)
router.register("sale-items", views.SaleItemViewSet)
router.register("gift-cards", views.GiftCardViewSet)
router.register("gift-card-transactions", views.GiftCardTransactionViewSet)
router.register("store-credit-accounts", views.StoreCreditAccountViewSet)
router.register("store-credit-transactions", views.StoreCreditTransactionViewSet)
router.register("packages", views.PackageViewSet)
router.register("package-items", views.PackageItemViewSet)
router.register("customer-packages", views.CustomerPackageViewSet)
router.register("package-redemptions", views.PackageRedemptionViewSet)
router.register("pricing-rules", views.PricingRuleViewSet)

urlpatterns = router.urls
