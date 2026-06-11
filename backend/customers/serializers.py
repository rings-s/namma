from rest_framework import serializers

from core.api import AUDIT_FIELDS
from customers.models import ClinicalNote, Customer, CustomerDocument, CustomerPreference


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = "__all__"
        read_only_fields = (*AUDIT_FIELDS, "deleted_at", "loyalty_points", "total_spent", "visit_count", "last_visit_at")


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
