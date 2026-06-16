<script>
	import { i18n } from '$lib/i18n/i18n.svelte.js';

	/**
	 * Labelled form-control wrapper. Renders the label (with an optional
	 * "optional" hint), the control snippet, and a field-level error/hint line —
	 * so module forms stay terse and consistent.
	 * @type {{ label: string; error?: string; hint?: string; optional?: boolean;
	 *   children: import('svelte').Snippet }}
	 */
	let { label, error = '', hint = '', optional = false, children } = $props();
</script>

<label class="block">
	<span class="mb-1 flex items-center gap-1.5 text-sm font-medium text-slate-700">
		{label}
		{#if optional}
			<span class="text-xs font-normal text-slate-400">({i18n.t('common.optional')})</span>
		{/if}
	</span>
	{@render children()}
	{#if error}
		<span class="mt-1 block text-xs text-rose-600">{error}</span>
	{:else if hint}
		<span class="mt-1 block text-xs text-slate-400">{hint}</span>
	{/if}
</label>
