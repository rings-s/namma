"""Root URL configuration: Django admin plus the versioned REST API.

Each domain app exposes its resources through a DRF router mounted under
/api/v1/. The integrations app is intentionally registered last.
"""

from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    # Session login/logout for the browsable API.
    path("api/auth/", include("rest_framework.urls")),
    # OpenAPI 3 schema + interactive docs. The schema view inherits the
    # default IsAuthenticated permission, so the contract isn't public.
    path("api/v1/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/v1/schema/swagger-ui/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/v1/schema/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
    path("api/v1/", include("core.urls")),
    path("api/v1/", include("accounts.urls")),
    path("api/v1/", include("organizations.urls")),
    path("api/v1/", include("customers.urls")),
    path("api/v1/", include("commerce.urls")),
    path("api/v1/", include("inventory.urls")),
    path("api/v1/", include("operations.urls")),
    path("api/v1/", include("financials.urls")),
    path("api/v1/", include("marketing.urls")),
    path("api/v1/", include("communications.urls")),
    path("api/v1/", include("analytics.urls")),
    path("api/v1/", include("ai.urls")),
    path("api/v1/", include("integrations.urls")),
]
