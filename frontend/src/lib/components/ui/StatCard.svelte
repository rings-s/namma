<script>
	import Icon from './Icon.svelte';

	/**
	 * Premium metric tile: a tinted icon chip, a label, a large value, and an
	 * optional hint line. Colour `tone` maps to a soft gradient chip so a row of
	 * cards reads as a cohesive dashboard.
	 * @type {{ label: string; value: string | number; icon?: string;
	 *   tone?: 'brand' | 'sky' | 'amber' | 'rose' | 'violet' | 'slate';
	 *   hint?: string }}
	 */
	let { label, value, icon = '', tone = 'brand', hint = '' } = $props();

	/** @type {Record<string, string>} */
	const CHIPS = {
		brand: 'bg-brand-50 text-brand-600 ring-brand-100',
		sky: 'bg-sky-50 text-sky-600 ring-sky-100',
		amber: 'bg-amber-50 text-amber-600 ring-amber-100',
		rose: 'bg-rose-50 text-rose-600 ring-rose-100',
		violet: 'bg-violet-50 text-violet-600 ring-violet-100',
		slate: 'bg-slate-100 text-slate-600 ring-slate-200'
	};
</script>

<div
	class="group relative overflow-hidden rounded-2xl border border-slate-200/70 bg-white p-5 shadow-sm transition hover:shadow-md"
>
	<div class="flex items-start justify-between gap-3">
		<div class="min-w-0">
			<p class="truncate text-xs font-medium tracking-wide text-slate-400 uppercase">{label}</p>
			<p class="mt-2 text-2xl font-semibold tracking-tight text-slate-900 tabular-nums">{value}</p>
			{#if hint}<p class="mt-1 truncate text-xs text-slate-400">{hint}</p>{/if}
		</div>
		{#if icon}
			<span
				class="flex size-10 shrink-0 items-center justify-center rounded-xl ring-1 ring-inset {CHIPS[
					tone
				] ?? CHIPS.brand}"
			>
				<Icon name={icon} size={20} />
			</span>
		{/if}
	</div>
</div>
