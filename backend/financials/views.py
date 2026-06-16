import hmac

from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import generics, mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from accounts.models import UserRole
from core.api import (
    TenantScopedQuerysetMixin,
    TenantScopedReadOnlyViewSet,
    TenantScopedViewSet,
    require_org_role,
)
from financials import serializers
from financials.models import Gateway
from financials.services import (
    next_document_number,
    post_journal_entry,
    validate_e_invoice_generable,
    validate_refund_executable,
)
from financials.models import DocumentSequence as _DocumentSequence
from financials.tasks import (
    activate_zatca_device_task,
    execute_moyasar_refund_task,
    generate_and_submit_e_invoice_task,
    onboard_zatca_device_task,
    process_payment_webhook_event_task,
)
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

    def perform_create(self, serializer):
        self._check_tenant_ownership(serializer)
        organization = serializer.validated_data["organization"]
        serializer.save(
            invoice_number=next_document_number(
                organization=organization,
                document_type=_DocumentSequence.DocumentType.INVOICE,
            )
        )

    @action(detail=True, methods=["post"], url_path="einvoice")
    def einvoice(self, request, pk=None):
        """Queue ZATCA e-invoice generation + submission. Accountant+ only.

        Optional body: ``zatca_device`` (defaults to the organization's
        active device) and ``invoice_type`` (defaults to simplified).
        """
        invoice = self.get_object()
        require_org_role(
            request.user, invoice.organization_id, UserRole.Role.ACCOUNTANT
        )
        device_id = request.data.get("zatca_device")
        devices = ZatcaDevice.objects.filter(
            organization_id=invoice.organization_id,
            status=ZatcaDevice.Status.ACTIVE,
        )
        device = devices.filter(pk=device_id).first() if device_id else devices.first()
        if device is None:
            raise ValidationError(
                "No active ZATCA device is available for this organization."
            )
        try:
            validate_e_invoice_generable(invoice, device)
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages)
        generate_and_submit_e_invoice_task.delay(str(invoice.pk), str(device.pk))
        return Response({"detail": "queued"}, status=status.HTTP_202_ACCEPTED)


class CreditNoteViewSet(TenantScopedViewSet):
    queryset = CreditNote.objects.select_related("original_invoice")
    serializer_class = serializers.CreditNoteSerializer
    search_fields = ["credit_note_number"]

    def perform_create(self, serializer):
        self._check_tenant_ownership(serializer)
        serializer.save(
            credit_note_number=next_document_number(
                organization=serializer.validated_data["organization"],
                document_type=_DocumentSequence.DocumentType.CREDIT_NOTE,
            )
        )


class DebitNoteViewSet(TenantScopedViewSet):
    queryset = DebitNote.objects.select_related("original_invoice")
    serializer_class = serializers.DebitNoteSerializer
    search_fields = ["debit_note_number"]

    def perform_create(self, serializer):
        self._check_tenant_ownership(serializer)
        serializer.save(
            debit_note_number=next_document_number(
                organization=serializer.validated_data["organization"],
                document_type=_DocumentSequence.DocumentType.DEBIT_NOTE,
            )
        )


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

    @action(detail=True, methods=["post"])
    def execute(self, request, pk=None):
        """Queue a pending refund for execution at Moyasar. Manager+ only."""
        refund = self.get_object()
        require_org_role(request.user, refund.organization_id, UserRole.Role.MANAGER)
        try:
            validate_refund_executable(refund)
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages)
        execute_moyasar_refund_task.delay(str(refund.pk), str(request.user.pk))
        # 202 + the pending state is the contract: the worker hasn't run yet,
        # so re-reading the row here would only echo back the same pre-task state.
        return Response(
            serializers.RefundSerializer(refund).data, status=status.HTTP_202_ACCEPTED
        )


class MoyasarWebhookView(generics.GenericAPIView):
    """Receiver for Moyasar webhook deliveries.

    Validates the shared secret token (constant-time), stores the event
    idempotently on its gateway event id, processes it locally, and always
    answers 200 for stored events so Moyasar stops retrying.
    """

    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        secret = settings.MOYASAR_WEBHOOK_SECRET
        token = str(request.data.get("secret_token", ""))
        if not secret or not hmac.compare_digest(token, secret):
            return Response(
                {"detail": "Invalid webhook token."}, status=status.HTTP_403_FORBIDDEN
            )
        event_id = request.data.get("id")
        if not event_id:
            return Response(
                {"detail": "Missing event id."}, status=status.HTTP_400_BAD_REQUEST
            )
        payload = dict(request.data)
        payload.pop("secret_token", None)  # never persist the shared secret
        event, created = PaymentWebhookEvent.objects.get_or_create(
            gateway_event_id=str(event_id),
            defaults={
                "gateway": Gateway.MOYASAR,
                "event_type": str(request.data.get("type", "")),
                "payload": payload,
            },
        )
        if created:
            # Store fast, return fast: a worker applies the event to the
            # payment domain. The 200 stops Moyasar's retries either way.
            process_payment_webhook_event_task.delay(str(event.pk))
        return Response({"detail": "ok"})


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

    def create(self, request, *args, **kwargs):
        """Post a *balanced* journal transaction.

        Accepts a list of ledger lines (or a single line, which is rejected as
        unbalanced). All lines must target one organization the caller controls
        and total debits must equal total credits; the lines are written under
        one server-assigned transaction id. This replaces the old single-line
        create that could record half a transaction.
        """
        payload = request.data if isinstance(request.data, list) else [request.data]
        serializer = self.get_serializer(data=payload, many=True)
        serializer.is_valid(raise_exception=True)
        lines = serializer.validated_data
        if not lines:
            raise ValidationError("Provide the journal lines to post.")

        organizations = {line["organization"] for line in lines}
        if len(organizations) > 1:
            raise ValidationError(
                "All lines of a journal transaction share one organization."
            )
        organization = organizations.pop()
        org_ids = self.allowed_organization_ids()
        if org_ids is not None and organization.id not in org_ids:
            raise PermissionDenied("You do not have access to this organization.")

        try:
            entries = post_journal_entry(organization=organization, lines=lines)
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages)
        output = self.get_serializer(entries, many=True)
        return Response(output.data, status=status.HTTP_201_CREATED)


class ZatcaDeviceViewSet(TenantScopedViewSet):
    queryset = ZatcaDevice.objects.select_related("branch")
    serializer_class = serializers.ZatcaDeviceSerializer

    @action(detail=True, methods=["post"])
    def onboard(self, request, pk=None):
        """Exchange a Fatoora portal OTP for the compliance CSID. Admin+.

        The OTP is forwarded to the worker and never persisted.
        """
        device = self.get_object()
        require_org_role(request.user, device.organization_id, UserRole.Role.ADMIN)
        otp = str(request.data.get("otp", "")).strip()
        if not otp:
            raise ValidationError("An OTP from the Fatoora portal is required.")
        if device.status not in (
            ZatcaDevice.Status.PENDING,
            ZatcaDevice.Status.REVOKED,
        ):
            raise ValidationError("This device has already been onboarded.")
        onboard_zatca_device_task.delay(str(device.pk), otp)
        return Response({"detail": "queued"}, status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        """Trade the compliance CSID for the production CSID. Admin+."""
        device = self.get_object()
        require_org_role(request.user, device.organization_id, UserRole.Role.ADMIN)
        if device.status != ZatcaDevice.Status.ONBOARDED:
            raise ValidationError("The device must hold a compliance CSID first.")
        activate_zatca_device_task.delay(str(device.pk))
        return Response({"detail": "queued"}, status=status.HTTP_202_ACCEPTED)


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
