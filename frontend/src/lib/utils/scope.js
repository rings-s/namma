/**
 * Client-side tenancy helpers. The backend scopes every list by the user's
 * role membership across ALL their organizations and exposes no
 * `?organization=` param (see MISSING_BACKEND.md), so the active-org filter
 * lives in the browser.
 */

/**
 * Keep only rows belonging to the active organization. Rows without an
 * `organization` field pass through (they're already scoped by a parent the
 * caller loaded for one org).
 * @template {{ organization?: string }} T
 * @param {T[]} rows
 * @param {string | null} orgId
 * @returns {T[]}
 */
export function scopeToOrg(rows, orgId) {
	if (!orgId) return rows;
	return rows.filter((row) => row.organization === undefined || row.organization === orgId);
}

/**
 * Build an id → row lookup. Useful for resolving FK ids the serializer returns
 * raw (e.g. a conversation's `customer` id → the customer row).
 * @template {{ id: string }} T
 * @param {T[]} rows
 * @returns {Map<string, T>}
 */
export function indexById(rows) {
	return new Map(rows.map((row) => [row.id, row]));
}

/**
 * Display name for a customer row (first + last, trimmed), with a fallback.
 * @param {{ first_name?: string; last_name?: string } | undefined | null} customer
 */
export function customerName(customer) {
	if (!customer) return '—';
	return `${customer.first_name ?? ''} ${customer.last_name ?? ''}`.trim() || '—';
}
