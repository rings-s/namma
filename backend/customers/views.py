from django.db.models import Count
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from accounts.models import UserRole
from ai.tasks import generate_ai_segment_task
from core.api import TenantScopedViewSet, require_org_role
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
from customers.serializers import (
    ClinicalNoteSerializer,
    CustomerDocumentSerializer,
    CustomerPreferenceSerializer,
    CustomerSegmentMembershipSerializer,
    CustomerSegmentSerializer,
    CustomerSerializer,
    SurveyResponseSerializer,
    SurveySerializer,
)
from customers.services import erase_customer, export_customer_data, refresh_segment


class CustomerViewSet(TenantScopedViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    search_fields = ["first_name", "last_name", "email", "phone"]
    ordering_fields = ["created_at", "last_visit_at", "total_spent"]

    @action(detail=True, methods=["get"], url_path="pdpl-export")
    def pdpl_export(self, request, pk=None):
        """PDPL portability export of everything held about a customer.
        Admin+ — this is a bulk PII release."""
        customer = self.get_object()
        require_org_role(request.user, customer.organization_id, UserRole.Role.ADMIN)
        return Response(export_customer_data(customer))

    @action(detail=True, methods=["post"], url_path="pdpl-erase")
    def pdpl_erase(self, request, pk=None):
        """PDPL right-to-be-forgotten. Admin+. Anonymizes PII and
        soft-deletes the profile; statutory financial records survive."""
        customer = self.get_object()
        require_org_role(request.user, customer.organization_id, UserRole.Role.ADMIN)
        erase_customer(customer, requested_by=request.user)
        return Response({"detail": "erased"})


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


class CustomerSegmentViewSet(TenantScopedViewSet):
    queryset = CustomerSegment.objects.annotate(member_count=Count("memberships"))
    serializer_class = CustomerSegmentSerializer
    search_fields = ["name"]

    @action(detail=True, methods=["post"])
    def refresh(self, request, pk=None):
        """Re-evaluate a dynamic segment's membership now."""
        segment = self.get_object()
        if segment.segment_type != CustomerSegment.SegmentType.DYNAMIC:
            raise ValidationError("Only dynamic segments can be refreshed.")
        refresh_segment(segment)
        segment = self.get_queryset().get(pk=segment.pk)
        return Response(self.get_serializer(segment).data)

    @action(detail=True, methods=["post"])
    def generate(self, request, pk=None):
        """Build an AI segment's criteria from its description and materialize
        its membership on a worker (marketer+). The LLM call never blocks the
        request — poll the segment for ``last_refreshed_at``/``member_count``."""
        segment = self.get_object()
        if segment.segment_type != CustomerSegment.SegmentType.AI:
            raise ValidationError("Only AI segments can be generated.")
        require_org_role(request.user, segment.organization_id, "marketer")
        generate_ai_segment_task.delay(str(segment.pk))
        return Response(
            {"detail": "AI segment generation queued."},
            status=status.HTTP_202_ACCEPTED,
        )


class CustomerSegmentMembershipViewSet(TenantScopedViewSet):
    """Manual curation of segment membership; dynamic memberships are
    system-managed and rejected here."""

    queryset = CustomerSegmentMembership.objects.select_related("segment", "customer")
    serializer_class = CustomerSegmentMembershipSerializer
    org_field = "segment__organization"

    def perform_create(self, serializer):
        segment = serializer.validated_data["segment"]
        if segment.segment_type != CustomerSegment.SegmentType.MANUAL:
            raise ValidationError(
                "Memberships of dynamic/AI segments are system-managed."
            )
        super().perform_create(serializer)


class SurveyViewSet(TenantScopedViewSet):
    queryset = Survey.objects.all()
    serializer_class = SurveySerializer


class SurveyResponseViewSet(TenantScopedViewSet):
    queryset = SurveyResponse.objects.select_related("survey", "customer")
    serializer_class = SurveyResponseSerializer
    org_field = "survey__organization"
    http_method_names = ["get", "post", "head", "options"]  # responses are immutable

    @action(detail=False, methods=["get"])
    def nps(self, request):
        """Current NPS across the requesting user's organizations:
        %promoters (9-10) − %detractors (0-6)."""
        responses = self.get_queryset().filter(
            survey__survey_type=Survey.SurveyType.NPS, score__isnull=False
        )
        total = responses.count()
        if total == 0:
            return Response({"nps": None, "responses": 0})
        promoters = responses.filter(score__gte=9).count()
        detractors = responses.filter(score__lte=6).count()
        nps = round(((promoters - detractors) / total) * 100, 1)
        return Response(
            {
                "nps": nps,
                "responses": total,
                "promoters": promoters,
                "detractors": detractors,
            },
            status=status.HTTP_200_OK,
        )
