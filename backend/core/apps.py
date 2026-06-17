from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = "core"

    def ready(self):
        # Importing the module registers its @register()-decorated system checks
        # (the Postgres-required-outside-DEBUG guard, audit gap V1).
        from core import checks  # noqa: F401
