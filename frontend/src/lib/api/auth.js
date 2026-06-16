import { apiFetch, rows } from './client.js';
import { resource } from './resource.js';

/** accounts app — auth/token & session flows live in client.js + the auth store. */

/** Role assignments across the user's organizations (UserRole). */
export const userRoles = resource('user-roles');

/**
 * Self-service account registration (POST /auth/register/, anonymous).
 * @param {{ email: string; password: string; first_name?: string; last_name?: string }} payload
 */
export function register(payload) {
	return apiFetch('/auth/register/', { method: 'POST', auth: false, body: payload });
}

/** The signed-in user + their roles (GET /me/). */
export function getMe() {
	return apiFetch('/me/');
}

/**
 * Update the signed-in user's profile (PATCH /me/).
 * @param {Record<string, any>} patch
 */
export function updateProfile(patch) {
	return apiFetch('/me/', { method: 'PATCH', body: patch });
}

/** Active sessions for the signed-in user (pagination disabled server-side). */
export async function listSessions() {
	return rows(await apiFetch('/auth/sessions/'));
}

/** @param {string} id */
export function revokeSession(id) {
	return apiFetch(`/auth/sessions/${id}/revoke/`, { method: 'POST' });
}

/** Begin TOTP enrollment → { secret, otpauth_uri }. */
export function setupTwoFactor() {
	return apiFetch('/auth/2fa/setup/', { method: 'POST' });
}

/** @param {string} code */
export function verifyTwoFactor(code) {
	return apiFetch('/auth/2fa/verify/', { method: 'POST', body: { code } });
}

/** @param {string} code */
export function disableTwoFactor(code) {
	return apiFetch('/auth/2fa/disable/', { method: 'POST', body: { code } });
}
