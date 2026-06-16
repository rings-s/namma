<script>
	import { auth } from '$lib/stores/auth.svelte.js';
	import { i18n } from '$lib/i18n/i18n.svelte.js';
	import Icon from '$lib/components/ui/Icon.svelte';

	/** @type {HTMLDetailsElement} */
	let details;

	/** @param {string} id */
	function choose(id) {
		auth.setOrg(id);
		if (details) details.open = false;
	}
</script>

<details bind:this={details} class="group relative">
	<summary
		class="flex cursor-pointer list-none items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
	>
		<span
			class="grid h-6 w-6 place-items-center rounded bg-brand-100 text-xs font-bold text-brand-700"
		>
			{(auth.currentOrg?.name ?? '?').slice(0, 1).toUpperCase()}
		</span>
		<span class="max-w-[10rem] truncate">{auth.currentOrg?.name ?? i18n.t('shell.noOrg')}</span>
		<Icon name="chevron" size={16} class="text-slate-400" />
	</summary>

	<div
		class="absolute z-20 mt-2 max-h-72 w-64 overflow-auto rounded-xl border border-slate-200 bg-white p-1 shadow-lg start-0"
	>
		<p class="px-3 py-2 text-xs font-semibold tracking-wide text-slate-400 uppercase">
			{i18n.t('shell.switchOrg')}
		</p>
		{#each auth.organizations as org (org.id)}
			<button
				type="button"
				onclick={() => choose(org.id)}
				class="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-start text-sm hover:bg-slate-50 {org.id ===
				auth.currentOrgId
					? 'font-semibold text-brand-700'
					: 'text-slate-700'}"
			>
				<span
					class="grid h-6 w-6 place-items-center rounded bg-slate-100 text-xs font-bold text-slate-600"
				>
					{org.name.slice(0, 1).toUpperCase()}
				</span>
				<span class="flex-1 truncate">{org.name}</span>
				{#if org.id === auth.currentOrgId}
					<Icon name="check" size={16} class="text-brand-600" />
				{/if}
			</button>
		{/each}
	</div>
</details>
