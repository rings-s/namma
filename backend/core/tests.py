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


class DatabaseEngineCheckTests(TestCase):
    """The core.E001 guard (audit V1): no SQLite once DEBUG is off."""

    def test_sqlite_engine_is_flagged(self):
        from core.checks import engine_errors

        # The suite runs on SQLite, so the default config is the flagged case.
        self.assertEqual([e.id for e in engine_errors()], ["core.E001"])

    def test_postgres_engine_is_clean(self):
        from core.checks import engine_errors

        engine = {"default": {"ENGINE": "django.db.backends.postgresql"}}
        with self.settings(DATABASES=engine):
            self.assertEqual(engine_errors(), [])

    def test_registered_check_is_skipped_in_debug(self):
        from core.checks import postgres_required_outside_debug

        with self.settings(DEBUG=True):
            self.assertEqual(postgres_required_outside_debug(app_configs=None), [])


class RetentionSweepTests(TestCase):
    """PDPL retention worker enforces RetentionPolicy windows (audit P1)."""

    @classmethod
    def setUpTestData(cls):
        import datetime as dt

        from django.utils import timezone

        from organizations.models import Organization

        cls.org = Organization.objects.create(name="Ret", slug="ret")
        cls.other = Organization.objects.create(name="Other", slug="ret-other")
        cls.old_ts = timezone.now() - dt.timedelta(days=400)
        cls.new_ts = timezone.now() - dt.timedelta(days=5)

    def _event(self, org, when, **extra):
        from analytics.models import AnalyticsEvent

        ev = AnalyticsEvent.objects.create(
            organization=org, event_type="page_view", **extra
        )
        AnalyticsEvent.objects.filter(pk=ev.pk).update(created_at=when)
        return ev

    def _policy(self, entity, days, action):
        from organizations.models import RetentionPolicy

        return RetentionPolicy.objects.create(
            organization=self.org,
            entity_type=entity,
            retention_days=days,
            action=action,
        )

    def test_delete_removes_only_expired_rows_in_the_policy_org(self):
        from analytics.models import AnalyticsEvent
        from core.retention import apply_policy
        from organizations.models import RetentionPolicy

        self._event(self.org, self.old_ts)
        self._event(self.org, self.new_ts)
        self._event(self.other, self.old_ts)  # different tenant, must survive

        policy = self._policy(
            RetentionPolicy.EntityType.ANALYTICS_EVENTS,
            365,
            RetentionPolicy.Action.DELETE,
        )
        removed = apply_policy(policy)

        self.assertEqual(removed, 1)
        self.assertEqual(
            AnalyticsEvent.objects.filter(organization=self.org).count(), 1
        )
        self.assertEqual(
            AnalyticsEvent.objects.filter(organization=self.other).count(), 1
        )

    def test_anonymize_strips_pii_but_keeps_the_row(self):
        from django.contrib.auth import get_user_model

        from analytics.models import AnalyticsEvent
        from core.retention import apply_policy
        from organizations.models import RetentionPolicy

        user = get_user_model().objects.create_user(
            email="ret@namaa.sa", password="pass12345"
        )
        self._event(
            self.org,
            self.old_ts,
            user=user,
            session_id="sess-1",
            event_data={"ip": "x"},
        )
        policy = self._policy(
            RetentionPolicy.EntityType.ANALYTICS_EVENTS,
            365,
            RetentionPolicy.Action.ANONYMIZE,
        )
        affected = apply_policy(policy)

        self.assertEqual(affected, 1)
        event = AnalyticsEvent.objects.get(organization=self.org)
        self.assertIsNone(event.user_id)
        self.assertEqual(event.session_id, "")
        self.assertEqual(event.event_data, {})

    def test_idempotency_records_policy_is_skipped_not_applied(self):
        # IdempotencyRecord has no organization FK; the sweep must refuse rather
        # than risk cross-tenant deletion.
        from core.retention import apply_policy
        from organizations.models import RetentionPolicy

        policy = self._policy(
            RetentionPolicy.EntityType.IDEMPOTENCY_RECORDS,
            30,
            RetentionPolicy.Action.DELETE,
        )
        self.assertEqual(apply_policy(policy), 0)

    def test_anonymize_without_anonymizer_is_skipped_not_deleted(self):
        from core.retention import apply_policy
        from organizations.models import RetentionPolicy

        policy = self._policy(
            RetentionPolicy.EntityType.SLOT_HOLDS,
            1,
            RetentionPolicy.Action.ANONYMIZE,
        )
        self.assertEqual(apply_policy(policy), 0)  # no anonymizer -> no-op


class WebhookBodyLimitTests(TestCase):
    """Unauthenticated webhook receivers reject oversized bodies (audit P1)."""

    def test_oversized_body_is_rejected_with_413(self):
        # Declared Content-Length over the cap is refused before the body is read.
        oversized = "x" * (256 * 1024 + 1)
        response = self.client.post(
            "/api/v1/webhooks/ses/",
            data=oversized,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 413)

    def test_small_body_passes_the_limit_check(self):
        # A tiny malformed payload gets past the size gate and is handled by the
        # view (400 for bad JSON / 403 for bad signature), never 413.
        response = self.client.post(
            "/api/v1/webhooks/ses/",
            data="{}",
            content_type="application/json",
        )
        self.assertNotEqual(response.status_code, 413)


class RequestIDMiddlewareTests(TestCase):
    """Correlation id plumbing (audit V3)."""

    def test_response_carries_a_request_id(self):
        response = self.client.get("/api/v1/services/")  # 401, but still tagged
        self.assertTrue(response.headers.get("X-Request-ID"))

    def test_upstream_request_id_is_honoured(self):
        response = self.client.get(
            "/api/v1/services/", HTTP_X_REQUEST_ID="trace-abc-123"
        )
        self.assertEqual(response.headers.get("X-Request-ID"), "trace-abc-123")
