import { env } from '$env/dynamic/public';

/**
 * Base path for every API request. Defaults to the same-origin `/api/v1`
 * path, which the Vite dev proxy forwards to the Django backend.
 */
export const API_BASE = env.PUBLIC_API_BASE || '/api/v1';

/** localStorage keys for the persisted auth session. */
export const STORAGE_KEYS = {
	access: 'namaa.access',
	refresh: 'namaa.refresh',
	org: 'namaa.org',
	locale: 'namaa.locale'
};
