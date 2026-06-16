<script>
	import { i18n } from '$lib/i18n/i18n.svelte.js';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { toasts } from '$lib/stores/toast.svelte.js';
	import { organizations, branches, organizationSettings } from '$lib/api/organizations.js';
	import { errMessage, isAbortError } from '$lib/api/client.js';
	import { scopeToOrg } from '$lib/utils/scope.js';
	import PageHeader from '$lib/components/ui/PageHeader.svelte';
	import Tabs from '$lib/components/ui/Tabs.svelte';
	import DataState from '$lib/components/ui/DataState.svelte';
	import Field from '$lib/components/ui/Field.svelte';
	import Icon from '$lib/components/ui/Icon.svelte';
	import Modal from '$lib/components/ui/Modal.svelte';
	import Spinner from '$lib/components/ui/Spinner.svelte';

	const INPUT =
		'w-full rounded-lg border-slate-300 text-sm focus:border-brand-500 focus:ring-brand-500';
	const canAdmin = $derived(auth.hasRole('admin'));

	let active = $state('profile');
	let loading = $state(true);
	let error = $state('');
	let savingOrg = $state(false);
	let savingPrefs = $state(false);

	/** @type {any} */
	let org = $state(null);
	/** @type {any[]} */
	let branchRows = $state([]);
	/** @type {any} */
	let prefs = $state(null);

	// branch modal
	let showBranch = $state(false);
	let savingBranch = $state(false);
	let brName = $state('');
	let brAddress = $state('');
	let brCity = $state('');
	let brCountry = $state('');
	let brPhone = $state('');

	const tabs = $derived([
		{ key: 'profile', label: i18n.t('set.tab.profile') },
		{ key: 'branches', label: i18n.t('set.tab.branches') },
		{ key: 'preferences', label: i18n.t('set.tab.preferences') }
	]);

	$effect(() => {
		const orgId = auth.currentOrgId;
		if (!orgId) return;
		const ctrl = new AbortController();
		load(orgId, ctrl.signal);
		return () => ctrl.abort();
	});

	/** @param {string} orgId @param {AbortSignal} [signal] */
	async function load(orgId, signal) {
		loading = true;
		error = '';
		try {
			const [o, b, s] = await Promise.all([
				organizations.get(orgId, undefined, { signal }),
				branches.list(undefined, { signal }),
				organizationSettings.list(undefined, { signal })
			]);
			org = o;
			branchRows = scopeToOrg(b, orgId);
			prefs = scopeToOrg(s, orgId)[0] ?? null;
		} catch (err) {
			if (isAbortError(err)) return;
			error = errMessage(err) || i18n.t('common.error');
		} finally {
			if (!signal?.aborted) loading = false;
		}
	}

	async function saveOrg() {
		if (!org) return;
		savingOrg = true;
		try {
			const updated = await organizations.patch(org.id, {
				name: org.name,
				industry: org.industry,
				website: org.website,
				email: org.email,
				phone: org.phone,
				vat_number: org.vat_number,
				commercial_registration_number: org.commercial_registration_number,
				city: org.city
			});
			org = updated;
			await auth.loadSession();
			toasts.success(i18n.t('set.saved'));
		} catch (err) {
			toasts.error(errMessage(err) || i18n.t('common.error'));
		} finally {
			savingOrg = false;
		}
	}

	async function savePrefs() {
		savingPrefs = true;
		try {
			const payload = {
				booking_lead_time: Number(prefs.booking_lead_time) || 0,
				reminder_hours: Number(prefs.reminder_hours) || 0,
				auto_confirm_bookings: !!prefs.auto_confirm_bookings
			};
			if (prefs?.id) {
				prefs = await organizationSettings.patch(prefs.id, payload);
			} else {
				prefs = await organizationSettings.create({ organization: auth.currentOrgId, ...payload });
			}
			toasts.success(i18n.t('common.saved'));
		} catch (err) {
			toasts.error(errMessage(err) || i18n.t('common.error'));
		} finally {
			savingPrefs = false;
		}
	}

	async function createBranch() {
		savingBranch = true;
		try {
			const row = await branches.create({
				organization: auth.currentOrgId,
				name: brName,
				address: brAddress,
				city: brCity,
				country: brCountry,
				phone: brPhone
			});
			branchRows = [...branchRows, row];
			toasts.success(i18n.t('set.branchCreated'));
			showBranch = false;
			brName = brAddress = brCity = brCountry = brPhone = '';
		} catch (err) {
			toasts.error(errMessage(err) || i18n.t('common.error'));
		} finally {
			savingBranch = false;
		}
	}
</script>

<div class="mx-auto max-w-4xl">
	<PageHeader title={i18n.t('set.title')} subtitle={i18n.t('set.subtitle')} />

	<div class="mb-6">
		<Tabs {tabs} {active} onSelect={(k) => (active = k)} />
	</div>

	{#if !canAdmin}
		<p class="mb-4 rounded-lg bg-amber-50 px-4 py-2.5 text-sm text-amber-700">
			{i18n.t('set.adminOnly')}
		</p>
	{/if}

	<DataState {loading} {error} onRetry={() => auth.currentOrgId && load(auth.currentOrgId)}>
		{#if active === 'profile' && org}
			<div class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
				<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
					<Field label={i18n.t('set.orgName')}
						><input bind:value={org.name} disabled={!canAdmin} class={INPUT} /></Field
					>
					<Field label={i18n.t('set.industry')} optional
						><input bind:value={org.industry} disabled={!canAdmin} class={INPUT} /></Field
					>
					<Field label={i18n.t('set.website')} optional
						><input bind:value={org.website} disabled={!canAdmin} class={INPUT} dir="ltr" /></Field
					>
					<Field label={i18n.t('set.phone')} optional
						><input bind:value={org.phone} disabled={!canAdmin} class={INPUT} dir="ltr" /></Field
					>
					<Field label={i18n.t('set.email')} optional
						><input bind:value={org.email} disabled={!canAdmin} class={INPUT} dir="ltr" /></Field
					>
					<Field label={i18n.t('set.city')} optional
						><input bind:value={org.city} disabled={!canAdmin} class={INPUT} /></Field
					>
					<Field label={i18n.t('set.vat')} optional
						><input
							bind:value={org.vat_number}
							disabled={!canAdmin}
							class={INPUT}
							dir="ltr"
						/></Field
					>
					<Field label={i18n.t('set.cr')} optional
						><input
							bind:value={org.commercial_registration_number}
							disabled={!canAdmin}
							class={INPUT}
							dir="ltr"
						/></Field
					>
				</div>
				{#if canAdmin}
					<div class="mt-6 flex justify-end">
						<button
							onclick={saveOrg}
							disabled={savingOrg}
							class="flex items-center gap-2 rounded-lg bg-brand-600 px-5 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-60"
						>
							{#if savingOrg}<Spinner size={16} />{/if}{i18n.t('common.save')}
						</button>
					</div>
				{/if}
			</div>
		{:else if active === 'branches'}
			{#if canAdmin}
				<div class="mb-4 flex justify-end">
					<button
						onclick={() => (showBranch = true)}
						class="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700"
					>
						<Icon name="plus" size={16} />{i18n.t('set.newBranch')}
					</button>
				</div>
			{/if}
			{#if branchRows.length}
				<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
					{#each branchRows as b (b.id)}
						<div
							class="flex items-start gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"
						>
							<span
								class="flex size-10 items-center justify-center rounded-xl bg-brand-50 text-brand-600"
								><Icon name="building" size={18} /></span
							>
							<div class="min-w-0">
								<p class="truncate text-sm font-semibold text-slate-800">{b.name}</p>
								{#if b.address}<p class="truncate text-xs text-slate-400">{b.address}</p>{/if}
								{#if b.city}<p class="text-xs text-slate-400">
										{b.city}{b.country ? `, ${b.country}` : ''}
									</p>{/if}
							</div>
						</div>
					{/each}
				</div>
			{:else}
				<div
					class="rounded-xl border border-dashed border-slate-200 bg-white p-10 text-center text-sm text-slate-400"
				>
					{i18n.t('set.noBranches')}
				</div>
			{/if}
		{:else if active === 'preferences'}
			<div class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
				<p class="mb-5 text-sm text-slate-400">{i18n.t('set.prefsNote')}</p>
				<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
					<Field label={i18n.t('set.leadTime')}>
						<input
							type="number"
							min="0"
							step="1"
							value={prefs?.booking_lead_time ?? 0}
							disabled={!canAdmin}
							oninput={(e) =>
								(prefs = { ...(prefs ?? {}), booking_lead_time: e.currentTarget.value })}
							class={INPUT}
							dir="ltr"
						/>
					</Field>
					<Field label={i18n.t('set.reminderHours')}>
						<input
							type="number"
							min="0"
							step="1"
							value={prefs?.reminder_hours ?? 24}
							disabled={!canAdmin}
							oninput={(e) => (prefs = { ...(prefs ?? {}), reminder_hours: e.currentTarget.value })}
							class={INPUT}
							dir="ltr"
						/>
					</Field>
				</div>
				<label class="mt-4 flex items-center gap-2 text-sm text-slate-700">
					<input
						type="checkbox"
						checked={!!prefs?.auto_confirm_bookings}
						disabled={!canAdmin}
						onchange={(e) =>
							(prefs = { ...(prefs ?? {}), auto_confirm_bookings: e.currentTarget.checked })}
						class="rounded border-slate-300 text-brand-600 focus:ring-brand-500"
					/>
					{i18n.t('set.autoConfirm')}
				</label>
				{#if canAdmin}
					<div class="mt-6 flex justify-end">
						<button
							onclick={savePrefs}
							disabled={savingPrefs}
							class="flex items-center gap-2 rounded-lg bg-brand-600 px-5 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-60"
						>
							{#if savingPrefs}<Spinner size={16} />{/if}{i18n.t('common.save')}
						</button>
					</div>
				{/if}
			</div>
		{/if}
	</DataState>
</div>

{#if showBranch}
	<Modal title={i18n.t('set.newBranch')} onClose={() => (showBranch = false)}>
		<div class="space-y-4">
			<Field label={i18n.t('set.branchName')}
				><input bind:value={brName} maxlength="255" class={INPUT} /></Field
			>
			<Field label={i18n.t('set.address')} optional
				><input bind:value={brAddress} maxlength="500" class={INPUT} /></Field
			>
			<div class="grid grid-cols-2 gap-4">
				<Field label={i18n.t('set.city')} optional
					><input bind:value={brCity} class={INPUT} /></Field
				>
				<Field label={i18n.t('set.country')} optional
					><input bind:value={brCountry} class={INPUT} /></Field
				>
			</div>
			<Field label={i18n.t('set.phone')} optional
				><input bind:value={brPhone} class={INPUT} dir="ltr" /></Field
			>
		</div>
		{#snippet footer()}
			<button
				onclick={() => (showBranch = false)}
				class="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-50"
				>{i18n.t('common.cancel')}</button
			>
			<button
				onclick={createBranch}
				disabled={savingBranch || !brName}
				class="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-60"
			>
				{#if savingBranch}<Spinner size={16} />{/if}{i18n.t('common.create')}
			</button>
		{/snippet}
	</Modal>
{/if}
