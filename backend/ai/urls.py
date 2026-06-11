from rest_framework.routers import DefaultRouter

from ai import views

router = DefaultRouter()
router.register("ai-conversations", views.AIConversationViewSet)
router.register("ai-messages", views.AIMessageViewSet)
router.register("ai-recommendations", views.AIRecommendationViewSet)

urlpatterns = router.urls
