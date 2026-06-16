<script>
	import { i18n } from '$lib/i18n/i18n.svelte.js';
	import { toasts } from '$lib/stores/toast.svelte.js';
	import {
		customerSegments,
		customerSegmentMemberships,
		refreshSegment
	} from '$lib/api/customers.js';
	import { errMessage, isAbortError } from '$lib/api/client.js';
	import { enumLabel, statusVariant } from '$lib/utils/status.js';
	import { dateTime } from '$lib/utils/format.js';
	import { customerName } from '$lib/utils/scope.js';
	import Badge from '$lib/components/ui/Badge.svelte';
	import Spinner from '$lib/components/ui/Spinner.svelte';
	import Icon from '$lib/components/ui/Icon.svelte';

	/**
	 * @type {{ segment: any; customersById: Map<string, any>; customersList: any[];
	 *   onChanged: (segment: any) => void }}
	 */
	let { segment, customersById, customersList, onChanged } = $props();

	const SOURCES = ['walk_in', 'online', 'phone', 'referral', 'social', 'import', 'other'];
	const GENDERS = ['male', 'female', 'other'];

	// --- manual membership ---
	/** @type {any[]} */
	let memberships = $state([]);
	let loadingMembers = $state(false);
	let addingCustomer = $state('');
	let busyMember = $state(false);

	// --- dynamic criteria (local editable copy) ---
	let criteria = $state(/** @type {Record<string, any>} */ ({}));
	let savingCriteria = $state(false);
	let refreshing = $state(false);

	$effect(() => {
		criteria = { ...(segment.criteria ?? {}) };
		if (segment.segment_type !== 'manual') return;
		const ctrl = new AbortController();
		loadMembers(segment.id, ctrl.signal);
		return () => ctrl.abort();
	});

	/** @param {string} segmentId @param {AbortSignal} [signal] */
	async function loadMembers(segmentId, signal) {
		loadingMembers = true;
		try {
			const all = await customerSegmentMemberships.list(undefined, { signal });
			memberships = all.filter((/** @type {any} */ m) => m.segment === segmentId);
		} catch (err) {
			if (isAbortError(err)) return;
			toasts.error(errMessage(err) || i18n.t('common.error'));
		} finally {
			if (!signal?.aborted) loadingMembers = false;
		}
	}

	async function addMember() {
		if (!addingCustomer) return;
		busyMember = true;
		try {
			const created = await customerSegmentMemberships.create({
				segment: segment.id,
				customer: addingCustomer
			});
			memberships = [...memberships, created];
			addingCustomer = '';
			toasts.success(i18n.t('segments.memberAdded'));
			onChanged({ ...segment, member_count: (segment.member_count ?? 0) + 1 });
		} catch (err) {
			toasts.error(errMessage(err) || i18n.t('common.error'));
		} finally {
			busyMember = false;
		}
	}

	/** @param {string} membershipId */
	async function removeMember(membershipId) {
		try {
			await customerSegmentMemberships.remove(membershipId);
			memberships = memberships.filter((m) => m.id !== membershipId);
			toasts.success(i18n.t('segments.memberRemoved'));
			onChanged({ ...segment, member_count: Math.max(0, (segment.member_count ?? 1) - 1) });
		} catch (err) {
			toasts.error(errMessage(err) || i18n.t('common.error'));
		}
	}

	/** Prune empty values so we don't store blank criteria keys. */
	function cleanedCriteria() {
		/** @type {Record<string, any>} */
		const out = {};
		for (const [k, v] of Object.entries(criteria)) {
			if (v !== '' && v !== null && v !== undefined) out[k] = v;
		}
		return out;
	}

	async function saveCriteria() {
		savingCriteria = true;
		try {
			const updated = await customerSegments.patch(segment.id, { criteria: cleanedCriteria() });
			toasts.success(i18n.t('common.saved'));
			onChanged(updated);
		} catch (err) {
			toasts.error(errMessage(err) || i18n.t('common.error'));
		} finally {
			savingCriteria = false;
		}
	}

	async function refresh() {
		refreshing = true;
		try {
			const updated = await refreshSegment(segment.id);
			toasts.success(i18n.t('segments.refreshed'));
			onChanged(updated);
		} catch (err) {
			toasts.error(errMessage(err) || i18n.t('common.error'));
		} finally {
			refreshing = false;
		}
	}

	// Members not yet in the segment, for the add picker.
	const candidates = $derived.by(() => {
		const inSegment = new Set(memberships.map((m) => m.customer));
		return customersList.filter((c) => !inSegment.has(c.id));
	});
</script>

<div class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
	<div class="flex items-start justify-between gap-3">
		<div>
			<h2 class="text-lg font-semibold text-slate-900">{segment.name}</h2>
			{#if segment.description}<p class="mt-1 text-sm text-slate-500">{segment.description}</p>{/if}
		</div>
		<Badge
			label={enumLabel('segment_type', segment.segment_type)}
			variant={statusVariant(segment.segment_type)}
		/>
	</div>

	{#if segment.segment_type === 'ai'}
		<p class="mt-4 rounded-lg bg-violet-50 p-3 text-sm text-violet-700">
			{i18n.t('segments.aiReadonly')}
		</p>
		{#if segment.criteria && Object.keys(segment.criteria).length}
			<pre
				class="mt-3 overflow-x-auto rounded-lg bg-slate-50 p-3 text-xs text-slate-600"
				dir="ltr">{JSON.stringify(segment.criteria, null, 2)}</pre>
		{/if}
	{:else if segment.segment_type === 'dynamic'}
		<p class="mt-4 text-xs text-slate-400">{i18n.t('segments.dynamicAuto')}</p>
		<div class="mt-3 grid grid-cols-2 gap-4">
			<label class="text-sm">
				<span class="mb-1 block font-medium text-slate-700">{i18n.t('criteria.min_visits')}</span>
				<input
					type="number"
					min="0"
					bind:value={criteria.min_visits}
					class="w-full rounded-lg border-slate-300 text-sm focus:border-brand-500 focus:ring-brand-500"
				/>
			</label>
			<label class="text-sm">
				<span class="mb-1 block font-medium text-slate-700"
					>{i18n.t('criteria.min_total_spent')}</span
				>
				<input
					type="number"
					min="0"
					step="0.01"
					bind:value={criteria.min_total_spent}
					class="w-full rounded-lg border-slate-300 text-sm focus:border-brand-500 focus:ring-brand-500"
				/>
			</label>
			<label class="text-sm">
				<span class="mb-1 block font-medium text-slate-700"
					>{i18n.t('criteria.last_visit_within_days')}</span
				>
				<input
					type="number"
					min="0"
					bind:value={criteria.last_visit_within_days}
					class="w-full rounded-lg border-slate-300 text-sm focus:border-brand-500 focus:ring-brand-500"
				/>
			</label>
			<label class="text-sm">
				<span class="mb-1 block font-medium text-slate-700"
					>{i18n.t('criteria.last_visit_not_within_days')}</span
				>
				<input
					type="number"
					min="0"
					bind:value={criteria.last_visit_not_within_days}
					class="w-full rounded-lg border-slate-300 text-sm focus:border-brand-500 focus:ring-brand-500"
				/>
			</label>
			<label class="text-sm">
				<span class="mb-1 block font-medium text-slate-700">{i18n.t('criteria.source')}</span>
				<select
					bind:value={criteria.source}
					class="w-full rounded-lg border-slate-300 text-sm focus:border-brand-500 focus:ring-brand-500"
				>
					<option value="">{i18n.t('common.all')}</option>
					{#each SOURCES as s (s)}<option value={s}>{i18n.t(`enum.${s}`)}</option>{/each}
				</select>
			</label>
			<label class="text-sm">
				<span class="mb-1 block font-medium text-slate-700">{i18n.t('criteria.gender')}</span>
				<select
					bind:value={criteria.gender}
					class="w-full rounded-lg border-slate-300 text-sm focus:border-brand-500 focus:ring-brand-500"
				>
					<option value="">{i18n.t('common.all')}</option>
					{#each GENDERS as g (g)}<option value={g}>{i18n.t(`enum.${g}`)}</option>{/each}
				</select>
			</label>
		</div>
		<div class="mt-4 flex items-center gap-3">
			<button
				onclick={saveCriteria}
				disabled={savingCriteria}
				class="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-60"
			>
				{#if savingCriteria}<Spinner size={14} />{/if}{i18n.t('common.save')}
			</button>
			<button
				onclick={refresh}
				disabled={refreshing}
				class="flex items-center gap-2 rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-600 transition hover:bg-slate-50 disabled:opacity-60"
			>
				{#if refreshing}<Spinner size={14} />{:else}<Icon name="refresh" size={15} />{/if}{i18n.t(
					'segments.refresh'
				)}
			</button>
			{#if segment.last_refreshed_at}
				<span class="text-xs text-slate-400"
					>{i18n.t('segments.lastRefreshed')}: {dateTime(segment.last_refreshed_at)}</span
				>
			{/if}
		</div>
	{:else}
		<!-- manual -->
		<div class="mt-4 flex items-end gap-2">
			<label class="flex-1 text-sm">
				<span class="mb-1 block font-medium text-slate-700">{i18n.t('segments.addMember')}</span>
				<select
					bind:value={addingCustomer}
					class="w-full rounded-lg border-slate-300 text-sm focus:border-brand-500 focus:ring-brand-500"
				>
					<option value="">{i18n.t('common.none')}</option>
					{#each candidates as c (c.id)}<option value={c.id}>{customerName(c)}</option>{/each}
				</select>
			</label>
			<button
				onclick={addMember}
				disabled={!addingCustomer || busyMember}
				class="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-60"
			>
				{#if busyMember}<Spinner size={14} />{:else}<Icon name="plus" size={15} />{/if}{i18n.t(
					'common.add'
				)}
			</button>
		</div>
		<div class="mt-4">
			<p class="mb-2 text-sm font-medium text-slate-700">{i18n.t('segments.members.title')}</p>
			{#if loadingMembers}
				<div class="flex items-center gap-2 py-4 text-slate-400"><Spinner size={16} /></div>
			{:else if memberships.length}
				<ul class="divide-y divide-slate-100 overflow-hidden rounded-lg border border-slate-200">
					{#each memberships as m (m.id)}
						<li class="flex items-center justify-between gap-3 px-3 py-2 text-sm">
							<span class="text-slate-700">{customerName(customersById.get(m.customer))}</span>
							<button
								onclick={() => removeMember(m.id)}
								class="rounded p-1 text-slate-400 transition hover:bg-rose-50 hover:text-rose-600"
								aria-label={i18n.t('common.remove')}
							>
								<Icon name="x" size={15} />
							</button>
						</li>
					{/each}
				</ul>
			{:else}
				<p class="py-3 text-sm text-slate-400">{i18n.t('common.empty')}</p>
			{/if}
		</div>
	{/if}
</div>
