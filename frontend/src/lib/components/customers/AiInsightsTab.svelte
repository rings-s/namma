<script>
	import { i18n } from '$lib/i18n/i18n.svelte.js';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { aiRecommendations } from '$lib/api/ai.js';
	import { errMessage, isAbortError } from '$lib/api/client.js';
	import { scopeToOrg } from '$lib/utils/scope.js';
	import DataState from '$lib/components/ui/DataState.svelte';
	import RecommendationCard from '$lib/components/ai/RecommendationCard.svelte';

	/** @type {{ customer: any }} */
	let { customer } = $props();

	/** @type {any[]} */
	let recs = $state([]);
	let loading = $state(true);
	let error = $state('');

	$effect(() => {
		const customerId = customer?.id;
		if (!customerId) return;
		const ctrl = new AbortController();
		load(customerId, ctrl.signal);
		return () => ctrl.abort();
	});

	/**
	 * AIRecommendation has no customer FK; the customer link (when present) lives
	 * in the evidence `data` payload. Match on common id keys, best-effort.
	 * @param {string} customerId @param {AbortSignal} [signal]
	 */
	async function load(customerId, signal) {
		loading = true;
		error = '';
		try {
			const all = scopeToOrg(await aiRecommendations.list(undefined, { signal }), auth.currentOrgId);
			recs = all.filter((/** @type {any} */ r) => {
				if (r.status !== 'active') return false;
				const d = r.data ?? {};
				return d.customer === customerId || d.customer_id === customerId;
			});
		} catch (err) {
			if (isAbortError(err)) return;
			error = errMessage(err) || i18n.t('common.error');
		} finally {
			if (!signal?.aborted) loading = false;
		}
	}

	/** @param {any} updated */
	function onUpdated(updated) {
		recs = recs.filter((r) => r.id !== updated.id);
	}
</script>

<DataState
	{loading}
	{error}
	empty={!recs.length}
	emptyText={i18n.t('ai.rec.empty')}
	onRetry={() => load(customer.id)}
>
	<div class="space-y-3">
		{#each recs as rec (rec.id)}
			<RecommendationCard {rec} {onUpdated} />
		{/each}
	</div>
</DataState>
