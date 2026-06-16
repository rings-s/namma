<script>
	import { i18n } from '$lib/i18n/i18n.svelte.js';
	import Spinner from './Spinner.svelte';

	/**
	 * Wraps an async region: shows a spinner while loading, an error card with a
	 * retry, an empty placeholder when there's nothing, otherwise the children.
	 * @type {{ loading?: boolean; error?: string; empty?: boolean;
	 *   emptyText?: string; onRetry?: () => void; children: import('svelte').Snippet }}
	 */
	let { loading = false, error = '', empty = false, emptyText = '', onRetry, children } = $props();
</script>

{#if loading}
	<div class="flex items-center gap-3 py-16 text-slate-400">
		<Spinner size={24} /><span class="text-sm">{i18n.t('common.loading')}</span>
	</div>
{:else if error}
	<div class="rounded-xl border border-rose-200 bg-rose-50 p-6 text-sm text-rose-700">
		{error}
		{#if onRetry}
			<button class="ms-2 font-semibold underline" onclick={onRetry}>
				{i18n.t('common.retry')}
			</button>
		{/if}
	</div>
{:else if empty}
	<div
		class="rounded-xl border border-dashed border-slate-200 bg-white p-10 text-center text-sm text-slate-400"
	>
		{emptyText || i18n.t('common.empty')}
	</div>
{:else}
	{@render children()}
{/if}
