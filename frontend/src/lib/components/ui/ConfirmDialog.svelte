<script>
	import { i18n } from '$lib/i18n/i18n.svelte.js';
	import Modal from './Modal.svelte';
	import Spinner from './Spinner.svelte';

	/**
	 * Destructive-action confirmation. The body explains the consequence; the
	 * confirm button is styled to match the danger of the action.
	 * @type {{ title: string; message: string; confirmLabel?: string;
	 *   danger?: boolean; busy?: boolean; onConfirm: () => void; onCancel: () => void }}
	 */
	let {
		title,
		message,
		confirmLabel = '',
		danger = true,
		busy = false,
		onConfirm,
		onCancel
	} = $props();
</script>

<Modal {title} onClose={onCancel} size="sm">
	<p class="text-sm leading-relaxed text-slate-600">{message}</p>
	{#snippet footer()}
		<button
			onclick={onCancel}
			class="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-50"
		>
			{i18n.t('common.cancel')}
		</button>
		<button
			onclick={onConfirm}
			disabled={busy}
			class="flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold text-white transition disabled:opacity-60 {danger
				? 'bg-rose-600 hover:bg-rose-700'
				: 'bg-brand-600 hover:bg-brand-700'}"
		>
			{#if busy}<Spinner size={16} />{/if}
			{confirmLabel || i18n.t('common.confirm')}
		</button>
	{/snippet}
</Modal>
