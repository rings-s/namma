<<<<<<< HEAD
from django.shortcuts import render

# Create your views here.
=======
from rest_framework import mixins, permissions, viewsets

from core.api import TenantScopedQuerysetMixin, TenantScopedReadOnlyViewSet, TenantScopedViewSet
from financials import serializers
from financials.models import (
    CreditNote,
    DebitNote,
    DocumentSequence,
    DunningAttempt,
    EInvoice,
    EInvoiceSubmission,
    Invoice,
    LedgerAccount,
    LedgerEntry,
    Payment,
    PaymentIntent,
    PaymentWebhookEvent,
    Plan,
    PlanEntitlement,
    Refund,
    Settlement,
    SettlementLine,
    Subscription,
    SubscriptionInvoice,
    UsageRecord,
    ZatcaCounter,
    ZatcaDevice,
)


class DocumentSequenceViewSet(TenantScopedViewSet):
    queryset = DocumentSequence.objects.select_related("branch")
    serializer_class = serializers.DocumentSequenceSerializer


class InvoiceViewSet(TenantScopedViewSet):
    queryset = Invoice.objects.select_related("customer", "sale")
    serializer_class = serializers.InvoiceSerializer
    search_fields = ["invoice_number"]
    ordering_fields = ["issued_at", "due_date", "total_amount", "created_at"]


class CreditNoteViewSet(TenantScopedViewSet):
    queryset = CreditNote.objects.select_related("original_invoice")
    serializer_class = serializers.CreditNoteSerializer
    search_fields = ["credit_note_number"]


class DebitNoteViewSet(TenantScopedViewSet):
    queryset = DebitNote.objects.select_related("original_invoice")
    serializer_class = serializers.DebitNoteSerializer
    search_fields = ["debit_note_number"]


class PaymentIntentViewSet(TenantScopedViewSet):
    queryset = PaymentIntent.objects.select_related("customer", "invoice")
    serializer_class = serializers.PaymentIntentSerializer


class PaymentViewSet(TenantScopedViewSet):
    queryset = Payment.objects.select_related("invoice", "customer")
    serializer_class = serializers.PaymentSerializer
    search_fields = ["gateway_transaction_id"]
    ordering_fields = ["paid_at", "created_at", "amount"]


class RefundViewSet(TenantScopedViewSet):
    queryset = Refund.objects.select_related("payment", "approver")
    serializer_class = serializers.RefundSerializer


class PaymentWebhookEventViewSet(TenantScopedReadOnlyViewSet):
    # Written exclusively by gateway webhook handlers.
    queryset = PaymentWebhookEvent.objects.all()
    serializer_class = serializers.PaymentWebhookEventSerializer
    ordering_fields = ["created_at"]


class SettlementViewSet(TenantScopedReadOnlyViewSet):
    queryset = Settlement.objects.all()
    serializer_class = serializers.SettlementSerializer
    ordering_fields = ["settled_at"]


class SettlementLineViewSet(TenantScopedReadOnlyViewSet):
    queryset = SettlementLine.objects.select_related("settlement", "payment")
    serializer_class = serializers.SettlementLineSerializer
    org_field = "settlement__organization"


class LedgerAccountViewSet(TenantScopedViewSet):
    queryset = LedgerAccount.objects.all()
    serializer_class = serializers.LedgerAccountSerializer
    search_fields = ["code", "name"]


class LedgerEntryViewSet(
    TenantScopedQuerysetMixin,
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    # Double-entry journal is immutable: create and read only, never update/delete.
    queryset = LedgerEntry.objects.select_related("account")
    serializer_class = serializers.LedgerEntrySerializer
    ordering_fields = ["posted_at", "created_at"]


class ZatcaDeviceViewSet(TenantScopedViewSet):
    queryset = ZatcaDevice.objects.select_related("branch")
    serializer_class = serializers.ZatcaDeviceSerializer


class ZatcaCounterViewSet(TenantScopedReadOnlyViewSet):
    # Maintained atomically by the e-invoicing pipeline.
    queryset = ZatcaCounter.objects.select_related("zatca_device")
    serializer_class = serializers.ZatcaCounterSerializer
    org_field = "zatca_device__organization"


class EInvoiceViewSet(TenantScopedReadOnlyViewSet):
    # Generated from invoices by the ZATCA pipeline; clients only consult status.
    queryset = EInvoice.objects.select_related("invoice", "zatca_device")
    serializer_class = serializers.EInvoiceSerializer
    ordering_fields = ["created_at"]


class EInvoiceSubmissionViewSet(TenantScopedReadOnlyViewSet):
    queryset = EInvoiceSubmission.objects.select_related("e_invoice")
    serializer_class = serializers.EInvoiceSubmissionSerializer
    org_field = "e_invoice__organization"


class PlanViewSet(viewsets.ReadOnlyModelViewSet):
    """Platform plan catalog — global, managed by Namaa staff via admin."""

    queryset = Plan.objects.filter(is_active=True)
    serializer_class = serializers.PlanSerializer
    permission_classes = [permissions.IsAuthenticated]


class PlanEntitlementViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PlanEntitlement.objects.select_related("plan")
    serializer_class = serializers.PlanEntitlementSerializer
    permission_classes = [permissions.IsAuthenticated]


class SubscriptionViewSet(TenantScopedReadOnlyViewSet):
    # Lifecycle is driven by the billing service, not direct API writes.
    queryset = Subscription.objects.select_related("plan")
    serializer_class = serializers.SubscriptionSerializer


class SubscriptionInvoiceViewSet(TenantScopedReadOnlyViewSet):
    queryset = SubscriptionInvoice.objects.select_related("subscription")
    serializer_class = serializers.SubscriptionInvoiceSerializer
    org_field = "subscription__organization"


class UsageRecordViewSet(TenantScopedReadOnlyViewSet):
    queryset = UsageRecord.objects.select_related("subscription")
    serializer_class = serializers.UsageRecordSerializer


class DunningAttemptViewSet(TenantScopedReadOnlyViewSet):
    queryset = DunningAttempt.objects.select_related("subscription")
    serializer_class = serializers.DunningAttemptSerializer
    org_field = "subscription__organization"
>>>>>>> a3235b4 (feat(db): initialize core relational schema)
