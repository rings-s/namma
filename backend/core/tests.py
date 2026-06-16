"""Platform-wide API sanity checks."""

from django.test import TestCase
from django.urls import URLResolver, get_resolver
from rest_framework.routers import DefaultRouter


def iter_registered_viewsets():
    """Yield every viewset registered on any router mounted under /api/v1/."""
    seen = set()
    for pattern in get_resolver().url_patterns:
        if not isinstance(pattern, URLResolver):
            continue
        if not hasattr(pattern.urlconf_module, "router"):
            continue
        router = pattern.urlconf_module.router
        if isinstance(router, DefaultRouter):
            for prefix, viewset, basename in router.registry:
                if viewset not in seen:
                    seen.add(viewset)
                    yield prefix, viewset


class SerializerConfigurationTests(TestCase):
    """Force-build every serializer so bad Meta configs fail loudly in CI."""

    def test_every_registered_serializer_builds(self):
        checked = 0
        for prefix, viewset in iter_registered_viewsets():
            serializer_class = viewset.serializer_class
            with self.subTest(resource=prefix, serializer=serializer_class.__name__):
                # Accessing .fields triggers full field/Meta validation.
                self.assertTrue(len(serializer_class().fields) > 0)
            checked += 1
        self.assertGreater(
            checked, 50, "expected the full API surface to be registered"
        )

    def test_every_tenant_viewset_queryset_is_evaluable(self):
        # Catches typos in select_related / org_field paths at test time.
        for prefix, viewset in iter_registered_viewsets():
            with self.subTest(resource=prefix, viewset=viewset.__name__):
                list(viewset.queryset.all()[:1])


class IdempotencyKeyTests(TestCase):
    """The Idempotency-Key header makes POST creates replay-safe."""

    @classmethod
    def setUpTestData(cls):
        from django.contrib.auth import get_user_model

        from accounts.models import UserRole
        from organizations.models import Organization

        cls.org = Organization.objects.create(name="Idem", slug="idem")
        cls.user = get_user_model().objects.create_user(
            email="idem@namaa.sa", password="pass12345"
        )
        UserRole.objects.create(
            user=cls.user, organization=cls.org, role=UserRole.Role.OWNER
        )

    def _post_customer(self, key, name="Sara"):
        from rest_framework.test import APIClient

        client = APIClient()
        client.force_authenticate(self.user)
        return client.post(
            "/api/v1/customers/",
            {"organization": str(self.org.id), "first_name": name},
            format="json",
            headers={"Idempotency-Key": key},
        )

    def test_replayed_key_returns_stored_response_without_duplicating(self):
        from customers.models import Customer

        first = self._post_customer("abc-123")
        second = self._post_customer("abc-123", name="Different")
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        self.assertEqual(second.headers.get("Idempotency-Replayed"), "true")
        self.assertEqual(first.data["id"], second.data["id"])
        self.assertEqual(Customer.objects.count(), 1)

    def test_distinct_keys_create_distinct_rows(self):
        from customers.models import Customer

        self._post_customer("key-1")
        self._post_customer("key-2")
        self.assertEqual(Customer.objects.count(), 2)

    def test_requests_without_key_are_unaffected(self):
        from customers.models import Customer
        from rest_framework.test import APIClient

        client = APIClient()
        client.force_authenticate(self.user)
        for _ in range(2):
            client.post(
                "/api/v1/customers/",
                {"organization": str(self.org.id), "first_name": "Twice"},
                format="json",
            )
        self.assertEqual(Customer.objects.count(), 2)


class DomainEventSeamTests(TestCase):
    """The explicit in-process event bus: commit-safe, non-blocking dispatch."""

    def setUp(self):
        # Snapshot and restore the registry so these tests don't wipe the
        # real AppConfig.ready() subscriptions for the rest of the suite.
        import copy

        from core import events

        original = copy.deepcopy(events._subscribers)
        events.clear_subscribers()
        self.addCleanup(events._subscribers.update, original)
        self.addCleanup(events.clear_subscribers)

    def _recording_task(self):
        calls = []

        class _Task:
            def delay(self_inner, **kwargs):
                calls.append(kwargs)

        return _Task(), calls

    def test_publish_enqueues_subscribers_after_commit(self):
        from core.events import publish, subscribe

        task, calls = self._recording_task()
        subscribe("ai.recommendations_generated", task)

        # Inside an atomic block the dispatch must wait for commit.
        with self.captureOnCommitCallbacks(execute=True):
            publish("ai.recommendations_generated", {"organization_id": "abc"})
            self.assertEqual(calls, [])  # not yet — transaction still open
        self.assertEqual(
            calls,
            [
                {
                    "event_type": "ai.recommendations_generated",
                    "payload": {"organization_id": "abc"},
                }
            ],
        )

    def test_publish_without_subscribers_is_noop(self):
        from core.events import publish

        with self.captureOnCommitCallbacks(execute=True):
            publish("ai.recommendations_generated", {"x": 1})  # must not raise

    def test_enqueue_failure_does_not_propagate(self):
        from core.events import publish, subscribe

        class _Boom:
            def delay(self, **kwargs):
                raise RuntimeError("broker down")

        subscribe("ai.recommendations_generated", _Boom())
        with self.captureOnCommitCallbacks(execute=True):
            publish("ai.recommendations_generated", {})  # swallowed, logged
