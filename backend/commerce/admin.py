<<<<<<< HEAD
from django.contrib import admin

# Register your models here.
=======
from django.apps import apps
from django.contrib import admin

from .models import Sale, SaleItem


class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = (
        "sale_number",
        "organization",
        "branch",
        "customer",
        "total_amount",
        "status",
        "created_at",
    )
    search_fields = ("sale_number", "customer__first_name", "customer__last_name")
    list_filter = ("status",)
    date_hierarchy = "created_at"
    inlines = [SaleItemInline]


for model in apps.get_app_config("commerce").get_models():
    if not admin.site.is_registered(model):
        admin.site.register(model)
>>>>>>> a3235b4 (feat(db): initialize core relational schema)
