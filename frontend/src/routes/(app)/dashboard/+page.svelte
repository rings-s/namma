<script>
	import { auth } from '$lib/stores/auth.svelte.js';
	import { i18n } from '$lib/i18n/i18n.svelte.js';
	import { listDailyMetrics, listGoals } from '$lib/api/analytics.js';
	import { errMessage, isAbortError } from '$lib/api/client.js';
	import { money, number } from '$lib/utils/format.js';
	import Spinner from '$lib/components/ui/Spinner.svelte';

	let loading = $state(true);
	let error = $state('');
	/** @type {any[]} */
	let metrics = $state([]);
	/** @type {any[]} */
	let goals = $state([]);

	// Refetch whenever the active organization changes. The backend has no org
	// query param, so we scope to the current org client-side.
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
			const [allMetrics, allGoals] = await Promise.all([
				listDailyMetrics({ signal }),
				listGoals({ signal })
			]);
			metrics = allMetrics.filter((/** @type {any} */ row) => row.organization === orgId);
			goals = allGoals.filter((/** @type {any} */ row) => row.organization === orgId);
		} catch (err) {
			if (isAbortError(err)) return;
			error = errMessage(err) || i18n.t('common.error');
		} finally {
			if (!signal?.aborted) loading = false;
		}
	}

	// Most recent day on record for the org-level (branch-null) rollup, falling
	// back to the latest metric of any branch.
	const latest = $derived(
		[...metrics].sort((a, b) => (a.date < b.date ? 1 : -1)).find((m) => !m.branch) ??
			[...metrics].sort((a, b) => (a.date < b.date ? 1 : -1))[0] ??
			null
	);

	const currency = $derived(auth.currentOrg?.currency ?? 'SAR');

	const cards = $derived(
		latest
			? [
					{ key: 'dashboard.metric.appointments', value: number(latest.total_appointments) },
					{ key: 'dashboard.metric.completed', value: number(latest.completed_appointments) },
					{ key: 'dashboard.metric.cancelled', value: number(latest.cancelled_appointments) },
					{ key: 'dashboard.metric.revenue', value: money(latest.total_revenue, currency) },
					{ key: 'dashboard.metric.customers', value: number(latest.total_customers) },
					{ key: 'dashboard.metric.newCustomers', value: number(latest.new_customers) }
				]
			: []
	);
</script>

<div class="mx-auto max-w-6xl space-y-8">
	<header>
		<h1 class="text-2xl font-semibold text-slate-900">{i18n.t('dashboard.title')}</h1>
		<p class="mt-1 text-sm text-slate-500">
			{i18n.t('dashboard.subtitle', { org: auth.currentOrg?.name ?? '' })}
		</p>
	</header>

	{#if loading}
		<div class="flex items-center gap-3 py-16 text-slate-400">
			<Spinner size={24} /><span class="text-sm">{i18n.t('common.loading')}</span>
		</div>
	{:else if error}
		<div class="rounded-xl border border-rose-200 bg-rose-50 p-6 text-sm text-rose-700">
			{error}
			<button
				class="ms-2 font-semibold underline"
				onclick={() => auth.currentOrgId && load(auth.currentOrgId)}
			>
				{i18n.t('common.retry')}
			</button>
		</div>
	{:else}
		<!-- Metric cards -->
		{#if cards.length}
			<section class="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
				{#each cards as card (card.key)}
					<div class="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
						<p class="text-xs font-medium text-slate-400">{i18n.t(card.key)}</p>
						<p class="mt-2 text-xl font-semibold text-slate-900">{card.value}</p>
					</div>
				{/each}
			</section>
		{:else}
			<div
				class="rounded-xl border border-dashed border-slate-200 bg-white p-10 text-center text-sm text-slate-400"
			>
				{i18n.t('dashboard.noMetrics')}
			</div>
		{/if}

		<!-- Goals -->
		<section>
			<h2 class="mb-3 text-lg font-semibold text-slate-900">{i18n.t('dashboard.goals')}</h2>
			{#if goals.length}
				<div class="space-y-3">
					{#each goals as goal (goal.id)}
						<div class="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
							<div class="flex items-center justify-between gap-3">
								<span class="font-medium text-slate-800">{goal.name}</span>
								<span class="text-sm text-slate-500">
									{number(goal.current_value)} / {number(goal.target_value)}
								</span>
							</div>
							<div class="mt-2 h-2 w-full overflow-hidden rounded-full bg-slate-100">
								<div
									class="h-full rounded-full bg-brand-500"
									style="width: {Math.min(100, goal.progress_percent ?? 0)}%"
								></div>
							</div>
						</div>
					{/each}
				</div>
			{:else}
				<div
					class="rounded-xl border border-dashed border-slate-200 bg-white p-10 text-center text-sm text-slate-400"
				>
					{i18n.t('dashboard.noGoals')}
				</div>
			{/if}
		</section>
	{/if}
</div>
