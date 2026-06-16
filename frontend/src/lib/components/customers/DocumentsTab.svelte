<script>
	import { i18n } from '$lib/i18n/i18n.svelte.js';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { customerDocuments } from '$lib/api/customers.js';
	import { errMessage, isAbortError } from '$lib/api/client.js';
	import { dateTime } from '$lib/utils/format.js';
	import DataState from '$lib/components/ui/DataState.svelte';
	import Badge from '$lib/components/ui/Badge.svelte';
	import Icon from '$lib/components/ui/Icon.svelte';

	/** @type {{ customer: any }} */
	let { customer } = $props();

	// Documents (and especially sensitive ones) are gated to admin+. The
	// storage URL is encrypted with no decrypted accessor (MISSING_BACKEND.md),
	// so we list metadata only — no file links.
	const canView = $derived(auth.hasRole('admin'));

	/** @type {any[]} */
	let docs = $state([]);
	let loading = $state(true);
	let error = $state('');

	$effect(() => {
		const customerId = customer?.id;
		if (!customerId || !canView) {
			loading = false;
			return;
		}
		const ctrl = new AbortController();
		load(customerId, ctrl.signal);
		return () => ctrl.abort();
	});

	/** @param {string} customerId @param {AbortSignal} [signal] */
	async function load(customerId, signal) {
		loading = true;
		error = '';
		try {
			const all = await customerDocuments.list(undefined, { signal });
			docs = all.filter((/** @type {any} */ d) => d.customer === customerId);
		} catch (err) {
			if (isAbortError(err)) return;
			error = errMessage(err) || i18n.t('common.error');
		} finally {
			if (!signal?.aborted) loading = false;
		}
	}
</script>

{#if !canView}
	<div class="rounded-xl border border-slate-200 bg-white p-10 text-center text-sm text-slate-400">
		{i18n.t('docs.restricted')}
	</div>
{:else}
	<DataState
		{loading}
		{error}
		empty={!docs.length}
		emptyText={i18n.t('docs.empty')}
		onRetry={() => load(customer.id)}
	>
		<ul class="space-y-2">
			{#each docs as doc (doc.id)}
				<li
					class="flex items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
				>
					<div class="flex items-center gap-3">
						<Icon name="file" size={18} class="text-slate-400" />
						<span class="text-sm font-medium text-slate-800">{doc.document_type}</span>
						{#if doc.is_sensitive}<Badge label={i18n.t('docs.sensitive')} variant="red" />{/if}
					</div>
					<span class="text-xs text-slate-400">{dateTime(doc.created_at)}</span>
				</li>
			{/each}
		</ul>
	</DataState>
{/if}
