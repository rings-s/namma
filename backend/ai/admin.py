<<<<<<< HEAD
from django.contrib import admin

# Register your models here.
=======
from django.apps import apps
from django.contrib import admin

for model in apps.get_app_config("ai").get_models():
    if not admin.site.is_registered(model):
        admin.site.register(model)
>>>>>>> a3235b4 (feat(db): initialize core relational schema)
