from rest_framework.routers import DefaultRouter

from financials import views

router = DefaultRouter()
router.register("document-sequences", views.DocumentSequenceViewSet)
router.register("invoices", views.InvoiceViewSet)
router.register("credit-notes", views.CreditNoteViewSet)
router.register("debit-notes", views.DebitNoteViewSet)
router.register("payment-intents", views.PaymentIntentViewSet)
router.register("payments", views.PaymentViewSet)
router.register("refunds", views.RefundViewSet)
router.register("payment-webhook-events", views.PaymentWebhookEventViewSet)
router.register("settlements", views.SettlementViewSet)
router.register("settlement-lines", views.SettlementLineViewSet)
router.register("ledger-accounts", views.LedgerAccountViewSet)
router.register("ledger-entries", views.LedgerEntryViewSet)
router.register("zatca-devices", views.ZatcaDeviceViewSet)
router.register("zatca-counters", views.ZatcaCounterViewSet)
router.register("e-invoices", views.EInvoiceViewSet)
router.register("e-invoice-submissions", views.EInvoiceSubmissionViewSet)
router.register("plans", views.PlanViewSet)
router.register("plan-entitlements", views.PlanEntitlementViewSet)
router.register("subscriptions", views.SubscriptionViewSet)
router.register("subscription-invoices", views.SubscriptionInvoiceViewSet)
router.register("usage-records", views.UsageRecordViewSet)
router.register("dunning-attempts", views.DunningAttemptViewSet)

urlpatterns = router.urls
