<script>
	import { i18n } from '$lib/i18n/i18n.svelte.js';
	import { clinicalNotes } from '$lib/api/customers.js';
	import { errMessage, isAbortError } from '$lib/api/client.js';
	import { enumLabel } from '$lib/utils/status.js';
	import { dateTime } from '$lib/utils/format.js';
	import DataState from '$lib/components/ui/DataState.svelte';
	import Badge from '$lib/components/ui/Badge.svelte';
	import Icon from '$lib/components/ui/Icon.svelte';

	/** @type {{ customer: any }} */
	let { customer } = $props();

	/** @type {any[]} */
	let notes = $state([]);
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
			const all = await clinicalNotes.list(undefined, { signal });
			notes = all.filter((/** @type {any} */ n) => n.customer === customerId);
		} catch (err) {
			if (isAbortError(err)) return;
			error = errMessage(err) || i18n.t('common.error');
		} finally {
			if (!signal?.aborted) loading = false;
		}
	}
</script>

<!-- Content is encrypted server-side with no decrypted accessor — metadata only. -->
<div
	class="mb-4 flex items-start gap-2 rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800"
>
	<Icon name="alert" size={16} class="mt-0.5 shrink-0" />
	<span>{i18n.t('notes.opaque')}</span>
</div>

<DataState
	{loading}
	{error}
	empty={!notes.length}
	emptyText={i18n.t('notes.empty')}
	onRetry={() => load(customer.id)}
>
	<ul class="space-y-2">
		{#each notes as note (note.id)}
			<li
				class="flex items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
			>
				<div class="flex items-center gap-3">
					<Badge label={enumLabel('note_type', note.note_type)} variant="blue" />
					{#if note.is_sensitive}<Badge label={i18n.t('notes.sensitive')} variant="red" />{/if}
				</div>
				<span class="text-xs text-slate-400">{dateTime(note.created_at)}</span>
			</li>
		{/each}
	</ul>
</DataState>
