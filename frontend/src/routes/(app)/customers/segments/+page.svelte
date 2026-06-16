<script>
	import { i18n } from '$lib/i18n/i18n.svelte.js';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { toasts } from '$lib/stores/toast.svelte.js';
	import { customerSegments, customers } from '$lib/api/customers.js';
	import { errMessage, isAbortError } from '$lib/api/client.js';
	import { scopeToOrg, indexById } from '$lib/utils/scope.js';
	import { enumLabel, statusVariant } from '$lib/utils/status.js';
	import PageHeader from '$lib/components/ui/PageHeader.svelte';
	import DataState from '$lib/components/ui/DataState.svelte';
	import Badge from '$lib/components/ui/Badge.svelte';
	import Icon from '$lib/components/ui/Icon.svelte';
	import Modal from '$lib/components/ui/Modal.svelte';
	import Spinner from '$lib/components/ui/Spinner.svelte';
	import SegmentDetail from '$lib/components/customers/SegmentDetail.svelte';

	/** @type {any[]} */
	let segments = $state([]);
	/** @type {any[]} */
	let customersList = $state([]);
	let loading = $state(true);
	let error = $state('');
	/** @type {string | null} */
	let selectedId = $state(null);

	// create form
	let showForm = $state(false);
	let newName = $state('');
	let newType = $state('manual');
	let newDescription = $state('');
	let creating = $state(false);

	const customersById = $derived(indexById(customersList));
	const selected = $derived(segments.find((s) => s.id === selectedId) ?? null);

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
			const [segs, custs] = await Promise.all([
				customerSegments.list(undefined, { signal }),
				customers.list(undefined, { signal })
			]);
			segments = scopeToOrg(segs, orgId);
			customersList = scopeToOrg(custs, orgId);
			if (!selectedId && segments.length) selectedId = segments[0].id;
		} catch (err) {
			if (isAbortError(err)) return;
			error = errMessage(err) || i18n.t('common.error');
		} finally {
			if (!signal?.aborted) loading = false;
		}
	}

	/** @param {SubmitEvent} event */
	async function create(event) {
		event.preventDefault();
		creating = true;
		try {
			const created = await customerSegments.create({
				organization: auth.currentOrgId,
				name: newName,
				segment_type: newType,
				description: newDescription,
				criteria: {}
			});
			segments = [created, ...segments];
			selectedId = created.id;
			showForm = false;
			newName = '';
			newDescription = '';
			newType = 'manual';
		} catch (err) {
			toasts.error(errMessage(err) || i18n.t('common.error'));
		} finally {
			creating = false;
		}
	}

	/** @param {any} updated */
	function onChanged(updated) {
		segments = segments.map((s) => (s.id === updated.id ? { ...s, ...updated } : s));
	}
</script>

<div class="mx-auto max-w-6xl">
	<PageHeader title={i18n.t('segments.title')} subtitle={i18n.t('segments.subtitle')}>
		{#snippet actions()}
			<button
				onclick={() => (showForm = true)}
				class="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700"
			>
				<Icon name="plus" size={16} />{i18n.t('segments.new')}
			</button>
		{/snippet}
	</PageHeader>

	<DataState
		{loading}
		{error}
		empty={!segments.length}
		emptyText={i18n.t('segments.empty')}
		onRetry={() => auth.currentOrgId && load(auth.currentOrgId)}
	>
		<div class="grid gap-6 lg:grid-cols-[20rem_1fr]">
			<ul class="space-y-2">
				{#each segments as seg (seg.id)}
					<li>
						<button
							onclick={() => (selectedId = seg.id)}
							class="w-full rounded-xl border px-4 py-3 text-start transition {selectedId === seg.id
								? 'border-brand-300 bg-brand-50'
								: 'border-slate-200 bg-white hover:bg-slate-50'}"
						>
							<div class="flex items-center justify-between gap-2">
								<span class="truncate font-medium text-slate-800">{seg.name}</span>
								<Badge
									label={enumLabel('segment_type', seg.segment_type)}
									variant={statusVariant(seg.segment_type)}
								/>
							</div>
							<p class="mt-1 text-xs text-slate-400">
								{i18n.t('segments.members', { count: seg.member_count ?? 0 })}
							</p>
						</button>
					</li>
				{/each}
			</ul>
			<div>
				{#if selected}
					{#key selected.id}
						<SegmentDetail segment={selected} {customersById} {customersList} {onChanged} />
					{/key}
				{/if}
			</div>
		</div>
	</DataState>
</div>

{#if showForm}
	<Modal title={i18n.t('segments.new')} onClose={() => (showForm = false)}>
		<form id="segment-form" onsubmit={create} class="space-y-4">
			<div>
				<label for="sg-name" class="mb-1 block text-sm font-medium text-slate-700"
					>{i18n.t('common.name')}</label
				>
				<input
					id="sg-name"
					bind:value={newName}
					required
					maxlength="255"
					class="w-full rounded-lg border-slate-300 text-sm focus:border-brand-500 focus:ring-brand-500"
				/>
			</div>
			<div>
				<label for="sg-type" class="mb-1 block text-sm font-medium text-slate-700"
					>{i18n.t('common.type')}</label
				>
				<select
					id="sg-type"
					bind:value={newType}
					class="w-full rounded-lg border-slate-300 text-sm focus:border-brand-500 focus:ring-brand-500"
				>
					<option value="manual">{i18n.t('enum.manual')}</option>
					<option value="dynamic">{i18n.t('enum.dynamic')}</option>
				</select>
			</div>
			<div>
				<label for="sg-desc" class="mb-1 block text-sm font-medium text-slate-700">
					{i18n.t('common.description')}
					<span class="text-slate-400">({i18n.t('common.optional')})</span>
				</label>
				<textarea
					id="sg-desc"
					bind:value={newDescription}
					rows="2"
					class="w-full rounded-lg border-slate-300 text-sm focus:border-brand-500 focus:ring-brand-500"
				></textarea>
			</div>
		</form>
		{#snippet footer()}
			<button
				onclick={() => (showForm = false)}
				class="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-50"
				>{i18n.t('common.cancel')}</button
			>
			<button
				type="submit"
				form="segment-form"
				disabled={creating || !newName}
				class="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-60"
			>
				{#if creating}<Spinner size={16} />{/if}{i18n.t('common.create')}
			</button>
		{/snippet}
	</Modal>
{/if}
