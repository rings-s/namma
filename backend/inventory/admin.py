from django.apps import apps
from django.contrib import admin

for model in apps.get_app_config("inventory").get_models():
    if not admin.site.is_registered(model):
        admin.site.register(model)
