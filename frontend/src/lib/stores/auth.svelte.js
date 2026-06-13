/**
 * Auth state singleton using Svelte 5 runes.
 * On the server this module is re-instantiated per request (no shared state).
 * On the client it persists for the lifetime of the page.
 */

let user = $state(/** @type {Record<string,unknown> | null} */ (null));
let accessToken = $state(/** @type {string | null} */ (null));
let organizationId = $state(/** @type {string | null} */ (null));
let role = $state(/** @type {string | null} */ (null));

export const isAuthenticated = $derived(user !== null);

/** @returns {Record<string,unknown> | null} */
export function getUser() {
  return user;
}

/** @param {Record<string,unknown> | null} value */
export function setUser(value) {
  user = value;
  organizationId = value ? /** @type {string | null} */ (value['organization_id'] ?? null) : null;
  role = value ? /** @type {string | null} */ (value['role'] ?? null) : null;
}

/** @returns {string | null} */
export function getAccessToken() {
  return accessToken;
}

/** @param {string | null} value */
export function setAccessToken(value) {
  accessToken = value;
}

/** @returns {string | null} */
export function getOrganizationId() {
  return organizationId;
}

/** @returns {string | null} */
export function getRole() {
  return role;
}

export function clearAuth() {
  user = null;
  accessToken = null;
  organizationId = null;
  role = null;
}
