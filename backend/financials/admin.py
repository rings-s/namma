from django.apps import apps
from django.contrib import admin

from .models import Invoice


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = (
        "invoice_number",
        "organization",
        "customer",
        "total_amount",
        "amount_due",
        "status",
        "issued_at",
    )
    search_fields = ("invoice_number", "customer__first_name", "customer__last_name")
    list_filter = ("status",)
    date_hierarchy = "created_at"


for model in apps.get_app_config("financials").get_models():
    if not admin.site.is_registered(model):
        admin.site.register(model)
