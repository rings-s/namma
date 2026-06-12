from django.db.models import Sum
from rest_framework.decorators import action
from rest_framework.response import Response

from analytics import serializers
from analytics.models import (
    AnalyticsEvent,
    DailyBranchMetric,
    DailyEmployeeMetric,
    DailyMetric,
    Goal,
    GoalMilestone,
    Report,
)
from core.api import TenantScopedReadOnlyViewSet, TenantScopedViewSet


class AnalyticsEventViewSet(TenantScopedViewSet):
    # Ingest endpoint: clients append events; history is never edited.
    http_method_names = ["get", "post", "head", "options"]
    queryset = AnalyticsEvent.objects.all()
    serializer_class = serializers.AnalyticsEventSerializer
    ordering_fields = ["created_at"]


class ReportViewSet(TenantScopedViewSet):
    queryset = Report.objects.all()
    serializer_class = serializers.ReportSerializer
    search_fields = ["name", "type"]


class DailyMetricViewSet(TenantScopedReadOnlyViewSet):
    # Rollups computed by the scheduler.
    queryset = DailyMetric.objects.select_related("branch")
    serializer_class = serializers.DailyMetricSerializer
    ordering_fields = ["date"]


class DailyBranchMetricViewSet(TenantScopedReadOnlyViewSet):
    queryset = DailyBranchMetric.objects.select_related("branch")
    serializer_class = serializers.DailyBranchMetricSerializer
    ordering_fields = ["date"]


class DailyEmployeeMetricViewSet(TenantScopedReadOnlyViewSet):
    queryset = DailyEmployeeMetric.objects.select_related("employee")
    serializer_class = serializers.DailyEmployeeMetricSerializer
    ordering_fields = ["date"]

    @action(detail=False, methods=["get"])
    def leaderboard(self, request):
        """Employees ranked by revenue over a date window
        (?date_from=&date_to=, default: current month)."""
        from django.utils import timezone

        today = timezone.now().date()
        date_from = request.query_params.get("date_from") or today.replace(day=1)
        date_to = request.query_params.get("date_to") or today
        rows = (
            self.get_queryset()
            .filter(date__gte=date_from, date__lte=date_to)
            .values("employee_id", "employee__user__first_name", "employee__job_title")
            .annotate(
                total_revenue=Sum("total_revenue"),
                total_appointments=Sum("total_appointments"),
                total_commission=Sum("total_commission"),
            )
            .order_by("-total_revenue")[:50]
        )
        return Response(
            [
                {
                    "rank": index,
                    "employee": str(row["employee_id"]),
                    "name": row["employee__user__first_name"] or "",
                    "job_title": row["employee__job_title"],
                    "total_revenue": str(row["total_revenue"] or 0),
                    "total_appointments": row["total_appointments"] or 0,
                    "total_commission": str(row["total_commission"] or 0),
                }
                for index, row in enumerate(rows, start=1)
            ]
        )


class GoalViewSet(TenantScopedViewSet):
    queryset = Goal.objects.select_related("branch", "employee").prefetch_related(
        "milestones"
    )
    serializer_class = serializers.GoalSerializer
    search_fields = ["name"]
    ordering_fields = ["period_start", "created_at"]

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """Explicit state transition: active -> cancelled."""
        from rest_framework.exceptions import ValidationError

        goal = self.get_object()
        if goal.status != Goal.Status.ACTIVE:
            raise ValidationError("Only active goals can be cancelled.")
        goal.status = Goal.Status.CANCELLED
        goal.save(update_fields=["status", "updated_at"])
        return Response(self.get_serializer(goal).data)


class GoalMilestoneViewSet(TenantScopedViewSet):
    queryset = GoalMilestone.objects.select_related("goal")
    serializer_class = serializers.GoalMilestoneSerializer
    org_field = "goal__organization"
