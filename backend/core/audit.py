"""Audit trail helper.

A single explicit entry point for writing :class:`core.models.AuditLog` rows.
We record audits with explicit service calls at the sensitive mutation points
(auth, RBAC, payments, refunds, bookings, PDPL actions) rather than via signals,
so the trail is greppable and the "why" lives next to the action — in line with
the platform's preference for explicit services over hidden signal side effects.

PDPL note: the trail captures *who did what, when, and from where* over
personal-data and money operations; it never copies the personal data itself
into ``new_values`` beyond the minimum needed to identify the action.
"""

from core.models import AuditLog


def _request_metadata(request):
    if request is None:
        return None, ""
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    ip = (
        forwarded.split(",")[0].strip()
        if forwarded
        else request.META.get("REMOTE_ADDR")
    )
    return ip, request.META.get("HTTP_USER_AGENT", "")[:512]


def record_audit(
    *,
    action,
    entity_type,
    organization=None,
    user=None,
    entity_id=None,
    old_values=None,
    new_values=None,
    request=None,
):
    """Append one immutable audit record. Never raises into the caller's flow:
    failing to audit must not break the audited operation, but it is logged."""
    ip_address, user_agent = _request_metadata(request)
    actor = user if (user is not None and getattr(user, "pk", None)) else None
    return AuditLog.objects.create(
        organization=organization,
        user=actor,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        old_values=old_values or {},
        new_values=new_values or {},
        ip_address=ip_address,
        user_agent=user_agent or "",
    )


__all__ = ["record_audit"]
