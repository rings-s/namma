<<<<<<< HEAD
from django.contrib import admin

# Register your models here.
=======
from django.apps import apps
from django.contrib import admin

from .models import Appointment


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = (
        "customer",
        "service",
        "employee",
        "branch",
        "scheduled_at",
        "status",
    )
    search_fields = (
        "customer__first_name",
        "customer__last_name",
        "customer__phone",
        "service__name",
    )
    list_filter = ("status", "source")
    date_hierarchy = "scheduled_at"


for model in apps.get_app_config("operations").get_models():
    if not admin.site.is_registered(model):
        admin.site.register(model)
>>>>>>> a3235b4 (feat(db): initialize core relational schema)
