import { browser } from '$app/environment';
import { STORAGE_KEYS } from '$lib/config.js';

/**
 * Plain (non-reactive) JWT storage. Both the API client and the auth store
 * read/write tokens here so there is a single source of truth in
 * localStorage, with no import cycle between them.
 */

export function getAccess() {
	return browser ? localStorage.getItem(STORAGE_KEYS.access) : null;
}

export function getRefresh() {
	return browser ? localStorage.getItem(STORAGE_KEYS.refresh) : null;
}

/**
 * @param {string} access
 * @param {string} refresh
 */
export function setTokens(access, refresh) {
	if (!browser) return;
	localStorage.setItem(STORAGE_KEYS.access, access);
	localStorage.setItem(STORAGE_KEYS.refresh, refresh);
}

/** @param {string} access */
export function setAccess(access) {
	if (browser) localStorage.setItem(STORAGE_KEYS.access, access);
}

export function clearTokens() {
	if (!browser) return;
	localStorage.removeItem(STORAGE_KEYS.access);
	localStorage.removeItem(STORAGE_KEYS.refresh);
}
