<script>
	import { i18n } from '$lib/i18n/i18n.svelte.js';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { toasts } from '$lib/stores/toast.svelte.js';
	import {
		invoices,
		payments,
		refunds,
		generateEInvoice,
		executeRefund
	} from '$lib/api/financials.js';
	import { customers } from '$lib/api/customers.js';
	import { errMessage, isAbortError } from '$lib/api/client.js';
	import { scopeToOrg, indexById, customerName } from '$lib/utils/scope.js';
	import { statusVariant, enumLabel } from '$lib/utils/status.js';
	import { money, number, date, dateTime } from '$lib/utils/format.js';
	import PageHeader from '$lib/components/ui/PageHeader.svelte';
	import Tabs from '$lib/components/ui/Tabs.svelte';
	import DataState from '$lib/components/ui/DataState.svelte';
	import StatCard from '$lib/components/ui/StatCard.svelte';
	import Badge from '$lib/components/ui/Badge.svelte';
	import Icon from '$lib/components/ui/Icon.svelte';
	import Spinner from '$lib/components/ui/Spinner.svelte';
	import RecordPaymentModal from '$lib/components/finance/RecordPaymentModal.svelte';

	let active = $state('invoices');
	let loading = $state(true);
	let error = $state('');
	/** @type {any[]} */
	let invoiceRows = $state([]);
	/** @type {any[]} */
	let paymentRows = $state([]);
	/** @type {any[]} */
	let refundRows = $state([]);
	/** @type {Map<string, any>} */
	let customerIndex = $state(new Map());
	let showPayment = $state(false);
	/** @type {string | null} */
	let busyId = $state(null);

	const currency = $derived(auth.currentOrg?.currency ?? 'SAR');
	const canAccount = $derived(auth.hasRole('accountant'));
	const canManage = $derived(auth.hasRole('manager'));

	const tabs = $derived([
		{ key: 'invoices', label: i18n.t('fin.tab.invoices') },
		{ key: 'payments', label: i18n.t('fin.tab.payments') },
		{ key: 'refunds', label: i18n.t('fin.tab.refunds') }
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
			const [inv, pay, ref, c] = await Promise.all([
				invoices.list(undefined, { signal }),
				payments.list(undefined, { signal }),
				refunds.list(undefined, { signal }),
				customers.list(undefined, { signal })
			]);
			invoiceRows = scopeToOrg(inv, orgId);
			paymentRows = scopeToOrg(pay, orgId);
			refundRows = scopeToOrg(ref, orgId);
			customerIndex = indexById(scopeToOrg(c, orgId));
		} catch (err) {
			if (isAbortError(err)) return;
			error = errMessage(err) || i18n.t('common.error');
		} finally {
			if (!signal?.aborted) loading = false;
		}
	}

	const collected = $derived(
		paymentRows
			.filter((p) => p.status === 'completed')
			.reduce((sum, p) => sum + (Number(p.amount) || 0), 0)
	);
	const outstanding = $derived(
		invoiceRows.reduce((sum, i) => sum + (Number(i.amount_due) || 0), 0)
	);
	const refunded = $derived(
		refundRows
			.filter((r) => r.status === 'processed')
			.reduce((sum, r) => sum + (Number(r.amount) || 0), 0)
	);

	/** @param {string} id */
	async function onEInvoice(id) {
		busyId = id;
		try {
			await generateEInvoice(id);
			toasts.success(i18n.t('inv.eInvoiceQueued'));
		} catch (err) {
			toasts.error(errMessage(err) || i18n.t('common.error'));
		} finally {
			busyId = null;
		}
	}

	/** @param {string} id */
	async function onExecuteRefund(id) {
		busyId = id;
		try {
			await executeRefund(id);
			toasts.success(i18n.t('ref.executed'));
			if (auth.currentOrgId) load(auth.currentOrgId);
		} catch (err) {
			toasts.error(errMessage(err) || i18n.t('common.error'));
		} finally {
			busyId = null;
		}
	}

	/** @param {any} payment */
	function onPaymentCreated(payment) {
		paymentRows = [payment, ...paymentRows];
		showPayment = false;
	}
</script>

<div class="mx-auto max-w-6xl">
	<PageHeader title={i18n.t('fin.title')} subtitle={i18n.t('fin.subtitle')} />

	<div class="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
		<StatCard
			label={i18n.t('fin.stat.collected')}
			value={money(collected, currency)}
			icon="dollar"
			tone="brand"
		/>
		<StatCard
			label={i18n.t('fin.stat.outstanding')}
			value={money(outstanding, currency)}
			icon="receipt"
			tone="amber"
		/>
		<StatCard
			label={i18n.t('fin.stat.refunded')}
			value={money(refunded, currency)}
			icon="refresh"
			tone="rose"
		/>
	</div>

	<div class="mb-4 flex items-center justify-between gap-3">
		<Tabs {tabs} {active} onSelect={(k) => (active = k)} />
		{#if active === 'payments' && canAccount}
			<button
				onclick={() => (showPayment = true)}
				class="flex shrink-0 items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700"
			>
				<Icon name="plus" size={16} />{i18n.t('pay.record')}
			</button>
		{/if}
	</div>

	<DataState {loading} {error} onRetry={() => auth.currentOrgId && load(auth.currentOrgId)}>
		{#if active === 'invoices'}
			{#if invoiceRows.length}
				<div class="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
					<table class="w-full text-sm">
						<thead class="border-b border-slate-100 text-xs text-slate-400">
							<tr>
								<th class="px-4 py-3 text-start font-medium">{i18n.t('inv.number')}</th>
								<th class="px-4 py-3 text-start font-medium">{i18n.t('common.customer')}</th>
								<th class="px-4 py-3 text-end font-medium">{i18n.t('common.total')}</th>
								<th class="px-4 py-3 text-end font-medium">{i18n.t('inv.due')}</th>
								<th class="px-4 py-3 text-start font-medium">{i18n.t('common.status')}</th>
								<th class="px-4 py-3 text-end font-medium"></th>
							</tr>
						</thead>
						<tbody class="divide-y divide-slate-50">
							{#each invoiceRows as inv (inv.id)}
								<tr class="transition hover:bg-slate-50">
									<td class="px-4 py-3 font-medium text-slate-800" dir="ltr"
										>{inv.invoice_number}</td
									>
									<td class="px-4 py-3 text-slate-600"
										>{customerName(customerIndex.get(inv.customer))}</td
									>
									<td class="px-4 py-3 text-end text-slate-700 tabular-nums"
										>{money(inv.total_amount, currency)}</td
									>
									<td class="px-4 py-3 text-end font-medium text-slate-800 tabular-nums"
										>{money(inv.amount_due, currency)}</td
									>
									<td class="px-4 py-3"
										><Badge
											label={enumLabel('invoice', inv.status)}
											variant={statusVariant(inv.status)}
										/></td
									>
									<td class="px-4 py-3 text-end">
										{#if canAccount}
											<button
												onclick={() => onEInvoice(inv.id)}
												disabled={busyId === inv.id}
												class="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-2.5 py-1.5 text-xs font-medium text-slate-600 transition hover:bg-slate-50 disabled:opacity-50"
												title={i18n.t('inv.generateEInvoice')}
											>
												{#if busyId === inv.id}<Spinner size={14} />{:else}<Icon
														name="file"
														size={14}
													/>{/if}
												{i18n.t('inv.einvoice')}
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
					{i18n.t('inv.empty')}
				</div>
			{/if}
		{:else if active === 'payments'}
			{#if paymentRows.length}
				<div class="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
					<table class="w-full text-sm">
						<thead class="border-b border-slate-100 text-xs text-slate-400">
							<tr>
								<th class="px-4 py-3 text-start font-medium">{i18n.t('common.date')}</th>
								<th class="px-4 py-3 text-start font-medium">{i18n.t('common.customer')}</th>
								<th class="px-4 py-3 text-start font-medium">{i18n.t('pay.method')}</th>
								<th class="px-4 py-3 text-end font-medium">{i18n.t('common.amount')}</th>
								<th class="px-4 py-3 text-start font-medium">{i18n.t('common.status')}</th>
							</tr>
						</thead>
						<tbody class="divide-y divide-slate-50">
							{#each paymentRows as p (p.id)}
								<tr class="transition hover:bg-slate-50">
									<td class="px-4 py-3 text-slate-500">{dateTime(p.created_at)}</td>
									<td class="px-4 py-3 text-slate-600"
										>{customerName(customerIndex.get(p.customer))}</td
									>
									<td class="px-4 py-3"><Badge label={enumLabel('method', p.payment_method)} /></td>
									<td class="px-4 py-3 text-end font-medium text-slate-800 tabular-nums"
										>{money(p.amount, p.currency || currency)}</td
									>
									<td class="px-4 py-3"
										><Badge
											label={enumLabel('payment', p.status)}
											variant={statusVariant(p.status)}
										/></td
									>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			{:else}
				<div
					class="rounded-xl border border-dashed border-slate-200 bg-white p-10 text-center text-sm text-slate-400"
				>
					{i18n.t('pay.empty')}
				</div>
			{/if}
		{:else if refundRows.length}
			<div class="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
				<table class="w-full text-sm">
					<thead class="border-b border-slate-100 text-xs text-slate-400">
						<tr>
							<th class="px-4 py-3 text-start font-medium">{i18n.t('common.date')}</th>
							<th class="px-4 py-3 text-end font-medium">{i18n.t('ref.amount')}</th>
							<th class="px-4 py-3 text-start font-medium">{i18n.t('ref.type')}</th>
							<th class="px-4 py-3 text-start font-medium">{i18n.t('common.status')}</th>
							<th class="px-4 py-3 text-end font-medium"></th>
						</tr>
					</thead>
					<tbody class="divide-y divide-slate-50">
						{#each refundRows as r (r.id)}
							<tr class="transition hover:bg-slate-50">
								<td class="px-4 py-3 text-slate-500">{date(r.created_at)}</td>
								<td class="px-4 py-3 text-end font-medium text-slate-800 tabular-nums"
									>{money(r.amount, currency)}</td
								>
								<td class="px-4 py-3"><Badge label={enumLabel('refundType', r.refund_type)} /></td>
								<td class="px-4 py-3"
									><Badge
										label={enumLabel('refund', r.status)}
										variant={statusVariant(r.status)}
									/></td
								>
								<td class="px-4 py-3 text-end">
									{#if canManage && r.status === 'approved'}
										<button
											onclick={() => onExecuteRefund(r.id)}
											disabled={busyId === r.id}
											class="inline-flex items-center gap-1.5 rounded-lg bg-rose-600 px-2.5 py-1.5 text-xs font-semibold text-white transition hover:bg-rose-700 disabled:opacity-50"
										>
											{#if busyId === r.id}<Spinner size={14} />{/if}{i18n.t('ref.execute')}
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
				{i18n.t('ref.empty.fin')}
			</div>
		{/if}
	</DataState>
</div>

{#if showPayment}
	<RecordPaymentModal onClose={() => (showPayment = false)} onCreated={onPaymentCreated} />
{/if}
