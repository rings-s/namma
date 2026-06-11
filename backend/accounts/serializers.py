from rest_framework import serializers

from accounts.models import User, UserRole
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
        read_only_fields = ["id", "email", "is_active", "is_verified", "last_login", "created_at", "updated_at"]


class UserRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserRole
        fields = "__all__"
        read_only_fields = AUDIT_FIELDS
