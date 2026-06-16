<script>
	// Status/label pill. Colour comes from a small named-variant palette so
	// callers map domain enums to a variant via `statusVariant()`.
	/** @type {{ label: string; variant?: string; class?: string }} */
	let { label, variant = 'slate', class: cls = '' } = $props();

	/** @type {Record<string, string>} */
	const VARIANTS = {
		slate: 'bg-slate-100 text-slate-600',
		blue: 'bg-sky-100 text-sky-700',
		green: 'bg-emerald-100 text-emerald-700',
		amber: 'bg-amber-100 text-amber-700',
		red: 'bg-rose-100 text-rose-700',
		violet: 'bg-violet-100 text-violet-700'
	};

	let palette = $derived(VARIANTS[variant] ?? VARIANTS.slate);
</script>

<span
	class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium whitespace-nowrap {palette} {cls}"
>
	{label}
</span>
