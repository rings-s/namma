<<<<<<< HEAD
from django.contrib import admin

# Register your models here.
=======
from django.apps import apps
from django.contrib import admin

from .models import Customer


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = (
        "first_name",
        "last_name",
        "phone",
        "organization",
        "loyalty_points",
        "total_spent",
        "is_active",
    )
    search_fields = ("first_name", "last_name", "phone", "email")
    list_filter = ("is_active", "gender", "source")


for model in apps.get_app_config("customers").get_models():
    if not admin.site.is_registered(model):
        admin.site.register(model)
>>>>>>> a3235b4 (feat(db): initialize core relational schema)
