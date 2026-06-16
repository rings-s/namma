<script>
	import { auth } from '$lib/stores/auth.svelte.js';
	import { i18n } from '$lib/i18n/i18n.svelte.js';
	import { updateProfile } from '$lib/api/auth.js';
	import { toasts } from '$lib/stores/toast.svelte.js';
	import { ApiError, errMessage } from '$lib/api/client.js';
	import Spinner from '$lib/components/ui/Spinner.svelte';

	let firstName = $state(auth.user?.first_name ?? '');
	let lastName = $state(auth.user?.last_name ?? '');
	let phone = $state(auth.user?.phone ?? '');
	let saving = $state(false);
	/** @type {Record<string, any>} */
	let fieldErrors = $state({});

	// Roles grouped by org so the user can see what access they hold.
	/** @param {string} orgId */
	function orgName(orgId) {
		return auth.organizations.find((org) => org.id === orgId)?.name ?? orgId;
	}

	/** @param {SubmitEvent} event */
	async function save(event) {
		event.preventDefault();
		if (saving) return;
		saving = true;
		fieldErrors = {};
		try {
			const updated = await updateProfile({
				first_name: firstName,
				last_name: lastName,
				phone
			});
			auth.user = { ...auth.user, ...updated };
			toasts.success(i18n.t('profile.saved'));
		} catch (err) {
			if (err instanceof ApiError && err.data && typeof err.data === 'object') {
				fieldErrors = err.data;
			}
			toasts.error(errMessage(err) || i18n.t('common.error'));
		} finally {
			saving = false;
		}
	}
</script>

<div class="mx-auto max-w-2xl space-y-8">
	<header>
		<h1 class="text-2xl font-semibold text-slate-900">{i18n.t('profile.title')}</h1>
		<p class="mt-1 text-sm text-slate-500">{auth.user?.email}</p>
	</header>

	<form
		onsubmit={save}
		class="space-y-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
	>
		<div class="grid gap-4 sm:grid-cols-2">
			<div>
				<label for="first" class="mb-1 block text-sm font-medium text-slate-700">
					{i18n.t('profile.firstName')}
				</label>
				<input
					id="first"
					bind:value={firstName}
					maxlength="150"
					class="w-full rounded-lg border-slate-300 text-sm focus:border-brand-500 focus:ring-brand-500"
				/>
			</div>
			<div>
				<label for="last" class="mb-1 block text-sm font-medium text-slate-700">
					{i18n.t('profile.lastName')}
				</label>
				<input
					id="last"
					bind:value={lastName}
					maxlength="150"
					class="w-full rounded-lg border-slate-300 text-sm focus:border-brand-500 focus:ring-brand-500"
				/>
			</div>
		</div>
		<div>
			<label for="phone" class="mb-1 block text-sm font-medium text-slate-700">
				{i18n.t('profile.phone')}
			</label>
			<input
				id="phone"
				bind:value={phone}
				maxlength="32"
				dir="ltr"
				class="w-full rounded-lg border-slate-300 text-sm focus:border-brand-500 focus:ring-brand-500"
			/>
			{#if fieldErrors.phone}
				<p class="mt-1 text-xs text-rose-600">{[].concat(fieldErrors.phone).join(' ')}</p>
			{/if}
		</div>

		<div class="flex justify-end">
			<button
				type="submit"
				disabled={saving}
				class="flex items-center gap-2 rounded-lg bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-60"
			>
				{#if saving}<Spinner size={16} />{/if}
				{saving ? i18n.t('common.saving') : i18n.t('common.save')}
			</button>
		</div>
	</form>

	<section>
		<h2 class="mb-3 text-lg font-semibold text-slate-900">{i18n.t('profile.roles')}</h2>
		<div class="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
			<ul class="divide-y divide-slate-100">
				{#each auth.roles as role (role.id)}
					<li class="flex items-center justify-between px-4 py-3 text-sm">
						<span class="text-slate-700">{orgName(role.organization)}</span>
						<span
							class="rounded-full bg-brand-50 px-2.5 py-0.5 text-xs font-semibold text-brand-700 capitalize"
						>
							{role.role}
						</span>
					</li>
				{:else}
					<li class="px-4 py-6 text-center text-sm text-slate-400">{i18n.t('common.empty')}</li>
				{/each}
			</ul>
		</div>
	</section>
</div>
