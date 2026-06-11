<<<<<<< HEAD
from django.shortcuts import render

# Create your views here.
=======
from core.api import TenantScopedViewSet
from customers.models import ClinicalNote, Customer, CustomerDocument, CustomerPreference
from customers.serializers import (
    ClinicalNoteSerializer,
    CustomerDocumentSerializer,
    CustomerPreferenceSerializer,
    CustomerSerializer,
)


class CustomerViewSet(TenantScopedViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    search_fields = ["first_name", "last_name", "email", "phone"]
    ordering_fields = ["created_at", "last_visit_at", "total_spent"]


class CustomerPreferenceViewSet(TenantScopedViewSet):
    queryset = CustomerPreference.objects.select_related("customer")
    serializer_class = CustomerPreferenceSerializer
    org_field = "customer__organization"


class ClinicalNoteViewSet(TenantScopedViewSet):
    # PDPL-sensitive: reads of these records belong in the access log (service layer, later).
    queryset = ClinicalNote.objects.select_related("customer", "employee")
    serializer_class = ClinicalNoteSerializer


class CustomerDocumentViewSet(TenantScopedViewSet):
    queryset = CustomerDocument.objects.select_related("customer")
    serializer_class = CustomerDocumentSerializer
>>>>>>> a3235b4 (feat(db): initialize core relational schema)
