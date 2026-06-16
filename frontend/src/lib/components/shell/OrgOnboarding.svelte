<script>
	import { auth } from '$lib/stores/auth.svelte.js';
	import { i18n } from '$lib/i18n/i18n.svelte.js';
	import { organizations } from '$lib/api/organizations.js';
	import { ApiError, errMessage } from '$lib/api/client.js';
	import Spinner from '$lib/components/ui/Spinner.svelte';
	import LanguageToggle from '$lib/components/ui/LanguageToggle.svelte';

	let name = $state('');
	let industry = $state('');
	let creating = $state(false);
	let error = $state('');

	/**
	 * Derive a unique-ish slug from the name (slug is unique server-side).
	 * @param {string} value
	 */
	function toSlug(value) {
		const base = value
			.toLowerCase()
			.trim()
			.replace(/[^a-z0-9\s-]/g, '')
			.replace(/[\s_-]+/g, '-')
			.replace(/^-+|-+$/g, '')
			.slice(0, 40);
		const suffix = Math.random().toString(36).slice(2, 8);
		return base ? `${base}-${suffix}` : `org-${suffix}`;
	}

	/** @param {SubmitEvent} event */
	async function submit(event) {
		event.preventDefault();
		if (creating || !name.trim()) return;
		creating = true;
		error = '';
		try {
			await organizations.create({ name: name.trim(), slug: toSlug(name), industry });
			// Refresh the session so roles + organizations populate and the new
			// org becomes current — the shell then renders the app.
			await auth.loadSession();
		} catch (err) {
			error = err instanceof ApiError ? err.message : errMessage(err) || i18n.t('common.error');
		} finally {
			creating = false;
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
				<h1 class="text-2xl font-semibold text-slate-900">{i18n.t('org.onboarding.title')}</h1>
				<p class="mt-1 text-sm text-slate-500">{i18n.t('org.onboarding.subtitle')}</p>
			</div>

			<form
				onsubmit={submit}
				class="space-y-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
			>
				<div>
					<label for="orgName" class="mb-1 block text-sm font-medium text-slate-700">
						{i18n.t('org.onboarding.name')}
					</label>
					<input
						id="orgName"
						type="text"
						bind:value={name}
						required
						autocomplete="organization"
						class="w-full rounded-lg border-slate-300 text-sm focus:border-brand-500 focus:ring-brand-500"
					/>
				</div>

				<div>
					<label for="orgIndustry" class="mb-1 block text-sm font-medium text-slate-700">
						{i18n.t('org.onboarding.industry')}
					</label>
					<input
						id="orgIndustry"
						type="text"
						bind:value={industry}
						class="w-full rounded-lg border-slate-300 text-sm focus:border-brand-500 focus:ring-brand-500"
					/>
				</div>

				{#if error}
					<p class="rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</p>
				{/if}

				<button
					type="submit"
					disabled={creating || !name.trim()}
					class="flex w-full items-center justify-center gap-2 rounded-lg bg-brand-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-60"
				>
					{#if creating}<Spinner size={16} />{/if}
					{creating ? i18n.t('org.onboarding.creating') : i18n.t('org.onboarding.create')}
				</button>
			</form>
		</div>
	</main>
</div>
