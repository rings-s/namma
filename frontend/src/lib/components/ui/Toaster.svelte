<script>
	import { toasts } from '$lib/stores/toast.svelte.js';
	import Icon from './Icon.svelte';

	const STYLES = {
		success: 'border-emerald-200 bg-emerald-50 text-emerald-900',
		error: 'border-rose-200 bg-rose-50 text-rose-900',
		info: 'border-slate-200 bg-white text-slate-900'
	};
</script>

<div
	class="pointer-events-none fixed inset-x-0 top-4 z-50 flex flex-col items-center gap-2 px-4"
	aria-live="polite"
>
	{#each toasts.items as toast (toast.id)}
		<div
			class="pointer-events-auto flex w-full max-w-sm items-start gap-3 rounded-xl border px-4 py-3 shadow-lg {STYLES[
				toast.kind
			]}"
			role="status"
		>
			<p class="flex-1 text-sm leading-5">{toast.message}</p>
			<button
				class="shrink-0 opacity-60 transition hover:opacity-100"
				onclick={() => toasts.dismiss(toast.id)}
				aria-label="dismiss"
			>
				<Icon name="x" size={16} />
			</button>
		</div>
	{/each}
</div>
