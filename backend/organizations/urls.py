from rest_framework.routers import DefaultRouter

from organizations import views

router = DefaultRouter()
router.register("organizations", views.OrganizationViewSet)
router.register("organization-settings", views.OrganizationSettingsViewSet)
router.register("branches", views.BranchViewSet)
router.register("branch-hours", views.BranchHourViewSet)
router.register("retention-policies", views.RetentionPolicyViewSet)

urlpatterns = router.urls
