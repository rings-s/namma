"""Customer domain services: dynamic segment evaluation and the PDPL
data-subject rights flows (portability export, right-to-be-forgotten).

Erasure anonymizes rather than deletes: invoices, payments and ZATCA
documents are statutory records that must survive the customer, so PII is
blanked and the row is soft-deleted while financial history keeps its
referential integrity. The action is recorded in the consent ledger.
"""

from django.db import transaction
from django.utils import timezone

from communications.models import ConsentRecord
from core.audit import record_audit
from customers.models import (
    Customer,
    CustomerSegment,
    CustomerSegmentMembership,
)

# ---------------------------------------------------------------------------
# Dynamic segments
# ---------------------------------------------------------------------------


def evaluate_segment_queryset(segment):
    """Customers currently matching a dynamic segment's criteria. All
    criteria are optional and AND-ed; unknown keys are ignored so older
    segments survive criteria-schema growth."""
    criteria = segment.criteria or {}
    queryset = Customer.objects.filter(
        organization_id=segment.organization_id, is_active=True
    )
    if "min_visits" in criteria:
        queryset = queryset.filter(visit_count__gte=int(criteria["min_visits"]))
    if "min_total_spent" in criteria:
        queryset = queryset.filter(total_spent__gte=criteria["min_total_spent"])
    if "last_visit_within_days" in criteria:
        cutoff = timezone.now() - timezone.timedelta(
            days=int(criteria["last_visit_within_days"])
        )
        queryset = queryset.filter(last_visit_at__gte=cutoff)
    if "last_visit_not_within_days" in criteria:
        cutoff = timezone.now() - timezone.timedelta(
            days=int(criteria["last_visit_not_within_days"])
        )
        queryset = queryset.filter(last_visit_at__lt=cutoff)
    if "source" in criteria:
        queryset = queryset.filter(source=criteria["source"])
    if "gender" in criteria:
        queryset = queryset.filter(gender=criteria["gender"])
    return queryset


@transaction.atomic
def converge_segment_membership(segment, matching_ids):
    """Make ``segment``'s membership exactly ``matching_ids``. Idempotent —
    the end state always equals the supplied set, however often it runs.
    Shared by dynamic refresh and the AI segment pipeline."""
    matching_ids = set(matching_ids)
    current_ids = set(segment.memberships.values_list("customer_id", flat=True))
    segment.memberships.filter(customer_id__in=current_ids - matching_ids).delete()
    CustomerSegmentMembership.objects.bulk_create(
        CustomerSegmentMembership(segment=segment, customer_id=customer_id)
        for customer_id in matching_ids - current_ids
    )
    segment.last_refreshed_at = timezone.now()
    segment.save(update_fields=["last_refreshed_at", "updated_at"])
    return segment


def refresh_segment(segment):
    """Re-evaluate one dynamic segment's membership against its criteria."""
    if segment.segment_type != CustomerSegment.SegmentType.DYNAMIC:
        return segment
    matching_ids = evaluate_segment_queryset(segment).values_list("id", flat=True)
    return converge_segment_membership(segment, matching_ids)


# ---------------------------------------------------------------------------
# PDPL data-subject rights
# ---------------------------------------------------------------------------


def export_customer_data(customer):
    """Portability export: every domain's data about one customer, as a
    JSON-serializable dict. Clinical note content stays encrypted — it is
    released through the clinical access flow, not the bulk export."""
    preferences = getattr(customer, "preferences", None)
    return {
        "profile": {
            "first_name": customer.first_name,
            "last_name": customer.last_name,
            "email": customer.email,
            "phone": customer.phone,
            "gender": customer.gender,
            "date_of_birth": customer.date_of_birth.isoformat()
            if customer.date_of_birth
            else None,
            "address": customer.address,
            "city": customer.city,
            "source": customer.source,
            "loyalty_points": customer.loyalty_points,
            "total_spent": str(customer.total_spent),
            "visit_count": customer.visit_count,
            "created_at": customer.created_at.isoformat(),
        },
        "preferences": {
            "communication_channel": preferences.communication_channel,
            "marketing_opt_in": preferences.marketing_opt_in,
            "reminder_opt_in": preferences.reminder_opt_in,
        }
        if preferences
        else None,
        "consents": list(
            ConsentRecord.objects.filter(customer=customer).values(
                "channel", "purpose", "granted_at", "revoked_at", "source", "created_at"
            )
        ),
        "appointments": list(
            customer.appointments.values(
                "id", "scheduled_at", "duration_minutes", "status", "created_at"
            )
        ),
        "invoices": list(
            customer.invoices.values(
                "invoice_number", "total_amount", "status", "issued_at"
            )
        ),
        "payments": list(
            customer.payments.values("amount", "currency", "status", "paid_at")
        ),
        "loyalty_transactions": list(
            customer.loyalty_transactions.values(
                "points", "type", "description", "created_at"
            )
        ),
        "survey_responses": list(
            customer.survey_responses.values(
                "score", "comment", "sentiment", "responded_at"
            )
        ),
        "segments": list(
            customer.segment_memberships.values_list("segment__name", flat=True)
        ),
    }


@transaction.atomic
def erase_customer(customer, requested_by=None):
    """Right-to-be-forgotten: blank PII, drop marketing artifacts, keep
    statutory financial records (anonymized), soft-delete the profile and
    append the erasure to the consent ledger."""
    erased_label = f"Erased Customer {str(customer.pk)[:8]}"

    # Marketing artifacts have no statutory basis — remove them outright.
    customer.segment_memberships.all().delete()
    if hasattr(customer, "preferences"):
        try:
            customer.preferences.delete()
        except Customer.preferences.RelatedObjectDoesNotExist:
            pass

    for channel in ("sms", "email", "whatsapp"):
        ConsentRecord.objects.create(
            organization=customer.organization,
            customer=customer,
            channel=channel,
            purpose=ConsentRecord.Purpose.MARKETING,
            source="pdpl_erasure",
            revoked_at=timezone.now(),
        )

    customer.first_name = erased_label
    customer.last_name = ""
    customer.email = ""
    customer.phone = ""
    customer.gender = ""
    customer.date_of_birth = None
    customer.address = ""
    customer.city = ""
    customer.notes = ""
    customer.is_active = False
    customer.save(
        update_fields=[
            "first_name",
            "last_name",
            "email",
            "phone",
            "gender",
            "date_of_birth",
            "address",
            "city",
            "notes",
            "is_active",
            "updated_at",
        ]
    )
    customer.delete()  # soft delete — financial FKs stay intact
    record_audit(
        action="pdpl.customer_erased",
        entity_type="Customer",
        entity_id=customer.pk,
        organization=customer.organization,
        user=requested_by,
        new_values={"label": erased_label},
    )
    return customer


__all__ = [
    "converge_segment_membership",
    "erase_customer",
    "evaluate_segment_queryset",
    "export_customer_data",
    "refresh_segment",
]
