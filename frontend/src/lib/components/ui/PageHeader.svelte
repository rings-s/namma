<script>
	import { goto } from '$app/navigation';
	import Icon from './Icon.svelte';

	/**
	 * @type {{ title: string; subtitle?: string; backHref?: string;
	 *   actions?: import('svelte').Snippet }}
	 */
	let { title, subtitle = '', backHref = '', actions } = $props();
</script>

<header class="mb-6 flex flex-wrap items-start justify-between gap-4">
	<div class="min-w-0">
		<div class="flex items-center gap-2">
			{#if backHref}
				<button
					onclick={() => goto(backHref)}
					class="-ms-1 rounded-lg p-1.5 text-slate-400 transition hover:bg-slate-100 hover:text-slate-600"
					aria-label="back"
				>
					<!-- chevron rotates to point at the inline-start edge in both directions -->
					<Icon name="chevron" size={18} class="rotate-90 rtl:-rotate-90" />
				</button>
			{/if}
			<h1 class="truncate text-2xl font-semibold text-slate-900">{title}</h1>
		</div>
		{#if subtitle}
			<p class="mt-1 text-sm text-slate-500">{subtitle}</p>
		{/if}
	</div>
	{#if actions}
		<div class="flex shrink-0 items-center gap-2">{@render actions()}</div>
	{/if}
</header>
