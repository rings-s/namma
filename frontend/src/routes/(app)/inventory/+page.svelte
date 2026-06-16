<script>
	import { i18n } from '$lib/i18n/i18n.svelte.js';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { toasts } from '$lib/stores/toast.svelte.js';
	import {
		stockMovements,
		suppliers,
		purchaseOrders,
		submitPurchaseOrder
	} from '$lib/api/inventory.js';
	import { products } from '$lib/api/commerce.js';
	import { branches } from '$lib/api/organizations.js';
	import { errMessage, isAbortError } from '$lib/api/client.js';
	import { scopeToOrg, indexById } from '$lib/utils/scope.js';
	import { statusVariant, enumLabel } from '$lib/utils/status.js';
	import { money, number, date, dateTime } from '$lib/utils/format.js';
	import PageHeader from '$lib/components/ui/PageHeader.svelte';
	import Tabs from '$lib/components/ui/Tabs.svelte';
	import DataState from '$lib/components/ui/DataState.svelte';
	import StatCard from '$lib/components/ui/StatCard.svelte';
	import Badge from '$lib/components/ui/Badge.svelte';
	import Icon from '$lib/components/ui/Icon.svelte';
	import Modal from '$lib/components/ui/Modal.svelte';
	import Field from '$lib/components/ui/Field.svelte';
	import Spinner from '$lib/components/ui/Spinner.svelte';

	const INPUT =
		'w-full rounded-lg border-slate-300 text-sm focus:border-brand-500 focus:ring-brand-500';
	const currency = $derived(auth.currentOrg?.currency ?? 'SAR');
	const canManage = $derived(auth.hasRole('manager'));

	let active = $state('stock');
	let loading = $state(true);
	let error = $state('');
	/** @type {any[]} */
	let productRows = $state([]);
	/** @type {any[]} */
	let movementRows = $state([]);
	/** @type {any[]} */
	let supplierRows = $state([]);
	/** @type {any[]} */
	let poRows = $state([]);
	/** @type {any[]} */
	let branchRows = $state([]);
	/** @type {Map<string, any>} */
	let productIndex = $state(new Map());
	/** @type {Map<string, any>} */
	let supplierIndex = $state(new Map());

	/** @type {'supplier' | 'po' | null} */
	let modal = $state(null);
	let saving = $state(false);
	/** @type {string | null} */
	let busyId = $state(null);

	// supplier form
	let supName = $state('');
	let supContact = $state('');
	let supPhone = $state('');
	let supEmail = $state('');
	let supTerms = $state('');
	// PO form
	let poSupplier = $state('');
	let poBranch = $state('');
	let poExpected = $state('');

	const tabs = $derived([
		{ key: 'stock', label: i18n.t('inv2.tab.stock') },
		{ key: 'suppliers', label: i18n.t('inv2.tab.suppliers') },
		{ key: 'purchasing', label: i18n.t('inv2.tab.purchasing') }
	]);

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
			const [p, m, s, po, b] = await Promise.all([
				products.list(undefined, { signal }),
				stockMovements.list(undefined, { signal }),
				suppliers.list(undefined, { signal }),
				purchaseOrders.list(undefined, { signal }),
				branches.list(undefined, { signal })
			]);
			productRows = scopeToOrg(p, orgId);
			movementRows = scopeToOrg(m, orgId).slice(0, 15);
			supplierRows = scopeToOrg(s, orgId);
			poRows = scopeToOrg(po, orgId);
			branchRows = scopeToOrg(b, orgId).filter((/** @type {any} */ r) => r.is_active !== false);
			productIndex = indexById(productRows);
			supplierIndex = indexById(supplierRows);
			poSupplier = supplierRows[0]?.id ?? '';
			poBranch = branchRows[0]?.id ?? '';
		} catch (err) {
			if (isAbortError(err)) return;
			error = errMessage(err) || i18n.t('common.error');
		} finally {
			if (!signal?.aborted) loading = false;
		}
	}

	const totalUnits = $derived(
		productRows.reduce((sum, p) => sum + (Number(p.stock_quantity) || 0), 0)
	);
	const outOfStock = $derived(
		productRows.filter((p) => (Number(p.stock_quantity) || 0) <= 0).length
	);

	async function createSupplier() {
		saving = true;
		try {
			const row = await suppliers.create({
				organization: auth.currentOrgId,
				name: supName,
				contact_name: supContact,
				phone: supPhone,
				email: supEmail,
				payment_terms: supTerms
			});
			supplierRows = [row, ...supplierRows];
			supplierIndex = indexById(supplierRows);
			toasts.success(i18n.t('sup.created'));
			modal = null;
			supName = supContact = supPhone = supEmail = supTerms = '';
		} catch (err) {
			toasts.error(errMessage(err) || i18n.t('common.error'));
		} finally {
			saving = false;
		}
	}

	async function createPO() {
		saving = true;
		try {
			const row = await purchaseOrders.create({
				organization: auth.currentOrgId,
				branch: poBranch,
				supplier: poSupplier,
				expected_at: poExpected || null
			});
			poRows = [row, ...poRows];
			toasts.success(i18n.t('po.created'));
			modal = null;
			poExpected = '';
		} catch (err) {
			toasts.error(errMessage(err) || i18n.t('common.error'));
		} finally {
			saving = false;
		}
	}

	/** @param {string} id */
	async function submitPO(id) {
		busyId = id;
		try {
			await submitPurchaseOrder(id);
			toasts.success(i18n.t('po.submitted'));
			if (auth.currentOrgId) load(auth.currentOrgId);
		} catch (err) {
			toasts.error(errMessage(err) || i18n.t('common.error'));
		} finally {
			busyId = null;
		}
	}
</script>

<div class="mx-auto max-w-6xl">
	<PageHeader title={i18n.t('inv2.title')} subtitle={i18n.t('inv2.subtitle')} />

	<div class="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
		<StatCard
			label={i18n.t('inv2.stat.skus')}
			value={number(productRows.length)}
			icon="box"
			tone="brand"
		/>
		<StatCard
			label={i18n.t('inv2.stat.units')}
			value={number(totalUnits)}
			icon="layers"
			tone="sky"
		/>
		<StatCard
			label={i18n.t('inv2.stat.outOfStock')}
			value={number(outOfStock)}
			icon="alert"
			tone="rose"
		/>
	</div>

	<div class="mb-4 flex items-center justify-between gap-3">
		<Tabs {tabs} {active} onSelect={(k) => (active = k)} />
		{#if active === 'suppliers' && canManage}
			<button
				onclick={() => (modal = 'supplier')}
				class="flex shrink-0 items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700"
			>
				<Icon name="plus" size={16} />{i18n.t('sup.new')}
			</button>
		{:else if active === 'purchasing' && canManage}
			<button
				onclick={() => (modal = 'po')}
				disabled={!supplierRows.length}
				class="flex shrink-0 items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-50"
			>
				<Icon name="plus" size={16} />{i18n.t('po.new')}
			</button>
		{/if}
	</div>

	<DataState {loading} {error} onRetry={() => auth.currentOrgId && load(auth.currentOrgId)}>
		{#if active === 'stock'}
			<div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
				<section class="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
					<header
						class="border-b border-slate-100 px-5 py-3.5 text-sm font-semibold text-slate-800"
					>
						{i18n.t('inv2.onHand')}
					</header>
					{#if productRows.length}
						<ul class="divide-y divide-slate-50">
							{#each productRows as p (p.id)}
								<li class="flex items-center justify-between px-5 py-3">
									<span class="truncate text-sm text-slate-700">{p.name}</span>
									{#if (Number(p.stock_quantity) || 0) <= 0}
										<Badge label={i18n.t('inv2.out')} variant="red" />
									{:else}
										<span class="text-sm font-medium text-slate-800 tabular-nums"
											>{number(p.stock_quantity)}</span
										>
									{/if}
								</li>
							{/each}
						</ul>
					{:else}
						<p class="px-5 py-10 text-center text-sm text-slate-400">{i18n.t('inv2.noProducts')}</p>
					{/if}
				</section>
				<section class="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
					<header
						class="border-b border-slate-100 px-5 py-3.5 text-sm font-semibold text-slate-800"
					>
						{i18n.t('inv2.movements')}
					</header>
					{#if movementRows.length}
						<ul class="divide-y divide-slate-50">
							{#each movementRows as m (m.id)}
								<li class="flex items-center justify-between gap-3 px-5 py-3">
									<div class="min-w-0">
										<p class="truncate text-sm text-slate-700">
											{productIndex.get(m.product)?.name ?? '—'}
										</p>
										<p class="text-xs text-slate-400">{dateTime(m.created_at)}</p>
									</div>
									<div class="flex items-center gap-2">
										<Badge label={enumLabel('movement', m.movement_type)} />
										<span
											class="w-12 text-end text-sm font-medium tabular-nums {Number(m.quantity) < 0
												? 'text-rose-600'
												: 'text-emerald-600'}"
										>
											{Number(m.quantity) > 0 ? '+' : ''}{number(m.quantity)}
										</span>
									</div>
								</li>
							{/each}
						</ul>
					{:else}
						<p class="px-5 py-10 text-center text-sm text-slate-400">
							{i18n.t('inv2.noMovements')}
						</p>
					{/if}
				</section>
			</div>
		{:else if active === 'suppliers'}
			{#if supplierRows.length}
				<div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
					{#each supplierRows as s (s.id)}
						<div class="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
							<div class="mb-2 flex items-center gap-2">
								<span
									class="flex size-9 items-center justify-center rounded-lg bg-amber-50 text-amber-600"
									><Icon name="truck" size={16} /></span
								>
								<p class="truncate text-sm font-semibold text-slate-800">{s.name}</p>
							</div>
							{#if s.contact_name}<p class="text-xs text-slate-500">{s.contact_name}</p>{/if}
							{#if s.phone}<p class="text-xs text-slate-400" dir="ltr">{s.phone}</p>{/if}
							{#if s.payment_terms}<p class="mt-1 text-xs text-slate-400">{s.payment_terms}</p>{/if}
						</div>
					{/each}
				</div>
			{:else}
				<div
					class="rounded-xl border border-dashed border-slate-200 bg-white p-10 text-center text-sm text-slate-400"
				>
					{i18n.t('sup.empty')}
				</div>
			{/if}
		{:else if poRows.length}
			<div class="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
				<table class="w-full text-sm">
					<thead class="border-b border-slate-100 text-xs text-slate-400">
						<tr>
							<th class="px-4 py-3 text-start font-medium">{i18n.t('po.number')}</th>
							<th class="px-4 py-3 text-start font-medium">{i18n.t('po.supplier')}</th>
							<th class="px-4 py-3 text-start font-medium">{i18n.t('po.expected')}</th>
							<th class="px-4 py-3 text-end font-medium">{i18n.t('common.total')}</th>
							<th class="px-4 py-3 text-start font-medium">{i18n.t('common.status')}</th>
							<th class="px-4 py-3 text-end font-medium"></th>
						</tr>
					</thead>
					<tbody class="divide-y divide-slate-50">
						{#each poRows as po (po.id)}
							<tr class="transition hover:bg-slate-50">
								<td class="px-4 py-3 font-medium text-slate-800" dir="ltr">{po.po_number || '—'}</td
								>
								<td class="px-4 py-3 text-slate-600"
									>{supplierIndex.get(po.supplier)?.name ?? '—'}</td
								>
								<td class="px-4 py-3 text-slate-500">{date(po.expected_at)}</td>
								<td class="px-4 py-3 text-end text-slate-700 tabular-nums"
									>{money(po.total_amount, currency)}</td
								>
								<td class="px-4 py-3"
									><Badge
										label={enumLabel('po', po.status)}
										variant={statusVariant(po.status)}
									/></td
								>
								<td class="px-4 py-3 text-end">
									{#if canManage && po.status === 'draft'}
										<button
											onclick={() => submitPO(po.id)}
											disabled={busyId === po.id}
											class="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-2.5 py-1.5 text-xs font-medium text-slate-600 transition hover:bg-slate-50 disabled:opacity-50"
										>
											{#if busyId === po.id}<Spinner size={14} />{:else}<Icon
													name="send"
													size={14}
												/>{/if}{i18n.t('po.submit')}
										</button>
									{/if}
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		{:else}
			<div
				class="rounded-xl border border-dashed border-slate-200 bg-white p-10 text-center text-sm text-slate-400"
			>
				{i18n.t('po.empty')}
			</div>
		{/if}
	</DataState>
</div>

{#if modal === 'supplier'}
	<Modal title={i18n.t('sup.new')} onClose={() => (modal = null)}>
		<div class="space-y-4">
			<Field label={i18n.t('common.name')}
				><input bind:value={supName} maxlength="255" class={INPUT} /></Field
			>
			<div class="grid grid-cols-2 gap-4">
				<Field label={i18n.t('sup.contact')} optional
					><input bind:value={supContact} class={INPUT} /></Field
				>
				<Field label={i18n.t('customers.form.phone')} optional
					><input bind:value={supPhone} class={INPUT} dir="ltr" /></Field
				>
			</div>
			<div class="grid grid-cols-2 gap-4">
				<Field label={i18n.t('customers.form.email')} optional
					><input type="email" bind:value={supEmail} class={INPUT} dir="ltr" /></Field
				>
				<Field label={i18n.t('sup.terms')} optional
					><input bind:value={supTerms} class={INPUT} /></Field
				>
			</div>
		</div>
		{#snippet footer()}
			<button
				onclick={() => (modal = null)}
				class="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-50"
				>{i18n.t('common.cancel')}</button
			>
			<button
				onclick={createSupplier}
				disabled={saving || !supName}
				class="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-60"
			>
				{#if saving}<Spinner size={16} />{/if}{i18n.t('common.create')}
			</button>
		{/snippet}
	</Modal>
{:else if modal === 'po'}
	<Modal title={i18n.t('po.new')} onClose={() => (modal = null)} size="sm">
		<div class="space-y-4">
			<Field label={i18n.t('po.supplier')}>
				<select bind:value={poSupplier} class={INPUT}>
					{#each supplierRows as s (s.id)}<option value={s.id}>{s.name}</option>{/each}
				</select>
			</Field>
			<Field label={i18n.t('common.branch')}>
				<select bind:value={poBranch} class={INPUT}>
					{#each branchRows as b (b.id)}<option value={b.id}>{b.name}</option>{/each}
				</select>
			</Field>
			<Field label={i18n.t('po.expected')} optional>
				<input type="date" bind:value={poExpected} class={INPUT} dir="ltr" />
			</Field>
		</div>
		{#snippet footer()}
			<button
				onclick={() => (modal = null)}
				class="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-50"
				>{i18n.t('common.cancel')}</button
			>
			<button
				onclick={createPO}
				disabled={saving || !poSupplier || !poBranch}
				class="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-60"
			>
				{#if saving}<Spinner size={16} />{/if}{i18n.t('common.create')}
			</button>
		{/snippet}
	</Modal>
{/if}
