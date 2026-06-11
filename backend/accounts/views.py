<<<<<<< HEAD
from django.shortcuts import render

# Create your views here.
=======
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import UserRole
from accounts.serializers import UserRoleSerializer, UserSerializer
from core.api import TenantScopedViewSet


class MeView(APIView):
    """Profile of the authenticated user, with their organization roles."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        data = UserSerializer(request.user).data
        data["roles"] = UserRoleSerializer(
            request.user.roles.select_related("organization", "branch"), many=True
        ).data
        return Response(data)

    def patch(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class UserRoleViewSet(TenantScopedViewSet):
    queryset = UserRole.objects.select_related("user", "organization", "branch")
    serializer_class = UserRoleSerializer
    search_fields = ["user__email", "role"]
>>>>>>> a3235b4 (feat(db): initialize core relational schema)
