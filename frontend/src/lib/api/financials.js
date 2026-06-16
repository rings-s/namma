import { resource } from './resource.js';

/**
 * financials app — invoicing, payments/refunds, settlements, ledger, ZATCA
 * Phase-2 e-invoicing, and subscription billing. Ledger entries and the ZATCA
 * pipeline tables are read-only via the API.
 */

export const documentSequences = resource('document-sequences');
export const invoices = resource('invoices');
export const creditNotes = resource('credit-notes');
export const debitNotes = resource('debit-notes');
export const paymentIntents = resource('payment-intents');
export const payments = resource('payments');
export const refunds = resource('refunds');
export const paymentWebhookEvents = resource('payment-webhook-events');
export const settlements = resource('settlements');
export const settlementLines = resource('settlement-lines');
export const ledgerAccounts = resource('ledger-accounts');
export const ledgerEntries = resource('ledger-entries');
export const zatcaDevices = resource('zatca-devices');
export const zatcaCounters = resource('zatca-counters');
export const eInvoices = resource('e-invoices');
export const eInvoiceSubmissions = resource('e-invoice-submissions');
export const plans = resource('plans');
export const planEntitlements = resource('plan-entitlements');
export const subscriptions = resource('subscriptions');
export const subscriptionInvoices = resource('subscription-invoices');
export const usageRecords = resource('usage-records');
export const dunningAttempts = resource('dunning-attempts');

/** Generate/submit the ZATCA e-invoice for an invoice (POST /invoices/{id}/einvoice/, accountant+). @param {string} id */
export function generateEInvoice(id) {
	return invoices.do(id, 'einvoice');
}

/** Execute an approved refund through the gateway (POST /refunds/{id}/execute/, manager+). @param {string} id */
export function executeRefund(id) {
	return refunds.do(id, 'execute');
}

/** Onboard a ZATCA device — compliance→production CSID (POST /zatca-devices/{id}/onboard/, admin+). @param {string} id @param {Record<string, any>} [body] */
export function onboardZatcaDevice(id, body) {
	return zatcaDevices.do(id, 'onboard', body);
}

/** Activate an onboarded ZATCA device (POST /zatca-devices/{id}/activate/, admin+). @param {string} id */
export function activateZatcaDevice(id) {
	return zatcaDevices.do(id, 'activate');
}
