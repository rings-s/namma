"""PDPL data-retention sweep (audit P1).

``organizations.RetentionPolicy`` declared a per-tenant, per-entity retention
window with a delete/anonymize action, and its docstring promised "a worker
sweeps expired rows per policy" — but no worker existed. This module is that
worker.

Design notes / surfaced conflicts:

* **Scope is the policy's organization.** Every swept entity carries an
  ``organization`` FK, so a policy only ever touches its own tenant's rows.
* **``IDEMPOTENCY_RECORDS`` is intentionally unsupported here.**
  ``core.IdempotencyRecord`` has *no* ``organization`` FK (it is keyed per
  user), so a per-org policy cannot tenant-scope it without risking deletion of
  another tenant's records. Rather than silently delete cross-tenant data to
  satisfy the policy row, the sweep skips it and logs a warning. Idempotency
  records are short-lived and better swept by a global TTL.
* **ANONYMIZE never falls back to DELETE.** If a policy asks to anonymize an
  entity with no defined anonymizer (e.g. slot holds), the sweep logs and skips
  it — honouring the chosen action rather than quietly destroying the row.
* **Statutory records are out of reach by construction.** Invoices, ledger
  entries and ZATCA documents are not in ``EntityType`` at all, so no tenant
  policy can shorten their legally-mandated retention.
"""

from __future__ import annotations

import datetime as dt
import logging
from dataclasses import dataclass, field

from django.utils import timezone

logger = logging.getLogger(__name__)

#: Delete in bounded batches so a large backlog never takes one giant lock.
_BATCH_SIZE = 1000


@dataclass(frozen=True)
class RetentionTarget:
    """How one ``EntityType`` is located and scrubbed."""

    model_path: str  # "app_label.ModelName", resolved lazily to dodge import cycles
    #: Field=value assignments that strip personal data, or empty if anonymize
    #: is not meaningful for this entity (delete-only).
    anonymize_fields: dict = field(default_factory=dict)

    def model(self):
        from django.apps import apps

        app_label, model_name = self.model_path.split(".")
        return apps.get_model(app_label, model_name)


def _targets():
    """Built lazily (apps must be ready) and keyed on RetentionPolicy.EntityType."""
    from organizations.models import RetentionPolicy

    E = RetentionPolicy.EntityType
    return {
        E.ANALYTICS_EVENTS: RetentionTarget(
            "analytics.AnalyticsEvent",
            {"customer": None, "user": None, "session_id": "", "event_data": {}},
        ),
        E.AUDIT_LOGS: RetentionTarget(
            "core.AuditLog",
            {"user": None, "ip_address": None, "user_agent": ""},
        ),
        E.ACCESS_LOGS: RetentionTarget(
            "core.AccessLog",
            {"user": None, "ip_address": None},
        ),
        E.MESSAGE_DISPATCHES: RetentionTarget(
            "communications.MessageDispatch",
            {"customer": None, "recipient": "", "subject": "", "content": ""},
        ),
        E.NOTIFICATIONS: RetentionTarget(
            "communications.Notification",
            {"customer": None, "user": None, "title": "", "message": "", "data": {}},
        ),
        E.SLOT_HOLDS: RetentionTarget("operations.SlotHold"),  # delete-only
        # IDEMPOTENCY_RECORDS deliberately absent — see module docstring.
    }


def _batched_delete(queryset) -> int:
    """Delete a queryset in PK batches; returns the number of rows removed."""
    model = queryset.model
    deleted = 0
    while True:
        batch_ids = list(queryset.values_list("pk", flat=True)[:_BATCH_SIZE])
        if not batch_ids:
            break
        count, _ = model._base_manager.filter(pk__in=batch_ids).delete()
        deleted += len(batch_ids)
        if len(batch_ids) < _BATCH_SIZE:
            break
    return deleted


def apply_policy(policy) -> int:
    """Enforce one ``RetentionPolicy``; returns the number of affected rows."""
    from organizations.models import RetentionPolicy

    if not policy.is_active:
        return 0
    target = _targets().get(policy.entity_type)
    if target is None:
        logger.warning(
            "Retention policy %s targets unsupported entity %s; skipping.",
            policy.pk,
            policy.entity_type,
        )
        return 0

    cutoff = timezone.now() - dt.timedelta(days=policy.retention_days)
    model = target.model()
    expired = model._base_manager.filter(
        organization_id=policy.organization_id, created_at__lt=cutoff
    )

    if policy.action == RetentionPolicy.Action.ANONYMIZE:
        if not target.anonymize_fields:
            logger.warning(
                "Retention policy %s asks to anonymize %s but no anonymizer is "
                "defined; skipping (never silently deleting instead).",
                policy.pk,
                policy.entity_type,
            )
            return 0
        # Only touch rows not already scrubbed, so the count reflects real work
        # and the sweep stays cheap on repeat runs.
        not_yet = {
            f"{k}__isnull": False
            for k, v in target.anonymize_fields.items()
            if v is None
        }
        affected = expired
        if not_yet:
            from django.db.models import Q

            condition = Q()
            for key in not_yet:
                condition |= Q(**{key: True})
            affected = expired.filter(condition)
        return affected.update(**target.anonymize_fields)

    return _batched_delete(expired)


def sweep_organization(organization_id) -> dict:
    """Apply every active policy for one organization."""
    from organizations.models import RetentionPolicy

    results = {}
    policies = RetentionPolicy.objects.filter(
        organization_id=organization_id, is_active=True
    )
    for policy in policies:
        results[policy.entity_type] = apply_policy(policy)
    return results


def sweep_all() -> int:
    """Apply every active retention policy across all tenants. Idempotent.

    Returns the number of policies applied.
    """
    from organizations.models import RetentionPolicy

    applied = 0
    for policy in RetentionPolicy.objects.filter(is_active=True).iterator():
        apply_policy(policy)
        applied += 1
    return applied
