from django.apps import AppConfig


class AiConfig(AppConfig):
    name = "ai"

    def ready(self):
        # Register domain-event subscribers once at startup. Imports are local
        # so app loading isn't ordering-sensitive.
        from core.events import DomainEvent, subscribe

        from ai.tasks import notify_recommendations_task

        subscribe(DomainEvent.AI_RECOMMENDATIONS_GENERATED, notify_recommendations_task)
