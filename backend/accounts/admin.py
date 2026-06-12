from django.apps import apps
from django.contrib import admin

from .models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = (
        "email",
        "first_name",
        "last_name",
        "is_active",
        "is_verified",
        "is_staff",
    )
    search_fields = ("email", "first_name", "last_name", "phone")
    list_filter = ("is_active", "is_verified", "is_staff")
    exclude = ("password",)


for model in apps.get_app_config("accounts").get_models():
    if not admin.site.is_registered(model):
        admin.site.register(model)
