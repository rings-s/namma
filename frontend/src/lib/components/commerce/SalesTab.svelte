<script>
	import { i18n } from '$lib/i18n/i18n.svelte.js';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { sales } from '$lib/api/commerce.js';
	import { errMessage, isAbortError } from '$lib/api/client.js';
	import { scopeToOrg } from '$lib/utils/scope.js';
	import { statusVariant, enumLabel } from '$lib/utils/status.js';
	import { money, number, dateTime } from '$lib/utils/format.js';
	import DataState from '$lib/components/ui/DataState.svelte';
	import StatCard from '$lib/components/ui/StatCard.svelte';
	import Badge from '$lib/components/ui/Badge.svelte';
	import Icon from '$lib/components/ui/Icon.svelte';
	import NewSaleModal from './NewSaleModal.svelte';

	/** @type {any[]} */
	let rows = $state([]);
	let loading = $state(true);
	let error = $state('');
	let showNew = $state(false);

	const currency = $derived(auth.currentOrg?.currency ?? 'SAR');

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
			rows = scopeToOrg(await sales.list(undefined, { signal }), orgId);
		} catch (err) {
			if (isAbortError(err)) return;
			error = errMessage(err) || i18n.t('common.error');
		} finally {
			if (!signal?.aborted) loading = false;
		}
	}

	const today = new Date().toISOString().slice(0, 10);
	const todays = $derived(rows.filter((s) => (s.created_at ?? '').slice(0, 10) === today));
	const revenueToday = $derived(todays.reduce((sum, s) => sum + (Number(s.total_amount) || 0), 0));
	const avgSale = $derived(todays.length ? revenueToday / todays.length : 0);

	/** @param {any} sale */
	function onCreated(sale) {
		rows = [sale, ...rows];
		showNew = false;
	}
</script>

<div class="space-y-6">
	<div class="grid grid-cols-1 gap-4 sm:grid-cols-3">
		<StatCard
			label={i18n.t('commerce.stat.salesToday')}
			value={number(todays.length)}
			icon="cart"
			tone="brand"
		/>
		<StatCard
			label={i18n.t('commerce.stat.revenueToday')}
			value={money(revenueToday, currency)}
			icon="dollar"
			tone="sky"
		/>
		<StatCard
			label={i18n.t('commerce.stat.avgSale')}
			value={money(avgSale, currency)}
			icon="trending"
			tone="violet"
		/>
	</div>

	<div class="flex justify-end">
		<button
			onclick={() => (showNew = true)}
			class="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700"
		>
			<Icon name="plus" size={16} />{i18n.t('sales.new')}
		</button>
	</div>

	<DataState
		{loading}
		{error}
		empty={!rows.length}
		emptyText={i18n.t('sales.empty')}
		onRetry={() => auth.currentOrgId && load(auth.currentOrgId)}
	>
		<div class="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
			<table class="w-full text-sm">
				<thead class="border-b border-slate-100 text-xs text-slate-400">
					<tr>
						<th class="px-4 py-3 text-start font-medium">{i18n.t('sales.number')}</th>
						<th class="px-4 py-3 text-start font-medium">{i18n.t('common.date')}</th>
						<th class="px-4 py-3 text-end font-medium">{i18n.t('common.total')}</th>
						<th class="px-4 py-3 text-start font-medium">{i18n.t('common.status')}</th>
					</tr>
				</thead>
				<tbody class="divide-y divide-slate-50">
					{#each rows as s (s.id)}
						<tr class="transition hover:bg-slate-50">
							<td class="px-4 py-3 font-medium text-slate-800" dir="ltr">{s.sale_number || '—'}</td>
							<td class="px-4 py-3 text-slate-500">{dateTime(s.created_at)}</td>
							<td class="px-4 py-3 text-end font-medium text-slate-800 tabular-nums"
								>{money(s.total_amount, currency)}</td
							>
							<td class="px-4 py-3"
								><Badge label={enumLabel('sale', s.status)} variant={statusVariant(s.status)} /></td
							>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	</DataState>
</div>

{#if showNew}
	<NewSaleModal onClose={() => (showNew = false)} {onCreated} />
{/if}
