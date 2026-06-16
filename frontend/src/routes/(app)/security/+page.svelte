<script>
	import { onMount } from 'svelte';
	import { i18n } from '$lib/i18n/i18n.svelte.js';
	import { toasts } from '$lib/stores/toast.svelte.js';
	import {
		listSessions,
		revokeSession,
		setupTwoFactor,
		verifyTwoFactor,
		disableTwoFactor
	} from '$lib/api/auth.js';
	import { dateTime } from '$lib/utils/format.js';
	import { errMessage } from '$lib/api/client.js';
	import Spinner from '$lib/components/ui/Spinner.svelte';
	import Icon from '$lib/components/ui/Icon.svelte';

	// --- Sessions ---
	/** @type {any[]} */
	let sessions = $state([]);
	let sessionsLoading = $state(true);
	/** @type {string | null} */
	let revokingId = $state(null);

	onMount(loadSessions);

	async function loadSessions() {
		sessionsLoading = true;
		try {
			const all = await listSessions();
			sessions = all.filter((/** @type {any} */ s) => !s.revoked_at);
		} catch (err) {
			toasts.error(errMessage(err) || i18n.t('common.error'));
		} finally {
			sessionsLoading = false;
		}
	}

	/** @param {string} id */
	async function revoke(id) {
		revokingId = id;
		try {
			await revokeSession(id);
			sessions = sessions.filter((/** @type {any} */ s) => s.id !== id);
			toasts.success(i18n.t('security.session.revoked'));
		} catch (err) {
			toasts.error(errMessage(err) || i18n.t('common.error'));
		} finally {
			revokingId = null;
		}
	}

	// --- Two-factor ---
	// The backend exposes no 2FA status, so both flows are always available;
	// setup returns 400 if 2FA is already enabled (see MISSING_BACKEND.md).
	let enrolling = $state(false);
	let enrollSecret = $state('');
	let enrollUri = $state('');
	let confirmCode = $state('');
	let confirming = $state(false);
	let disableCode = $state('');
	let disabling = $state(false);

	async function startEnroll() {
		try {
			const data = await setupTwoFactor();
			enrollSecret = data.secret;
			enrollUri = data.otpauth_uri;
			enrolling = true;
		} catch (err) {
			toasts.error(errMessage(err) || i18n.t('common.error'));
		}
	}

	/** @param {SubmitEvent} event */
	async function confirmEnroll(event) {
		event.preventDefault();
		confirming = true;
		try {
			await verifyTwoFactor(confirmCode);
			toasts.success(i18n.t('security.2fa.enabledMsg'));
			enrolling = false;
			enrollSecret = '';
			enrollUri = '';
			confirmCode = '';
		} catch (err) {
			toasts.error(errMessage(err) || i18n.t('common.error'));
		} finally {
			confirming = false;
		}
	}

	/** @param {SubmitEvent} event */
	async function disable(event) {
		event.preventDefault();
		disabling = true;
		try {
			await disableTwoFactor(disableCode);
			toasts.success(i18n.t('security.2fa.disabledMsg'));
			disableCode = '';
		} catch (err) {
			toasts.error(errMessage(err) || i18n.t('common.error'));
		} finally {
			disabling = false;
		}
	}
</script>

<div class="mx-auto max-w-2xl space-y-8">
	<header>
		<h1 class="text-2xl font-semibold text-slate-900">{i18n.t('security.title')}</h1>
	</header>

	<!-- Active sessions -->
	<section>
		<h2 class="mb-3 text-lg font-semibold text-slate-900">{i18n.t('security.sessions')}</h2>
		<div class="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
			{#if sessionsLoading}
				<div class="flex items-center gap-3 p-6 text-slate-400">
					<Spinner size={20} /><span class="text-sm">{i18n.t('common.loading')}</span>
				</div>
			{:else if sessions.length}
				<ul class="divide-y divide-slate-100">
					{#each sessions as session (session.id)}
						<li class="flex items-center justify-between gap-4 px-4 py-3">
							<div class="min-w-0">
								<p class="truncate text-sm font-medium text-slate-800">
									{session.device_label || session.user_agent || '—'}
								</p>
								<p class="text-xs text-slate-400">
									{session.ip_address ?? '—'} · {i18n.t('security.session.lastSeen')}:
									{dateTime(session.last_seen_at)}
								</p>
							</div>
							<button
								onclick={() => revoke(session.id)}
								disabled={revokingId === session.id}
								class="flex shrink-0 items-center gap-1.5 rounded-lg border border-rose-200 px-3 py-1.5 text-xs font-semibold text-rose-600 transition hover:bg-rose-50 disabled:opacity-60"
							>
								{#if revokingId === session.id}<Spinner size={14} />{/if}
								{i18n.t('security.session.revoke')}
							</button>
						</li>
					{/each}
				</ul>
			{:else}
				<p class="p-6 text-center text-sm text-slate-400">{i18n.t('security.sessions.none')}</p>
			{/if}
		</div>
	</section>

	<!-- Two-factor authentication -->
	<section>
		<h2 class="mb-3 text-lg font-semibold text-slate-900">{i18n.t('security.2fa')}</h2>
		<div class="space-y-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
			{#if !enrolling}
				<button
					onclick={startEnroll}
					class="rounded-lg bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-brand-700"
				>
					{i18n.t('security.2fa.enable')}
				</button>
			{:else}
				<p class="text-sm text-slate-600">{i18n.t('security.2fa.scan')}</p>
				<div class="rounded-lg bg-slate-50 p-4">
					<p class="text-xs text-slate-400">{i18n.t('security.2fa.secret')}</p>
					<code class="mt-1 block break-all text-sm font-semibold text-slate-800" dir="ltr">
						{enrollSecret}
					</code>
					<a
						href={enrollUri}
						class="mt-2 inline-flex items-center gap-1 text-xs font-medium text-brand-600 hover:underline"
						dir="ltr"
					>
						<Icon name="shield" size={14} /> otpauth://
					</a>
				</div>
				<form onsubmit={confirmEnroll} class="flex items-end gap-3">
					<div class="flex-1">
						<label for="confirm" class="mb-1 block text-sm font-medium text-slate-700">
							{i18n.t('security.2fa.confirm')}
						</label>
						<input
							id="confirm"
							bind:value={confirmCode}
							inputmode="numeric"
							maxlength="10"
							class="w-full rounded-lg border-slate-300 text-center text-lg tracking-[0.3em] focus:border-brand-500 focus:ring-brand-500"
						/>
					</div>
					<button
						type="submit"
						disabled={confirming || !confirmCode}
						class="flex items-center gap-2 rounded-lg bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-60"
					>
						{#if confirming}<Spinner size={16} />{/if}
						{i18n.t('common.confirm')}
					</button>
				</form>
			{/if}

			<div class="border-t border-slate-100 pt-4">
				<p class="mb-2 text-sm text-slate-500">{i18n.t('security.2fa.codeToDisable')}</p>
				<form onsubmit={disable} class="flex items-end gap-3">
					<div class="flex-1">
						<input
							bind:value={disableCode}
							inputmode="numeric"
							maxlength="10"
							placeholder="000000"
							class="w-full rounded-lg border-slate-300 text-center tracking-[0.3em] focus:border-brand-500 focus:ring-brand-500"
						/>
					</div>
					<button
						type="submit"
						disabled={disabling || !disableCode}
						class="flex items-center gap-2 rounded-lg border border-rose-200 px-5 py-2.5 text-sm font-semibold text-rose-600 transition hover:bg-rose-50 disabled:opacity-60"
					>
						{#if disabling}<Spinner size={16} />{/if}
						{i18n.t('security.2fa.disable')}
					</button>
				</form>
			</div>
		</div>
	</section>
</div>
