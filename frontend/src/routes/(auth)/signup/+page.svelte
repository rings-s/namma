<script>
	import { goto } from '$app/navigation';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { i18n } from '$lib/i18n/i18n.svelte.js';
	import { ApiError } from '$lib/api/client.js';
	import Spinner from '$lib/components/ui/Spinner.svelte';
	import LanguageToggle from '$lib/components/ui/LanguageToggle.svelte';

	let firstName = $state('');
	let lastName = $state('');
	let email = $state('');
	let password = $state('');
	let submitting = $state(false);
	let error = $state('');
	/** @type {Record<string, string>} */
	let fieldErrors = $state({});

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
		fieldErrors = {};
		try {
			await auth.register({
				email,
				password,
				first_name: firstName,
				last_name: lastName
			});
			goto('/dashboard', { replaceState: true });
		} catch (err) {
			if (err instanceof ApiError && err.data && typeof err.data === 'object') {
				// Surface DRF field-level messages (email taken, weak password, …).
				fieldErrors = {
					email: err.fieldError('email') ?? '',
					password: err.fieldError('password') ?? '',
					first_name: err.fieldError('first_name') ?? '',
					last_name: err.fieldError('last_name') ?? ''
				};
				if (!Object.values(fieldErrors).some(Boolean)) error = err.message;
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
				<h1 class="text-2xl font-semibold text-slate-900">{i18n.t('auth.signup.title')}</h1>
				<p class="mt-1 text-sm text-slate-500">{i18n.t('auth.signup.subtitle')}</p>
			</div>

			<form
				onsubmit={submit}
				class="space-y-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
			>
				<div class="grid grid-cols-2 gap-3">
					<div>
						<label for="firstName" class="mb-1 block text-sm font-medium text-slate-700">
							{i18n.t('auth.firstName')}
						</label>
						<input
							id="firstName"
							type="text"
							bind:value={firstName}
							required
							autocomplete="given-name"
							class="w-full rounded-lg border-slate-300 text-sm focus:border-brand-500 focus:ring-brand-500"
						/>
						{#if fieldErrors.first_name}
							<p class="mt-1 text-xs text-rose-600">{fieldErrors.first_name}</p>
						{/if}
					</div>
					<div>
						<label for="lastName" class="mb-1 block text-sm font-medium text-slate-700">
							{i18n.t('auth.lastName')}
						</label>
						<input
							id="lastName"
							type="text"
							bind:value={lastName}
							required
							autocomplete="family-name"
							class="w-full rounded-lg border-slate-300 text-sm focus:border-brand-500 focus:ring-brand-500"
						/>
						{#if fieldErrors.last_name}
							<p class="mt-1 text-xs text-rose-600">{fieldErrors.last_name}</p>
						{/if}
					</div>
				</div>

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
					{#if fieldErrors.email}
						<p class="mt-1 text-xs text-rose-600">{fieldErrors.email}</p>
					{/if}
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
						minlength="8"
						autocomplete="new-password"
						class="w-full rounded-lg border-slate-300 text-sm focus:border-brand-500 focus:ring-brand-500"
					/>
					{#if fieldErrors.password}
						<p class="mt-1 text-xs text-rose-600">{fieldErrors.password}</p>
					{:else}
						<p class="mt-1 text-xs text-slate-400">{i18n.t('auth.password.hint')}</p>
					{/if}
				</div>

				{#if error}
					<p class="rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</p>
				{/if}

				<button
					type="submit"
					disabled={submitting}
					class="flex w-full items-center justify-center gap-2 rounded-lg bg-brand-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-60"
				>
					{#if submitting}<Spinner size={16} />{/if}
					{submitting ? i18n.t('auth.creatingAccount') : i18n.t('auth.createAccount')}
				</button>
			</form>

			<p class="mt-6 text-center text-sm text-slate-500">
				{i18n.t('auth.haveAccount')}
				<a href="/login" class="font-semibold text-brand-600 hover:underline">
					{i18n.t('auth.toLogin')}
				</a>
			</p>
		</div>
	</main>
</div>
