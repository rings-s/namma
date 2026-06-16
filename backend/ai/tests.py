"""AI workforce tests.

The provider is faked with ``httpx.MockTransport`` — every test asserts the
engine's behaviour (parsing, persistence, membership convergence, retry
classification) without a network call or a real API key.
"""

import json
from unittest.mock import patch

import httpx
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APITestCase

from accounts.models import UserRole
from ai.gateways import AIClient, AIError
from ai.models import AIConversation, AIMessage, AIRecommendation
from ai.services import (
    generate_ai_segment,
    generate_assistant_reply,
    generate_recommendations,
)
from analytics.models import DailyMetric
from customers.models import Customer, CustomerSegment
from organizations.models import Organization

User = get_user_model()


def _completion(content):
    """An OpenAI-style chat completion envelope wrapping ``content``."""
    return {
        "model": "fake-model",
        "choices": [{"message": {"role": "assistant", "content": content}}],
        "usage": {"prompt_tokens": 11, "completion_tokens": 7},
    }


def fake_client(content, *, status_code=200):
    """An :class:`AIClient` whose single endpoint returns ``content``."""

    def handler(request):
        if status_code == 200:
            return httpx.Response(200, json=_completion(content))
        return httpx.Response(status_code, json={"error": {"message": "boom"}})

    return AIClient(
        api_key="test",
        base_url="http://fake/v1",
        model="fake-model",
        transport=httpx.MockTransport(handler),
    )


class AIClientTests(TestCase):
    def test_parses_content_and_usage(self):
        result = fake_client("Hello!").chat([{"role": "user", "content": "hi"}])
        self.assertEqual(result.content, "Hello!")
        self.assertEqual(result.total_tokens, 18)

    def test_rate_limit_is_retryable(self):
        with self.assertRaises(AIError) as ctx:
            fake_client("", status_code=429).chat([{"role": "user", "content": "hi"}])
        self.assertTrue(ctx.exception.retryable)

    def test_bad_request_is_final(self):
        with self.assertRaises(AIError) as ctx:
            fake_client("", status_code=400).chat([{"role": "user", "content": "hi"}])
        self.assertFalse(ctx.exception.retryable)


class AssistantReplyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org = Organization.objects.create(name="Glow Spa", slug="glow")
        cls.user = User.objects.create_user(email="o@namaa.sa", password="pass12345")
        cls.conversation = AIConversation.objects.create(
            organization=cls.org, user=cls.user
        )
        AIMessage.objects.create(
            conversation=cls.conversation,
            role=AIMessage.Role.USER,
            content="How many bookings did we have?",
        )

    def test_appends_assistant_message_and_titles_conversation(self):
        reply = generate_assistant_reply(
            self.conversation, client=fake_client("You had 12 bookings.")
        )
        self.assertEqual(reply.role, AIMessage.Role.ASSISTANT)
        self.assertEqual(reply.content, "You had 12 bookings.")
        self.assertEqual(reply.tokens_used, 18)
        self.conversation.refresh_from_db()
        self.assertEqual(self.conversation.title, "How many bookings did we have?")

    def test_assistant_reply_records_provenance(self):
        from decimal import Decimal

        from ai.services import PROMPT_VERSION

        reply = generate_assistant_reply(
            self.conversation, client=fake_client("You had 12 bookings.")
        )
        self.assertEqual(reply.ai_model, "fake-model")
        self.assertEqual(reply.ai_provider, "fake")  # derived from base_url host
        self.assertEqual(reply.prompt_version, PROMPT_VERSION)
        self.assertEqual(reply.prompt_tokens, 11)
        self.assertEqual(reply.completion_tokens, 7)
        self.assertEqual(reply.temperature, Decimal("0.40"))


class RecommendationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org = Organization.objects.create(name="Glow Spa", slug="glow")
        DailyMetric.objects.create(
            organization=cls.org,
            date="2026-06-10",
            total_appointments=20,
            completed_appointments=15,
            cancelled_appointments=5,
            total_revenue=4000,
            total_customers=18,
            new_customers=3,
        )

    def test_parses_array_and_dedupes_by_title(self):
        payload = json.dumps(
            [
                {
                    "type": "retention",
                    "title": "Win back lapsed customers",
                    "description": "5 of 20 appointments cancelled.",
                    "priority": "high",
                },
                {"title": "", "description": "ignored — no title"},
            ]
        )
        created = generate_recommendations(self.org, client=fake_client(payload))
        self.assertEqual(len(created), 1)
        rec = created[0]
        self.assertEqual(rec.priority, AIRecommendation.Priority.HIGH)
        self.assertEqual(rec.type, "retention")
        self.assertEqual(rec.data["source"], "daily_metrics")

        # Re-running with the same title creates nothing new.
        again = generate_recommendations(self.org, client=fake_client(payload))
        self.assertEqual(again, [])
        self.assertEqual(AIRecommendation.objects.filter(title=rec.title).count(), 1)

    def test_invalid_priority_falls_back_to_medium(self):
        payload = json.dumps([{"title": "Do a thing", "priority": "urgent"}])
        created = generate_recommendations(self.org, client=fake_client(payload))
        self.assertEqual(created[0].priority, AIRecommendation.Priority.MEDIUM)

    def test_recommendation_records_provenance(self):
        from ai.services import PROMPT_VERSION

        payload = json.dumps([{"title": "Add evening slots", "priority": "high"}])
        rec = generate_recommendations(self.org, client=fake_client(payload))[0]
        self.assertEqual(rec.ai_model, "fake-model")
        self.assertEqual(rec.ai_provider, "fake")
        self.assertEqual(rec.prompt_version, PROMPT_VERSION)
        self.assertEqual(rec.prompt_tokens, 11)

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
    def test_creating_recommendations_publishes_event_that_notifies_staff(self):
        """End-to-end seam: the producer publishes, and the registered consumer
        raises an in-app notification on commit — without the AI engine ever
        importing the communications layer."""
        from communications.models import Notification

        payload = json.dumps([{"title": "Reduce no-shows", "priority": "high"}])
        with self.captureOnCommitCallbacks(execute=True):
            created = generate_recommendations(self.org, client=fake_client(payload))
        self.assertEqual(len(created), 1)
        note = Notification.objects.get(organization=self.org)
        self.assertEqual(note.type, Notification.NotificationType.ALERT)
        self.assertEqual(note.data["count"], 1)
        self.assertIn("1 new AI recommendation", note.title)


class AISegmentTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org = Organization.objects.create(name="Glow Spa", slug="glow")
        cls.loyal = Customer.objects.create(
            organization=cls.org, first_name="Loyal", last_name="One", visit_count=10
        )
        cls.new = Customer.objects.create(
            organization=cls.org, first_name="New", last_name="Two", visit_count=1
        )

    def test_generates_criteria_and_converges_membership(self):
        segment = CustomerSegment.objects.create(
            organization=self.org,
            name="VIPs",
            description="Customers with at least 5 visits",
            segment_type=CustomerSegment.SegmentType.AI,
        )
        # Model also returns an unsupported key, which must be dropped.
        payload = json.dumps({"min_visits": 5, "made_up_key": "x"})
        generate_ai_segment(segment, client=fake_client(payload))
        segment.refresh_from_db()
        self.assertEqual(segment.criteria, {"min_visits": 5})
        member_ids = set(segment.memberships.values_list("customer_id", flat=True))
        self.assertEqual(member_ids, {self.loyal.id})

    def test_noop_for_non_ai_segment(self):
        segment = CustomerSegment.objects.create(
            organization=self.org,
            name="Manual",
            segment_type=CustomerSegment.SegmentType.MANUAL,
        )
        # A failing client that would raise if actually called.
        result = generate_ai_segment(segment, client=fake_client("{}", status_code=500))
        self.assertEqual(result, segment)


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
class AIMessageEndpointTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org = Organization.objects.create(name="Glow Spa", slug="glow")
        cls.user = User.objects.create_user(email="o@namaa.sa", password="pass12345")
        UserRole.objects.create(
            user=cls.user, organization=cls.org, role=UserRole.Role.OWNER
        )
        cls.conversation = AIConversation.objects.create(
            organization=cls.org, user=cls.user
        )

    def test_posting_user_message_enqueues_assistant_reply(self):
        self.client.force_authenticate(self.user)
        # Patch the gateway the eager task builds so it uses a fake client.
        with patch("ai.services.AIClient", return_value=fake_client("Sure!")):
            response = self.client.post(
                "/api/v1/ai-messages/",
                {
                    "conversation": str(self.conversation.id),
                    "role": "user",
                    "content": "Hello",
                },
                format="json",
            )
        self.assertEqual(response.status_code, 201)
        roles = list(
            self.conversation.messages.order_by("created_at").values_list(
                "role", flat=True
            )
        )
        self.assertEqual(roles, ["user", "assistant"])

    def test_cannot_post_message_into_another_orgs_conversation(self):
        """IDOR guard: a user may not append messages to a conversation in an
        organization they hold no role in."""
        other_org = Organization.objects.create(name="Rival Spa", slug="rival")
        foreign_conversation = AIConversation.objects.create(
            organization=other_org, user=self.user
        )
        self.client.force_authenticate(self.user)
        response = self.client.post(
            "/api/v1/ai-messages/",
            {
                "conversation": str(foreign_conversation.id),
                "role": "user",
                "content": "leak",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(foreign_conversation.messages.count(), 0)
