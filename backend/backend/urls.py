<<<<<<< HEAD
"""
URL configuration for backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path

urlpatterns = [
    path('admin/', admin.site.urls),
=======
"""Root URL configuration: Django admin plus the versioned REST API.

Each domain app exposes its resources through a DRF router mounted under
/api/v1/. The integrations app is intentionally registered last.
"""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    # Session login/logout for the browsable API.
    path("api/auth/", include("rest_framework.urls")),
    path("api/v1/", include("core.urls")),
    path("api/v1/", include("accounts.urls")),
    path("api/v1/", include("organnizations.urls")),
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
>>>>>>> a3235b4 (feat(db): initialize core relational schema)
]
