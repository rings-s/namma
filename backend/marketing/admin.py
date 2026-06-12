from django.contrib import admin

# Register your models here.
from django.apps import apps

for model in apps.get_app_config("marketing").get_models():
    if not admin.site.is_registered(model):
        admin.site.register(model)
