<script>
	import { i18n } from '$lib/i18n/i18n.svelte.js';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { toasts } from '$lib/stores/toast.svelte.js';
	import { giftCards, storeCreditAccounts, packages } from '$lib/api/commerce.js';
	import { customers } from '$lib/api/customers.js';
	import { errMessage, isAbortError } from '$lib/api/client.js';
	import { scopeToOrg, customerName, indexById } from '$lib/utils/scope.js';
	import { statusVariant, enumLabel } from '$lib/utils/status.js';
	import { money, number } from '$lib/utils/format.js';
	import DataState from '$lib/components/ui/DataState.svelte';
	import Badge from '$lib/components/ui/Badge.svelte';
	import Icon from '$lib/components/ui/Icon.svelte';
	import Modal from '$lib/components/ui/Modal.svelte';
	import Field from '$lib/components/ui/Field.svelte';
	import Spinner from '$lib/components/ui/Spinner.svelte';

	const INPUT =
		'w-full rounded-lg border-slate-300 text-sm focus:border-brand-500 focus:ring-brand-500';
	const currency = $derived(auth.currentOrg?.currency ?? 'SAR');

	/** @type {any[]} */
	let cardRows = $state([]);
	/** @type {any[]} */
	let creditRows = $state([]);
	/** @type {any[]} */
	let packageRows = $state([]);
	/** @type {Map<string, any>} */
	let customerIndex = $state(new Map());
	let loading = $state(true);
	let error = $state('');

	/** @type {'card' | 'package' | null} */
	let modal = $state(null);
	let saving = $state(false);

	// gift-card form
	let gcCode = $state('');
	let gcValue = $state('');
	// package form
	let pkName = $state('');
	let pkType = $state('bundle');
	let pkPrice = $state('');
	let pkValidity = $state('');

	$effect(() => {
		const orgId = auth.currentOrgId;
		if (!orgId) return;
		const ctrl = new AbortController();
		load(orgId, ctrl.signal);
		return () => ctrl.abort();
	});

	/** @param {string} orgId @param {AbortSignal} [signal] */
	async function load(orgId, signal) {
		loading = true;
		error = '';
		try {
			const [g, c, p, cu] = await Promise.all([
				giftCards.list(undefined, { signal }),
				storeCreditAccounts.list(undefined, { signal }),
				packages.list(undefined, { signal }),
				customers.list(undefined, { signal })
			]);
			cardRows = scopeToOrg(g, orgId);
			creditRows = scopeToOrg(c, orgId);
			packageRows = scopeToOrg(p, orgId);
			customerIndex = indexById(scopeToOrg(cu, orgId));
		} catch (err) {
			if (isAbortError(err)) return;
			error = errMessage(err) || i18n.t('common.error');
		} finally {
			if (!signal?.aborted) loading = false;
		}
	}

	async function createGiftCard() {
		saving = true;
		try {
			const row = await giftCards.create({
				organization: auth.currentOrgId,
				code: gcCode,
				initial_value: Number(gcValue) || 0,
				balance: Number(gcValue) || 0
			});
			cardRows = [row, ...cardRows];
			toasts.success(i18n.t('sv.giftCardCreated'));
			modal = null;
			gcCode = '';
			gcValue = '';
		} catch (err) {
			toasts.error(errMessage(err) || i18n.t('common.error'));
		} finally {
			saving = false;
		}
	}

	async function createPackage() {
		saving = true;
		try {
			const row = await packages.create({
				organization: auth.currentOrgId,
				name: pkName,
				package_type: pkType,
				price: Number(pkPrice) || 0,
				validity_days: pkValidity ? Number(pkValidity) : null
			});
			packageRows = [row, ...packageRows];
			toasts.success(i18n.t('sv.packageCreated'));
			modal = null;
			pkName = '';
			pkPrice = '';
			pkValidity = '';
		} catch (err) {
			toasts.error(errMessage(err) || i18n.t('common.error'));
		} finally {
			saving = false;
		}
	}
</script>

<DataState {loading} {error} onRetry={() => auth.currentOrgId && load(auth.currentOrgId)}>
	<div class="space-y-6">
		<!-- Gift cards -->
		<section class="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
			<header class="flex items-center justify-between border-b border-slate-100 px-5 py-3.5">
				<div class="flex items-center gap-2">
					<span
						class="flex size-8 items-center justify-center rounded-lg bg-violet-50 text-violet-600"
						><Icon name="gift" size={16} /></span
					>
					<h3 class="text-sm font-semibold text-slate-800">{i18n.t('sv.giftCards')}</h3>
					<span class="text-xs text-slate-400">{number(cardRows.length)}</span>
				</div>
				<button
					onclick={() => (modal = 'card')}
					class="flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-xs font-semibold text-brand-700 transition hover:bg-brand-50"
				>
					<Icon name="plus" size={14} />{i18n.t('sv.newGiftCard')}
				</button>
			</header>
			{#if cardRows.length}
				<table class="w-full text-sm">
					<tbody class="divide-y divide-slate-50">
						{#each cardRows as g (g.id)}
							<tr>
								<td class="px-5 py-3 font-medium text-slate-800" dir="ltr">{g.code}</td>
								<td class="px-5 py-3 text-end text-slate-500 tabular-nums"
									>{money(g.initial_value, currency)}</td
								>
								<td class="px-5 py-3 text-end font-medium text-slate-800 tabular-nums"
									>{money(g.balance, currency)}</td
								>
								<td class="px-5 py-3 text-end"
									><Badge
										label={enumLabel('giftcard', g.status)}
										variant={statusVariant(g.status)}
									/></td
								>
							</tr>
						{/each}
					</tbody>
				</table>
			{:else}
				<p class="px-5 py-10 text-center text-sm text-slate-400">{i18n.t('sv.noGiftCards')}</p>
			{/if}
		</section>

		<div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
			<!-- Store credit -->
			<section class="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
				<header class="flex items-center gap-2 border-b border-slate-100 px-5 py-3.5">
					<span
						class="flex size-8 items-center justify-center rounded-lg bg-emerald-50 text-emerald-600"
						><Icon name="wallet" size={16} /></span
					>
					<h3 class="text-sm font-semibold text-slate-800">{i18n.t('sv.storeCredit')}</h3>
					<span class="text-xs text-slate-400">{number(creditRows.length)}</span>
				</header>
				{#if creditRows.length}
					<ul class="divide-y divide-slate-50">
						{#each creditRows as c (c.id)}
							<li class="flex items-center justify-between px-5 py-3">
								<span class="truncate text-sm text-slate-700"
									>{customerName(customerIndex.get(c.customer))}</span
								>
								<span class="text-sm font-medium text-slate-800 tabular-nums"
									>{money(c.balance, currency)}</span
								>
							</li>
						{/each}
					</ul>
				{:else}
					<p class="px-5 py-10 text-center text-sm text-slate-400">{i18n.t('sv.noStoreCredit')}</p>
				{/if}
			</section>

			<!-- Packages -->
			<section class="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
				<header class="flex items-center justify-between border-b border-slate-100 px-5 py-3.5">
					<div class="flex items-center gap-2">
						<span
							class="flex size-8 items-center justify-center rounded-lg bg-amber-50 text-amber-600"
							><Icon name="layers" size={16} /></span
						>
						<h3 class="text-sm font-semibold text-slate-800">{i18n.t('sv.packages')}</h3>
						<span class="text-xs text-slate-400">{number(packageRows.length)}</span>
					</div>
					<button
						onclick={() => (modal = 'package')}
						class="flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-xs font-semibold text-brand-700 transition hover:bg-brand-50"
					>
						<Icon name="plus" size={14} />{i18n.t('sv.newPackage')}
					</button>
				</header>
				{#if packageRows.length}
					<ul class="divide-y divide-slate-50">
						{#each packageRows as p (p.id)}
							<li class="flex items-center justify-between gap-3 px-5 py-3">
								<div class="min-w-0">
									<p class="truncate text-sm font-medium text-slate-800">{p.name}</p>
									<Badge label={enumLabel('packageType', p.package_type)} />
								</div>
								<span class="text-sm font-medium text-slate-800 tabular-nums"
									>{money(p.price, currency)}</span
								>
							</li>
						{/each}
					</ul>
				{:else}
					<p class="px-5 py-10 text-center text-sm text-slate-400">{i18n.t('sv.noPackages')}</p>
				{/if}
			</section>
		</div>
	</div>
</DataState>

{#if modal === 'card'}
	<Modal title={i18n.t('sv.newGiftCard')} onClose={() => (modal = null)} size="sm">
		<div class="space-y-4">
			<Field label={i18n.t('sv.code')}>
				<input bind:value={gcCode} maxlength="32" class={INPUT} dir="ltr" />
			</Field>
			<Field label={i18n.t('sv.initialValue')}>
				<input type="number" min="0.01" step="0.01" bind:value={gcValue} class={INPUT} dir="ltr" />
			</Field>
		</div>
		{#snippet footer()}
			<button
				onclick={() => (modal = null)}
				class="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-50"
				>{i18n.t('common.cancel')}</button
			>
			<button
				onclick={createGiftCard}
				disabled={saving || !gcCode || !gcValue}
				class="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-60"
			>
				{#if saving}<Spinner size={16} />{/if}{i18n.t('common.create')}
			</button>
		{/snippet}
	</Modal>
{:else if modal === 'package'}
	<Modal title={i18n.t('sv.newPackage')} onClose={() => (modal = null)} size="sm">
		<div class="space-y-4">
			<Field label={i18n.t('common.name')}>
				<input bind:value={pkName} maxlength="255" class={INPUT} />
			</Field>
			<Field label={i18n.t('common.type')}>
				<select bind:value={pkType} class={INPUT}>
					{#each ['bundle', 'membership', 'prepaid'] as t (t)}<option value={t}
							>{i18n.t(`enum.${t}`)}</option
						>{/each}
				</select>
			</Field>
			<div class="grid grid-cols-2 gap-4">
				<Field label={i18n.t('common.price')}>
					<input type="number" min="0" step="0.01" bind:value={pkPrice} class={INPUT} dir="ltr" />
				</Field>
				<Field label={i18n.t('sv.validityDays')} optional>
					<input type="number" min="0" step="1" bind:value={pkValidity} class={INPUT} dir="ltr" />
				</Field>
			</div>
		</div>
		{#snippet footer()}
			<button
				onclick={() => (modal = null)}
				class="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-50"
				>{i18n.t('common.cancel')}</button
			>
			<button
				onclick={createPackage}
				disabled={saving || !pkName || !pkPrice}
				class="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-60"
			>
				{#if saving}<Spinner size={16} />{/if}{i18n.t('common.create')}
			</button>
		{/snippet}
	</Modal>
{/if}
