import { auth } from '$lib/stores/auth.svelte.js';
import { apiFetch, rows } from './client.js';

/** Fresh idempotency key per mutating call (core.IdempotentCreateMixin reads it). */
function newIdempotencyKey() {
	return (
		globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(36).slice(2)}`
	);
}

/**
 * Inject the active organization as a query param so the backend scopes the
 * list server-side (`TenantScopedQuerysetMixin` honors `?organization=`). This
 * replaces the old in-browser row filtering, so pagination is now correct
 * per-org. The param is ignored by non-tenant endpoints (organizations,
 * reference data). A caller that sets `organization` explicitly — including to
 * `null`/`undefined` to opt out (e.g. the org switcher) — always wins.
 * @param {Params} [params]
 * @returns {Params | undefined}
 */
function withOrg(params) {
	if (params && 'organization' in params) return params;
	const orgId = auth.currentOrgId;
	if (!orgId) return params;
	return { ...params, organization: orgId };
}

/**
 * @typedef {Record<string, string | number | boolean | null | undefined>} Params
 * @typedef {{ idempotencyKey?: string }} MutateOptions
 * @typedef {{ signal?: AbortSignal }} ReadOptions Cancel an in-flight read, e.g.
 *   from an `$effect` cleanup when the org/route changes mid-request.
 */

/**
 * Standard DRF router interface for one collection endpoint. The backend mounts
 * every app under `/api/v1/` via routers, so each resource maps 1:1 to a
 * ViewSet basename — e.g. `resource('customers')` covers `/customers/` and
 * `/customers/{id}/`, plus its `@action` routes via `do`/`read`/`collection`.
 *
 * @param {string} base Collection segment, e.g. `'customers'`.
 */
export function resource(base) {
	const root = `/${base}/`;
	return {
		/** List rows (DRF pagination unwrapped). @param {Params} [params] @param {ReadOptions} [opts] */
		async list(params, opts = {}) {
			return rows(await apiFetch(root, { params: withOrg(params), signal: opts.signal }));
		},
		/** Raw paginated payload `{ count, next, previous, results }`. @param {Params} [params] @param {ReadOptions} [opts] */
		page(params, opts = {}) {
			return apiFetch(root, { params: withOrg(params), signal: opts.signal });
		},
		/** @param {string} id @param {Params} [params] @param {ReadOptions} [opts] */
		get(id, params, opts = {}) {
			return apiFetch(`${root}${id}/`, { params, signal: opts.signal });
		},
		/** @param {Record<string, any> | FormData} body @param {MutateOptions} [opts] */
		create(body, opts = {}) {
			return apiFetch(root, {
				method: 'POST',
				body,
				idempotencyKey: opts.idempotencyKey ?? newIdempotencyKey()
			});
		},
		/** @param {string} id @param {Record<string, any> | FormData} body */
		update(id, body) {
			return apiFetch(`${root}${id}/`, { method: 'PUT', body });
		},
		/** @param {string} id @param {Record<string, any> | FormData} body */
		patch(id, body) {
			return apiFetch(`${root}${id}/`, { method: 'PATCH', body });
		},
		/** @param {string} id */
		remove(id) {
			return apiFetch(`${root}${id}/`, { method: 'DELETE' });
		},
		/**
		 * POST a detail `@action`, e.g. `do(id, 'redeem', body)` → `/{base}/{id}/redeem/`.
		 * @param {string} id @param {string} action
		 * @param {Record<string, any>} [body] @param {MutateOptions} [opts]
		 */
		do(id, action, body, opts = {}) {
			return apiFetch(`${root}${id}/${action}/`, {
				method: 'POST',
				body,
				idempotencyKey: opts.idempotencyKey ?? newIdempotencyKey()
			});
		},
		/**
		 * GET a detail `@action`, e.g. `read(id, 'loaded-cost')` → `/{base}/{id}/loaded-cost/`.
		 * @param {string} id @param {string} action @param {Params} [params] @param {ReadOptions} [opts]
		 */
		read(id, action, params, opts = {}) {
			return apiFetch(`${root}${id}/${action}/`, { params, signal: opts.signal });
		},
		/**
		 * GET a collection `@action`, e.g. `collection('low-stock')` → `/{base}/low-stock/`.
		 * @param {string} action @param {Params} [params] @param {ReadOptions} [opts]
		 */
		collection(action, params, opts = {}) {
			return apiFetch(`${root}${action}/`, { params, signal: opts.signal });
		},
		/**
		 * POST a collection `@action`, e.g. `collectionDo('quote', body)` → `/{base}/quote/`.
		 * @param {string} action @param {Record<string, any>} [body] @param {MutateOptions} [opts]
		 */
		collectionDo(action, body, opts = {}) {
			return apiFetch(`${root}${action}/`, {
				method: 'POST',
				body,
				idempotencyKey: opts.idempotencyKey ?? newIdempotencyKey()
			});
		}
	};
}
