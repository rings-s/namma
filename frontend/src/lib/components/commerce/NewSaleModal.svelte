<script>
	import { i18n } from '$lib/i18n/i18n.svelte.js';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { toasts } from '$lib/stores/toast.svelte.js';
	import { sales, saleItems, services, products } from '$lib/api/commerce.js';
	import { branches } from '$lib/api/organizations.js';
	import { customers } from '$lib/api/customers.js';
	import { employees } from '$lib/api/operations.js';
	import { errMessage, isAbortError } from '$lib/api/client.js';
	import { scopeToOrg, customerName } from '$lib/utils/scope.js';
	import { money } from '$lib/utils/format.js';
	import Modal from '$lib/components/ui/Modal.svelte';
	import Field from '$lib/components/ui/Field.svelte';
	import Icon from '$lib/components/ui/Icon.svelte';
	import Spinner from '$lib/components/ui/Spinner.svelte';

	/**
	 * Point-of-sale ticket builder. Branch is required by the model; customer and
	 * employee are optional. Creates the Sale as `completed` (which commits stock
	 * server-side) then appends each line as a SaleItem.
	 * @type {{ onClose: () => void; onCreated: (sale: any) => void }}
	 */
	let { onClose, onCreated } = $props();

	const INPUT =
		'w-full rounded-lg border-slate-300 text-sm focus:border-brand-500 focus:ring-brand-500';
	const currency = $derived(auth.currentOrg?.currency ?? 'SAR');

	let loading = $state(true);
	let saving = $state(false);
	/** @type {any[]} */
	let branchRows = $state([]);
	/** @type {any[]} */
	let customerRows = $state([]);
	/** @type {any[]} */
	let employeeRows = $state([]);
	/** @type {any[]} */
	let serviceRows = $state([]);
	/** @type {any[]} */
	let productRows = $state([]);

	let branch = $state('');
	let customer = $state('');
	let employee = $state('');
	let discount = $state('0');
	let notes = $state('');
	let picker = $state('');
	/** @type {{ key: string; kind: 'service' | 'product'; refId: string; description: string; unit_price: number; quantity: number }[]} */
	let items = $state([]);

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
			const [b, c, e, s, p] = await Promise.all([
				branches.list(undefined, { signal }),
				customers.list(undefined, { signal }),
				employees.list(undefined, { signal }),
				services.list(undefined, { signal }),
				products.list(undefined, { signal })
			]);
			branchRows = scopeToOrg(b, orgId).filter((/** @type {any} */ r) => r.is_active !== false);
			customerRows = scopeToOrg(c, orgId);
			employeeRows = scopeToOrg(e, orgId).filter((/** @type {any} */ r) => r.is_active !== false);
			serviceRows = scopeToOrg(s, orgId).filter((/** @type {any} */ r) => r.is_active !== false);
			productRows = scopeToOrg(p, orgId).filter((/** @type {any} */ r) => r.is_active !== false);
			branch = branchRows[0]?.id ?? '';
		} catch (err) {
			if (isAbortError(err)) return;
			toasts.error(errMessage(err) || i18n.t('common.error'));
		} finally {
			if (!signal?.aborted) loading = false;
		}
	}

	function addPicked() {
		if (!picker) return;
		const [kind, refId] = picker.split(':');
		const src = kind === 'service' ? serviceRows : productRows;
		const row = src.find((/** @type {any} */ r) => r.id === refId);
		if (!row) return;
		items = [
			...items,
			{
				key: crypto.randomUUID(),
				kind: /** @type {'service' | 'product'} */ (kind),
				refId,
				description: row.name,
				unit_price: Number(row.price) || 0,
				quantity: 1
			}
		];
		picker = '';
	}

	/** @param {string} key */
	function removeItem(key) {
		items = items.filter((it) => it.key !== key);
	}

	const subtotal = $derived(items.reduce((sum, it) => sum + it.unit_price * it.quantity, 0));
	const total = $derived(Math.max(0, subtotal - (Number(discount) || 0)));

	async function submit() {
		if (!branch || !items.length) return;
		saving = true;
		try {
			const sale = await sales.create({
				organization: auth.currentOrgId,
				branch,
				customer: customer || null,
				employee: employee || null,
				status: 'completed',
				subtotal,
				discount_amount: Number(discount) || 0,
				tax_amount: 0,
				total_amount: total,
				notes
			});
			for (const it of items) {
				await saleItems.create({
					sale: sale.id,
					service: it.kind === 'service' ? it.refId : null,
					product: it.kind === 'product' ? it.refId : null,
					description: it.description,
					quantity: it.quantity,
					unit_price: it.unit_price,
					discount: 0,
					total_price: it.unit_price * it.quantity
				});
			}
			toasts.success(i18n.t('sales.created'));
			onCreated(sale);
		} catch (err) {
			toasts.error(errMessage(err) || i18n.t('common.error'));
		} finally {
			saving = false;
		}
	}
</script>

<Modal title={i18n.t('sales.new')} {onClose} size="lg">
	{#if loading}
		<div class="flex items-center justify-center py-12 text-slate-400"><Spinner size={24} /></div>
	{:else}
		<div class="space-y-4">
			<div class="grid grid-cols-1 gap-4 sm:grid-cols-3">
				<Field label={i18n.t('common.branch')}>
					<select bind:value={branch} required class={INPUT}>
						{#each branchRows as b (b.id)}<option value={b.id}>{b.name}</option>{/each}
					</select>
				</Field>
				<Field label={i18n.t('common.customer')} optional>
					<select bind:value={customer} class={INPUT}>
						<option value="">{i18n.t('common.none.option')}</option>
						{#each customerRows as c (c.id)}<option value={c.id}>{customerName(c)}</option>{/each}
					</select>
				</Field>
				<Field label={i18n.t('common.employee')} optional>
					<select bind:value={employee} class={INPUT}>
						<option value="">{i18n.t('common.none.option')}</option>
						{#each employeeRows as e (e.id)}
							<option value={e.id}>{e.job_title || e.employee_code || e.id.slice(0, 8)}</option>
						{/each}
					</select>
				</Field>
			</div>

			<div class="rounded-xl border border-slate-200 bg-slate-50/60 p-4">
				<div class="mb-3 flex items-end gap-2">
					<div class="flex-1">
						<Field label={i18n.t('sales.items')}>
							<select bind:value={picker} class={INPUT}>
								<option value="">{i18n.t('sales.pickItem')}</option>
								{#if serviceRows.length}
									<optgroup label={i18n.t('catalog.services')}>
										{#each serviceRows as s (s.id)}
											<option value="service:{s.id}">{s.name} · {money(s.price, currency)}</option>
										{/each}
									</optgroup>
								{/if}
								{#if productRows.length}
									<optgroup label={i18n.t('catalog.products')}>
										{#each productRows as p (p.id)}
											<option value="product:{p.id}">{p.name} · {money(p.price, currency)}</option>
										{/each}
									</optgroup>
								{/if}
							</select>
						</Field>
					</div>
					<button
						type="button"
						onclick={addPicked}
						disabled={!picker}
						class="flex h-[38px] items-center gap-1.5 rounded-lg bg-brand-600 px-3 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-50"
					>
						<Icon name="plus" size={16} />{i18n.t('sales.addItem')}
					</button>
				</div>

				{#if items.length}
					<div class="space-y-2">
						{#each items as it (it.key)}
							<div
								class="flex items-center gap-3 rounded-lg border border-slate-200 bg-white px-3 py-2"
							>
								<span class="min-w-0 flex-1 truncate text-sm text-slate-700">{it.description}</span>
								<input
									type="number"
									min="1"
									step="1"
									bind:value={it.quantity}
									class="w-16 rounded-lg border-slate-300 text-sm focus:border-brand-500 focus:ring-brand-500"
									dir="ltr"
								/>
								<span class="w-24 text-end text-sm font-medium text-slate-800 tabular-nums">
									{money(it.unit_price * it.quantity, currency)}
								</span>
								<button
									type="button"
									onclick={() => removeItem(it.key)}
									class="rounded-md p-1 text-slate-400 transition hover:bg-rose-50 hover:text-rose-600"
									aria-label={i18n.t('common.remove')}
								>
									<Icon name="trash" size={16} />
								</button>
							</div>
						{/each}
					</div>
				{:else}
					<p class="py-4 text-center text-sm text-slate-400">{i18n.t('sales.noItems')}</p>
				{/if}
			</div>

			<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
				<Field label={i18n.t('common.discount')} optional>
					<input type="number" min="0" step="0.01" bind:value={discount} class={INPUT} dir="ltr" />
				</Field>
				<Field label={i18n.t('common.notes')} optional>
					<input bind:value={notes} class={INPUT} />
				</Field>
			</div>

			<div class="space-y-1 rounded-xl bg-brand-50 px-4 py-3 text-sm">
				<div class="flex justify-between text-slate-600">
					<span>{i18n.t('common.subtotal')}</span><span class="tabular-nums"
						>{money(subtotal, currency)}</span
					>
				</div>
				<div class="flex justify-between text-slate-600">
					<span>{i18n.t('common.discount')}</span><span class="tabular-nums"
						>−{money(Number(discount) || 0, currency)}</span
					>
				</div>
				<div
					class="flex justify-between border-t border-brand-200 pt-1 text-base font-semibold text-brand-800"
				>
					<span>{i18n.t('common.total')}</span><span class="tabular-nums"
						>{money(total, currency)}</span
					>
				</div>
			</div>
		</div>
	{/if}

	{#snippet footer()}
		<button
			onclick={onClose}
			class="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-50"
		>
			{i18n.t('common.cancel')}
		</button>
		<button
			onclick={submit}
			disabled={saving || loading || !branch || !items.length}
			class="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-60"
		>
			{#if saving}<Spinner size={16} />{/if}
			{i18n.t('sales.complete')}
		</button>
	{/snippet}
</Modal>
