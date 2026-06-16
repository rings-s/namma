<script>
	import { i18n } from '$lib/i18n/i18n.svelte.js';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { toasts } from '$lib/stores/toast.svelte.js';
	import { events } from '$lib/api/operations.js';
	import { branches } from '$lib/api/organizations.js';
	import { errMessage, isAbortError } from '$lib/api/client.js';
	import { scopeToOrg } from '$lib/utils/scope.js';
	import { enumLabel } from '$lib/utils/status.js';
	import { money, number, dateTime } from '$lib/utils/format.js';
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
	let rows = $state([]);
	/** @type {any[]} */
	let branchRows = $state([]);
	let loading = $state(true);
	let error = $state('');
	let show = $state(false);
	let saving = $state(false);

	let name = $state('');
	let eventType = $state('class');
	let branch = $state('');
	let starts = $state('');
	let ends = $state('');
	let capacity = $state('0');
	let price = $state('0');

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
			const [e, b] = await Promise.all([
				events.list(undefined, { signal }),
				branches.list(undefined, { signal })
			]);
			rows = scopeToOrg(e, orgId);
			branchRows = scopeToOrg(b, orgId).filter((/** @type {any} */ r) => r.is_active !== false);
			branch = branchRows[0]?.id ?? '';
		} catch (err) {
			if (isAbortError(err)) return;
			error = errMessage(err) || i18n.t('common.error');
		} finally {
			if (!signal?.aborted) loading = false;
		}
	}

	async function submit() {
		saving = true;
		try {
			const row = await events.create({
				organization: auth.currentOrgId,
				branch,
				name,
				event_type: eventType,
				start_datetime: new Date(starts).toISOString(),
				end_datetime: new Date(ends).toISOString(),
				capacity: Number(capacity) || 0,
				price: Number(price) || 0
			});
			rows = [row, ...rows];
			toasts.success(i18n.t('evt.created'));
			show = false;
			name = '';
			starts = '';
			ends = '';
		} catch (err) {
			toasts.error(errMessage(err) || i18n.t('common.error'));
		} finally {
			saving = false;
		}
	}
</script>

<div class="space-y-4">
	<div class="flex justify-end">
		<button
			onclick={() => (show = true)}
			class="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700"
		>
			<Icon name="plus" size={16} />{i18n.t('evt.new')}
		</button>
	</div>

	<DataState
		{loading}
		{error}
		empty={!rows.length}
		emptyText={i18n.t('evt.empty')}
		onRetry={() => auth.currentOrgId && load(auth.currentOrgId)}
	>
		<div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
			{#each rows as e (e.id)}
				<div
					class="flex flex-col rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:shadow-md"
				>
					<div class="mb-3 flex items-start justify-between gap-2">
						<span
							class="flex size-10 items-center justify-center rounded-xl bg-brand-50 text-brand-600"
							><Icon name="calendar" size={18} /></span
						>
						<Badge label={enumLabel('eventType', e.event_type)} variant="violet" />
					</div>
					<h3 class="truncate text-sm font-semibold text-slate-800">{e.name}</h3>
					<p class="mt-0.5 text-xs text-slate-400">{dateTime(e.start_datetime)}</p>
					<div
						class="mt-3 flex items-center justify-between border-t border-slate-100 pt-3 text-xs"
					>
						<span class="text-slate-500">
							{i18n.t('evt.booked')}: {number(e.booked_count)} / {Number(e.capacity) > 0
								? number(e.capacity)
								: i18n.t('evt.unlimited')}
						</span>
						<span class="font-medium text-slate-800">{money(e.price, currency)}</span>
					</div>
				</div>
			{/each}
		</div>
	</DataState>
</div>

{#if show}
	<Modal title={i18n.t('evt.new')} onClose={() => (show = false)}>
		<div class="space-y-4">
			<Field label={i18n.t('evt.name')}>
				<input bind:value={name} maxlength="255" class={INPUT} />
			</Field>
			<div class="grid grid-cols-2 gap-4">
				<Field label={i18n.t('common.type')}>
					<select bind:value={eventType} class={INPUT}>
						{#each ['class', 'workshop', 'session', 'special', 'other'] as t (t)}<option value={t}
								>{i18n.t(`enum.${t}`)}</option
							>{/each}
					</select>
				</Field>
				<Field label={i18n.t('common.branch')}>
					<select bind:value={branch} class={INPUT}>
						{#each branchRows as b (b.id)}<option value={b.id}>{b.name}</option>{/each}
					</select>
				</Field>
			</div>
			<div class="grid grid-cols-2 gap-4">
				<Field label={i18n.t('evt.starts')}>
					<input type="datetime-local" bind:value={starts} class={INPUT} dir="ltr" />
				</Field>
				<Field label={i18n.t('evt.ends')}>
					<input type="datetime-local" bind:value={ends} class={INPUT} dir="ltr" />
				</Field>
			</div>
			<div class="grid grid-cols-2 gap-4">
				<Field label={i18n.t('evt.capacity')} hint={i18n.t('evt.unlimited')}>
					<input type="number" min="0" step="1" bind:value={capacity} class={INPUT} dir="ltr" />
				</Field>
				<Field label={i18n.t('common.price')}>
					<input type="number" min="0" step="0.01" bind:value={price} class={INPUT} dir="ltr" />
				</Field>
			</div>
		</div>
		{#snippet footer()}
			<button
				onclick={() => (show = false)}
				class="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-50"
				>{i18n.t('common.cancel')}</button
			>
			<button
				onclick={submit}
				disabled={saving || !name || !starts || !ends}
				class="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-60"
			>
				{#if saving}<Spinner size={16} />{/if}{i18n.t('common.create')}
			</button>
		{/snippet}
	</Modal>
{/if}
