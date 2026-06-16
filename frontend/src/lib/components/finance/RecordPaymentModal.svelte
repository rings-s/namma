<script>
	import { i18n } from '$lib/i18n/i18n.svelte.js';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { toasts } from '$lib/stores/toast.svelte.js';
	import { payments, invoices } from '$lib/api/financials.js';
	import { customers } from '$lib/api/customers.js';
	import { ApiError, errMessage, isAbortError } from '$lib/api/client.js';
	import { scopeToOrg, customerName } from '$lib/utils/scope.js';
	import { money } from '$lib/utils/format.js';
	import Modal from '$lib/components/ui/Modal.svelte';
	import Field from '$lib/components/ui/Field.svelte';
	import Spinner from '$lib/components/ui/Spinner.svelte';

	/**
	 * Record a manual payment (cash/card/transfer). Invoice and customer are
	 * optional; the payment posts as completed so it counts toward collections.
	 * @type {{ onClose: () => void; onCreated: (payment: any) => void }}
	 */
	let { onClose, onCreated } = $props();

	const INPUT =
		'w-full rounded-lg border-slate-300 text-sm focus:border-brand-500 focus:ring-brand-500';
	const currency = $derived(auth.currentOrg?.currency ?? 'SAR');
	const METHODS = ['cash', 'card', 'mada', 'apple_pay', 'stc_pay', 'bank_transfer', 'wallet'];

	let loading = $state(true);
	let saving = $state(false);
	/** @type {any[]} */
	let invoiceRows = $state([]);
	/** @type {any[]} */
	let customerRows = $state([]);

	let invoice = $state('');
	let customer = $state('');
	let method = $state('cash');
	let amount = $state('');
	let reference = $state('');
	/** @type {Record<string, string>} */
	let fieldErrors = $state({});

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
		try {
			const [inv, c] = await Promise.all([
				invoices.list(undefined, { signal }),
				customers.list(undefined, { signal })
			]);
			invoiceRows = scopeToOrg(inv, orgId).filter(
				(/** @type {any} */ r) => r.status !== 'paid' && r.status !== 'void'
			);
			customerRows = scopeToOrg(c, orgId);
		} catch (err) {
			if (isAbortError(err)) return;
			toasts.error(errMessage(err) || i18n.t('common.error'));
		} finally {
			if (!signal?.aborted) loading = false;
		}
	}

	// Default the amount + customer from the chosen invoice.
	$effect(() => {
		const inv = invoiceRows.find((r) => r.id === invoice);
		if (inv) {
			if (!amount) amount = String(inv.amount_due ?? inv.total_amount ?? '');
			if (inv.customer) customer = inv.customer;
		}
	});

	/** @param {SubmitEvent} event */
	async function submit(event) {
		event.preventDefault();
		saving = true;
		fieldErrors = {};
		try {
			const created = await payments.create({
				organization: auth.currentOrgId,
				invoice: invoice || null,
				customer: customer || null,
				payment_method: method,
				gateway: 'manual',
				gateway_transaction_id: reference,
				amount: Number(amount) || 0,
				currency,
				status: 'completed'
			});
			toasts.success(i18n.t('pay.recorded'));
			onCreated(created);
		} catch (err) {
			if (err instanceof ApiError && err.data && typeof err.data === 'object') {
				for (const [key, val] of Object.entries(err.data)) {
					fieldErrors[key] = Array.isArray(val) ? val.join(' ') : String(val);
				}
			}
			toasts.error(errMessage(err) || i18n.t('common.error'));
		} finally {
			saving = false;
		}
	}
</script>

<Modal title={i18n.t('pay.record')} {onClose}>
	{#if loading}
		<div class="flex items-center justify-center py-12 text-slate-400"><Spinner size={24} /></div>
	{:else}
		<form id="pay-form" onsubmit={submit} class="space-y-4">
			<Field label={i18n.t('pay.invoice')} optional error={fieldErrors.invoice}>
				<select bind:value={invoice} class={INPUT}>
					<option value="">{i18n.t('common.none.option')}</option>
					{#each invoiceRows as inv (inv.id)}
						<option value={inv.id}>{inv.invoice_number} · {money(inv.amount_due, currency)}</option>
					{/each}
				</select>
			</Field>
			<Field label={i18n.t('common.customer')} optional error={fieldErrors.customer}>
				<select bind:value={customer} class={INPUT}>
					<option value="">{i18n.t('common.none.option')}</option>
					{#each customerRows as c (c.id)}<option value={c.id}>{customerName(c)}</option>{/each}
				</select>
			</Field>
			<div class="grid grid-cols-2 gap-4">
				<Field label={i18n.t('pay.method')}>
					<select bind:value={method} class={INPUT}>
						{#each METHODS as m (m)}<option value={m}>{i18n.t(`enum.${m}`)}</option>{/each}
					</select>
				</Field>
				<Field label={i18n.t('common.amount')} error={fieldErrors.amount}>
					<input
						type="number"
						min="0.01"
						step="0.01"
						bind:value={amount}
						required
						class={INPUT}
						dir="ltr"
					/>
				</Field>
			</div>
			<Field label={i18n.t('common.reference')} optional>
				<input bind:value={reference} maxlength="255" class={INPUT} dir="ltr" />
			</Field>
		</form>
	{/if}
	{#snippet footer()}
		<button
			onclick={onClose}
			class="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-50"
			>{i18n.t('common.cancel')}</button
		>
		<button
			type="submit"
			form="pay-form"
			disabled={saving || loading || !amount}
			class="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-60"
		>
			{#if saving}<Spinner size={16} />{/if}{i18n.t('common.save')}
		</button>
	{/snippet}
</Modal>
