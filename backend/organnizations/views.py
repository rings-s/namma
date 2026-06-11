<<<<<<< HEAD
from django.shortcuts import render

# Create your views here.
=======
from rest_framework import permissions, viewsets

from accounts.models import UserRole
from core.api import TenantScopedViewSet
from organnizations.models import Branch, BranchHour, Organization, OrganizationSettings
from organnizations.serializers import (
    BranchHourSerializer,
    BranchSerializer,
    OrganizationSerializer,
    OrganizationSettingsSerializer,
)


class OrganizationViewSet(viewsets.ModelViewSet):
    """Organizations the user belongs to; creating one grants the owner role."""

    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer
    permission_classes = [permissions.IsAuthenticated]
    search_fields = ["name", "slug"]
    ordering = ["-created_at"]

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.is_superuser:
            return queryset
        return queryset.filter(user_roles__user=self.request.user).distinct()

    def perform_create(self, serializer):
        organization = serializer.save()
        UserRole.objects.create(
            user=self.request.user,
            organization=organization,
            role=UserRole.Role.OWNER,
        )


class OrganizationSettingsViewSet(TenantScopedViewSet):
    queryset = OrganizationSettings.objects.all()
    serializer_class = OrganizationSettingsSerializer


class BranchViewSet(TenantScopedViewSet):
    queryset = Branch.objects.all()
    serializer_class = BranchSerializer
    search_fields = ["name", "city"]


class BranchHourViewSet(TenantScopedViewSet):
    queryset = BranchHour.objects.select_related("branch")
    serializer_class = BranchHourSerializer
    org_field = "branch__organization"
>>>>>>> a3235b4 (feat(db): initialize core relational schema)
