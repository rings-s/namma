<script>
	import { i18n } from '$lib/i18n/i18n.svelte.js';
	import { surveyResponses } from '$lib/api/customers.js';
	import { errMessage, isAbortError } from '$lib/api/client.js';
	import { enumLabel, statusVariant } from '$lib/utils/status.js';
	import { dateTime } from '$lib/utils/format.js';
	import DataState from '$lib/components/ui/DataState.svelte';
	import Badge from '$lib/components/ui/Badge.svelte';

	/** @type {{ customer: any }} */
	let { customer } = $props();

	/** @type {any[]} */
	let responses = $state([]);
	let loading = $state(true);
	let error = $state('');

	$effect(() => {
		const customerId = customer?.id;
		if (!customerId) return;
		const ctrl = new AbortController();
		load(customerId, ctrl.signal);
		return () => ctrl.abort();
	});

	/** @param {string} customerId @param {AbortSignal} [signal] */
	async function load(customerId, signal) {
		loading = true;
		error = '';
		try {
			const all = await surveyResponses.list(undefined, { signal });
			responses = all.filter((/** @type {any} */ r) => r.customer === customerId);
		} catch (err) {
			if (isAbortError(err)) return;
			error = errMessage(err) || i18n.t('common.error');
		} finally {
			if (!signal?.aborted) loading = false;
		}
	}
</script>

<DataState
	{loading}
	{error}
	empty={!responses.length}
	emptyText={i18n.t('surveyResp.empty')}
	onRetry={() => load(customer.id)}
>
	<ul class="space-y-2">
		{#each responses as r (r.id)}
			<li class="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
				<div class="flex items-center justify-between gap-3">
					<div class="flex items-center gap-3">
						{#if r.score !== null && r.score !== undefined}
							<span class="text-lg font-semibold text-slate-900">{r.score}</span>
							<span class="text-xs text-slate-400">{i18n.t('surveyResp.score')}</span>
						{/if}
						{#if r.sentiment}
							<Badge
								label={enumLabel('sentiment', r.sentiment)}
								variant={statusVariant(r.sentiment)}
							/>
						{/if}
					</div>
					<span class="text-xs text-slate-400">{dateTime(r.responded_at || r.created_at)}</span>
				</div>
				{#if r.comment}<p class="mt-2 text-sm text-slate-600">{r.comment}</p>{/if}
			</li>
		{/each}
	</ul>
</DataState>
