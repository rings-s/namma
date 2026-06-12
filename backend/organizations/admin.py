from django.contrib import admin

# Register your models here.
from django.apps import apps

from .models import Branch, Organization


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "slug",
        "industry",
        "tenant_tier",
        "is_active",
        "created_at",
    )
    search_fields = ("name", "slug", "email", "phone")
    list_filter = ("tenant_tier", "is_active", "industry")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "city", "is_active", "created_at")
    search_fields = ("name", "city", "organization__name")
    list_filter = ("is_active", "city")


for model in apps.get_app_config("organizations").get_models():
    if not admin.site.is_registered(model):
        admin.site.register(model)
