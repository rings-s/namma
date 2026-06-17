import { browser } from '$app/environment';
import { goto } from '$app/navigation';
import { STORAGE_KEYS } from '$lib/config.js';
import { apiFetch, rows, setUnauthorizedHandler } from '$lib/api/client.js';
import { clearTokens, getAccess, setTokens } from '$lib/api/tokens.js';

/** Role hierarchy — mirrors backend core.api.ROLE_RANKS for UI gating. */
export const ROLE_RANKS = {
	owner: 100,
	admin: 80,
	manager: 60,
	accountant: 40,
	marketer: 40,
	receptionist: 30,
	staff: 20
};

/**
 * Authoritative client auth state: the signed-in user, their organization
 * roles, the organizations they can access, and the currently selected org.
 * The selected org drives server-side scoping: `resource.list`/`page` send it
 * as `?organization=` so the backend narrows each list (the browser no longer
 * filters whole pages itself).
 *
 * @typedef {{ id: string; role: string; organization: string; branch: string | null }} Role
 * @typedef {{ id: string; name: string; slug: string; currency: string; timezone: string; logo_url: string }} Organization
 */
function createAuth() {
	/** @type {any} */
	let user = $state(null);
	/** @type {Role[]} */
	let roles = $state([]);
	/** @type {Organization[]} */
	let organizations = $state([]);
	let currentOrgId = $state(browser ? localStorage.getItem(STORAGE_KEYS.org) : null);
	let loading = $state(true);

	const isAuthenticated = $derived(!!user);

	const currentOrg = $derived(
		organizations.find((org) => org.id === currentOrgId) ?? organizations[0] ?? null
	);

	/** Highest role rank the user holds in the currently selected org. */
	const currentRank = $derived(
		currentOrg
			? Math.max(
					0,
					...roles
						.filter((role) => role.organization === currentOrg.id)
						.map((role) => ROLE_RANKS[/** @type {keyof typeof ROLE_RANKS} */ (role.role)] ?? 0)
				)
			: 0
	);

	/** @param {string} minimumRole */
	function hasRole(minimumRole) {
		return currentRank >= (ROLE_RANKS[/** @type {keyof typeof ROLE_RANKS} */ (minimumRole)] ?? 0);
	}

	/**
	 * Exchange credentials for tokens, then load the session.
	 * @param {{ email: string; password: string; otp_code?: string }} credentials
	 */
	async function login(credentials) {
		const data = await apiFetch('/auth/token/', {
			method: 'POST',
			auth: false,
			body: credentials
		});
		setTokens(data.access, data.refresh);
		await loadSession();
	}

	/**
	 * Create a new account, then sign in with the same credentials. A fresh
	 * account has no 2FA enrolled, so the token call never needs an OTP here.
	 * @param {{ email: string; password: string; first_name?: string; last_name?: string }} payload
	 */
	async function register(payload) {
		await apiFetch('/auth/register/', { method: 'POST', auth: false, body: payload });
		await login({ email: payload.email, password: payload.password });
	}

	/** Fetch /me/ (user + roles) and the accessible organizations. */
	async function loadSession() {
		const me = await apiFetch('/me/');
		user = me;
		roles = me.roles ?? [];
		organizations = rows(await apiFetch('/organizations/'));
		if (!currentOrgId || !organizations.some((org) => org.id === currentOrgId)) {
			setOrg(organizations[0]?.id ?? null);
		}
	}

	/** Rehydrate on app load if a token is present. */
	async function hydrate() {
		loading = true;
		try {
			if (getAccess()) await loadSession();
		} catch {
			reset();
		} finally {
			loading = false;
		}
	}

	/** @param {string | null} orgId */
	function setOrg(orgId) {
		currentOrgId = orgId;
		if (browser) {
			if (orgId) localStorage.setItem(STORAGE_KEYS.org, orgId);
			else localStorage.removeItem(STORAGE_KEYS.org);
		}
	}

	function reset() {
		user = null;
		roles = [];
		organizations = [];
		setOrg(null);
	}

	async function logout() {
		const refresh = browser ? localStorage.getItem(STORAGE_KEYS.refresh) : null;
		if (refresh) {
			// Best-effort blacklist; ignore failures so logout always proceeds.
			await apiFetch('/auth/token/blacklist/', {
				method: 'POST',
				auth: false,
				body: { refresh }
			}).catch(() => {});
		}
		clearTokens();
		reset();
		goto('/login');
	}

	// Force a logout when token refresh fails mid-session.
	setUnauthorizedHandler(() => {
		reset();
		if (browser) goto('/login');
	});

	return {
		get user() {
			return user;
		},
		get roles() {
			return roles;
		},
		get organizations() {
			return organizations;
		},
		get currentOrg() {
			return currentOrg;
		},
		get currentOrgId() {
			return currentOrg?.id ?? null;
		},
		get currentRank() {
			return currentRank;
		},
		get isAuthenticated() {
			return isAuthenticated;
		},
		get loading() {
			return loading;
		},
		set user(value) {
			user = value;
		},
		hasRole,
		login,
		register,
		logout,
		hydrate,
		loadSession,
		setOrg
	};
}

export const auth = createAuth();
