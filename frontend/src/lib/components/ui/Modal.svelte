<script>
	import { i18n } from '$lib/i18n/i18n.svelte.js';
	import Icon from './Icon.svelte';

	/**
	 * @type {{ title?: string; onClose: () => void; size?: 'sm' | 'md' | 'lg';
	 *   children: import('svelte').Snippet; footer?: import('svelte').Snippet }}
	 */
	let { title = '', onClose, size = 'md', children, footer } = $props();

	const WIDTHS = { sm: 'max-w-sm', md: 'max-w-lg', lg: 'max-w-2xl' };

	/** @type {HTMLElement | null} */
	let dialogEl = $state(null);

	const FOCUSABLE =
		'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

	/** @returns {HTMLElement[]} visible, focusable descendants in tab order */
	function focusables() {
		if (!dialogEl) return [];
		return /** @type {HTMLElement[]} */ (
			[...dialogEl.querySelectorAll(FOCUSABLE)].filter(
				(el) => el instanceof HTMLElement && el.offsetParent !== null
			)
		);
	}

	// Move focus into the dialog on open, keep Tab cycling inside it, and
	// restore focus to the trigger on close. Cleanup runs when the modal unmounts.
	$effect(() => {
		if (!dialogEl) return;
		const previouslyFocused =
			document.activeElement instanceof HTMLElement ? document.activeElement : null;
		(focusables()[0] ?? dialogEl).focus();

		/** @param {KeyboardEvent} e */
		function onTrap(e) {
			if (e.key !== 'Tab') return;
			const els = focusables();
			if (!els.length) {
				e.preventDefault();
				return;
			}
			const first = els[0];
			const last = els[els.length - 1];
			if (e.shiftKey && document.activeElement === first) {
				e.preventDefault();
				last.focus();
			} else if (!e.shiftKey && document.activeElement === last) {
				e.preventDefault();
				first.focus();
			}
		}

		dialogEl.addEventListener('keydown', onTrap);
		return () => {
			dialogEl?.removeEventListener('keydown', onTrap);
			previouslyFocused?.focus();
		};
	});

	/** @param {KeyboardEvent} e */
	function onKey(e) {
		if (e.key === 'Escape') onClose();
	}
</script>

<svelte:window onkeydown={onKey} />

<div class="fixed inset-0 z-50 flex items-center justify-center p-4">
	<button
		class="absolute inset-0 bg-slate-900/50"
		aria-label={i18n.t('common.close')}
		onclick={onClose}
	></button>
	<div
		bind:this={dialogEl}
		tabindex="-1"
		class="relative flex max-h-[90vh] w-full {WIDTHS[size]} flex-col rounded-2xl bg-white shadow-xl focus:outline-none"
		role="dialog"
		aria-modal="true"
	>
		<div class="flex items-center justify-between border-b border-slate-100 px-5 py-4">
			<h2 class="text-base font-semibold text-slate-900">{title}</h2>
			<button
				onclick={onClose}
				class="rounded-lg p-1.5 text-slate-400 transition hover:bg-slate-100 hover:text-slate-600"
				aria-label={i18n.t('common.close')}
			>
				<Icon name="x" size={18} />
			</button>
		</div>
		<div class="flex-1 overflow-y-auto px-5 py-4">{@render children()}</div>
		{#if footer}
			<div class="flex justify-end gap-2 border-t border-slate-100 px-5 py-4">
				{@render footer()}
			</div>
		{/if}
	</div>
</div>
