<script>
	import { goto } from '$app/navigation';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { i18n } from '$lib/i18n/i18n.svelte.js';
	import { ApiError } from '$lib/api/client.js';
	import Spinner from '$lib/components/ui/Spinner.svelte';
	import LanguageToggle from '$lib/components/ui/LanguageToggle.svelte';

	let email = $state('');
	let password = $state('');
	let otpCode = $state('');
	let otpRequired = $state(false);
	let submitting = $state(false);
	let error = $state('');

	// If a hydrated session already exists, skip the form.
	$effect(() => {
		if (!auth.loading && auth.isAuthenticated) goto('/dashboard', { replaceState: true });
	});

	/** @param {SubmitEvent} event */
	async function submit(event) {
		event.preventDefault();
		if (submitting) return;
		submitting = true;
		error = '';
		try {
			/** @type {{ email: string; password: string; otp_code?: string }} */
			const credentials = { email, password };
			if (otpRequired) credentials.otp_code = otpCode;
			await auth.login(credentials);
			goto('/dashboard', { replaceState: true });
		} catch (err) {
			if (err instanceof ApiError) {
				// The token endpoint asks for an OTP once 2FA is enabled.
				if (err.fieldError('otp_code')) {
					otpRequired = true;
					error = otpCode ? (err.fieldError('otp_code') ?? '') : '';
				} else if (err.status === 401) {
					error = i18n.t('auth.invalid');
				} else {
					error = err.message;
				}
			} else {
				error = i18n.t('common.error');
			}
		} finally {
			submitting = false;
		}
	}
</script>

<div class="flex min-h-screen flex-col bg-slate-50">
	<header class="flex items-center justify-between p-6">
		<span class="text-lg font-bold text-brand-700">{i18n.t('app.name')}</span>
		<LanguageToggle />
	</header>

	<main class="flex flex-1 items-center justify-center px-4 pb-16">
		<div class="w-full max-w-sm">
			<div class="mb-8 text-center">
				<h1 class="text-2xl font-semibold text-slate-900">{i18n.t('auth.login.title')}</h1>
				<p class="mt-1 text-sm text-slate-500">{i18n.t('auth.login.subtitle')}</p>
			</div>

			<form
				onsubmit={submit}
				class="space-y-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
			>
				<div>
					<label for="email" class="mb-1 block text-sm font-medium text-slate-700">
						{i18n.t('auth.email')}
					</label>
					<input
						id="email"
						type="email"
						bind:value={email}
						required
						autocomplete="email"
						class="w-full rounded-lg border-slate-300 text-sm focus:border-brand-500 focus:ring-brand-500"
					/>
				</div>

				<div>
					<label for="password" class="mb-1 block text-sm font-medium text-slate-700">
						{i18n.t('auth.password')}
					</label>
					<input
						id="password"
						type="password"
						bind:value={password}
						required
						autocomplete="current-password"
						class="w-full rounded-lg border-slate-300 text-sm focus:border-brand-500 focus:ring-brand-500"
					/>
				</div>

				{#if otpRequired}
					<div>
						<label for="otp" class="mb-1 block text-sm font-medium text-slate-700">
							{i18n.t('auth.otp')}
						</label>
						<input
							id="otp"
							type="text"
							inputmode="numeric"
							bind:value={otpCode}
							autocomplete="one-time-code"
							class="w-full rounded-lg border-slate-300 text-center text-lg tracking-[0.4em] focus:border-brand-500 focus:ring-brand-500"
						/>
						<p class="mt-1 text-xs text-slate-400">{i18n.t('auth.otp.hint')}</p>
					</div>
				{/if}

				{#if error}
					<p class="rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</p>
				{/if}

				<button
					type="submit"
					disabled={submitting}
					class="flex w-full items-center justify-center gap-2 rounded-lg bg-brand-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-60"
				>
					{#if submitting}<Spinner size={16} />{/if}
					{submitting ? i18n.t('auth.signingin') : i18n.t('auth.signin')}
				</button>
			</form>

			<p class="mt-6 text-center text-sm text-slate-500">
				{i18n.t('auth.noAccount')}
				<a href="/signup" class="font-semibold text-brand-600 hover:underline">
					{i18n.t('auth.toSignup')}
				</a>
			</p>
		</div>
	</main>
</div>
