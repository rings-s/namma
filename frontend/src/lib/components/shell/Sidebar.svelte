<script>
	import { page } from '$app/state';
	import { NAV } from '$lib/config/nav.js';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { i18n } from '$lib/i18n/i18n.svelte.js';
	import Icon from '$lib/components/ui/Icon.svelte';

	/** @type {{ onNavigate?: (event?: Event) => void }} */
	let { onNavigate = () => {} } = $props();

	/**
	 * Hide items the current role can't access; everything else renders.
	 * @param {import('$lib/config/nav.js').NavItem[]} items
	 */
	function visibleItems(items) {
		return items.filter((item) => !item.minRole || auth.hasRole(item.minRole));
	}

	// All real (linkable) hrefs, so a path activates only its longest match —
	// otherwise `/customers` would also light up on `/customers/segments`.
	const allHrefs = $derived(
		NAV.flatMap((g) => g.items.filter((i) => !i.comingSoon).map((i) => i.href))
	);

	const activeHref = $derived.by(() => {
		const path = page.url.pathname;
		let best = '';
		for (const href of allHrefs) {
			if ((path === href || path.startsWith(href + '/')) && href.length > best.length) {
				best = href;
			}
		}
		return best;
	});

	/** @param {string} href */
	function isActive(href) {
		return activeHref === href;
	}
</script>

<div class="flex h-full flex-col bg-white">
	<div class="flex h-16 items-center gap-2 px-5">
		<span
			class="grid h-8 w-8 place-items-center rounded-lg bg-brand-600 text-sm font-bold text-white"
		>
			ن
		</span>
		<span class="text-lg font-bold text-slate-900">{i18n.t('app.name')}</span>
	</div>

	<nav class="flex-1 space-y-6 overflow-y-auto px-3 py-2">
		{#each NAV as group (group.key)}
			{@const items = visibleItems(group.items)}
			{#if items.length}
				<div>
					<p class="px-3 pb-2 text-xs font-semibold tracking-wide text-slate-400 uppercase">
						{i18n.t(group.labelKey)}
					</p>
					<ul class="space-y-1">
						{#each items as item (item.key)}
							<li>
								{#if item.comingSoon}
									<span
										class="flex cursor-not-allowed items-center gap-3 rounded-lg px-3 py-2 text-sm text-slate-400"
										title={i18n.t('shell.comingSoon')}
									>
										<Icon name={item.icon} size={18} />
										<span class="flex-1">{i18n.t(item.labelKey)}</span>
										<span
											class="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-medium text-slate-400"
										>
											{i18n.t('shell.comingSoon')}
										</span>
									</span>
								{:else}
									<a
										href={item.href}
										onclick={onNavigate}
										class="flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition {isActive(
											item.href
										)
											? 'bg-brand-50 text-brand-700'
											: 'text-slate-600 hover:bg-slate-50'}"
										aria-current={isActive(item.href) ? 'page' : undefined}
									>
										<Icon name={item.icon} size={18} />
										<span>{i18n.t(item.labelKey)}</span>
									</a>
								{/if}
							</li>
						{/each}
					</ul>
				</div>
			{/if}
		{/each}
	</nav>
</div>
