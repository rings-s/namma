<<<<<<< HEAD
from django.shortcuts import render

# Create your views here.
=======
from analytics import serializers
from analytics.models import (
    AnalyticsEvent,
    DailyBranchMetric,
    DailyEmployeeMetric,
    DailyMetric,
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
>>>>>>> a3235b4 (feat(db): initialize core relational schema)
