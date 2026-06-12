from rest_framework import serializers

from core.api import AUDIT_FIELDS
from organizations.models import (
    Branch,
    BranchHour,
    Organization,
    OrganizationSettings,
    RetentionPolicy,
)


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = "__all__"
        read_only_fields = AUDIT_FIELDS


class OrganizationSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrganizationSettings
        fields = "__all__"
        read_only_fields = AUDIT_FIELDS


class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = "__all__"
        read_only_fields = AUDIT_FIELDS


class BranchHourSerializer(serializers.ModelSerializer):
    class Meta:
        model = BranchHour
        fields = "__all__"
        read_only_fields = AUDIT_FIELDS


class RetentionPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = RetentionPolicy
        fields = "__all__"
        read_only_fields = AUDIT_FIELDS
