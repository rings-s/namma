import { resource } from './resource.js';

/** customers app — profiles, preferences, clinical notes, documents, segments, surveys. */

export const customers = resource('customers');
export const customerPreferences = resource('customer-preferences');
export const clinicalNotes = resource('clinical-notes');
export const customerDocuments = resource('customer-documents');
export const customerSegments = resource('customer-segments');
export const customerSegmentMemberships = resource('customer-segment-memberships');
export const surveys = resource('surveys');
export const surveyResponses = resource('survey-responses');

/** PDPL data export for a customer (POST /customers/{id}/pdpl-export/, admin+). @param {string} id */
export function pdplExport(id) {
	return customers.do(id, 'pdpl-export');
}

/** PDPL erasure — anonymizes PII, keeps statutory records (admin+). @param {string} id */
export function pdplErase(id) {
	return customers.do(id, 'pdpl-erase');
}

/**
 * Re-converge a dynamic/AI segment's membership (POST /customer-segments/{id}/refresh/).
 * Only `manual` segments accept membership add/remove via the UI.
 * @param {string} id
 */
export function refreshSegment(id) {
	return customerSegments.do(id, 'refresh');
}

/**
 * Net Promoter Score rollup (GET /survey-responses/nps/).
 * @param {Record<string, any>} [params] @param {{ signal?: AbortSignal }} [opts]
 */
export function npsSummary(params, opts = {}) {
	return surveyResponses.collection('nps', params, opts);
}
