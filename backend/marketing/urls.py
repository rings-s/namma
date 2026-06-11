from rest_framework.routers import DefaultRouter

from marketing import views

router = DefaultRouter()
router.register("campaigns", views.CampaignViewSet)
router.register("campaign-recipients", views.CampaignRecipientViewSet)
router.register("promotions", views.PromotionViewSet)
router.register("loyalty-programs", views.LoyaltyProgramViewSet)
router.register("loyalty-transactions", views.LoyaltyTransactionViewSet)

urlpatterns = router.urls
