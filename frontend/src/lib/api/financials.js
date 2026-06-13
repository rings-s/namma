/** @param {import('./client.js').createClient extends (...args: any[]) => infer R ? R : never} client */
export function financialsApi(client) {
  return {
    // ── Document Sequences ──────────────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    listDocumentSequences: (params) => client.get('/api/v1/document-sequences/', { params }),
    /** @param {unknown} data */
    createDocumentSequence: (data) => client.post('/api/v1/document-sequences/', data),
    /** @param {string|number} id @param {unknown} data */
    updateDocumentSequence: (id, data) => client.patch(`/api/v1/document-sequences/${id}/`, data),
    /** @param {string|number} id */
    deleteDocumentSequence: (id) => client.delete(`/api/v1/document-sequences/${id}/`),

    // ── Invoices ────────────────────────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    listInvoices: (params) => client.get('/api/v1/invoices/', { params }),
    /** @param {unknown} data */
    createInvoice: (data) => client.post('/api/v1/invoices/', data),
    /** @param {string|number} id */
    getInvoice: (id) => client.get(`/api/v1/invoices/${id}/`),
    /** @param {string|number} id @param {unknown} data */
    updateInvoice: (id, data) => client.patch(`/api/v1/invoices/${id}/`, data),
    /** @param {string|number} id */
    deleteInvoice: (id) => client.delete(`/api/v1/invoices/${id}/`),
    /** @param {string|number} id */
    generateEInvoice: (id) => client.post(`/api/v1/invoices/${id}/einvoice/`),

    // ── Credit & Debit Notes ────────────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    listCreditNotes: (params) => client.get('/api/v1/credit-notes/', { params }),
    /** @param {unknown} data */
    createCreditNote: (data) => client.post('/api/v1/credit-notes/', data),
    /** @param {string|number} id @param {unknown} data */
    updateCreditNote: (id, data) => client.patch(`/api/v1/credit-notes/${id}/`, data),
    /** @param {string|number} id */
    deleteCreditNote: (id) => client.delete(`/api/v1/credit-notes/${id}/`),
    /** @param {Record<string,string|number|boolean>} [params] */
    listDebitNotes: (params) => client.get('/api/v1/debit-notes/', { params }),
    /** @param {unknown} data */
    createDebitNote: (data) => client.post('/api/v1/debit-notes/', data),
    /** @param {string|number} id @param {unknown} data */
    updateDebitNote: (id, data) => client.patch(`/api/v1/debit-notes/${id}/`, data),
    /** @param {string|number} id */
    deleteDebitNote: (id) => client.delete(`/api/v1/debit-notes/${id}/`),

    // ── Payment Intents ─────────────────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    listPaymentIntents: (params) => client.get('/api/v1/payment-intents/', { params }),
    /** @param {unknown} data */
    createPaymentIntent: (data) => client.post('/api/v1/payment-intents/', data),
    /** @param {string|number} id */
    getPaymentIntent: (id) => client.get(`/api/v1/payment-intents/${id}/`),
    /** @param {string|number} id @param {unknown} data */
    updatePaymentIntent: (id, data) => client.patch(`/api/v1/payment-intents/${id}/`, data),
    /** @param {string|number} id */
    deletePaymentIntent: (id) => client.delete(`/api/v1/payment-intents/${id}/`),

    // ── Payments ────────────────────────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    listPayments: (params) => client.get('/api/v1/payments/', { params }),
    /** @param {unknown} data */
    createPayment: (data) => client.post('/api/v1/payments/', data),
    /** @param {string|number} id */
    getPayment: (id) => client.get(`/api/v1/payments/${id}/`),
    /** @param {string|number} id @param {unknown} data */
    updatePayment: (id, data) => client.patch(`/api/v1/payments/${id}/`, data),
    /** @param {string|number} id */
    deletePayment: (id) => client.delete(`/api/v1/payments/${id}/`),

    // ── Refunds ─────────────────────────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    listRefunds: (params) => client.get('/api/v1/refunds/', { params }),
    /** @param {unknown} data */
    createRefund: (data) => client.post('/api/v1/refunds/', data),
    /** @param {string|number} id @param {unknown} data */
    updateRefund: (id, data) => client.patch(`/api/v1/refunds/${id}/`, data),
    /** @param {string|number} id */
    executeRefund: (id) => client.post(`/api/v1/refunds/${id}/execute/`),

    // ── Webhook Events ──────────────────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    listWebhookEvents: (params) => client.get('/api/v1/payment-webhook-events/', { params }),

    // ── Settlements ─────────────────────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    listSettlements: (params) => client.get('/api/v1/settlements/', { params }),
    /** @param {Record<string,string|number|boolean>} [params] */
    listSettlementLines: (params) => client.get('/api/v1/settlement-lines/', { params }),

    // ── Ledger ──────────────────────────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    listLedgerAccounts: (params) => client.get('/api/v1/ledger-accounts/', { params }),
    /** @param {unknown} data */
    createLedgerAccount: (data) => client.post('/api/v1/ledger-accounts/', data),
    /** @param {string|number} id @param {unknown} data */
    updateLedgerAccount: (id, data) => client.patch(`/api/v1/ledger-accounts/${id}/`, data),
    /** @param {string|number} id */
    deleteLedgerAccount: (id) => client.delete(`/api/v1/ledger-accounts/${id}/`),
    /** @param {Record<string,string|number|boolean>} [params] */
    listLedgerEntries: (params) => client.get('/api/v1/ledger-entries/', { params }),
    /** @param {unknown} data */
    createLedgerEntry: (data) => client.post('/api/v1/ledger-entries/', data),

    // ── ZATCA ───────────────────────────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    listZatcaDevices: (params) => client.get('/api/v1/zatca-devices/', { params }),
    /** @param {unknown} data */
    createZatcaDevice: (data) => client.post('/api/v1/zatca-devices/', data),
    /** @param {string|number} id */
    getZatcaDevice: (id) => client.get(`/api/v1/zatca-devices/${id}/`),
    /** @param {string|number} id @param {unknown} data */
    updateZatcaDevice: (id, data) => client.patch(`/api/v1/zatca-devices/${id}/`, data),
    /** @param {string|number} id */
    deleteZatcaDevice: (id) => client.delete(`/api/v1/zatca-devices/${id}/`),
    /** @param {string|number} id @param {unknown} data */
    onboardZatcaDevice: (id, data) => client.post(`/api/v1/zatca-devices/${id}/onboard/`, data),
    /** @param {string|number} id */
    activateZatcaDevice: (id) => client.post(`/api/v1/zatca-devices/${id}/activate/`),
    /** @param {Record<string,string|number|boolean>} [params] */
    listZatcaCounters: (params) => client.get('/api/v1/zatca-counters/', { params }),
    /** @param {Record<string,string|number|boolean>} [params] */
    listEInvoices: (params) => client.get('/api/v1/e-invoices/', { params }),
    /** @param {Record<string,string|number|boolean>} [params] */
    listEInvoiceSubmissions: (params) => client.get('/api/v1/e-invoice-submissions/', { params }),

    // ── Subscription / SaaS ─────────────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    listPlans: (params) => client.get('/api/v1/plans/', { params }),
    /** @param {Record<string,string|number|boolean>} [params] */
    listPlanEntitlements: (params) => client.get('/api/v1/plan-entitlements/', { params }),
    /** @param {Record<string,string|number|boolean>} [params] */
    listSubscriptions: (params) => client.get('/api/v1/subscriptions/', { params }),
    /** @param {Record<string,string|number|boolean>} [params] */
    listSubscriptionInvoices: (params) => client.get('/api/v1/subscription-invoices/', { params }),
    /** @param {Record<string,string|number|boolean>} [params] */
    listUsageRecords: (params) => client.get('/api/v1/usage-records/', { params }),
    /** @param {Record<string,string|number|boolean>} [params] */
    listDunningAttempts: (params) => client.get('/api/v1/dunning-attempts/', { params }),
  };
}
