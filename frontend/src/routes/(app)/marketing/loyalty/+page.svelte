<script>
	import { i18n } from '$lib/i18n/i18n.svelte.js';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { toasts } from '$lib/stores/toast.svelte.js';
	import { loyaltyPrograms, loyaltyTransactions } from '$lib/api/marketing.js';
	import { customers } from '$lib/api/customers.js';
	import { errMessage, isAbortError } from '$lib/api/client.js';
	import { scopeToOrg, indexById, customerName } from '$lib/utils/scope.js';
	import { enumLabel, statusVariant } from '$lib/utils/status.js';
	import { number, dateTime } from '$lib/utils/format.js';
	import PageHeader from '$lib/components/ui/PageHeader.svelte';
	import DataState from '$lib/components/ui/DataState.svelte';
	import Badge from '$lib/components/ui/Badge.svelte';
	import Icon from '$lib/components/ui/Icon.svelte';
	import Modal from '$lib/components/ui/Modal.svelte';
	import Spinner from '$lib/components/ui/Spinner.svelte';

	/** @type {any[]} */
	let programs = $state([]);
	/** @type {any[]} */
	let transactions = $state([]);
	/** @type {any[]} */
	let customersList = $state([]);
	let loading = $state(true);
	let error = $state('');

	/** @type {any | null} */
	let editing = $state(null);
	let showForm = $state(false);
	let fName = $state('');
	let fPoints = $state('1');
	let fRate = $state('0.01');
	let fActive = $state(true);
	let saving = $state(false);

	const customersById = $derived(indexById(customersList));

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
			const [progs, txns, custs] = await Promise.all([
				loyaltyPrograms.list(undefined, { signal }),
				loyaltyTransactions.list(undefined, { signal }),
				customers.list(undefined, { signal })
			]);
			programs = scopeToOrg(progs, orgId);
			customersList = scopeToOrg(custs, orgId);
			const programIds = new Set(programs.map((p) => p.id));
			transactions = txns.filter((/** @type {any} */ t) => programIds.has(t.loyalty_program));
		} catch (err) {
			if (isAbortError(err)) return;
			error = errMessage(err) || i18n.t('common.error');
		} finally {
			if (!signal?.aborted) loading = false;
		}
	}

	/** @param {any | null} program */
	function openForm(program) {
		editing = program;
		fName = program?.name ?? '';
		fPoints = String(program?.points_per_currency ?? '1');
		fRate = String(program?.redemption_rate ?? '0.01');
		fActive = program?.is_active ?? true;
		showForm = true;
	}

	/** @param {SubmitEvent} event */
	async function save(event) {
		event.preventDefault();
		saving = true;
		const body = {
			organization: auth.currentOrgId,
			name: fName,
			points_per_currency: fPoints,
			redemption_rate: fRate,
			is_active: fActive
		};
		try {
			const saved = editing
				? await loyaltyPrograms.patch(editing.id, body)
				: await loyaltyPrograms.create(body);
			programs = editing
				? programs.map((p) => (p.id === saved.id ? saved : p))
				: [saved, ...programs];
			showForm = false;
			toasts.success(i18n.t('common.saved'));
		} catch (err) {
			toasts.error(errMessage(err) || i18n.t('common.error'));
		} finally {
			saving = false;
		}
	}
</script>

<div class="mx-auto max-w-5xl">
	<PageHeader title={i18n.t('loyalty.title')} subtitle={i18n.t('loyalty.subtitle')}>
		{#snippet actions()}
			<button
				onclick={() => openForm(null)}
				class="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700"
			>
				<Icon name="plus" size={16} />{i18n.t('loyalty.newProgram')}
			</button>
		{/snippet}
	</PageHeader>

	<DataState {loading} {error} onRetry={() => auth.currentOrgId && load(auth.currentOrgId)}>
		<!-- Programs -->
		<section class="mb-8">
			{#if programs.length}
				<div class="grid gap-4 sm:grid-cols-2">
					{#each programs as p (p.id)}
						<div class="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
							<div class="flex items-start justify-between gap-2">
								<div>
									<h3 class="font-semibold text-slate-900">{p.name}</h3>
									<Badge
										class="mt-1"
										label={p.is_active ? i18n.t('enum.active') : i18n.t('enum.inactive')}
										variant={statusVariant(p.is_active ? 'active' : 'inactive')}
									/>
								</div>
								<button
									onclick={() => openForm(p)}
									class="rounded-lg p-1.5 text-slate-400 transition hover:bg-slate-100 hover:text-slate-600"
									aria-label={i18n.t('common.edit')}
								>
									<Icon name="edit" size={16} />
								</button>
							</div>
							<dl class="mt-4 space-y-1 text-sm">
								<div class="flex justify-between">
									<dt class="text-slate-400">{i18n.t('loyalty.pointsPerCurrency')}</dt>
									<dd class="font-medium text-slate-700">{p.points_per_currency}</dd>
								</div>
								<div class="flex justify-between">
									<dt class="text-slate-400">{i18n.t('loyalty.redemptionRate')}</dt>
									<dd class="font-medium text-slate-700">{p.redemption_rate}</dd>
								</div>
							</dl>
						</div>
					{/each}
				</div>
			{:else}
				<p
					class="rounded-xl border border-dashed border-slate-200 bg-white p-10 text-center text-sm text-slate-400"
				>
					{i18n.t('loyalty.noProgram')}
				</p>
			{/if}
		</section>

		<!-- Ledger -->
		<section>
			<h2 class="mb-1 text-lg font-semibold text-slate-900">{i18n.t('loyalty.ledger')}</h2>
			<p class="mb-3 flex items-start gap-1.5 text-xs text-slate-400">
				<Icon name="alert" size={13} class="mt-0.5 shrink-0" />{i18n.t('loyalty.readonlyNote')}
			</p>
			{#if transactions.length}
				<div class="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
					<table class="w-full text-sm">
						<thead class="border-b border-slate-100 text-xs text-slate-400">
							<tr>
								<th class="px-4 py-3 text-start font-medium">{i18n.t('common.name')}</th>
								<th class="px-4 py-3 text-start font-medium">{i18n.t('common.type')}</th>
								<th class="px-4 py-3 text-end font-medium">{i18n.t('loyalty.ledger.points')}</th>
								<th class="px-4 py-3 text-start font-medium">{i18n.t('common.description')}</th>
								<th class="px-4 py-3 text-start font-medium">{i18n.t('customers.col.lastVisit')}</th
								>
							</tr>
						</thead>
						<tbody class="divide-y divide-slate-50">
							{#each transactions as t (t.id)}
								<tr>
									<td class="px-4 py-3 text-slate-700"
										>{customerName(customersById.get(t.customer))}</td
									>
									<td class="px-4 py-3"
										><Badge
											label={enumLabel('loyalty_type', t.type)}
											variant={statusVariant(t.type)}
										/></td
									>
									<td
										class="px-4 py-3 text-end font-medium {t.points < 0
											? 'text-rose-600'
											: 'text-emerald-600'}">{t.points > 0 ? '+' : ''}{number(t.points)}</td
									>
									<td class="px-4 py-3 text-slate-500">{t.description || '—'}</td>
									<td class="px-4 py-3 text-slate-400">{dateTime(t.created_at)}</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			{:else}
				<p
					class="rounded-xl border border-dashed border-slate-200 bg-white p-10 text-center text-sm text-slate-400"
				>
					{i18n.t('loyalty.ledger.empty')}
				</p>
			{/if}
		</section>
	</DataState>
</div>

{#if showForm}
	<Modal
		title={editing ? i18n.t('common.edit') : i18n.t('loyalty.newProgram')}
		onClose={() => (showForm = false)}
	>
		<form id="loyalty-form" onsubmit={save} class="space-y-4">
			<div>
				<label for="lp-name" class="mb-1 block text-sm font-medium text-slate-700"
					>{i18n.t('common.name')}</label
				>
				<input
					id="lp-name"
					bind:value={fName}
					required
					maxlength="255"
					class="w-full rounded-lg border-slate-300 text-sm focus:border-brand-500 focus:ring-brand-500"
				/>
			</div>
			<div class="grid grid-cols-2 gap-4">
				<div>
					<label for="lp-points" class="mb-1 block text-sm font-medium text-slate-700"
						>{i18n.t('loyalty.pointsPerCurrency')}</label
					>
					<input
						id="lp-points"
						type="number"
						min="0"
						step="0.01"
						bind:value={fPoints}
						class="w-full rounded-lg border-slate-300 text-sm focus:border-brand-500 focus:ring-brand-500"
					/>
				</div>
				<div>
					<label for="lp-rate" class="mb-1 block text-sm font-medium text-slate-700"
						>{i18n.t('loyalty.redemptionRate')}</label
					>
					<input
						id="lp-rate"
						type="number"
						min="0"
						step="0.01"
						bind:value={fRate}
						class="w-full rounded-lg border-slate-300 text-sm focus:border-brand-500 focus:ring-brand-500"
					/>
				</div>
			</div>
			<label class="flex items-center gap-3 text-sm text-slate-700">
				<input
					type="checkbox"
					bind:checked={fActive}
					class="rounded border-slate-300 text-brand-600 focus:ring-brand-500"
				/>
				{i18n.t('enum.active')}
			</label>
		</form>
		{#snippet footer()}
			<button
				onclick={() => (showForm = false)}
				class="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-50"
				>{i18n.t('common.cancel')}</button
			>
			<button
				type="submit"
				form="loyalty-form"
				disabled={saving || !fName}
				class="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-60"
			>
				{#if saving}<Spinner size={16} />{/if}{i18n.t('common.save')}
			</button>
		{/snippet}
	</Modal>
{/if}
