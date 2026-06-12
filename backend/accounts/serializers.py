from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from accounts.models import User, UserRole, UserSession
from core.api import AUDIT_FIELDS


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "phone",
            "avatar_url",
            "is_active",
            "is_verified",
            "last_login",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "email",
            "is_active",
            "is_verified",
            "last_login",
            "created_at",
            "updated_at",
        ]


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ["id", "email", "password", "first_name", "last_name", "phone"]
        read_only_fields = ["id"]

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class TwoFactorTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Standard SimpleJWT pair issuance, with TOTP enforcement once enabled."""

    otp_code = serializers.CharField(required=False, allow_blank=True, write_only=True)

    def validate(self, attrs):
        otp_code = attrs.pop("otp_code", "")
        data = super().validate(attrs)
        device = getattr(self.user, "two_factor_device", None)
        if device is not None and device.confirmed:
            if not otp_code:
                raise serializers.ValidationError(
                    {"otp_code": "Two-factor authentication code is required."}
                )
            if not device.verify(otp_code):
                raise serializers.ValidationError(
                    {"otp_code": "Invalid two-factor authentication code."}
                )
        return data


class TwoFactorCodeSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=10)


class UserRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserRole
        fields = "__all__"
        read_only_fields = AUDIT_FIELDS


class UserSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSession
        # The jti is a credential identifier — never expose it.
        exclude = ("refresh_jti", "user")
        read_only_fields = (
            *AUDIT_FIELDS,
            "ip_address",
            "user_agent",
            "last_seen_at",
            "revoked_at",
        )
