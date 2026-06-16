<script>
	import { i18n } from '$lib/i18n/i18n.svelte.js';
	import { toasts } from '$lib/stores/toast.svelte.js';
	import { aiRecommendations } from '$lib/api/ai.js';
	import { errMessage } from '$lib/api/client.js';
	import { enumLabel, statusVariant } from '$lib/utils/status.js';
	import Badge from '$lib/components/ui/Badge.svelte';
	import Spinner from '$lib/components/ui/Spinner.svelte';

	/**
	 * One AI recommendation. Only `status` is client-writable (active →
	 * dismissed | actioned); every other field is read-only.
	 * @type {{ rec: any; onUpdated: (rec: any) => void }}
	 */
	let { rec, onUpdated } = $props();

	let busy = $state(false);

	/** @param {'dismissed' | 'actioned'} status */
	async function setStatus(status) {
		busy = true;
		try {
			const updated = await aiRecommendations.patch(rec.id, { status });
			toasts.success(i18n.t('ai.rec.updated'));
			onUpdated(updated);
		} catch (err) {
			toasts.error(errMessage(err) || i18n.t('common.error'));
		} finally {
			busy = false;
		}
	}

	// `data` is a free-form evidence payload — render it generically as key/value.
	const evidence = $derived(
		rec.data && typeof rec.data === 'object' ? Object.entries(rec.data) : []
	);
</script>

<div class="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
	<div class="flex items-start justify-between gap-3">
		<div class="min-w-0">
			<div class="flex items-center gap-2">
				<Badge label={enumLabel('priority', rec.priority)} variant={statusVariant(rec.priority)} />
				{#if rec.type}<span class="text-xs text-slate-400">{rec.type}</span>{/if}
			</div>
			<h3 class="mt-2 font-semibold text-slate-900">{rec.title}</h3>
			{#if rec.description}<p class="mt-1 text-sm text-slate-600">{rec.description}</p>{/if}
		</div>
		{#if rec.status !== 'active'}
			<Badge label={enumLabel('rec_status', rec.status)} variant={statusVariant(rec.status)} />
		{/if}
	</div>

	{#if evidence.length}
		<dl class="mt-3 grid grid-cols-2 gap-x-4 gap-y-1 rounded-lg bg-slate-50 p-3 text-xs">
			{#each evidence as [key, value] (key)}
				<div class="flex justify-between gap-2">
					<dt class="text-slate-400">{key}</dt>
					<dd class="font-medium text-slate-700">
						{typeof value === 'object' ? JSON.stringify(value) : value}
					</dd>
				</div>
			{/each}
		</dl>
	{/if}

	{#if rec.status === 'active'}
		<div class="mt-4 flex gap-2">
			<button
				onclick={() => setStatus('actioned')}
				disabled={busy}
				class="flex items-center gap-1.5 rounded-lg bg-brand-600 px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-brand-700 disabled:opacity-60"
			>
				{#if busy}<Spinner size={12} />{/if}{i18n.t('ai.rec.action')}
			</button>
			<button
				onclick={() => setStatus('dismissed')}
				disabled={busy}
				class="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-semibold text-slate-600 transition hover:bg-slate-50 disabled:opacity-60"
			>
				{i18n.t('ai.rec.dismiss')}
			</button>
		</div>
	{/if}
</div>
