<script>
	import { i18n } from '$lib/i18n/i18n.svelte.js';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { appointments, employees } from '$lib/api/operations.js';
	import { services } from '$lib/api/commerce.js';
	import { customers } from '$lib/api/customers.js';
	import { errMessage, isAbortError } from '$lib/api/client.js';
	import { scopeToOrg, indexById, customerName } from '$lib/utils/scope.js';
	import { statusVariant, enumLabel } from '$lib/utils/status.js';
	import { number } from '$lib/utils/format.js';
	import DataState from '$lib/components/ui/DataState.svelte';
	import StatCard from '$lib/components/ui/StatCard.svelte';
	import Badge from '$lib/components/ui/Badge.svelte';
	import Icon from '$lib/components/ui/Icon.svelte';
	import NewAppointmentModal from './NewAppointmentModal.svelte';

	/** @type {any[]} */
	let rows = $state([]);
	/** @type {Map<string, any>} */
	let customerIndex = $state(new Map());
	/** @type {Map<string, any>} */
	let serviceIndex = $state(new Map());
	/** @type {Map<string, any>} */
	let employeeIndex = $state(new Map());
	let loading = $state(true);
	let error = $state('');
	let showNew = $state(false);

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
			const [a, c, s, e] = await Promise.all([
				appointments.list(undefined, { signal }),
				customers.list(undefined, { signal }),
				services.list(undefined, { signal }),
				employees.list(undefined, { signal })
			]);
			rows = scopeToOrg(a, orgId);
			customerIndex = indexById(scopeToOrg(c, orgId));
			serviceIndex = indexById(scopeToOrg(s, orgId));
			employeeIndex = indexById(scopeToOrg(e, orgId));
		} catch (err) {
			if (isAbortError(err)) return;
			error = errMessage(err) || i18n.t('common.error');
		} finally {
			if (!signal?.aborted) loading = false;
		}
	}

	const todayStr = new Date().toISOString().slice(0, 10);

	const sorted = $derived([...rows].sort((a, b) => (a.scheduled_at < b.scheduled_at ? -1 : 1)));
	const todays = $derived(sorted.filter((a) => (a.scheduled_at ?? '').slice(0, 10) === todayStr));
	const upcoming = $derived(sorted.filter((a) => (a.scheduled_at ?? '').slice(0, 10) > todayStr));
	const past = $derived(
		[...sorted].reverse().filter((a) => (a.scheduled_at ?? '').slice(0, 10) < todayStr)
	);
	const confirmedToday = $derived(
		todays.filter((a) => a.status === 'confirmed' || a.status === 'completed').length
	);

	const groups = $derived([
		{ key: 'today', label: i18n.t('cal.today'), list: todays },
		{ key: 'upcoming', label: i18n.t('cal.upcoming'), list: upcoming },
		{ key: 'past', label: i18n.t('cal.past'), list: past.slice(0, 20) }
	]);

	/** @param {string} iso */
	function timeOf(iso) {
		if (!iso) return '—';
		return new Intl.DateTimeFormat(i18n.locale === 'ar' ? 'ar-SA' : 'en-US', {
			hour: '2-digit',
			minute: '2-digit'
		}).format(new Date(iso));
	}

	/** @param {string} iso */
	function dayOf(iso) {
		if (!iso) return '—';
		return new Intl.DateTimeFormat(i18n.locale === 'ar' ? 'ar-SA' : 'en-US', {
			weekday: 'short',
			day: 'numeric',
			month: 'short'
		}).format(new Date(iso));
	}

	/** @param {any} appt */
	function onCreated(appt) {
		rows = [appt, ...rows];
		showNew = false;
	}

	/** @param {any} a */
	function empName(a) {
		const e = employeeIndex.get(a.employee);
		return e ? e.job_title || e.employee_code || '—' : '';
	}
</script>

<div class="space-y-6">
	<div class="grid grid-cols-1 gap-4 sm:grid-cols-3">
		<StatCard
			label={i18n.t('cal.statTotal')}
			value={number(todays.length)}
			icon="calendar"
			tone="brand"
		/>
		<StatCard
			label={i18n.t('cal.statConfirmed')}
			value={number(confirmedToday)}
			icon="check"
			tone="sky"
		/>
		<StatCard
			label={i18n.t('cal.statUpcoming')}
			value={number(upcoming.length)}
			icon="clock"
			tone="violet"
		/>
	</div>

	<div class="flex justify-end">
		<button
			onclick={() => (showNew = true)}
			class="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700"
		>
			<Icon name="plus" size={16} />{i18n.t('cal.new')}
		</button>
	</div>

	<DataState
		{loading}
		{error}
		empty={!rows.length}
		emptyText={i18n.t('cal.empty')}
		onRetry={() => auth.currentOrgId && load(auth.currentOrgId)}
	>
		<div class="space-y-6">
			{#each groups as group (group.key)}
				{#if group.list.length}
					<section>
						<h3 class="mb-2 text-xs font-semibold tracking-wide text-slate-400 uppercase">
							{group.label} · {number(group.list.length)}
						</h3>
						<div class="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
							<ul class="divide-y divide-slate-50">
								{#each group.list as a (a.id)}
									<li class="flex items-center gap-4 px-4 py-3 transition hover:bg-slate-50">
										<div
											class="flex w-16 shrink-0 flex-col items-center rounded-lg bg-brand-50 px-2 py-1.5 text-center"
										>
											<span class="text-sm font-semibold text-brand-700 tabular-nums"
												>{timeOf(a.scheduled_at)}</span
											>
											<span class="text-[10px] text-brand-500">{dayOf(a.scheduled_at)}</span>
										</div>
										<div class="min-w-0 flex-1">
											<p class="truncate text-sm font-medium text-slate-800">
												{customerName(customerIndex.get(a.customer))}
											</p>
											<p class="truncate text-xs text-slate-400">
												{serviceIndex.get(a.service)?.name ?? '—'}{empName(a)
													? ` · ${i18n.t('cal.with')} ${empName(a)}`
													: ''}
											</p>
										</div>
										<Badge
											label={enumLabel('appointment', a.status)}
											variant={statusVariant(a.status)}
										/>
									</li>
								{/each}
							</ul>
						</div>
					</section>
				{/if}
			{/each}
		</div>
	</DataState>
</div>

{#if showNew}
	<NewAppointmentModal onClose={() => (showNew = false)} {onCreated} />
{/if}
