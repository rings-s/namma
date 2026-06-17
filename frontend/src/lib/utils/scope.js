/**
 * Tenancy helpers. The active org is now scoped server-side: `resource.list`
 * / `page` send `?organization=<id>` and `TenantScopedQuerysetMixin` honors it
 * (MISSING_BACKEND #1 — resolved), so pagination is correct per-org. The
 * helpers below remain as a defensive client-side guard and for resolving raw
 * FK ids the serializers still return.
 */

/**
 * Defensive secondary filter: keep only rows belonging to the active org.
 * Server-side scoping is now primary, so this is normally a no-op (every row
 * already matches); it stays as a guard for any list fetched without the param
 * and for rows whose serializer omits `organization`.
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
