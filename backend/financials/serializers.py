from rest_framework import serializers

from core.api import AUDIT_FIELDS
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


class DocumentSequenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentSequence
        fields = "__all__"
        read_only_fields = (*AUDIT_FIELDS, "current_number")


class InvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = "__all__"
        # invoice_number is allocated server-side from DocumentSequence.
        read_only_fields = (
            *AUDIT_FIELDS,
            "invoice_number",
            "amount_paid",
            "amount_due",
        )


class CreditNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreditNote
        fields = "__all__"
        read_only_fields = (*AUDIT_FIELDS, "credit_note_number")


class DebitNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = DebitNote
        fields = "__all__"
        read_only_fields = (*AUDIT_FIELDS, "debit_note_number")


class PaymentIntentSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentIntent
        fields = "__all__"
        read_only_fields = (*AUDIT_FIELDS, "gateway_intent_id")


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = "__all__"
        read_only_fields = AUDIT_FIELDS


class RefundSerializer(serializers.ModelSerializer):
    class Meta:
        model = Refund
        fields = "__all__"
        read_only_fields = AUDIT_FIELDS


class PaymentWebhookEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentWebhookEvent
        fields = "__all__"


class SettlementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Settlement
        fields = "__all__"


class SettlementLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = SettlementLine
        fields = "__all__"


class LedgerAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = LedgerAccount
        fields = "__all__"
        read_only_fields = (*AUDIT_FIELDS, "is_system")


class LedgerEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = LedgerEntry
        fields = "__all__"
        # transaction_id groups a balanced set of lines and is assigned by the
        # posting service, never by the client.
        read_only_fields = (*AUDIT_FIELDS, "transaction_id")


class ZatcaDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ZatcaDevice
        # Key material and CSID credentials never cross the API in either
        # direction; the onboarding pipeline is their only writer.
        exclude = ("private_key_encrypted", "csid_secret_encrypted")
        read_only_fields = (
            *AUDIT_FIELDS,
            "compliance_csid",
            "production_csid",
            "certificate",
            "compliance_request_id",
            "status",
            "onboarded_at",
        )


class ZatcaCounterSerializer(serializers.ModelSerializer):
    class Meta:
        model = ZatcaCounter
        fields = "__all__"


class EInvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = EInvoice
        fields = "__all__"


class EInvoiceSubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = EInvoiceSubmission
        fields = "__all__"


class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = "__all__"


class PlanEntitlementSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlanEntitlement
        fields = "__all__"


class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = "__all__"
        read_only_fields = AUDIT_FIELDS


class SubscriptionInvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionInvoice
        fields = "__all__"


class UsageRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = UsageRecord
        fields = "__all__"


class DunningAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = DunningAttempt
        fields = "__all__"
