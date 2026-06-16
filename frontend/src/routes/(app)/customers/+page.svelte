<script>
	import { i18n } from '$lib/i18n/i18n.svelte.js';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { customers } from '$lib/api/customers.js';
	import { errMessage, isAbortError } from '$lib/api/client.js';
	import { scopeToOrg } from '$lib/utils/scope.js';
	import { statusVariant, enumLabel } from '$lib/utils/status.js';
	import { money, number, date } from '$lib/utils/format.js';
	import PageHeader from '$lib/components/ui/PageHeader.svelte';
	import DataState from '$lib/components/ui/DataState.svelte';
	import Badge from '$lib/components/ui/Badge.svelte';
	import Icon from '$lib/components/ui/Icon.svelte';
	import CustomerForm from '$lib/components/customers/CustomerForm.svelte';

	/** @type {any[]} */
	let rows = $state([]);
	let loading = $state(true);
	let error = $state('');
	let search = $state('');
	let sourceFilter = $state('');
	let statusFilter = $state('');
	let showForm = $state(false);

	const SOURCES = ['walk_in', 'online', 'phone', 'referral', 'social', 'import', 'other'];
	const currency = $derived(auth.currentOrg?.currency ?? 'SAR');

	// Reload whenever the active org changes (tenancy is client-side).
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
			rows = scopeToOrg(await customers.list(undefined, { signal }), orgId);
		} catch (err) {
			if (isAbortError(err)) return;
			error = errMessage(err) || i18n.t('common.error');
		} finally {
			if (!signal?.aborted) loading = false;
		}
	}

	const filtered = $derived(
		rows.filter((c) => {
			if (sourceFilter && c.source !== sourceFilter) return false;
			if (statusFilter === 'active' && !c.is_active) return false;
			if (statusFilter === 'inactive' && c.is_active) return false;
			if (search) {
				const q = search.toLowerCase();
				const hay = `${c.first_name} ${c.last_name} ${c.phone} ${c.email}`.toLowerCase();
				if (!hay.includes(q)) return false;
			}
			return true;
		})
	);

	/** @param {any} created */
	function onCreated(created) {
		rows = [created, ...rows];
		showForm = false;
	}
</script>

<div class="mx-auto max-w-6xl">
	<PageHeader title={i18n.t('customers.title')} subtitle={i18n.t('customers.subtitle')}>
		{#snippet actions()}
			<button
				onclick={() => (showForm = true)}
				class="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700"
			>
				<Icon name="plus" size={16} />{i18n.t('customers.new')}
			</button>
		{/snippet}
	</PageHeader>

	<div class="mb-4 flex flex-wrap gap-3">
		<div class="relative min-w-56 flex-1">
			<input
				bind:value={search}
				placeholder={i18n.t('customers.searchPlaceholder')}
				class="w-full rounded-lg border-slate-300 ps-9 text-sm focus:border-brand-500 focus:ring-brand-500"
			/>
			<span
				class="pointer-events-none absolute inset-y-0 start-2.5 flex items-center text-slate-400"
			>
				<Icon name="users" size={16} />
			</span>
		</div>
		<select
			bind:value={sourceFilter}
			class="rounded-lg border-slate-300 text-sm focus:border-brand-500 focus:ring-brand-500"
		>
			<option value="">{i18n.t('customers.col.source')}: {i18n.t('common.all')}</option>
			{#each SOURCES as s (s)}<option value={s}>{i18n.t(`enum.${s}`)}</option>{/each}
		</select>
		<select
			bind:value={statusFilter}
			class="rounded-lg border-slate-300 text-sm focus:border-brand-500 focus:ring-brand-500"
		>
			<option value="">{i18n.t('common.status')}: {i18n.t('common.all')}</option>
			<option value="active">{i18n.t('enum.active')}</option>
			<option value="inactive">{i18n.t('enum.inactive')}</option>
		</select>
	</div>

	<DataState
		{loading}
		{error}
		empty={!filtered.length}
		emptyText={i18n.t('customers.empty')}
		onRetry={() => auth.currentOrgId && load(auth.currentOrgId)}
	>
		<div class="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
			<table class="w-full text-sm">
				<thead class="border-b border-slate-100 text-start text-xs text-slate-400">
					<tr>
						<th class="px-4 py-3 text-start font-medium">{i18n.t('common.name')}</th>
						<th class="px-4 py-3 text-start font-medium">{i18n.t('customers.form.phone')}</th>
						<th class="px-4 py-3 text-start font-medium">{i18n.t('customers.col.source')}</th>
						<th class="px-4 py-3 text-end font-medium">{i18n.t('customers.col.spent')}</th>
						<th class="px-4 py-3 text-end font-medium">{i18n.t('customers.col.visits')}</th>
						<th class="px-4 py-3 text-start font-medium">{i18n.t('customers.col.lastVisit')}</th>
						<th class="px-4 py-3 text-start font-medium">{i18n.t('common.status')}</th>
					</tr>
				</thead>
				<tbody class="divide-y divide-slate-50">
					{#each filtered as c (c.id)}
						<tr class="transition hover:bg-slate-50">
							<td class="px-4 py-3">
								<a href="/customers/{c.id}" class="font-medium text-brand-700 hover:underline">
									{`${c.first_name} ${c.last_name}`.trim() || '—'}
								</a>
							</td>
							<td class="px-4 py-3 text-slate-500" dir="ltr">{c.phone || '—'}</td>
							<td class="px-4 py-3"><Badge label={enumLabel('source', c.source)} /></td>
							<td class="px-4 py-3 text-end text-slate-700">{money(c.total_spent, currency)}</td>
							<td class="px-4 py-3 text-end text-slate-700">{number(c.visit_count)}</td>
							<td class="px-4 py-3 text-slate-500">{date(c.last_visit_at)}</td>
							<td class="px-4 py-3">
								<Badge
									label={c.is_active ? i18n.t('enum.active') : i18n.t('enum.inactive')}
									variant={statusVariant(c.is_active ? 'active' : 'inactive')}
								/>
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	</DataState>
</div>

{#if showForm}
	<CustomerForm onClose={() => (showForm = false)} {onCreated} />
{/if}
