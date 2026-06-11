from django.urls import path
from rest_framework.routers import DefaultRouter

from accounts import views

router = DefaultRouter()
router.register("user-roles", views.UserRoleViewSet)

urlpatterns = [
    path("me/", views.MeView.as_view(), name="me"),
    *router.urls,
]
