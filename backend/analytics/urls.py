from rest_framework.routers import DefaultRouter

from analytics import views

router = DefaultRouter()
router.register("analytics-events", views.AnalyticsEventViewSet)
router.register("reports", views.ReportViewSet)
router.register("daily-metrics", views.DailyMetricViewSet)
router.register("daily-branch-metrics", views.DailyBranchMetricViewSet)
router.register("daily-employee-metrics", views.DailyEmployeeMetricViewSet)
router.register("goals", views.GoalViewSet)
router.register("goal-milestones", views.GoalMilestoneViewSet)

urlpatterns = router.urls
