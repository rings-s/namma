<script>
	import { i18n } from '$lib/i18n/i18n.svelte.js';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { toasts } from '$lib/stores/toast.svelte.js';
	import { consentRecords } from '$lib/api/communications.js';
	import { errMessage, isAbortError } from '$lib/api/client.js';
	import { enumLabel } from '$lib/utils/status.js';
	import { dateTime } from '$lib/utils/format.js';
	import DataState from '$lib/components/ui/DataState.svelte';
	import Badge from '$lib/components/ui/Badge.svelte';
	import Icon from '$lib/components/ui/Icon.svelte';
	import Spinner from '$lib/components/ui/Spinner.svelte';

	/** @type {{ customer: any }} */
	let { customer } = $props();

	const CHANNELS = ['sms', 'email', 'whatsapp', 'push', 'in_app'];
	const PURPOSES = ['marketing', 'reminders', 'transactional'];

	/** @type {any[]} */
	let records = $state([]);
	let loading = $state(true);
	let error = $state('');
	let channel = $state('sms');
	let purpose = $state('marketing');
	let busy = $state(false);

	$effect(() => {
		const customerId = customer?.id;
		if (!customerId) return;
		const ctrl = new AbortController();
		load(customerId, ctrl.signal);
		return () => ctrl.abort();
	});

	/** @param {string} customerId @param {AbortSignal} [signal] */
	async function load(customerId, signal) {
		loading = true;
		error = '';
		try {
			const all = await consentRecords.list(undefined, { signal });
			records = all.filter((/** @type {any} */ r) => r.customer === customerId);
		} catch (err) {
			if (isAbortError(err)) return;
			error = errMessage(err) || i18n.t('common.error');
		} finally {
			if (!signal?.aborted) loading = false;
		}
	}

	// Latest record per channel×purpose. The list is ordered -created_at, so the
	// first row seen for a key is the most recent.
	const latest = $derived.by(() => {
		/** @type {Map<string, any>} */
		const map = new Map();
		for (const r of records) {
			const key = `${r.channel}:${r.purpose}`;
			if (!map.has(key)) map.set(key, r);
		}
		return [...map.values()];
	});

	/** @param {boolean} granting */
	async function record(granting) {
		busy = true;
		const now = new Date().toISOString();
		try {
			await consentRecords.create({
				organization: auth.currentOrgId,
				customer: customer.id,
				channel,
				purpose,
				source: 'staff',
				granted_at: granting ? now : null,
				revoked_at: granting ? null : now
			});
			toasts.success(i18n.t('consent.recorded'));
			await load(customer.id);
		} catch (err) {
			toasts.error(errMessage(err) || i18n.t('common.error'));
		} finally {
			busy = false;
		}
	}
</script>

<div class="space-y-5">
	<!-- Grant/revoke writes a new immutable record. -->
	<div class="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
		<p class="mb-3 flex items-start gap-2 text-xs text-slate-400">
			<Icon name="alert" size={14} class="mt-0.5 shrink-0" />{i18n.t('consent.appendOnly')}
		</p>
		<div class="flex flex-wrap items-end gap-3">
			<div>
				<label for="cs-channel" class="mb-1 block text-sm font-medium text-slate-700"
					>{i18n.t('consent.channel')}</label
				>
				<select
					id="cs-channel"
					bind:value={channel}
					class="rounded-lg border-slate-300 text-sm focus:border-brand-500 focus:ring-brand-500"
				>
					{#each CHANNELS as c (c)}<option value={c}>{i18n.t(`enum.${c}`)}</option>{/each}
				</select>
			</div>
			<div>
				<label for="cs-purpose" class="mb-1 block text-sm font-medium text-slate-700"
					>{i18n.t('consent.purpose')}</label
				>
				<select
					id="cs-purpose"
					bind:value={purpose}
					class="rounded-lg border-slate-300 text-sm focus:border-brand-500 focus:ring-brand-500"
				>
					{#each PURPOSES as p (p)}<option value={p}>{i18n.t(`enum.${p}`)}</option>{/each}
				</select>
			</div>
			<button
				onclick={() => record(true)}
				disabled={busy}
				class="flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-emerald-700 disabled:opacity-60"
			>
				{#if busy}<Spinner size={14} />{/if}{i18n.t('consent.grant')}
			</button>
			<button
				onclick={() => record(false)}
				disabled={busy}
				class="rounded-lg border border-rose-200 px-4 py-2 text-sm font-semibold text-rose-600 transition hover:bg-rose-50 disabled:opacity-60"
			>
				{i18n.t('consent.revoke')}
			</button>
		</div>
	</div>

	<DataState
		{loading}
		{error}
		empty={!latest.length}
		emptyText={i18n.t('consent.empty')}
		onRetry={() => load(customer.id)}
	>
		<ul
			class="divide-y divide-slate-100 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm"
		>
			{#each latest as r (`${r.channel}:${r.purpose}`)}
				{@const granted = !!r.granted_at && !r.revoked_at}
				<li class="flex items-center justify-between gap-3 px-4 py-3">
					<div class="flex items-center gap-2 text-sm text-slate-700">
						<Badge label={enumLabel('channel', r.channel)} />
						<span class="text-slate-400">·</span>
						<span>{enumLabel('purpose', r.purpose)}</span>
					</div>
					<div class="flex items-center gap-3">
						<span class="text-xs text-slate-400"
							>{dateTime(granted ? r.granted_at : r.revoked_at)}</span
						>
						<Badge
							label={granted ? i18n.t('consent.granted') : i18n.t('consent.revoked')}
							variant={granted ? 'green' : 'red'}
						/>
					</div>
				</li>
			{/each}
		</ul>
	</DataState>
</div>
