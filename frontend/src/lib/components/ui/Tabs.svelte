<script>
	/**
	 * Controlled tab bar. Caller owns the active key.
	 * @type {{ tabs: { key: string; label: string }[]; active: string;
	 *   onSelect: (key: string) => void }}
	 */
	let { tabs, active, onSelect } = $props();
</script>

<div class="border-b border-slate-200">
	<nav class="-mb-px flex gap-1 overflow-x-auto" aria-label="Tabs">
		{#each tabs as tab (tab.key)}
			<button
				onclick={() => onSelect(tab.key)}
				class="whitespace-nowrap border-b-2 px-4 py-2.5 text-sm font-medium transition {active ===
				tab.key
					? 'border-brand-600 text-brand-700'
					: 'border-transparent text-slate-500 hover:border-slate-300 hover:text-slate-700'}"
				aria-current={active === tab.key ? 'page' : undefined}
			>
				{tab.label}
			</button>
		{/each}
	</nav>
</div>
