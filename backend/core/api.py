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
    if getattr(user, "is_superuser", False):
        return max(ROLE_RANKS.values()) + 1
    # API-key / non-user principals (pk is None) hold no UserRole, so every
    # role-gated action denies them. Guarding here also avoids feeding a
    # non-model principal into a FK filter.
    if getattr(user, "pk", None) is None:
        return 0
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


def organization_roles(user, organization_id):
    """The set of role strings the user holds in the organization."""
    # Non-user principals (API keys, pk None) hold no UserRole.
    if getattr(user, "pk", None) is None:
        return set()
    from accounts.models import UserRole

    return set(
        UserRole.objects.filter(user=user, organization_id=organization_id).values_list(
            "role", flat=True
        )
    )


def require_org_roles(user, organization_id, allowed_roles):
    """Raise PermissionDenied unless the user holds one of ``allowed_roles``.

    Membership check, *not* a rank floor: rank gating cannot distinguish two
    roles that share a rank (Accountant and Marketer are both 40). Use this
    when a permission must include some same-rank roles but exclude others.
    Superusers keep the platform escape hatch.
    """
    if getattr(user, "is_superuser", False):
        return
    if not set(allowed_roles) & organization_roles(user, organization_id):
        roles = ", ".join(sorted(allowed_roles))
        raise PermissionDenied(
            f"This action requires one of these roles in this organization: {roles}."
        )


class OrgRoleWriteGateMixin:
    """Gate create/update/destroy behind a minimum org role; reads stay open
    to any tenant member.

    ``write_min_role`` is a UserRole.Role value. The superuser escape hatch is
    inherited from ``require_org_role`` (superusers outrank every role). Layer
    this *before* ``TenantScopedViewSet`` so the gate runs ahead of the save.
    Custom @action methods are unaffected — only the standard write verbs.
    """

    write_min_role = None

    def _write_org_id(self, serializer=None, instance=None):
        head = self.org_field.split("__")[0]
        if instance is not None:
            related = (
                instance if head == "organization" else getattr(instance, head, None)
            )
        else:
            related = serializer.validated_data.get(head)
        if related is None:
            return None
        return (
            related.id
            if head == "organization"
            else getattr(related, "organization_id", None)
        )

    def _gate_write(self, *, serializer=None, instance=None):
        org_id = self._write_org_id(serializer=serializer, instance=instance)
        if org_id is not None:
            require_org_role(self.request.user, org_id, self.write_min_role)

    def perform_create(self, serializer):
        self._gate_write(serializer=serializer)
        super().perform_create(serializer)

    def perform_update(self, serializer):
        self._gate_write(instance=serializer.instance)
        super().perform_update(serializer)

    def perform_destroy(self, instance):
        self._gate_write(instance=instance)
        super().perform_destroy(instance)


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
            if getattr(user, "is_superuser", False):
                self._allowed_org_ids = None
            elif getattr(user, "organization_id", None) is not None and not getattr(
                user, "pk", None
            ):
                # API-key principal (integrations.authentication.APIKeyUser):
                # scoped to exactly the key's organization, never a UserRole.
                self._allowed_org_ids = [user.organization_id]
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
        # IdempotencyRecord.user is a FK to a real account; API-key principals
        # have no user row (pk is None), so they bypass replay dedup rather than
        # break the FK. Human-authenticated requests keep at-least-once safety.
        if (
            not key
            or not request.user.is_authenticated
            or getattr(request.user, "pk", None) is None
        ):
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


class ZatcaImmutableError(PermissionDenied):
    """Raised when a row bound to a reported ZATCA document is mutated."""

    status_code = 409
    default_detail = (
        "This record is locked: it has been reported to ZATCA and is legally "
        "immutable. Issue a credit note (full or partial reversal) and a new "
        "sale instead of editing it."
    )
    default_code = "zatca_immutable"


class ZatcaImmutableMixin:
    """Block update/destroy once the row is bound to a reported ZATCA invoice.

    This is a *data invariant*, not a permission: ZATCA Phase-2 makes a
    reported/cleared invoice legally immutable, so — unlike the role gates —
    there is deliberately **no superuser escape hatch**. Exempting anyone would
    void the append-only guarantee. The remedy is always a credit note.

    Subclasses implement ``zatca_locked_invoice(instance)`` returning the
    ``Invoice`` whose ZATCA state governs this row (or ``None`` if unbound).
    """

    def zatca_locked_invoice(self, instance):  # pragma: no cover - overridden
        raise NotImplementedError

    def _assert_not_zatca_locked(self, instance):
        from financials.services import invoice_has_live_e_invoice

        invoice = self.zatca_locked_invoice(instance)
        if invoice is not None and invoice_has_live_e_invoice(invoice):
            raise ZatcaImmutableError()

    def perform_update(self, serializer):
        self._assert_not_zatca_locked(serializer.instance)
        super().perform_update(serializer)

    def perform_destroy(self, instance):
        self._assert_not_zatca_locked(instance)
        super().perform_destroy(instance)


class WebhookBodyLimitMixin:
    """Reject oversized bodies on unauthenticated webhook receivers (audit P1).

    The gateway/SNS/Meta receivers are ``AllowAny`` and read ``request.body``
    (or ``request.data``) into memory and persist it. ``DATA_UPLOAD_MAX_MEMORY_SIZE``
    is the global backstop, but legitimate webhook payloads are tiny, so each
    receiver advertises a far tighter cap and rejects early on the declared
    ``Content-Length`` — cheap, before the body is read — with 413. The global
    setting still enforces the hard limit if a client lies about its length.
    """

    max_webhook_body_bytes = 256 * 1024

    def initial(self, request, *args, **kwargs):
        declared = request.META.get("CONTENT_LENGTH") or 0
        try:
            declared = int(declared)
        except (TypeError, ValueError):
            declared = 0
        if declared > self.max_webhook_body_bytes:
            from rest_framework.exceptions import APIException

            class PayloadTooLarge(APIException):
                status_code = 413
                default_detail = "Webhook payload too large."
                default_code = "payload_too_large"

            raise PayloadTooLarge()
        super().initial(request, *args, **kwargs)


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
