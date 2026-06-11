from rest_framework import serializers

from analytics.models import (
    AnalyticsEvent,
    DailyBranchMetric,
    DailyEmployeeMetric,
    DailyMetric,
    Report,
)
from core.api import AUDIT_FIELDS


class AnalyticsEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalyticsEvent
        fields = "__all__"
        read_only_fields = AUDIT_FIELDS


class ReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = "__all__"
        read_only_fields = (*AUDIT_FIELDS, "generated_at", "file_url")


class DailyMetricSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyMetric
        fields = "__all__"


class DailyBranchMetricSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyBranchMetric
        fields = "__all__"


class DailyEmployeeMetricSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyEmployeeMetric
        fields = "__all__"
