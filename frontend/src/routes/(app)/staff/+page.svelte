<script>
	import { i18n } from '$lib/i18n/i18n.svelte.js';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { employees, commissionRules, commissionEntries } from '$lib/api/operations.js';
	import { errMessage, isAbortError } from '$lib/api/client.js';
	import { scopeToOrg, indexById } from '$lib/utils/scope.js';
	import { statusVariant, enumLabel } from '$lib/utils/status.js';
	import { money, number } from '$lib/utils/format.js';
	import PageHeader from '$lib/components/ui/PageHeader.svelte';
	import Tabs from '$lib/components/ui/Tabs.svelte';
	import DataState from '$lib/components/ui/DataState.svelte';
	import StatCard from '$lib/components/ui/StatCard.svelte';
	import Badge from '$lib/components/ui/Badge.svelte';
	import Icon from '$lib/components/ui/Icon.svelte';
	import NewEmployeeModal from '$lib/components/staff/NewEmployeeModal.svelte';

	let active = $state('team');
	let loading = $state(true);
	let error = $state('');
	/** @type {any[]} */
	let employeeRows = $state([]);
	/** @type {any[]} */
	let ruleRows = $state([]);
	/** @type {any[]} */
	let entryRows = $state([]);
	/** @type {Map<string, any>} */
	let employeeIndex = $state(new Map());
	let showNew = $state(false);

	const currency = $derived(auth.currentOrg?.currency ?? 'SAR');
	const canManage = $derived(auth.hasRole('manager'));

	const tabs = $derived([
		{ key: 'team', label: i18n.t('staff.tab.team') },
		{ key: 'commissions', label: i18n.t('staff.tab.commissions') }
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
			const [e, r, en] = await Promise.all([
				employees.list(undefined, { signal }),
				commissionRules.list(undefined, { signal }),
				commissionEntries.list(undefined, { signal })
			]);
			employeeRows = scopeToOrg(e, orgId);
			ruleRows = scopeToOrg(r, orgId);
			entryRows = scopeToOrg(en, orgId);
			employeeIndex = indexById(employeeRows);
		} catch (err) {
			if (isAbortError(err)) return;
			error = errMessage(err) || i18n.t('common.error');
		} finally {
			if (!signal?.aborted) loading = false;
		}
	}

	const activeStaff = $derived(employeeRows.filter((e) => e.is_active !== false));
	const saudiPct = $derived(
		activeStaff.length
			? Math.round((activeStaff.filter((e) => e.is_saudi).length / activeStaff.length) * 100)
			: 0
	);
	const payroll = $derived(
		activeStaff.reduce((sum, e) => sum + (Number(e.monthly_salary) || 0), 0)
	);

	/** @param {any} e */
	function empName(e) {
		return e?.job_title || e?.employee_code || (e ? e.id.slice(0, 8) : '—');
	}

	/** @param {any} created */
	function onCreated(created) {
		employeeRows = [created, ...employeeRows];
		showNew = false;
	}
</script>

<div class="mx-auto max-w-6xl">
	<PageHeader title={i18n.t('staff.title')} subtitle={i18n.t('staff.subtitle')} />

	<div class="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
		<StatCard
			label={i18n.t('staff.stat.headcount')}
			value={number(activeStaff.length)}
			icon="badge"
			tone="brand"
		/>
		<StatCard
			label={i18n.t('staff.stat.saudization')}
			value={`${saudiPct}%`}
			icon="shield"
			tone="sky"
		/>
		<StatCard
			label={i18n.t('staff.stat.payroll')}
			value={money(payroll, currency)}
			icon="dollar"
			tone="violet"
		/>
	</div>

	<div class="mb-4 flex items-center justify-between gap-3">
		<Tabs {tabs} {active} onSelect={(k) => (active = k)} />
		{#if active === 'team' && canManage}
			<button
				onclick={() => (showNew = true)}
				class="flex shrink-0 items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700"
			>
				<Icon name="plus" size={16} />{i18n.t('staff.new')}
			</button>
		{/if}
	</div>

	<DataState {loading} {error} onRetry={() => auth.currentOrgId && load(auth.currentOrgId)}>
		{#if active === 'team'}
			{#if employeeRows.length}
				<div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
					{#each employeeRows as e (e.id)}
						<div
							class="flex items-center gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"
						>
							<span
								class="flex size-11 items-center justify-center rounded-full bg-brand-50 text-sm font-bold text-brand-700"
							>
								{(e.job_title || e.employee_code || '?').slice(0, 2).toUpperCase()}
							</span>
							<div class="min-w-0 flex-1">
								<p class="truncate text-sm font-semibold text-slate-800">{e.job_title || '—'}</p>
								<p class="truncate text-xs text-slate-400">
									{e.department || e.employee_code || ''}
								</p>
							</div>
							<div class="flex flex-col items-end gap-1">
								{#if e.is_saudi}<Badge label="🇸🇦" variant="green" />{/if}
								{#if e.is_active === false}<Badge label={i18n.t('enum.inactive')} />{/if}
							</div>
						</div>
					{/each}
				</div>
			{:else}
				<div
					class="rounded-xl border border-dashed border-slate-200 bg-white p-10 text-center text-sm text-slate-400"
				>
					{i18n.t('staff.empty')}
				</div>
			{/if}
		{:else}
			<div class="space-y-6">
				<!-- Rules -->
				<section class="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
					<header
						class="border-b border-slate-100 px-5 py-3.5 text-sm font-semibold text-slate-800"
					>
						{i18n.t('staff.rules')}
					</header>
					{#if ruleRows.length}
						<table class="w-full text-sm">
							<thead class="border-b border-slate-100 text-xs text-slate-400">
								<tr>
									<th class="px-5 py-2.5 text-start font-medium">{i18n.t('common.name')}</th>
									<th class="px-5 py-2.5 text-start font-medium">{i18n.t('staff.basis')}</th>
									<th class="px-5 py-2.5 text-start font-medium">{i18n.t('staff.appliesTo')}</th>
									<th class="px-5 py-2.5 text-end font-medium">{i18n.t('staff.priority')}</th>
								</tr>
							</thead>
							<tbody class="divide-y divide-slate-50">
								{#each ruleRows as r (r.id)}
									<tr>
										<td class="px-5 py-2.5 font-medium text-slate-800">{r.name}</td>
										<td class="px-5 py-2.5"><Badge label={enumLabel('basis', r.basis)} /></td>
										<td class="px-5 py-2.5 text-slate-600"
											>{enumLabel('appliesTo', r.applies_to)}</td
										>
										<td class="px-5 py-2.5 text-end text-slate-500 tabular-nums"
											>{number(r.priority)}</td
										>
									</tr>
								{/each}
							</tbody>
						</table>
					{:else}
						<p class="px-5 py-8 text-center text-sm text-slate-400">{i18n.t('staff.noRules')}</p>
					{/if}
				</section>

				<!-- Entries -->
				<section class="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
					<header
						class="border-b border-slate-100 px-5 py-3.5 text-sm font-semibold text-slate-800"
					>
						{i18n.t('staff.entries')}
					</header>
					{#if entryRows.length}
						<table class="w-full text-sm">
							<tbody class="divide-y divide-slate-50">
								{#each entryRows as en (en.id)}
									<tr>
										<td class="px-5 py-2.5 text-slate-700"
											>{empName(employeeIndex.get(en.employee))}</td
										>
										<td class="px-5 py-2.5"
											><Badge
												label={enumLabel('entryType', en.entry_type)}
												variant={statusVariant(en.entry_type)}
											/></td
										>
										<td class="px-5 py-2.5 text-end font-medium text-slate-800 tabular-nums"
											>{money(en.amount, currency)}</td
										>
									</tr>
								{/each}
							</tbody>
						</table>
					{:else}
						<p class="px-5 py-8 text-center text-sm text-slate-400">{i18n.t('staff.noEntries')}</p>
					{/if}
				</section>
			</div>
		{/if}
	</DataState>
</div>

{#if showNew}
	<NewEmployeeModal onClose={() => (showNew = false)} {onCreated} />
{/if}
