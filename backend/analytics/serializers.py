from rest_framework import serializers

from analytics.models import (
    AnalyticsEvent,
    DailyBranchMetric,
    DailyEmployeeMetric,
    DailyMetric,
    Goal,
    GoalMilestone,
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


class GoalMilestoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = GoalMilestone
        fields = "__all__"
        read_only_fields = (*AUDIT_FIELDS, "reached_at")


class GoalSerializer(serializers.ModelSerializer):
    milestones = GoalMilestoneSerializer(many=True, read_only=True)
    progress_percent = serializers.SerializerMethodField()

    class Meta:
        model = Goal
        fields = "__all__"
        read_only_fields = (*AUDIT_FIELDS, "current_value", "status")

    def get_progress_percent(self, goal):
        if not goal.target_value:
            return None
        return round(float(goal.current_value / goal.target_value) * 100, 1)
