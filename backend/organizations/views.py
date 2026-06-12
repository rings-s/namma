from rest_framework import permissions, viewsets

from accounts.models import UserRole
from core.api import TenantScopedViewSet, require_org_role
from organizations.models import (
    Branch,
    BranchHour,
    Organization,
    OrganizationSettings,
    RetentionPolicy,
)
from organizations.serializers import (
    BranchHourSerializer,
    BranchSerializer,
    OrganizationSerializer,
    OrganizationSettingsSerializer,
    RetentionPolicySerializer,
)


class OrganizationViewSet(viewsets.ModelViewSet):
    """Organizations the user belongs to; creating one grants the owner role.

    Updates require the admin role; deletion is owner-only.
    """

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

    def perform_update(self, serializer):
        require_org_role(self.request.user, serializer.instance.id, UserRole.Role.ADMIN)
        serializer.save()

    def perform_destroy(self, instance):
        require_org_role(self.request.user, instance.id, UserRole.Role.OWNER)
        instance.delete()


class OrganizationSettingsViewSet(TenantScopedViewSet):
    queryset = OrganizationSettings.objects.all()
    serializer_class = OrganizationSettingsSerializer

    def _check_tenant_ownership(self, serializer):
        super()._check_tenant_ownership(serializer)
        organization = serializer.validated_data.get(
            "organization", getattr(serializer.instance, "organization", None)
        )
        if organization is not None:
            require_org_role(self.request.user, organization.id, UserRole.Role.ADMIN)

    def perform_destroy(self, instance):
        require_org_role(
            self.request.user, instance.organization_id, UserRole.Role.ADMIN
        )
        instance.delete()


class BranchViewSet(TenantScopedViewSet):
    queryset = Branch.objects.all()
    serializer_class = BranchSerializer
    search_fields = ["name", "city"]

    def _check_tenant_ownership(self, serializer):
        super()._check_tenant_ownership(serializer)
        organization = serializer.validated_data.get(
            "organization", getattr(serializer.instance, "organization", None)
        )
        if organization is not None:
            require_org_role(self.request.user, organization.id, UserRole.Role.ADMIN)

    def perform_destroy(self, instance):
        require_org_role(
            self.request.user, instance.organization_id, UserRole.Role.ADMIN
        )
        instance.delete()


class BranchHourViewSet(TenantScopedViewSet):
    queryset = BranchHour.objects.select_related("branch")
    serializer_class = BranchHourSerializer
    org_field = "branch__organization"


class RetentionPolicyViewSet(TenantScopedViewSet):
    queryset = RetentionPolicy.objects.all()
    serializer_class = RetentionPolicySerializer

    def _check_tenant_ownership(self, serializer):
        super()._check_tenant_ownership(serializer)
        organization = serializer.validated_data.get(
            "organization", getattr(serializer.instance, "organization", None)
        )
        if organization is not None:
            require_org_role(self.request.user, organization.id, UserRole.Role.ADMIN)

    def perform_destroy(self, instance):
        require_org_role(
            self.request.user, instance.organization_id, UserRole.Role.ADMIN
        )
        instance.delete()
