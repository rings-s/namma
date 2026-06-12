from rest_framework import serializers

from core.api import AUDIT_FIELDS
from customers.models import (
    ClinicalNote,
    Customer,
    CustomerDocument,
    CustomerPreference,
    CustomerSegment,
    CustomerSegmentMembership,
    Survey,
    SurveyResponse,
)


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = "__all__"
        read_only_fields = (
            *AUDIT_FIELDS,
            "deleted_at",
            "loyalty_points",
            "total_spent",
            "visit_count",
            "last_visit_at",
        )


class CustomerPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerPreference
        fields = "__all__"
        read_only_fields = AUDIT_FIELDS


class ClinicalNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClinicalNote
        fields = "__all__"
        read_only_fields = AUDIT_FIELDS


class CustomerDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerDocument
        fields = "__all__"
        read_only_fields = AUDIT_FIELDS


class CustomerSegmentSerializer(serializers.ModelSerializer):
    member_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = CustomerSegment
        fields = "__all__"
        read_only_fields = (*AUDIT_FIELDS, "last_refreshed_at")


class CustomerSegmentMembershipSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerSegmentMembership
        fields = "__all__"
        read_only_fields = AUDIT_FIELDS


class SurveySerializer(serializers.ModelSerializer):
    class Meta:
        model = Survey
        fields = "__all__"
        read_only_fields = AUDIT_FIELDS


class SurveyResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = SurveyResponse
        fields = "__all__"
        read_only_fields = AUDIT_FIELDS
