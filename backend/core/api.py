"""Shared DRF building blocks: tenant scoping for the multi-tenant API.

Every tenant-owned resource is exposed through ``TenantScopedViewSet`` (or its
read-only variant), which filters querysets to the organizations the request
user belongs to (via ``accounts.UserRole``) and blocks writes that point at
another tenant's data. ``org_field`` is the ORM path from the model to its
organization, e.g. ``"organization"`` or ``"sale__organization"``.
"""

from django.db import IntegrityError, transaction
from rest_framework import permissions, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

#: Fields the API never accepts from clients.
AUDIT_FIELDS = ("id", "created_at", "updated_at")

#: Role hierarchy used for write-permission checks (higher = more privileged).
#: Keys are UserRole.Role values, kept as plain strings to avoid import cycles.
ROLE_RANKS = {
    "owner": 100,
    "admin": 80,
    "manager": 60,
    "accountant": 40,
    "marketer": 40,
    "receptionist": 30,
    "staff": 20,
}


def organization_role_rank(user, organization_id):
    """Highest role rank the user holds in the organization (0 = no role)."""
    if user.is_superuser:
        return max(ROLE_RANKS.values()) + 1
    from accounts.models import UserRole

    roles = UserRole.objects.filter(
        user=user, organization_id=organization_id
    ).values_list("role", flat=True)
    return max((ROLE_RANKS.get(role, 0) for role in roles), default=0)


def require_org_role(user, organization_id, minimum_role):
    """Raise PermissionDenied unless the user holds at least ``minimum_role``."""
    if organization_role_rank(user, organization_id) < ROLE_RANKS[minimum_role]:
        raise PermissionDenied(
            f"This action requires the {minimum_role} role in this organization."
        )


class TenantScopedQuerysetMixin:
    permission_classes = [permissions.IsAuthenticated]
    org_field = "organization"
    # Stable default ordering so pagination is deterministic.
    ordering = ["-created_at"]

    def allowed_organization_ids(self):
        """Org ids the user may access, or None meaning unrestricted (superuser).

        Memoized on the view instance: ``get_queryset`` and the write-ownership
        check both need this within one request, so the ``UserRole`` lookup runs
        once instead of per call. (None is a valid result, so the presence of the
        attribute — not its truthiness — is the cache guard.)
        """
        if not hasattr(self, "_allowed_org_ids"):
            user = self.request.user
            if user.is_superuser:
                self._allowed_org_ids = None
            else:
                from accounts.models import UserRole

                self._allowed_org_ids = list(
                    UserRole.objects.filter(user=user).values_list(
                        "organization_id", flat=True
                    )
                )
        return self._allowed_org_ids

    def get_queryset(self):
        queryset = super().get_queryset()
        org_ids = self.allowed_organization_ids()
        if org_ids is None:
            return queryset
        return queryset.filter(**{f"{self.org_field}__in": org_ids})


class IdempotentCreateMixin:
    """Honors the ``Idempotency-Key`` request header on create endpoints.

    A replayed key returns the stored response (with ``Idempotency-Replayed:
    true``) instead of re-executing the mutation — at-least-once clients on
    flaky branch connections can retry POSTs safely. Keys are optional;
    requests without the header behave normally.
    """

    def create(self, request, *args, **kwargs):
        key = request.headers.get("Idempotency-Key", "").strip()
        if not key or not request.user.is_authenticated:
            return super().create(request, *args, **kwargs)
        from core.models import IdempotencyRecord

        existing = IdempotencyRecord.objects.filter(
            user=request.user, key=key, method=request.method, path=request.path
        ).first()
        if existing is not None:
            return Response(
                existing.response_body,
                status=existing.response_status,
                headers={"Idempotency-Replayed": "true"},
            )
        with transaction.atomic():
            response = super().create(request, *args, **kwargs)
            try:
                # An inner atomic block so a concurrent duplicate violating
                # the unique constraint cannot roll back the mutation itself.
                with transaction.atomic():
                    IdempotencyRecord.objects.create(
                        user=request.user,
                        key=key,
                        method=request.method,
                        path=request.path,
                        response_status=response.status_code,
                        response_body=response.data,
                    )
            except IntegrityError:
                pass  # concurrent retry already stored the outcome
        return response


class TenantScopedReadOnlyViewSet(
    TenantScopedQuerysetMixin, viewsets.ReadOnlyModelViewSet
):
    """List/retrieve only — for logs, metrics and system-written records."""


class TenantScopedViewSet(
    IdempotentCreateMixin, TenantScopedQuerysetMixin, viewsets.ModelViewSet
):
    """Full CRUD with tenant-ownership enforcement and idempotent creates."""

    def _check_tenant_ownership(self, serializer):
        org_ids = self.allowed_organization_ids()
        if org_ids is None:
            return
        head = self.org_field.split("__")[0]
        related = serializer.validated_data.get(head)
        if related is None:
            return
        org_id = (
            related.id
            if head == "organization"
            else getattr(related, "organization_id", None)
        )
        if org_id is not None and org_id not in org_ids:
            raise PermissionDenied("You do not have access to this organization.")

    def perform_create(self, serializer):
        self._check_tenant_ownership(serializer)
        serializer.save()

    def perform_update(self, serializer):
        self._check_tenant_ownership(serializer)
        serializer.save()
