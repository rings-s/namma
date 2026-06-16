<script>
	import { i18n } from '$lib/i18n/i18n.svelte.js';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { toasts } from '$lib/stores/toast.svelte.js';
	import { referralPrograms, referrals, qualifyReferral } from '$lib/api/marketing.js';
	import { customers } from '$lib/api/customers.js';
	import { errMessage, isAbortError } from '$lib/api/client.js';
	import { scopeToOrg, indexById, customerName } from '$lib/utils/scope.js';
	import { enumLabel, statusVariant } from '$lib/utils/status.js';
	import { money } from '$lib/utils/format.js';
	import PageHeader from '$lib/components/ui/PageHeader.svelte';
	import DataState from '$lib/components/ui/DataState.svelte';
	import Badge from '$lib/components/ui/Badge.svelte';
	import Icon from '$lib/components/ui/Icon.svelte';
	import Modal from '$lib/components/ui/Modal.svelte';
	import Spinner from '$lib/components/ui/Spinner.svelte';

	const REWARD_TYPES = ['loyalty_points', 'store_credit'];

	/** @type {any[]} */
	let programs = $state([]);
	/** @type {any[]} */
	let refs = $state([]);
	/** @type {any[]} */
	let customersList = $state([]);
	let loading = $state(true);
	let error = $state('');

	const canQualify = $derived(auth.hasRole('receptionist'));
	const customersById = $derived(indexById(customersList));
	const programsById = $derived(indexById(programs));
	const currency = $derived(auth.currentOrg?.currency ?? 'SAR');

	// program form
	let showProgram = $state(false);
	let pName = $state('');
	let pRrType = $state('loyalty_points');
	let pRrValue = $state('0');
	let pReType = $state('loyalty_points');
	let pReValue = $state('0');
	let pMinSpend = $state('0');
	let pMax = $state('20');
	let savingProgram = $state(false);

	// referral create
	let showReferral = $state(false);
	let rProgram = $state('');
	let rReferrer = $state('');
	let creatingRef = $state(false);

	// qualify
	let showQualify = $state(false);
	/** @type {any} */
	let qualifyTarget = $state(null);
	let qReferee = $state('');
	let qualifying = $state(false);

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
			const [progs, rfs, custs] = await Promise.all([
				referralPrograms.list(undefined, { signal }),
				referrals.list(undefined, { signal }),
				customers.list(undefined, { signal })
			]);
			programs = scopeToOrg(progs, orgId);
			refs = scopeToOrg(rfs, orgId);
			customersList = scopeToOrg(custs, orgId);
		} catch (err) {
			if (isAbortError(err)) return;
			error = errMessage(err) || i18n.t('common.error');
		} finally {
			if (!signal?.aborted) loading = false;
		}
	}

	/** @param {SubmitEvent} event */
	async function saveProgram(event) {
		event.preventDefault();
		savingProgram = true;
		try {
			const created = await referralPrograms.create({
				organization: auth.currentOrgId,
				name: pName,
				referrer_reward_type: pRrType,
				referrer_reward_value: pRrValue,
				referee_reward_type: pReType,
				referee_reward_value: pReValue,
				min_referee_spend: pMinSpend,
				max_referrals_per_customer: Number(pMax),
				is_active: true
			});
			programs = [created, ...programs];
			showProgram = false;
			pName = '';
			toasts.success(i18n.t('common.saved'));
		} catch (err) {
			toasts.error(errMessage(err) || i18n.t('common.error'));
		} finally {
			savingProgram = false;
		}
	}

	/** @param {SubmitEvent} event */
	async function createReferral(event) {
		event.preventDefault();
		creatingRef = true;
		try {
			const created = await referrals.create({
				organization: auth.currentOrgId,
				program: rProgram,
				referrer: rReferrer
			});
			refs = [created, ...refs];
			showReferral = false;
			rProgram = '';
			rReferrer = '';
			toasts.success(i18n.t('ref.created'));
		} catch (err) {
			toasts.error(errMessage(err) || i18n.t('common.error'));
		} finally {
			creatingRef = false;
		}
	}

	/** @param {any} referral */
	function openQualify(referral) {
		qualifyTarget = referral;
		qReferee = '';
		showQualify = true;
	}

	/** @param {SubmitEvent} event */
	async function submitQualify(event) {
		event.preventDefault();
		qualifying = true;
		try {
			// Backend runs fraud guards: it may return the referral as `rejected`
			// with a reason, or raise a validation error.
			const updated = await qualifyReferral(qualifyTarget.id, { referee: qReferee });
			refs = refs.map((r) => (r.id === updated.id ? updated : r));
			showQualify = false;
			toasts.success(i18n.t('ref.qualified'));
		} catch (err) {
			toasts.error(errMessage(err) || i18n.t('common.error'));
		} finally {
			qualifying = false;
		}
	}
</script>

<div class="mx-auto max-w-5xl">
	<PageHeader title={i18n.t('ref.title')} subtitle={i18n.t('ref.subtitle')}>
		{#snippet actions()}
			<button
				onclick={() => (showReferral = true)}
				disabled={!programs.length}
				class="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-50"
			>
				<Icon name="plus" size={16} />{i18n.t('ref.new')}
			</button>
		{/snippet}
	</PageHeader>

	<DataState {loading} {error} onRetry={() => auth.currentOrgId && load(auth.currentOrgId)}>
		<!-- Programs -->
		<section class="mb-8">
			<div class="mb-3 flex items-center justify-between">
				<h2 class="text-lg font-semibold text-slate-900">{i18n.t('ref.programs')}</h2>
				<button
					onclick={() => (showProgram = true)}
					class="flex items-center gap-1.5 text-sm font-semibold text-brand-700 hover:underline"
				>
					<Icon name="plus" size={15} />{i18n.t('ref.newProgram')}
				</button>
			</div>
			{#if programs.length}
				<div class="grid gap-4 sm:grid-cols-2">
					{#each programs as p (p.id)}
						<div class="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
							<h3 class="font-semibold text-slate-900">{p.name}</h3>
							<dl class="mt-3 space-y-1 text-sm">
								<div class="flex justify-between">
									<dt class="text-slate-400">{i18n.t('ref.referrerReward')}</dt>
									<dd class="font-medium text-slate-700">
										{p.referrer_reward_value} · {enumLabel('reward_type', p.referrer_reward_type)}
									</dd>
								</div>
								<div class="flex justify-between">
									<dt class="text-slate-400">{i18n.t('ref.refereeReward')}</dt>
									<dd class="font-medium text-slate-700">
										{p.referee_reward_value} · {enumLabel('reward_type', p.referee_reward_type)}
									</dd>
								</div>
								<div class="flex justify-between">
									<dt class="text-slate-400">{i18n.t('ref.minSpend')}</dt>
									<dd class="font-medium text-slate-700">{money(p.min_referee_spend, currency)}</dd>
								</div>
								<div class="flex justify-between">
									<dt class="text-slate-400">{i18n.t('ref.maxPerCustomer')}</dt>
									<dd class="font-medium text-slate-700">{p.max_referrals_per_customer}</dd>
								</div>
							</dl>
						</div>
					{/each}
				</div>
			{:else}
				<p
					class="rounded-xl border border-dashed border-slate-200 bg-white p-10 text-center text-sm text-slate-400"
				>
					{i18n.t('ref.noPrograms')}
				</p>
			{/if}
		</section>

		<!-- Referrals -->
		<section>
			<h2 class="mb-3 text-lg font-semibold text-slate-900">{i18n.t('ref.list')}</h2>
			{#if refs.length}
				<div class="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
					<table class="w-full text-sm">
						<thead class="border-b border-slate-100 text-xs text-slate-400">
							<tr>
								<th class="px-4 py-3 text-start font-medium">{i18n.t('ref.code')}</th>
								<th class="px-4 py-3 text-start font-medium">{i18n.t('ref.referrer')}</th>
								<th class="px-4 py-3 text-start font-medium">{i18n.t('ref.referee')}</th>
								<th class="px-4 py-3 text-start font-medium">{i18n.t('common.status')}</th>
								<th class="px-4 py-3 text-end font-medium">{i18n.t('common.actions')}</th>
							</tr>
						</thead>
						<tbody class="divide-y divide-slate-50">
							{#each refs as r (r.id)}
								<tr>
									<td class="px-4 py-3 font-mono text-xs text-slate-600" dir="ltr">{r.code}</td>
									<td class="px-4 py-3 text-slate-700"
										>{customerName(customersById.get(r.referrer))}</td
									>
									<td class="px-4 py-3 text-slate-700"
										>{r.referee ? customerName(customersById.get(r.referee)) : '—'}</td
									>
									<td class="px-4 py-3">
										<Badge
											label={enumLabel('referral_status', r.status)}
											variant={statusVariant(r.status)}
										/>
										{#if r.status === 'rejected' && r.rejection_reason}
											<p class="mt-1 text-xs text-rose-600">{r.rejection_reason}</p>
										{/if}
									</td>
									<td class="px-4 py-3 text-end">
										{#if r.status === 'pending' && canQualify}
											<button
												onclick={() => openQualify(r)}
												class="rounded-lg border border-brand-200 px-3 py-1 text-xs font-semibold text-brand-700 transition hover:bg-brand-50"
											>
												{i18n.t('ref.qualify')}
											</button>
										{/if}
									</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			{:else}
				<p
					class="rounded-xl border border-dashed border-slate-200 bg-white p-10 text-center text-sm text-slate-400"
				>
					{i18n.t('ref.empty')}
				</p>
			{/if}
		</section>
	</DataState>
</div>

{#if showProgram}
	<Modal title={i18n.t('ref.newProgram')} onClose={() => (showProgram = false)}>
		<form id="ref-program" onsubmit={saveProgram} class="space-y-4">
			<div>
				<label for="rp-name" class="mb-1 block text-sm font-medium text-slate-700"
					>{i18n.t('common.name')}</label
				>
				<input
					id="rp-name"
					bind:value={pName}
					required
					maxlength="255"
					class="w-full rounded-lg border-slate-300 text-sm focus:border-brand-500 focus:ring-brand-500"
				/>
			</div>
			<div class="grid grid-cols-2 gap-4">
				<div>
					<label for="rp-rrt" class="mb-1 block text-sm font-medium text-slate-700"
						>{i18n.t('ref.referrerReward')}</label
					>
					<select
						id="rp-rrt"
						bind:value={pRrType}
						class="w-full rounded-lg border-slate-300 text-sm focus:border-brand-500 focus:ring-brand-500"
					>
						{#each REWARD_TYPES as t (t)}<option value={t}>{i18n.t(`enum.${t}`)}</option>{/each}
					</select>
				</div>
				<div>
					<label for="rp-rrv" class="mb-1 block text-sm font-medium text-slate-700">&nbsp;</label>
					<input
						id="rp-rrv"
						type="number"
						min="0"
						step="0.01"
						bind:value={pRrValue}
						class="w-full rounded-lg border-slate-300 text-sm focus:border-brand-500 focus:ring-brand-500"
					/>
				</div>
				<div>
					<label for="rp-ret" class="mb-1 block text-sm font-medium text-slate-700"
						>{i18n.t('ref.refereeReward')}</label
					>
					<select
						id="rp-ret"
						bind:value={pReType}
						class="w-full rounded-lg border-slate-300 text-sm focus:border-brand-500 focus:ring-brand-500"
					>
						{#each REWARD_TYPES as t (t)}<option value={t}>{i18n.t(`enum.${t}`)}</option>{/each}
					</select>
				</div>
				<div>
					<label for="rp-rev" class="mb-1 block text-sm font-medium text-slate-700">&nbsp;</label>
					<input
						id="rp-rev"
						type="number"
						min="0"
						step="0.01"
						bind:value={pReValue}
						class="w-full rounded-lg border-slate-300 text-sm focus:border-brand-500 focus:ring-brand-500"
					/>
				</div>
				<div>
					<label for="rp-min" class="mb-1 block text-sm font-medium text-slate-700"
						>{i18n.t('ref.minSpend')}</label
					>
					<input
						id="rp-min"
						type="number"
						min="0"
						step="0.01"
						bind:value={pMinSpend}
						class="w-full rounded-lg border-slate-300 text-sm focus:border-brand-500 focus:ring-brand-500"
					/>
				</div>
				<div>
					<label for="rp-max" class="mb-1 block text-sm font-medium text-slate-700"
						>{i18n.t('ref.maxPerCustomer')}</label
					>
					<input
						id="rp-max"
						type="number"
						min="1"
						bind:value={pMax}
						class="w-full rounded-lg border-slate-300 text-sm focus:border-brand-500 focus:ring-brand-500"
					/>
				</div>
			</div>
		</form>
		{#snippet footer()}
			<button
				onclick={() => (showProgram = false)}
				class="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-50"
				>{i18n.t('common.cancel')}</button
			>
			<button
				type="submit"
				form="ref-program"
				disabled={savingProgram || !pName}
				class="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-60"
			>
				{#if savingProgram}<Spinner size={16} />{/if}{i18n.t('common.create')}
			</button>
		{/snippet}
	</Modal>
{/if}

{#if showReferral}
	<Modal title={i18n.t('ref.new')} onClose={() => (showReferral = false)} size="sm">
		<form id="ref-create" onsubmit={createReferral} class="space-y-4">
			<div>
				<label for="rc-program" class="mb-1 block text-sm font-medium text-slate-700"
					>{i18n.t('ref.program')}</label
				>
				<select
					id="rc-program"
					bind:value={rProgram}
					required
					class="w-full rounded-lg border-slate-300 text-sm focus:border-brand-500 focus:ring-brand-500"
				>
					<option value="">—</option>
					{#each programs as p (p.id)}<option value={p.id}>{p.name}</option>{/each}
				</select>
			</div>
			<div>
				<label for="rc-referrer" class="mb-1 block text-sm font-medium text-slate-700"
					>{i18n.t('ref.referrer')}</label
				>
				<select
					id="rc-referrer"
					bind:value={rReferrer}
					required
					class="w-full rounded-lg border-slate-300 text-sm focus:border-brand-500 focus:ring-brand-500"
				>
					<option value="">—</option>
					{#each customersList as c (c.id)}<option value={c.id}>{customerName(c)}</option>{/each}
				</select>
			</div>
		</form>
		{#snippet footer()}
			<button
				onclick={() => (showReferral = false)}
				class="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-50"
				>{i18n.t('common.cancel')}</button
			>
			<button
				type="submit"
				form="ref-create"
				disabled={creatingRef || !rProgram || !rReferrer}
				class="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-60"
			>
				{#if creatingRef}<Spinner size={16} />{/if}{i18n.t('common.create')}
			</button>
		{/snippet}
	</Modal>
{/if}

{#if showQualify}
	<Modal title={i18n.t('ref.qualifyTitle')} onClose={() => (showQualify = false)} size="sm">
		<form id="ref-qualify" onsubmit={submitQualify} class="space-y-4">
			<div>
				<label for="rq-referee" class="mb-1 block text-sm font-medium text-slate-700"
					>{i18n.t('ref.referee')}</label
				>
				<select
					id="rq-referee"
					bind:value={qReferee}
					required
					class="w-full rounded-lg border-slate-300 text-sm focus:border-brand-500 focus:ring-brand-500"
				>
					<option value="">—</option>
					{#each customersList as c (c.id)}<option value={c.id}>{customerName(c)}</option>{/each}
				</select>
			</div>
		</form>
		{#snippet footer()}
			<button
				onclick={() => (showQualify = false)}
				class="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-50"
				>{i18n.t('common.cancel')}</button
			>
			<button
				type="submit"
				form="ref-qualify"
				disabled={qualifying || !qReferee}
				class="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-60"
			>
				{#if qualifying}<Spinner size={16} />{/if}{i18n.t('ref.qualify')}
			</button>
		{/snippet}
	</Modal>
{/if}
