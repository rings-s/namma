<<<<<<< HEAD
from django.db import models

# Create your models here.
=======
"""Financials: invoicing, payments, ledger, ZATCA e-invoicing,
SaaS plans/subscriptions and dunning."""

from django.conf import settings
from django.db import models
from django.utils import timezone

from core.models import BaseModel


class PaymentMethod(models.TextChoices):
    CASH = "cash", "Cash"
    CARD = "card", "Card"
    MADA = "mada", "mada"
    APPLE_PAY = "apple_pay", "Apple Pay"
    STC_PAY = "stc_pay", "STC Pay"
    BANK_TRANSFER = "bank_transfer", "Bank Transfer"
    WALLET = "wallet", "Wallet"


class Gateway(models.TextChoices):
    MOYASAR = "moyasar", "Moyasar"
    TAP = "tap", "Tap"
    HYPERPAY = "hyperpay", "HyperPay"
    STRIPE = "stripe", "Stripe"
    MANUAL = "manual", "Manual"


# ---------------------------------------------------------------------------
# Document numbering & invoices
# ---------------------------------------------------------------------------

class DocumentSequence(BaseModel):
    class DocumentType(models.TextChoices):
        INVOICE = "invoice", "Invoice"
        CREDIT_NOTE = "credit_note", "Credit Note"
        DEBIT_NOTE = "debit_note", "Debit Note"
        SALE = "sale", "Sale"
        BOOKING = "booking", "Booking"
        TICKET = "ticket", "Ticket"

    organization = models.ForeignKey(
        "organnizations.Organization",
        on_delete=models.CASCADE,
        related_name="document_sequences",
    )
    branch = models.ForeignKey(
        "organnizations.Branch",
        on_delete=models.CASCADE,
        related_name="document_sequences",
        null=True,
        blank=True,
    )
    document_type = models.CharField(max_length=20, choices=DocumentType.choices)
    year = models.PositiveIntegerField()
    prefix = models.CharField(max_length=20, blank=True)
    current_number = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "branch", "document_type", "year"],
                name="uniq_document_sequence",
            )
        ]

    def __str__(self):
        return f"{self.get_document_type_display()} {self.year} ({self.prefix}{self.current_number})"


class Invoice(BaseModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ISSUED = "issued", "Issued"
        PARTIALLY_PAID = "partially_paid", "Partially Paid"
        PAID = "paid", "Paid"
        OVERDUE = "overdue", "Overdue"
        VOID = "void", "Void"

    organization = models.ForeignKey(
        "organnizations.Organization",
        on_delete=models.CASCADE,
        related_name="invoices",
    )
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.SET_NULL,
        related_name="invoices",
        null=True,
        blank=True,
    )
    sale = models.OneToOneField(
        "commerce.Sale",
        on_delete=models.SET_NULL,
        related_name="invoice",
        null=True,
        blank=True,
    )
    invoice_number = models.CharField(max_length=50, unique=True)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    amount_due = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    due_date = models.DateField(null=True, blank=True)
    issued_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["organization", "created_at"]),
        ]

    def __str__(self):
        return self.invoice_number


class CreditNote(BaseModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ISSUED = "issued", "Issued"
        VOID = "void", "Void"

    organization = models.ForeignKey(
        "organnizations.Organization",
        on_delete=models.CASCADE,
        related_name="credit_notes",
    )
    original_invoice = models.ForeignKey(
        Invoice, on_delete=models.CASCADE, related_name="credit_notes"
    )
    credit_note_number = models.CharField(max_length=50, unique=True)
    reason_code = models.CharField(max_length=50, blank=True)
    reason_text = models.TextField(blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    issued_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.credit_note_number


class DebitNote(BaseModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ISSUED = "issued", "Issued"
        VOID = "void", "Void"

    organization = models.ForeignKey(
        "organnizations.Organization",
        on_delete=models.CASCADE,
        related_name="debit_notes",
    )
    original_invoice = models.ForeignKey(
        Invoice, on_delete=models.CASCADE, related_name="debit_notes"
    )
    debit_note_number = models.CharField(max_length=50, unique=True)
    reason_code = models.CharField(max_length=50, blank=True)
    reason_text = models.TextField(blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    issued_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.debit_note_number


# ---------------------------------------------------------------------------
# Payments
# ---------------------------------------------------------------------------

class PaymentIntent(BaseModel):
    class Status(models.TextChoices):
        REQUIRES_PAYMENT = "requires_payment", "Requires Payment"
        PROCESSING = "processing", "Processing"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"
        EXPIRED = "expired", "Expired"

    organization = models.ForeignKey(
        "organnizations.Organization",
        on_delete=models.CASCADE,
        related_name="payment_intents",
    )
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.SET_NULL,
        related_name="payment_intents",
        null=True,
        blank=True,
    )
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.SET_NULL,
        related_name="payment_intents",
        null=True,
        blank=True,
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="SAR")
    payment_method = models.CharField(
        max_length=20, choices=PaymentMethod.choices, blank=True
    )
    gateway = models.CharField(
        max_length=20, choices=Gateway.choices, default=Gateway.MANUAL
    )
    gateway_intent_id = models.CharField(max_length=255, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.REQUIRES_PAYMENT
    )
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "status"]),
        ]

    def __str__(self):
        return f"Intent {self.amount} {self.currency} ({self.get_status_display()})"


class Payment(BaseModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        REFUNDED = "refunded", "Refunded"
        PARTIALLY_REFUNDED = "partially_refunded", "Partially Refunded"

    organization = models.ForeignKey(
        "organnizations.Organization",
        on_delete=models.CASCADE,
        related_name="payments",
    )
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.SET_NULL,
        related_name="payments",
        null=True,
        blank=True,
    )
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.SET_NULL,
        related_name="payments",
        null=True,
        blank=True,
    )
    payment_method = models.CharField(
        max_length=20, choices=PaymentMethod.choices, default=PaymentMethod.CASH
    )
    gateway = models.CharField(
        max_length=20, choices=Gateway.choices, default=Gateway.MANUAL
    )
    gateway_transaction_id = models.CharField(max_length=255, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="SAR")
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    paid_at = models.DateTimeField(null=True, blank=True)
    refunded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "created_at"]),
            models.Index(fields=["organization", "status"]),
        ]

    def __str__(self):
        return f"Payment {self.amount} {self.currency} ({self.get_status_display()})"


class Refund(BaseModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        PROCESSED = "processed", "Processed"
        REJECTED = "rejected", "Rejected"

    class RefundType(models.TextChoices):
        FULL = "full", "Full"
        PARTIAL = "partial", "Partial"

    organization = models.ForeignKey(
        "organnizations.Organization",
        on_delete=models.CASCADE,
        related_name="refunds",
    )
    payment = models.ForeignKey(
        Payment, on_delete=models.CASCADE, related_name="refunds"
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reason = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    refunded_at = models.DateTimeField(null=True, blank=True)
    refund_type = models.CharField(
        max_length=10, choices=RefundType.choices, default=RefundType.FULL
    )
    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="+",
        null=True,
        blank=True,
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Refund {self.amount} for {self.payment}"


class PaymentWebhookEvent(BaseModel):
    class ProcessingStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSED = "processed", "Processed"
        FAILED = "failed", "Failed"
        IGNORED = "ignored", "Ignored"

    organization = models.ForeignKey(
        "organnizations.Organization",
        on_delete=models.CASCADE,
        related_name="payment_webhook_events",
        null=True,
        blank=True,
    )
    gateway = models.CharField(max_length=20, choices=Gateway.choices)
    gateway_event_id = models.CharField(max_length=255, unique=True)
    event_type = models.CharField(max_length=100)
    payload = models.JSONField(default=dict, blank=True)
    processing_status = models.CharField(
        max_length=20, choices=ProcessingStatus.choices, default=ProcessingStatus.PENDING
    )
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.gateway}:{self.gateway_event_id}"


class Settlement(BaseModel):
    organization = models.ForeignKey(
        "organnizations.Organization",
        on_delete=models.CASCADE,
        related_name="settlements",
    )
    gateway = models.CharField(max_length=20, choices=Gateway.choices)
    settlement_reference = models.CharField(max_length=255)
    gross_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    gateway_fees = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default="SAR")
    settled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Settlement {self.settlement_reference}"


class SettlementLine(BaseModel):
    settlement = models.ForeignKey(
        Settlement, on_delete=models.CASCADE, related_name="lines"
    )
    payment = models.ForeignKey(
        Payment,
        on_delete=models.SET_NULL,
        related_name="settlement_lines",
        null=True,
        blank=True,
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    fee = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.settlement} line {self.amount}"


# ---------------------------------------------------------------------------
# Ledger
# ---------------------------------------------------------------------------

class LedgerAccount(BaseModel):
    class AccountType(models.TextChoices):
        ASSET = "asset", "Asset"
        LIABILITY = "liability", "Liability"
        EQUITY = "equity", "Equity"
        REVENUE = "revenue", "Revenue"
        EXPENSE = "expense", "Expense"

    organization = models.ForeignKey(
        "organnizations.Organization",
        on_delete=models.CASCADE,
        related_name="ledger_accounts",
    )
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=255)
    account_type = models.CharField(max_length=20, choices=AccountType.choices)
    is_system = models.BooleanField(default=False)

    class Meta:
        ordering = ["code"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "code"], name="uniq_ledger_account_code"
            )
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"


class LedgerEntry(BaseModel):
    organization = models.ForeignKey(
        "organnizations.Organization",
        on_delete=models.CASCADE,
        related_name="ledger_entries",
    )
    transaction_id = models.UUIDField()
    account = models.ForeignKey(
        LedgerAccount, on_delete=models.PROTECT, related_name="entries"
    )
    debit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    credit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default="SAR")
    description = models.TextField(blank=True)
    reference_type = models.CharField(max_length=100, blank=True)
    reference_id = models.UUIDField(null=True, blank=True)
    posted_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name_plural = "ledger entries"
        ordering = ["-posted_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(debit__gte=0), name="ledger_entry_debit_gte_0"
            ),
            models.CheckConstraint(
                condition=models.Q(credit__gte=0), name="ledger_entry_credit_gte_0"
            ),
        ]
        indexes = [
            models.Index(fields=["organization", "posted_at"]),
            models.Index(fields=["account", "posted_at"]),
            models.Index(fields=["transaction_id"]),
        ]

    def __str__(self):
        return f"{self.account} D{self.debit}/C{self.credit}"


# ---------------------------------------------------------------------------
# ZATCA e-invoicing
# ---------------------------------------------------------------------------

class ZatcaDevice(BaseModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ONBOARDED = "onboarded", "Onboarded"
        ACTIVE = "active", "Active"
        SUSPENDED = "suspended", "Suspended"
        REVOKED = "revoked", "Revoked"

    organization = models.ForeignKey(
        "organnizations.Organization",
        on_delete=models.CASCADE,
        related_name="zatca_devices",
    )
    branch = models.ForeignKey(
        "organnizations.Branch",
        on_delete=models.SET_NULL,
        related_name="zatca_devices",
        null=True,
        blank=True,
    )
    device_name = models.CharField(max_length=255)
    compliance_csid = models.CharField(max_length=255, blank=True)
    production_csid = models.CharField(max_length=255, blank=True)
    certificate = models.TextField(blank=True)
    private_key_encrypted = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    onboarded_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.device_name


class ZatcaCounter(BaseModel):
    zatca_device = models.OneToOneField(
        ZatcaDevice, on_delete=models.CASCADE, related_name="counter"
    )
    current_icv = models.PositiveIntegerField(default=0)
    last_invoice_hash = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"Counter for {self.zatca_device} (ICV {self.current_icv})"


class EInvoice(BaseModel):
    class InvoiceType(models.TextChoices):
        STANDARD = "standard", "Standard"
        SIMPLIFIED = "simplified", "Simplified"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        REPORTED = "reported", "Reported"
        CLEARED = "cleared", "Cleared"
        REJECTED = "rejected", "Rejected"
        FAILED = "failed", "Failed"

    organization = models.ForeignKey(
        "organnizations.Organization",
        on_delete=models.CASCADE,
        related_name="e_invoices",
    )
    invoice = models.ForeignKey(
        Invoice, on_delete=models.CASCADE, related_name="e_invoices"
    )
    zatca_device = models.ForeignKey(
        ZatcaDevice,
        on_delete=models.SET_NULL,
        related_name="e_invoices",
        null=True,
        blank=True,
    )
    uuid = models.CharField(max_length=64, unique=True)
    invoice_type = models.CharField(
        max_length=20, choices=InvoiceType.choices, default=InvoiceType.SIMPLIFIED
    )
    ubl_xml_url = models.URLField(blank=True)
    cryptographic_stamp = models.TextField(blank=True)
    qr_code_tlv = models.TextField(blank=True)
    previous_invoice_hash = models.CharField(max_length=255, blank=True)
    icv = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "status"]),
        ]

    def __str__(self):
        return f"E-Invoice {self.uuid}"


class EInvoiceSubmission(BaseModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SUBMITTED = "submitted", "Submitted"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"
        FAILED = "failed", "Failed"

    e_invoice = models.ForeignKey(
        EInvoice, on_delete=models.CASCADE, related_name="submissions"
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    api_response = models.JSONField(default=dict, blank=True)
    retry_count = models.PositiveIntegerField(default=0)
    submitted_at = models.DateTimeField(null=True, blank=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Submission for {self.e_invoice} ({self.get_status_display()})"


# ---------------------------------------------------------------------------
# SaaS plans, subscriptions & billing
# ---------------------------------------------------------------------------

class Plan(BaseModel):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    price_monthly = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    price_yearly = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["price_monthly"]

    def __str__(self):
        return self.name


class PlanEntitlement(BaseModel):
    plan = models.ForeignKey(
        Plan, on_delete=models.CASCADE, related_name="entitlements"
    )
    feature_key = models.CharField(max_length=100)
    limit_value = models.IntegerField(null=True, blank=True)
    is_enabled = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["plan", "feature_key"], name="uniq_plan_feature"
            )
        ]

    def __str__(self):
        return f"{self.plan} - {self.feature_key}"


class Subscription(BaseModel):
    class BillingCycle(models.TextChoices):
        MONTHLY = "monthly", "Monthly"
        YEARLY = "yearly", "Yearly"

    class Status(models.TextChoices):
        TRIALING = "trialing", "Trialing"
        ACTIVE = "active", "Active"
        PAST_DUE = "past_due", "Past Due"
        CANCELLED = "cancelled", "Cancelled"
        EXPIRED = "expired", "Expired"

    organization = models.ForeignKey(
        "organnizations.Organization",
        on_delete=models.CASCADE,
        related_name="subscriptions",
    )
    plan = models.ForeignKey(
        Plan, on_delete=models.PROTECT, related_name="subscriptions"
    )
    billing_cycle = models.CharField(
        max_length=10, choices=BillingCycle.choices, default=BillingCycle.MONTHLY
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.TRIALING
    )
    trial_ends_at = models.DateTimeField(null=True, blank=True)
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "status"]),
        ]

    def __str__(self):
        return f"{self.organization} on {self.plan} ({self.get_status_display()})"


class SubscriptionInvoice(BaseModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        FAILED = "failed", "Failed"
        VOID = "void", "Void"

    subscription = models.ForeignKey(
        Subscription, on_delete=models.CASCADE, related_name="invoices"
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    due_date = models.DateField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Subscription invoice {self.amount} ({self.get_status_display()})"


class UsageRecord(BaseModel):
    organization = models.ForeignKey(
        "organnizations.Organization",
        on_delete=models.CASCADE,
        related_name="usage_records",
    )
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.SET_NULL,
        related_name="usage_records",
        null=True,
        blank=True,
    )
    feature_key = models.CharField(max_length=100)
    quantity = models.PositiveIntegerField(default=0)
    recorded_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-recorded_at"]
        indexes = [
            models.Index(fields=["organization", "feature_key", "recorded_at"]),
        ]

    def __str__(self):
        return f"{self.organization} {self.feature_key} x {self.quantity}"


class DunningAttempt(BaseModel):
    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        ATTEMPTED = "attempted", "Attempted"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"

    subscription = models.ForeignKey(
        Subscription, on_delete=models.CASCADE, related_name="dunning_attempts"
    )
    attempt_number = models.PositiveIntegerField(default=1)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.SCHEDULED
    )
    next_attempt_at = models.DateTimeField(null=True, blank=True)
    grace_period_ends_at = models.DateTimeField(null=True, blank=True)
    attempted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Dunning #{self.attempt_number} for {self.subscription}"
>>>>>>> a3235b4 (feat(db): initialize core relational schema)
