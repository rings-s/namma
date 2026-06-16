<script>
	import { i18n } from '$lib/i18n/i18n.svelte.js';
	import { toasts } from '$lib/stores/toast.svelte.js';
	import {
		customerPackages,
		packages,
		services,
		packageRedemptions,
		redeemPackage
	} from '$lib/api/commerce.js';
	import { errMessage, isAbortError } from '$lib/api/client.js';
	import { enumLabel, statusVariant } from '$lib/utils/status.js';
	import { date, number } from '$lib/utils/format.js';
	import DataState from '$lib/components/ui/DataState.svelte';
	import Badge from '$lib/components/ui/Badge.svelte';
	import Spinner from '$lib/components/ui/Spinner.svelte';

	/** @type {{ customer: any }} */
	let { customer } = $props();

	/** @type {any[]} */
	let mine = $state([]);
	/** @type {Map<string, any>} */
	let packageMap = $state(new Map());
	/** @type {Map<string, string>} */
	let serviceNames = $state(new Map());
	/** @type {any[]} */
	let redemptions = $state([]);
	let loading = $state(true);
	let error = $state('');
	/** @type {string | null} */
	let redeeming = $state(null);

	$effect(() => {
		const customerId = customer?.id;
		if (!customerId) return;
		const ctrl = new AbortController();
		load(customerId, ctrl.signal);
		return () => ctrl.abort();
	});

	/** @param {string} customerId @param {AbortSignal} [signal] */
	async function load(customerId, signal) {
		loading = true;
		error = '';
		try {
			const [cps, pkgs, svcs] = await Promise.all([
				customerPackages.list(undefined, { signal }),
				packages.list(undefined, { signal }),
				services.list(undefined, { signal })
			]);
			mine = cps.filter((/** @type {any} */ cp) => cp.customer === customerId);
			packageMap = new Map(pkgs.map((/** @type {any} */ p) => [p.id, p]));
			serviceNames = new Map(svcs.map((/** @type {any} */ s) => [s.id, s.name]));
			const ids = new Set(mine.map((/** @type {any} */ cp) => cp.id));
			const reds = await packageRedemptions.list(undefined, { signal });
			redemptions = reds.filter((/** @type {any} */ r) => ids.has(r.customer_package));
		} catch (err) {
			if (isAbortError(err)) return;
			error = errMessage(err) || i18n.t('common.error');
		} finally {
			if (!signal?.aborted) loading = false;
		}
	}

	/** Remaining for one (customer package, item) = item.quantity − redeemed. */
	function remaining(/** @type {string} */ cpId, /** @type {any} */ item) {
		const used = redemptions
			.filter((r) => r.customer_package === cpId && r.package_item === item.id)
			.reduce((sum, r) => sum + (r.quantity ?? 0), 0);
		return (item.quantity ?? 0) - used;
	}

	/** @param {string} cpId @param {string} itemId */
	async function redeem(cpId, itemId) {
		redeeming = `${cpId}:${itemId}`;
		try {
			await redeemPackage(cpId, { package_item: itemId, quantity: 1 });
			toasts.success(i18n.t('packages.redeemed'));
			await load(customer.id);
		} catch (err) {
			toasts.error(errMessage(err) || i18n.t('common.error'));
		} finally {
			redeeming = null;
		}
	}
</script>

<DataState
	{loading}
	{error}
	empty={!mine.length}
	emptyText={i18n.t('packages.empty')}
	onRetry={() => load(customer.id)}
>
	<div class="space-y-3">
		{#each mine as cp (cp.id)}
			{@const pkg = packageMap.get(cp.package)}
			<div class="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
				<div class="flex items-center justify-between gap-3">
					<div>
						<p class="font-semibold text-slate-900">{pkg?.name ?? '—'}</p>
						<p class="text-xs text-slate-400">{date(cp.starts_at)} → {date(cp.expires_at)}</p>
					</div>
					<Badge
						label={enumLabel('package_status', cp.status)}
						variant={statusVariant(cp.status)}
					/>
				</div>
				{#if pkg?.items?.length}
					<ul class="mt-4 space-y-2 border-t border-slate-100 pt-3">
						{#each pkg.items as item (item.id)}
							{@const left = remaining(cp.id, item)}
							<li class="flex items-center justify-between gap-3 text-sm">
								<span class="text-slate-700">{serviceNames.get(item.service) ?? '—'}</span>
								<div class="flex items-center gap-3">
									<span class="text-xs text-slate-500">
										{number(left)} / {number(item.quantity)}
										{i18n.t('packages.remaining')}
									</span>
									<button
										onclick={() => redeem(cp.id, item.id)}
										disabled={left <= 0 ||
											cp.status !== 'active' ||
											redeeming === `${cp.id}:${item.id}`}
										class="flex items-center gap-1.5 rounded-lg border border-brand-200 px-3 py-1 text-xs font-semibold text-brand-700 transition hover:bg-brand-50 disabled:opacity-40"
									>
										{#if redeeming === `${cp.id}:${item.id}`}<Spinner size={12} />{/if}
										{i18n.t('packages.redeem')}
									</button>
								</div>
							</li>
						{/each}
					</ul>
				{/if}
			</div>
		{/each}
	</div>
</DataState>
