from rest_framework.routers import DefaultRouter

from organnizations import views

router = DefaultRouter()
router.register("organizations", views.OrganizationViewSet)
router.register("organization-settings", views.OrganizationSettingsViewSet)
router.register("branches", views.BranchViewSet)
router.register("branch-hours", views.BranchHourViewSet)

urlpatterns = router.urls
