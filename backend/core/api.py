"""Shared DRF building blocks: tenant scoping for the multi-tenant API.

Every tenant-owned resource is exposed through ``TenantScopedViewSet`` (or its
read-only variant), which filters querysets to the organizations the request
user belongs to (via ``accounts.UserRole``) and blocks writes that point at
another tenant's data. ``org_field`` is the ORM path from the model to its
organization, e.g. ``"organization"`` or ``"sale__organization"``.
"""

from rest_framework import permissions, viewsets
from rest_framework.exceptions import PermissionDenied

#: Fields the API never accepts from clients.
AUDIT_FIELDS = ("id", "created_at", "updated_at")


class TenantScopedQuerysetMixin:
    permission_classes = [permissions.IsAuthenticated]
    org_field = "organization"
    # Stable default ordering so pagination is deterministic.
    ordering = ["-created_at"]

    def allowed_organization_ids(self):
        """Org ids the user may access, or None meaning unrestricted (superuser)."""
        user = self.request.user
        if user.is_superuser:
            return None
        from accounts.models import UserRole

        return list(
            UserRole.objects.filter(user=user).values_list("organization_id", flat=True)
        )

    def get_queryset(self):
        queryset = super().get_queryset()
        org_ids = self.allowed_organization_ids()
        if org_ids is None:
            return queryset
        return queryset.filter(**{f"{self.org_field}__in": org_ids})


class TenantScopedReadOnlyViewSet(TenantScopedQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    """List/retrieve only — for logs, metrics and system-written records."""


class TenantScopedViewSet(TenantScopedQuerysetMixin, viewsets.ModelViewSet):
    """Full CRUD with tenant-ownership enforcement on writes."""

    def _check_tenant_ownership(self, serializer):
        org_ids = self.allowed_organization_ids()
        if org_ids is None:
            return
        head = self.org_field.split("__")[0]
        related = serializer.validated_data.get(head)
        if related is None:
            return
        org_id = related.id if head == "organization" else getattr(related, "organization_id", None)
        if org_id is not None and org_id not in org_ids:
            raise PermissionDenied("You do not have access to this organization.")

    def perform_create(self, serializer):
        self._check_tenant_ownership(serializer)
        serializer.save()

    def perform_update(self, serializer):
        self._check_tenant_ownership(serializer)
        serializer.save()
