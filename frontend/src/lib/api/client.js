import { API_BASE } from '$lib/config.js';
import { clearTokens, getAccess, getRefresh, setAccess } from './tokens.js';

/**
 * Normalized API error. `data` carries the raw DRF error body so callers can
 * surface field-level messages; `message` is a best-effort human string.
 */
export class ApiError extends Error {
	/**
	 * @param {number} status
	 * @param {any} data
	 */
	constructor(status, data) {
		super(extractMessage(data, status));
		this.name = 'ApiError';
		this.status = status;
		this.data = data;
	}

	/** @param {string} field */
	fieldError(field) {
		const value = this.data?.[field];
		if (Array.isArray(value)) return value.join(' ');
		return typeof value === 'string' ? value : null;
	}
}

/**
 * Pulls a readable message out of a DRF error payload.
 * @param {any} data
 * @param {number} status
 */
function extractMessage(data, status) {
	if (typeof data === 'string' && data) return data;
	if (data && typeof data === 'object') {
		if (typeof data.detail === 'string') return data.detail;
		const first = Object.values(data)[0];
		if (Array.isArray(first) && typeof first[0] === 'string') return first[0];
		if (typeof first === 'string') return first;
	}
	return `Request failed (${status})`;
}

/** Called when refresh fails — wired by the auth store to force a logout. */
let onUnauthorized = () => {};
/** @param {() => void} handler */
export function setUnauthorizedHandler(handler) {
	onUnauthorized = handler;
}

/** Single-flight refresh: concurrent 401s share one refresh request. */
/** @type {Promise<string | null> | null} */
let refreshing = null;

async function refreshAccessToken() {
	const refresh = getRefresh();
	if (!refresh) return null;
	if (!refreshing) {
		refreshing = (async () => {
			try {
				const res = await fetch(`${API_BASE}/auth/token/refresh/`, {
					method: 'POST',
					headers: { 'Content-Type': 'application/json' },
					body: JSON.stringify({ refresh })
				});
				if (!res.ok) return null;
				const data = await res.json();
				if (data.access) setAccess(data.access);
				// Rotation is on, so a fresh refresh token comes back too.
				if (data.refresh) {
					const { setTokens } = await import('./tokens.js');
					setTokens(data.access, data.refresh);
				}
				return data.access ?? null;
			} catch {
				return null;
			} finally {
				refreshing = null;
			}
		})();
	}
	return refreshing;
}

/**
 * @typedef {Object} RequestOptions
 * @property {string} [method]
 * @property {any} [body] JSON-serialized unless it is a FormData instance.
 * @property {Record<string, string>} [headers]
 * @property {Record<string, string | number | boolean | null | undefined>} [params]
 * @property {boolean} [auth] Attach the bearer token (default true).
 * @property {string} [idempotencyKey]
 * @property {AbortSignal} [signal] Abort the request (e.g. on rapid navigation).
 * @property {boolean} [_retried] Internal: marks a post-refresh retry.
 */

/**
 * Core fetch wrapper: builds the URL, attaches auth + JSON headers, normalizes
 * errors, and transparently refreshes the access token once on a 401.
 *
 * @param {string} path Path under API_BASE, e.g. `/me/`.
 * @param {RequestOptions} [options]
 */
export async function apiFetch(path, options = {}) {
	const {
		method = 'GET',
		body,
		headers = {},
		params,
		auth = true,
		idempotencyKey,
		signal
	} = options;

	let url = `${API_BASE}${path}`;
	if (params) {
		const query = new URLSearchParams();
		for (const [key, value] of Object.entries(params)) {
			if (value !== null && value !== undefined && value !== '') {
				query.set(key, String(value));
			}
		}
		const qs = query.toString();
		if (qs) url += `?${qs}`;
	}

	const isForm = typeof FormData !== 'undefined' && body instanceof FormData;
	/** @type {Record<string, string>} */
	const finalHeaders = { Accept: 'application/json', ...headers };
	if (body !== undefined && !isForm) finalHeaders['Content-Type'] = 'application/json';
	if (idempotencyKey) finalHeaders['Idempotency-Key'] = idempotencyKey;

	const token = auth ? getAccess() : null;
	if (token) finalHeaders.Authorization = `Bearer ${token}`;

	const res = await fetch(url, {
		method,
		headers: finalHeaders,
		body: body === undefined ? undefined : isForm ? body : JSON.stringify(body),
		signal
	});

	if (res.status === 401 && auth && !options._retried) {
		const newToken = await refreshAccessToken();
		if (newToken) {
			return apiFetch(path, { ...options, _retried: true });
		}
		clearTokens();
		onUnauthorized();
		throw new ApiError(401, { detail: 'Session expired. Please sign in again.' });
	}

	if (res.status === 204) return null;

	let data = null;
	const contentType = res.headers.get('Content-Type') || '';
	if (contentType.includes('application/json')) {
		data = await res.json().catch(() => null);
	} else {
		const text = await res.text().catch(() => '');
		data = text || null;
	}

	if (!res.ok) throw new ApiError(res.status, data);
	return data;
}

/**
 * Collapses a DRF paginated list into its rows. Endpoints with pagination
 * disabled already return a plain array, which passes through untouched.
 * @param {any} data
 */
export function rows(data) {
	if (Array.isArray(data)) return data;
	return data?.results ?? [];
}

/**
 * True when a thrown value is an aborted fetch (request cancelled via an
 * AbortSignal). Callers swallow these — they're an intentional cancellation,
 * not a failure to surface.
 * @param {unknown} err
 */
export function isAbortError(err) {
	return err instanceof DOMException && err.name === 'AbortError';
}

/**
 * Best-effort human message from any thrown value (ApiError, Error, or raw).
 * @param {unknown} err
 */
export function errMessage(err) {
	if (err instanceof Error) return err.message;
	return typeof err === 'string' ? err : '';
}
