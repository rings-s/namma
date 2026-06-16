from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from accounts.models import TwoFactorDevice, UserRole, UserSession
from accounts.throttling import LoginRateThrottle
from core.audit import record_audit
from accounts.serializers import (
    RegisterSerializer,
    TwoFactorCodeSerializer,
    TwoFactorTokenObtainPairSerializer,
    UserRoleSerializer,
    UserSerializer,
    UserSessionSerializer,
)
from core.api import ROLE_RANKS, TenantScopedViewSet, organization_role_rank


def _client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class TwoFactorTokenObtainPairView(TokenObtainPairView):
    """JWT pair issuance; demands a TOTP code once the user has 2FA enabled.

    Every successful login opens a UserSession tracking the refresh-token
    lineage, so users can audit and remotely revoke their devices.
    """

    serializer_class = TwoFactorTokenObtainPairSerializer
    # Brute-force guard: tight per-(IP, email) limit, independent of the
    # shared anonymous bucket.
    throttle_classes = [LoginRateThrottle]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as exc:
            raise InvalidToken(exc.args[0]) from exc
        data = serializer.validated_data
        UserSession.objects.create(
            user=serializer.user,
            refresh_jti=RefreshToken(data["refresh"])["jti"],
            ip_address=_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", "")[:512],
        )
        record_audit(
            action="auth.login",
            entity_type="User",
            entity_id=serializer.user.id,
            user=serializer.user,
            request=request,
        )
        return Response(data, status=status.HTTP_200_OK)


class SessionTrackingTokenRefreshView(TokenRefreshView):
    """Token refresh that re-points the session at the rotated jti, so a
    session row follows its device across the whole token lineage."""

    def post(self, request, *args, **kwargs):
        old_jti = None
        try:
            old_jti = RefreshToken(request.data.get("refresh", ""))["jti"]
        except TokenError:
            pass  # super() raises the proper 401 below
        response = super().post(request, *args, **kwargs)
        new_refresh = response.data.get("refresh")
        if old_jti and new_refresh:
            UserSession.objects.filter(
                refresh_jti=old_jti, revoked_at__isnull=True
            ).update(
                refresh_jti=RefreshToken(new_refresh)["jti"],
                last_seen_at=timezone.now(),
            )
        return response


class SessionListView(generics.ListAPIView):
    """The authenticated user's sessions, active first."""

    serializer_class = UserSessionSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None
    filter_backends = []

    def get_queryset(self):
        return UserSession.objects.filter(user=self.request.user)


class SessionRevokeView(generics.GenericAPIView):
    """Remote sign-out: blacklists the session's refresh token lineage."""

    serializer_class = UserSessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk=None):
        session = UserSession.objects.filter(
            pk=pk, user=request.user, revoked_at__isnull=True
        ).first()
        if session is None:
            raise NotFound("No active session with this id.")
        outstanding = OutstandingToken.objects.filter(jti=session.refresh_jti).first()
        if outstanding is not None:
            BlacklistedToken.objects.get_or_create(token=outstanding)
        session.revoked_at = timezone.now()
        session.save(update_fields=["revoked_at", "updated_at"])
        record_audit(
            action="auth.session_revoked",
            entity_type="UserSession",
            entity_id=session.id,
            user=request.user,
            request=request,
        )
        return Response(UserSessionSerializer(session).data)


class MeView(generics.RetrieveUpdateAPIView):
    """Profile of the authenticated user, with their organization roles."""

    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "patch", "head", "options"]

    def get_object(self):
        return self.request.user

    def retrieve(self, request, *args, **kwargs):
        data = self.get_serializer(request.user).data
        data["roles"] = UserRoleSerializer(
            request.user.roles.select_related("organization", "branch"), many=True
        ).data
        return Response(data)


class TwoFactorSetupView(generics.GenericAPIView):
    """Start 2FA enrollment: issue a fresh secret and provisioning URI.

    The device stays unconfirmed (and 2FA unenforced) until the user proves
    possession by verifying a code at the verify endpoint.
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TwoFactorCodeSerializer  # for schema only; POST takes no body

    def post(self, request):
        device = TwoFactorDevice.objects.filter(user=request.user).first()
        if device is not None and device.confirmed:
            raise ValidationError("Two-factor authentication is already enabled.")
        if device is None:
            device = TwoFactorDevice(user=request.user)
        device.secret = TwoFactorDevice.generate_secret()
        device.confirmed = False
        device.confirmed_at = None
        device.save()
        return Response(
            {"secret": device.secret, "otpauth_uri": device.provisioning_uri()},
            status=status.HTTP_201_CREATED,
        )


class TwoFactorVerifyView(generics.GenericAPIView):
    """Confirm enrollment with a valid TOTP code; 2FA is enforced from here on."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TwoFactorCodeSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        device = TwoFactorDevice.objects.filter(user=request.user).first()
        if device is None:
            raise ValidationError("Run two-factor setup first.")
        if device.confirmed:
            raise ValidationError("Two-factor authentication is already enabled.")
        if not device.verify(serializer.validated_data["code"]):
            raise ValidationError({"code": "Invalid two-factor authentication code."})
        device.confirm()
        return Response({"detail": "Two-factor authentication enabled."})


class TwoFactorDisableView(generics.GenericAPIView):
    """Disable 2FA; requires a currently valid TOTP code."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TwoFactorCodeSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        device = TwoFactorDevice.objects.filter(
            user=request.user, confirmed=True
        ).first()
        if device is None:
            raise ValidationError("Two-factor authentication is not enabled.")
        if not device.verify(serializer.validated_data["code"]):
            raise ValidationError({"code": "Invalid two-factor authentication code."})
        device.delete()
        return Response({"detail": "Two-factor authentication disabled."})


class UserRoleViewSet(TenantScopedViewSet):
    """Role assignments within an organization.

    Only owners/admins of the target organization may manage roles, a role
    higher than the requester's own may never be granted, and users cannot
    modify their own role row — closing the self-elevation path.
    """

    queryset = UserRole.objects.select_related("user", "organization", "branch")
    serializer_class = UserRoleSerializer
    search_fields = ["user__email", "role"]

    def _check_role_management(self, organization, target_role=None):
        requester_rank = organization_role_rank(self.request.user, organization.id)
        if requester_rank < ROLE_RANKS[UserRole.Role.ADMIN]:
            raise PermissionDenied(
                "Only organization owners or admins can manage roles."
            )
        if target_role is not None and ROLE_RANKS.get(target_role, 0) > requester_rank:
            raise PermissionDenied("You cannot grant a role higher than your own.")

    def perform_create(self, serializer):
        self._check_tenant_ownership(serializer)
        self._check_role_management(
            serializer.validated_data["organization"],
            serializer.validated_data.get("role"),
        )
        role = serializer.save()
        record_audit(
            action="rbac.role_granted",
            entity_type="UserRole",
            entity_id=role.id,
            organization=role.organization,
            user=self.request.user,
            new_values={"target_user": str(role.user_id), "role": role.role},
            request=self.request,
        )

    def perform_update(self, serializer):
        if (
            serializer.instance.user_id == self.request.user.id
            and not self.request.user.is_superuser
        ):
            raise PermissionDenied("You cannot modify your own role.")
        self._check_tenant_ownership(serializer)
        organization = serializer.validated_data.get(
            "organization", serializer.instance.organization
        )
        target_role = serializer.validated_data.get("role", serializer.instance.role)
        old_role = serializer.instance.role
        self._check_role_management(organization, target_role)
        role = serializer.save()
        record_audit(
            action="rbac.role_updated",
            entity_type="UserRole",
            entity_id=role.id,
            organization=role.organization,
            user=self.request.user,
            old_values={"role": old_role},
            new_values={"target_user": str(role.user_id), "role": role.role},
            request=self.request,
        )

    def perform_destroy(self, instance):
        self._check_role_management(instance.organization)
        record_audit(
            action="rbac.role_revoked",
            entity_type="UserRole",
            entity_id=instance.id,
            organization=instance.organization,
            user=self.request.user,
            old_values={"target_user": str(instance.user_id), "role": instance.role},
            request=self.request,
        )
        instance.delete()
