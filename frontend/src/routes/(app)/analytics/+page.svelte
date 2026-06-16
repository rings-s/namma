<script>
	import { i18n } from '$lib/i18n/i18n.svelte.js';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { toasts } from '$lib/stores/toast.svelte.js';
	import { dailyMetrics, goals, employeeLeaderboard, cancelGoal } from '$lib/api/analytics.js';
	import { errMessage, isAbortError } from '$lib/api/client.js';
	import { scopeToOrg } from '$lib/utils/scope.js';
	import { statusVariant, enumLabel } from '$lib/utils/status.js';
	import { money, number, date } from '$lib/utils/format.js';
	import PageHeader from '$lib/components/ui/PageHeader.svelte';
	import DataState from '$lib/components/ui/DataState.svelte';
	import StatCard from '$lib/components/ui/StatCard.svelte';
	import Badge from '$lib/components/ui/Badge.svelte';
	import Icon from '$lib/components/ui/Icon.svelte';

	let loading = $state(true);
	let error = $state('');
	/** @type {any[]} */
	let metricRows = $state([]);
	/** @type {any[]} */
	let goalRows = $state([]);
	/** @type {any[]} */
	let leaders = $state([]);
	/** @type {string | null} */
	let busyId = $state(null);

	const currency = $derived(auth.currentOrg?.currency ?? 'SAR');
	const canManage = $derived(auth.hasRole('manager'));

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
			const [m, g, lb] = await Promise.all([
				dailyMetrics.list(undefined, { signal }),
				goals.list(undefined, { signal }),
				employeeLeaderboard(undefined, { signal }).catch(() => [])
			]);
			metricRows = scopeToOrg(m, orgId);
			goalRows = scopeToOrg(g, orgId);
			leaders = Array.isArray(lb) ? lb : (lb?.results ?? []);
		} catch (err) {
			if (isAbortError(err)) return;
			error = errMessage(err) || i18n.t('common.error');
		} finally {
			if (!signal?.aborted) loading = false;
		}
	}

	// Org-level (branch-null) daily metrics, most recent last, last 14 days.
	const trend = $derived(
		metricRows
			.filter((m) => !m.branch)
			.slice()
			.sort((a, b) => (a.date < b.date ? -1 : 1))
			.slice(-14)
	);
	const latest = $derived(trend.length ? trend[trend.length - 1] : null);
	const maxRevenue = $derived(Math.max(1, ...trend.map((m) => Number(m.total_revenue) || 0)));

	/** @param {any} row */
	function leaderName(row) {
		return row.employee__user__first_name || row.employee__job_title || '—';
	}

	/** @param {string} id */
	async function onCancelGoal(id) {
		busyId = id;
		try {
			await cancelGoal(id);
			toasts.success(i18n.t('an.goalCancelled'));
			if (auth.currentOrgId) load(auth.currentOrgId);
		} catch (err) {
			toasts.error(errMessage(err) || i18n.t('common.error'));
		} finally {
			busyId = null;
		}
	}

	/** @param {string} iso */
	function shortDay(iso) {
		if (!iso) return '';
		return new Intl.DateTimeFormat(i18n.locale === 'ar' ? 'ar-SA' : 'en-US', {
			day: 'numeric'
		}).format(new Date(iso));
	}
</script>

<div class="mx-auto max-w-6xl space-y-6">
	<PageHeader title={i18n.t('an.title')} subtitle={i18n.t('an.subtitle')} />

	<DataState {loading} {error} onRetry={() => auth.currentOrgId && load(auth.currentOrgId)}>
		<div class="grid grid-cols-1 gap-4 sm:grid-cols-3">
			<StatCard
				label={i18n.t('an.stat.revenue')}
				value={money(latest?.total_revenue ?? 0, currency)}
				icon="dollar"
				tone="brand"
			/>
			<StatCard
				label={i18n.t('an.stat.appointments')}
				value={number(latest?.total_appointments ?? 0)}
				icon="calendar"
				tone="sky"
			/>
			<StatCard
				label={i18n.t('an.stat.newCustomers')}
				value={number(latest?.new_customers ?? 0)}
				icon="users"
				tone="violet"
			/>
		</div>

		<!-- Revenue trend -->
		<section class="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
			<h2 class="mb-4 text-sm font-semibold text-slate-800">{i18n.t('an.revenueTrend')}</h2>
			{#if trend.length}
				<div class="flex h-44 items-end gap-1.5">
					{#each trend as m (m.id)}
						<div class="group flex flex-1 flex-col items-center gap-1.5">
							<div class="relative flex w-full flex-1 items-end">
								<div
									class="w-full rounded-t-md bg-gradient-to-t from-brand-500 to-brand-400 transition-all group-hover:from-brand-600 group-hover:to-brand-500"
									style="height: {Math.max(
										2,
										((Number(m.total_revenue) || 0) / maxRevenue) * 100
									)}%"
									title={money(m.total_revenue, currency)}
								></div>
							</div>
							<span class="text-[10px] text-slate-400 tabular-nums">{shortDay(m.date)}</span>
						</div>
					{/each}
				</div>
			{:else}
				<p class="py-10 text-center text-sm text-slate-400">{i18n.t('an.noTrend')}</p>
			{/if}
		</section>

		<div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
			<!-- Leaderboard -->
			<section class="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
				<header class="border-b border-slate-100 px-5 py-3.5">
					<h2 class="text-sm font-semibold text-slate-800">{i18n.t('an.leaderboard')}</h2>
					<p class="text-xs text-slate-400">{i18n.t('an.leaderboard.sub')}</p>
				</header>
				{#if leaders.length}
					<ul class="divide-y divide-slate-50">
						{#each leaders.slice(0, 8) as row, idx (row.employee_id)}
							<li class="flex items-center gap-3 px-5 py-3">
								<span
									class="flex size-7 items-center justify-center rounded-full text-xs font-bold {idx ===
									0
										? 'bg-amber-100 text-amber-700'
										: 'bg-slate-100 text-slate-500'}">{idx + 1}</span
								>
								<div class="min-w-0 flex-1">
									<p class="truncate text-sm font-medium text-slate-800">{leaderName(row)}</p>
									<p class="text-xs text-slate-400">
										{i18n.t('an.col.appointments')}: {number(row.total_appointments ?? 0)}
									</p>
								</div>
								<span class="text-sm font-semibold text-slate-800 tabular-nums"
									>{money(row.total_revenue ?? 0, currency)}</span
								>
							</li>
						{/each}
					</ul>
				{:else}
					<p class="px-5 py-10 text-center text-sm text-slate-400">{i18n.t('an.noLeaderboard')}</p>
				{/if}
			</section>

			<!-- Goals -->
			<section class="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
				<header class="border-b border-slate-100 px-5 py-3.5 text-sm font-semibold text-slate-800">
					{i18n.t('an.goals')}
				</header>
				{#if goalRows.length}
					<ul class="divide-y divide-slate-50">
						{#each goalRows as g (g.id)}
							<li class="px-5 py-3.5">
								<div class="flex items-center justify-between gap-2">
									<span class="truncate text-sm font-medium text-slate-800">{g.name}</span>
									<div class="flex items-center gap-2">
										<Badge label={enumLabel('goal', g.status)} variant={statusVariant(g.status)} />
										{#if canManage && g.status === 'active'}
											<button
												onclick={() => onCancelGoal(g.id)}
												disabled={busyId === g.id}
												class="rounded-md p-1 text-slate-300 transition hover:bg-rose-50 hover:text-rose-600"
												aria-label={i18n.t('an.cancelGoal')}
											>
												<Icon name="x" size={15} />
											</button>
										{/if}
									</div>
								</div>
								<div class="mt-2 h-2 w-full overflow-hidden rounded-full bg-slate-100">
									<div
										class="h-full rounded-full bg-brand-500"
										style="width: {Math.min(100, g.progress_percent ?? 0)}%"
									></div>
								</div>
								<div class="mt-1 flex justify-between text-xs text-slate-400">
									<span>{number(g.current_value)} / {number(g.target_value)}</span>
									<span>{date(g.period_end)}</span>
								</div>
							</li>
						{/each}
					</ul>
				{:else}
					<p class="px-5 py-10 text-center text-sm text-slate-400">{i18n.t('an.noGoals')}</p>
				{/if}
			</section>
		</div>
	</DataState>
</div>
