from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenBlacklistView

from accounts import views

router = DefaultRouter()
router.register("user-roles", views.UserRoleViewSet)

urlpatterns = [
    path("auth/register/", views.RegisterView.as_view(), name="register"),
    path(
        "auth/token/",
        views.TwoFactorTokenObtainPairView.as_view(),
        name="token_obtain_pair",
    ),
    path(
        "auth/token/refresh/",
        views.SessionTrackingTokenRefreshView.as_view(),
        name="token_refresh",
    ),
    path("auth/token/blacklist/", TokenBlacklistView.as_view(), name="token_blacklist"),
    path("auth/sessions/", views.SessionListView.as_view(), name="session_list"),
    path(
        "auth/sessions/<uuid:pk>/revoke/",
        views.SessionRevokeView.as_view(),
        name="session_revoke",
    ),
    path("auth/2fa/setup/", views.TwoFactorSetupView.as_view(), name="2fa_setup"),
    path("auth/2fa/verify/", views.TwoFactorVerifyView.as_view(), name="2fa_verify"),
    path("auth/2fa/disable/", views.TwoFactorDisableView.as_view(), name="2fa_disable"),
    path("me/", views.MeView.as_view(), name="me"),
    *router.urls,
]
