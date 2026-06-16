<script>
	import { i18n } from '$lib/i18n/i18n.svelte.js';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { services, products } from '$lib/api/commerce.js';
	import { errMessage, isAbortError } from '$lib/api/client.js';
	import { scopeToOrg } from '$lib/utils/scope.js';
	import { money, number } from '$lib/utils/format.js';
	import DataState from '$lib/components/ui/DataState.svelte';
	import Badge from '$lib/components/ui/Badge.svelte';
	import Icon from '$lib/components/ui/Icon.svelte';
	import CatalogForm from './CatalogForm.svelte';

	/** @type {any[]} */
	let serviceRows = $state([]);
	/** @type {any[]} */
	let productRows = $state([]);
	let loading = $state(true);
	let error = $state('');
	/** @type {'service' | 'product' | null} */
	let formKind = $state(null);

	const currency = $derived(auth.currentOrg?.currency ?? 'SAR');

	$effect(() => {
		const orgId = auth.currentOrgId;
		if (!orgId) return;
		// Cancel the in-flight load when the org changes (or this tab unmounts),
		// so a slow response for the previous org can't overwrite the new one's data.
		const ctrl = new AbortController();
		load(orgId, ctrl.signal);
		return () => ctrl.abort();
	});

	/** @param {string} orgId @param {AbortSignal} [signal] */
	async function load(orgId, signal) {
		loading = true;
		error = '';
		try {
			const [s, p] = await Promise.all([
				services.list(undefined, { signal }),
				products.list(undefined, { signal })
			]);
			serviceRows = scopeToOrg(s, orgId);
			productRows = scopeToOrg(p, orgId);
		} catch (err) {
			if (isAbortError(err)) return; // superseded by a newer load — ignore
			error = errMessage(err) || i18n.t('common.error');
		} finally {
			if (!signal?.aborted) loading = false;
		}
	}

	/** @param {any} row */
	function onCreated(row) {
		if (formKind === 'service') serviceRows = [row, ...serviceRows];
		else productRows = [row, ...productRows];
		formKind = null;
	}
</script>

<DataState {loading} {error} onRetry={() => auth.currentOrgId && load(auth.currentOrgId)}>
	<div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
		<!-- Services -->
		<section class="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
			<header class="flex items-center justify-between border-b border-slate-100 px-5 py-3.5">
				<div class="flex items-center gap-2">
					<span
						class="flex size-8 items-center justify-center rounded-lg bg-brand-50 text-brand-600"
					>
						<Icon name="scissors" size={16} />
					</span>
					<h3 class="text-sm font-semibold text-slate-800">{i18n.t('catalog.services')}</h3>
					<span class="text-xs text-slate-400">{number(serviceRows.length)}</span>
				</div>
				<button
					onclick={() => (formKind = 'service')}
					class="flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-xs font-semibold text-brand-700 transition hover:bg-brand-50"
				>
					<Icon name="plus" size={14} />{i18n.t('catalog.newService')}
				</button>
			</header>
			{#if serviceRows.length}
				<ul class="divide-y divide-slate-50">
					{#each serviceRows as s (s.id)}
						<li class="flex items-center justify-between gap-3 px-5 py-3">
							<div class="min-w-0">
								<p class="truncate text-sm font-medium text-slate-800">{s.name}</p>
								<p class="text-xs text-slate-400">
									{i18n.t('catalog.minutes', { n: number(s.duration_minutes) })}
								</p>
							</div>
							<div class="flex items-center gap-2">
								{#if s.is_active === false}<Badge label={i18n.t('enum.inactive')} />{/if}
								<span class="text-sm font-medium text-slate-800 tabular-nums"
									>{money(s.price, currency)}</span
								>
							</div>
						</li>
					{/each}
				</ul>
			{:else}
				<p class="px-5 py-10 text-center text-sm text-slate-400">{i18n.t('catalog.noServices')}</p>
			{/if}
		</section>

		<!-- Products -->
		<section class="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
			<header class="flex items-center justify-between border-b border-slate-100 px-5 py-3.5">
				<div class="flex items-center gap-2">
					<span class="flex size-8 items-center justify-center rounded-lg bg-sky-50 text-sky-600">
						<Icon name="box" size={16} />
					</span>
					<h3 class="text-sm font-semibold text-slate-800">{i18n.t('catalog.products')}</h3>
					<span class="text-xs text-slate-400">{number(productRows.length)}</span>
				</div>
				<button
					onclick={() => (formKind = 'product')}
					class="flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-xs font-semibold text-brand-700 transition hover:bg-brand-50"
				>
					<Icon name="plus" size={14} />{i18n.t('catalog.newProduct')}
				</button>
			</header>
			{#if productRows.length}
				<ul class="divide-y divide-slate-50">
					{#each productRows as p (p.id)}
						<li class="flex items-center justify-between gap-3 px-5 py-3">
							<div class="min-w-0">
								<p class="truncate text-sm font-medium text-slate-800">{p.name}</p>
								<p class="text-xs text-slate-400">
									{p.sku ? `${i18n.t('catalog.sku')}: ${p.sku} · ` : ''}{i18n.t('catalog.stock')}: {number(
										p.stock_quantity
									)}
								</p>
							</div>
							<span class="text-sm font-medium text-slate-800 tabular-nums"
								>{money(p.price, currency)}</span
							>
						</li>
					{/each}
				</ul>
			{:else}
				<p class="px-5 py-10 text-center text-sm text-slate-400">{i18n.t('catalog.noProducts')}</p>
			{/if}
		</section>
	</div>
</DataState>

{#if formKind}
	<CatalogForm kind={formKind} onClose={() => (formKind = null)} {onCreated} />
{/if}
