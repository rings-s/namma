"""AI workforce services: the engine behind the ``ai`` app's models.

Three capabilities, all provider-agnostic through :class:`ai.gateways.AIClient`:

* **Engagement** — ``generate_assistant_reply`` answers a conversation, appending
  an assistant :class:`~ai.models.AIMessage`.
* **Predictive** — ``generate_recommendations`` reads an org's ``daily_*`` rollups
  and writes actionable :class:`~ai.models.AIRecommendation` rows.
* **Segmentation** — ``generate_ai_segment`` turns a natural-language audience
  description into structured segment criteria, then converges membership with
  the deterministic customer-segment engine (no per-customer LLM calls).

Each function accepts an optional ``client`` so callers (and tests) can inject a
configured or fake gateway; otherwise a default :class:`AIClient` is built from
settings.
"""

import json
import logging
from decimal import Decimal

from django.utils import timezone

from ai.gateways import AIClient
from ai.models import AIConversation, AIMessage, AIRecommendation
from analytics.models import DailyMetric
from core.events import DomainEvent, publish
from customers.models import CustomerSegment
from customers.services import converge_segment_membership, evaluate_segment_queryset

logger = logging.getLogger(__name__)

#: Bumped whenever a system prompt in this module changes materially. Stored on
#: every AI-produced row so output regressions trace back to a prompt revision.
PROMPT_VERSION = "2026-06-14"

#: Sampling temperatures per capability, recorded as provenance alongside output.
_ASSISTANT_TEMPERATURE = 0.4
_RECOMMENDATIONS_TEMPERATURE = 0.2
_SEGMENT_TEMPERATURE = 0.0

#: Roles the Chat Completions API accepts in the message history.
_CHAT_ROLES = {"system", "user", "assistant"}

#: Criteria keys the deterministic segment engine understands. Anything the model
#: invents outside this set is discarded so generated segments stay safe to run.
_SEGMENT_CRITERIA_KEYS = {
    "min_visits",
    "min_total_spent",
    "last_visit_within_days",
    "last_visit_not_within_days",
    "source",
    "gender",
}


# ---------------------------------------------------------------------------
# Prompt building
# ---------------------------------------------------------------------------


def _org_descriptor(organization):
    """One-line business context shared across prompts."""
    industry = getattr(organization, "industry", "") or "service business"
    currency = getattr(organization, "currency", "") or "SAR"
    return (
        f"You are assisting '{organization.name}', a {industry} operating in Saudi "
        f"Arabia / the GCC. Amounts are in {currency}. Be concise and practical, and "
        f"respect Saudi business norms (prayer times, Hijri dates, Arabic/English)."
    )


def _assistant_system_prompt(organization):
    return (
        f"{_org_descriptor(organization)}\n\n"
        "You are Namaa's in-app assistant for staff. Answer questions about the "
        "business clearly. If you are unsure or lack data, say so rather than "
        "inventing numbers. Reply in the same language the user writes in."
    )


def _recommendations_system_prompt(organization):
    return (
        f"{_org_descriptor(organization)}\n\n"
        "You are a business analyst. From the daily metrics provided, surface the "
        "most useful, specific, actionable recommendations. Respond ONLY with a "
        "JSON array (no prose, no code fences). Each element must be an object with "
        'keys: "type" (short slug e.g. "retention", "revenue", "scheduling"), '
        '"title" (<=120 chars), "description" (1-3 sentences), and "priority" '
        '(one of "low", "medium", "high", "critical"). Return at most 5 items.'
    )


def _segment_system_prompt(organization):
    return (
        f"{_org_descriptor(organization)}\n\n"
        "Translate the audience description into segment filter criteria. Respond "
        "ONLY with a JSON object (no prose, no code fences) using only these keys "
        "when relevant: "
        '"min_visits" (int), "min_total_spent" (number), '
        '"last_visit_within_days" (int, recently active), '
        '"last_visit_not_within_days" (int, lapsed customers), '
        '"source" (string), "gender" (string). Omit keys that do not apply. '
        "All criteria are AND-ed together."
    )


def _metrics_user_prompt(metrics):
    """Compact, model-friendly rendering of recent daily metrics."""
    lines = [
        "date | appts | completed | cancelled | revenue | customers | new_customers"
    ]
    for m in metrics:
        lines.append(
            f"{m.date} | {m.total_appointments} | {m.completed_appointments} | "
            f"{m.cancelled_appointments} | {m.total_revenue} | "
            f"{m.total_customers} | {m.new_customers}"
        )
    return "Recent daily metrics (most recent first):\n" + "\n".join(lines)


# ---------------------------------------------------------------------------
# Robust JSON extraction (local models rarely honour response_format)
# ---------------------------------------------------------------------------


def _strip_fences(text):
    text = text.strip()
    if text.startswith("```"):
        # Drop the opening fence (optionally ```json) and the closing fence.
        text = text.split("\n", 1)[-1] if "\n" in text else ""
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]
    return text.strip()


def _extract_json(text, opener, closer):
    """Best-effort parse of the first JSON value bounded by opener/closer."""
    cleaned = _strip_fences(text)
    start = cleaned.find(opener)
    end = cleaned.rfind(closer)
    if start == -1 or end == -1 or end < start:
        return None
    snippet = cleaned[start : end + 1]
    try:
        return json.loads(snippet)
    except (ValueError, TypeError):
        return None


def parse_json_list(text):
    value = _extract_json(text, "[", "]")
    return value if isinstance(value, list) else []


def parse_json_object(text):
    value = _extract_json(text, "{", "}")
    return value if isinstance(value, dict) else {}


def _provenance(result, *, temperature):
    """Build the provenance kwargs shared by every AI-produced row from a
    gateway :class:`~ai.gateways.ChatResult`."""
    return {
        "ai_provider": result.provider,
        "ai_model": result.model,
        "prompt_version": PROMPT_VERSION,
        "prompt_tokens": result.prompt_tokens,
        "completion_tokens": result.completion_tokens,
        "latency_ms": result.latency_ms,
        "temperature": Decimal(str(temperature)),
    }


# ---------------------------------------------------------------------------
# Engagement: conversational assistant
# ---------------------------------------------------------------------------


def generate_assistant_reply(conversation, *, client=None):
    """Generate and persist the assistant's reply to a conversation.

    Reads the full message history, prepends the org-aware system prompt, calls
    the provider and appends one assistant ``AIMessage``. Returns that message.
    """
    client = client or AIClient()
    organization = conversation.organization

    history = conversation.messages.order_by("created_at").values("role", "content")
    messages = [{"role": "system", "content": _assistant_system_prompt(organization)}]
    messages.extend(
        {"role": m["role"], "content": m["content"]}
        for m in history
        if m["role"] in _CHAT_ROLES and m["content"]
    )

    result = client.chat(messages, temperature=_ASSISTANT_TEMPERATURE, max_tokens=1024)
    reply = AIMessage.objects.create(
        conversation=conversation,
        role=AIMessage.Role.ASSISTANT,
        content=result.content.strip(),
        tokens_used=result.total_tokens,
        **_provenance(result, temperature=_ASSISTANT_TEMPERATURE),
    )

    # Touch updated_at (drives -updated_at ordering) and backfill a title once.
    updates = {"updated_at": timezone.now()}
    if not conversation.title:
        first_user = next(
            (m["content"] for m in history if m["role"] == "user" and m["content"]),
            "",
        )
        if first_user:
            updates["title"] = first_user.strip()[:255]
    AIConversation.objects.filter(pk=conversation.pk).update(**updates)
    return reply


# ---------------------------------------------------------------------------
# Predictive: recommendations from analytics rollups
# ---------------------------------------------------------------------------


def generate_recommendations(organization, *, client=None, days=30):
    """Read recent daily metrics and create active ``AIRecommendation`` rows.

    Dashboards read only from the ``daily_*`` rollups, so do we. Idempotent per
    title: an existing active recommendation with the same title is left as-is,
    so re-running does not pile up duplicates. Returns the newly created rows.
    """
    client = client or AIClient()

    # Prefer the org-level (branch-null) rollup; fall back to any branch rows.
    metrics = list(
        DailyMetric.objects.filter(
            organization=organization, branch__isnull=True
        ).order_by("-date")[:days]
    )
    if not metrics:
        metrics = list(
            DailyMetric.objects.filter(organization=organization).order_by("-date")[
                :days
            ]
        )
    if not metrics:
        logger.info("No daily metrics for org %s; skipping.", organization.pk)
        return []

    messages = [
        {"role": "system", "content": _recommendations_system_prompt(organization)},
        {"role": "user", "content": _metrics_user_prompt(metrics)},
    ]
    result = client.chat(
        messages,
        temperature=_RECOMMENDATIONS_TEMPERATURE,
        max_tokens=1500,
        response_format={"type": "json_object"},
    )

    provenance = _provenance(result, temperature=_RECOMMENDATIONS_TEMPERATURE)
    valid_priorities = set(AIRecommendation.Priority.values)
    created = []
    for item in parse_json_list(result.content):
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()[:255]
        if not title:
            continue
        priority = item.get("priority")
        if priority not in valid_priorities:
            priority = AIRecommendation.Priority.MEDIUM
        recommendation, was_created = AIRecommendation.objects.get_or_create(
            organization=organization,
            title=title,
            status=AIRecommendation.Status.ACTIVE,
            defaults={
                "type": str(item.get("type") or "insight")[:100],
                "description": str(item.get("description") or ""),
                "priority": priority,
                "data": {"source": "daily_metrics"},
                **provenance,
            },
        )
        if was_created:
            created.append(recommendation)

    if created:
        # Decouple downstream reactions (staff notification, analytics, …) from
        # this producer: subscribers react on commit, never inline. See
        # core.events for the seam and ai.apps.AiConfig.ready for registration.
        publish(
            DomainEvent.AI_RECOMMENDATIONS_GENERATED,
            {"organization_id": str(organization.pk), "count": len(created)},
        )
    return created


# ---------------------------------------------------------------------------
# Segmentation: NL description -> structured criteria -> membership
# ---------------------------------------------------------------------------


def generate_ai_segment(segment, *, client=None):
    """Populate an AI segment's criteria from its description, then materialize
    membership with the deterministic engine. No-op for non-AI segments."""
    if segment.segment_type != CustomerSegment.SegmentType.AI:
        return segment
    client = client or AIClient()

    user_prompt = f"Segment name: {segment.name}\nDescription: {segment.description}"
    result = client.chat(
        [
            {"role": "system", "content": _segment_system_prompt(segment.organization)},
            {"role": "user", "content": user_prompt},
        ],
        temperature=_SEGMENT_TEMPERATURE,
        max_tokens=400,
        response_format={"type": "json_object"},
    )

    raw = parse_json_object(result.content)
    segment.criteria = {k: v for k, v in raw.items() if k in _SEGMENT_CRITERIA_KEYS}
    segment.save(update_fields=["criteria", "updated_at"])

    matching_ids = evaluate_segment_queryset(segment).values_list("id", flat=True)
    return converge_segment_membership(segment, matching_ids)


__all__ = [
    "generate_ai_segment",
    "generate_assistant_reply",
    "generate_recommendations",
    "parse_json_list",
    "parse_json_object",
]
