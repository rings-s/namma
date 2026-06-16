<script>
	import { i18n } from '$lib/i18n/i18n.svelte.js';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { queueTickets } from '$lib/api/operations.js';
	import { customers } from '$lib/api/customers.js';
	import { services } from '$lib/api/commerce.js';
	import { errMessage, isAbortError } from '$lib/api/client.js';
	import { scopeToOrg, indexById, customerName } from '$lib/utils/scope.js';
	import { statusVariant, enumLabel } from '$lib/utils/status.js';
	import { number } from '$lib/utils/format.js';
	import DataState from '$lib/components/ui/DataState.svelte';
	import Badge from '$lib/components/ui/Badge.svelte';
	import Icon from '$lib/components/ui/Icon.svelte';

	/** @type {any[]} */
	let rows = $state([]);
	/** @type {Map<string, any>} */
	let customerIndex = $state(new Map());
	/** @type {Map<string, any>} */
	let serviceIndex = $state(new Map());
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
			const [q, c, s] = await Promise.all([
				queueTickets.list(undefined, { signal }),
				customers.list(undefined, { signal }),
				services.list(undefined, { signal })
			]);
			rows = scopeToOrg(q, orgId);
			customerIndex = indexById(scopeToOrg(c, orgId));
			serviceIndex = indexById(scopeToOrg(s, orgId));
		} catch (err) {
			if (isAbortError(err)) return;
			error = errMessage(err) || i18n.t('common.error');
		} finally {
			if (!signal?.aborted) loading = false;
		}
	}

	const ACTIVE = ['waiting', 'called', 'serving'];
	const active = $derived(
		[...rows]
			.filter((t) => ACTIVE.includes(t.status))
			.sort((a, b) => (a.position ?? 0) - (b.position ?? 0))
	);
</script>

<div class="space-y-4">
	<div class="flex justify-end">
		<button
			onclick={() => auth.currentOrgId && load(auth.currentOrgId)}
			class="flex items-center gap-2 rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-50"
		>
			<Icon name="refresh" size={16} />{i18n.t('common.refresh')}
		</button>
	</div>

	<DataState
		{loading}
		{error}
		empty={!active.length}
		emptyText={i18n.t('queue.empty')}
		onRetry={() => auth.currentOrgId && load(auth.currentOrgId)}
	>
		<div class="space-y-2">
			{#each active as t (t.id)}
				<div
					class="flex items-center gap-4 rounded-2xl border border-slate-200 bg-white px-4 py-3 shadow-sm"
				>
					<div
						class="flex size-11 shrink-0 items-center justify-center rounded-xl bg-brand-600 text-base font-bold text-white tabular-nums"
					>
						{number(t.position)}
					</div>
					<div class="min-w-0 flex-1">
						<p class="truncate text-sm font-medium text-slate-800">
							{customerName(customerIndex.get(t.customer))}
						</p>
						<p class="truncate text-xs text-slate-400">
							{i18n.t('queue.ticket')}
							{t.ticket_number}{serviceIndex.get(t.service)?.name
								? ` · ${serviceIndex.get(t.service).name}`
								: ''}
						</p>
					</div>
					<Badge label={enumLabel('queue', t.status)} variant={statusVariant(t.status)} />
				</div>
			{/each}
		</div>
	</DataState>
</div>
