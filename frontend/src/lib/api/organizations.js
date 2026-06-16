import { apiFetch, rows } from './client.js';
import { resource } from './resource.js';

/** organizations app — the tenant root and its branch/settings/retention config. */

export const organizations = resource('organizations');
export const organizationSettings = resource('organization-settings');
export const branches = resource('branches');
export const branchHours = resource('branch-hours');
export const retentionPolicies = resource('retention-policies');

/**
 * Organizations the signed-in user can access (tenant-scoped by role).
 * Kept as a named helper because the auth store + org switcher depend on it.
 */
export async function listOrganizations() {
	return rows(await apiFetch('/organizations/'));
}

/** @param {string} id */
export function getOrganization(id) {
	return apiFetch(`/organizations/${id}/`);
}
