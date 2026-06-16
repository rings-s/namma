<script>
	import { i18n } from '$lib/i18n/i18n.svelte.js';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { surveys, npsSummary } from '$lib/api/customers.js';
	import { errMessage, isAbortError } from '$lib/api/client.js';
	import { scopeToOrg } from '$lib/utils/scope.js';
	import { enumLabel, statusVariant } from '$lib/utils/status.js';
	import { number } from '$lib/utils/format.js';
	import PageHeader from '$lib/components/ui/PageHeader.svelte';
	import DataState from '$lib/components/ui/DataState.svelte';
	import Badge from '$lib/components/ui/Badge.svelte';

	/** @type {any[]} */
	let surveyList = $state([]);
	/** @type {any} */
	let nps = $state(null);
	let loading = $state(true);
	let error = $state('');

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
			const [list, npsData] = await Promise.all([
				surveys.list(undefined, { signal }),
				npsSummary(undefined, { signal })
			]);
			surveyList = scopeToOrg(list, orgId);
			nps = npsData;
		} catch (err) {
			if (isAbortError(err)) return;
			error = errMessage(err) || i18n.t('common.error');
		} finally {
			if (!signal?.aborted) loading = false;
		}
	}

	// NPS ranges −100..100; map onto a 0..100% bar for the gauge fill.
	const gaugePct = $derived(nps?.nps != null ? Math.round(((nps.nps + 100) / 200) * 100) : 0);
	const npsColor = $derived(
		nps?.nps == null
			? 'text-slate-400'
			: nps.nps >= 50
				? 'text-emerald-600'
				: nps.nps >= 0
					? 'text-amber-600'
					: 'text-rose-600'
	);
</script>

<div class="mx-auto max-w-5xl">
	<PageHeader title={i18n.t('surveys.title')} subtitle={i18n.t('surveys.subtitle')} />

	<DataState {loading} {error} onRetry={() => auth.currentOrgId && load(auth.currentOrgId)}>
		<!-- NPS dashboard -->
		<section class="mb-8 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
			<h2 class="text-sm font-semibold text-slate-500">{i18n.t('surveys.nps.title')}</h2>
			{#if !nps || nps.responses === 0}
				<p class="mt-4 text-sm text-slate-400">{i18n.t('surveys.nps.none')}</p>
			{:else}
				<div class="mt-4 flex flex-wrap items-center gap-8">
					<div class="text-center">
						<p class="text-5xl font-bold {npsColor}">{nps.nps}</p>
						<div class="mt-3 h-2 w-40 overflow-hidden rounded-full bg-slate-100">
							<div class="h-full rounded-full bg-brand-500" style="width: {gaugePct}%"></div>
						</div>
					</div>
					<dl class="flex gap-8 text-sm">
						<div>
							<dt class="text-slate-400">{i18n.t('surveys.nps.responses')}</dt>
							<dd class="mt-1 text-2xl font-semibold text-slate-900">{number(nps.responses)}</dd>
						</div>
						<div>
							<dt class="text-slate-400">{i18n.t('surveys.nps.promoters')}</dt>
							<dd class="mt-1 text-2xl font-semibold text-emerald-600">
								{number(nps.promoters ?? 0)}
							</dd>
						</div>
						<div>
							<dt class="text-slate-400">{i18n.t('surveys.nps.detractors')}</dt>
							<dd class="mt-1 text-2xl font-semibold text-rose-600">
								{number(nps.detractors ?? 0)}
							</dd>
						</div>
					</dl>
				</div>
			{/if}
		</section>

		<!-- Survey configs -->
		<section>
			<h2 class="mb-3 text-lg font-semibold text-slate-900">{i18n.t('surveys.list.title')}</h2>
			{#if surveyList.length}
				<ul class="space-y-2">
					{#each surveyList as s (s.id)}
						<li
							class="flex items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
						>
							<div>
								<p class="font-medium text-slate-800">{s.name}</p>
								<p class="text-xs text-slate-400">
									{i18n.t('surveys.sendDelay', { hours: s.send_delay_hours })}
								</p>
							</div>
							<div class="flex items-center gap-2">
								<Badge label={enumLabel('survey_type', s.survey_type)} variant="blue" />
								<Badge
									label={s.is_active ? i18n.t('enum.active') : i18n.t('enum.inactive')}
									variant={statusVariant(s.is_active ? 'active' : 'inactive')}
								/>
							</div>
						</li>
					{/each}
				</ul>
			{:else}
				<p
					class="rounded-xl border border-dashed border-slate-200 bg-white p-10 text-center text-sm text-slate-400"
				>
					{i18n.t('surveys.empty')}
				</p>
			{/if}
		</section>
	</DataState>
</div>
