<script>
	import { i18n } from '$lib/i18n/i18n.svelte.js';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { toasts } from '$lib/stores/toast.svelte.js';
	import { campaigns, sendCampaign } from '$lib/api/marketing.js';
	import { errMessage, isAbortError } from '$lib/api/client.js';
	import { scopeToOrg } from '$lib/utils/scope.js';
	import { statusVariant, enumLabel } from '$lib/utils/status.js';
	import { number, dateTime } from '$lib/utils/format.js';
	import PageHeader from '$lib/components/ui/PageHeader.svelte';
	import DataState from '$lib/components/ui/DataState.svelte';
	import StatCard from '$lib/components/ui/StatCard.svelte';
	import Badge from '$lib/components/ui/Badge.svelte';
	import Icon from '$lib/components/ui/Icon.svelte';
	import Modal from '$lib/components/ui/Modal.svelte';
	import Field from '$lib/components/ui/Field.svelte';
	import Spinner from '$lib/components/ui/Spinner.svelte';
	import ConfirmDialog from '$lib/components/ui/ConfirmDialog.svelte';

	const INPUT =
		'w-full rounded-lg border-slate-300 text-sm focus:border-brand-500 focus:ring-brand-500';
	const canMarket = $derived(auth.hasRole('marketer'));

	/** @type {any[]} */
	let rows = $state([]);
	let loading = $state(true);
	let error = $state('');
	let showNew = $state(false);
	let saving = $state(false);
	/** @type {any | null} */
	let sendTarget = $state(null);
	let sendingBusy = $state(false);

	let name = $state('');
	let type = $state('promotional');
	let channel = $state('email');
	let subject = $state('');
	let content = $state('');
	let audience = $state('');
	let scheduledAt = $state('');

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
			rows = scopeToOrg(await campaigns.list(undefined, { signal }), orgId);
		} catch (err) {
			if (isAbortError(err)) return;
			error = errMessage(err) || i18n.t('common.error');
		} finally {
			if (!signal?.aborted) loading = false;
		}
	}

	const sentCount = $derived(rows.filter((c) => c.status === 'sent').length);
	const draftCount = $derived(rows.filter((c) => c.status === 'draft').length);

	async function create() {
		saving = true;
		try {
			const row = await campaigns.create({
				organization: auth.currentOrgId,
				name,
				type,
				channel,
				subject,
				content,
				target_audience: audience,
				scheduled_at: scheduledAt ? new Date(scheduledAt).toISOString() : null
			});
			rows = [row, ...rows];
			toasts.success(i18n.t('camp.created'));
			showNew = false;
			name = subject = content = audience = scheduledAt = '';
		} catch (err) {
			toasts.error(errMessage(err) || i18n.t('common.error'));
		} finally {
			saving = false;
		}
	}

	async function confirmSend() {
		if (!sendTarget) return;
		sendingBusy = true;
		try {
			await sendCampaign(sendTarget.id);
			toasts.success(i18n.t('camp.sent'));
			sendTarget = null;
			if (auth.currentOrgId) load(auth.currentOrgId);
		} catch (err) {
			toasts.error(errMessage(err) || i18n.t('common.error'));
		} finally {
			sendingBusy = false;
		}
	}
</script>

<div class="mx-auto max-w-6xl">
	<PageHeader title={i18n.t('camp.title')} subtitle={i18n.t('camp.subtitle')}>
		{#snippet actions()}
			{#if canMarket}
				<button
					onclick={() => (showNew = true)}
					class="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700"
				>
					<Icon name="plus" size={16} />{i18n.t('camp.new')}
				</button>
			{/if}
		{/snippet}
	</PageHeader>

	<div class="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
		<StatCard
			label={i18n.t('camp.statTotal')}
			value={number(rows.length)}
			icon="megaphone"
			tone="brand"
		/>
		<StatCard label={i18n.t('camp.statSent')} value={number(sentCount)} icon="send" tone="sky" />
		<StatCard
			label={i18n.t('camp.statDraft')}
			value={number(draftCount)}
			icon="edit"
			tone="amber"
		/>
	</div>

	<DataState
		{loading}
		{error}
		empty={!rows.length}
		emptyText={i18n.t('camp.empty')}
		onRetry={() => auth.currentOrgId && load(auth.currentOrgId)}
	>
		<div class="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
			<table class="w-full text-sm">
				<thead class="border-b border-slate-100 text-xs text-slate-400">
					<tr>
						<th class="px-4 py-3 text-start font-medium">{i18n.t('common.name')}</th>
						<th class="px-4 py-3 text-start font-medium">{i18n.t('camp.channel')}</th>
						<th class="px-4 py-3 text-start font-medium">{i18n.t('camp.scheduledAt')}</th>
						<th class="px-4 py-3 text-start font-medium">{i18n.t('common.status')}</th>
						<th class="px-4 py-3 text-end font-medium"></th>
					</tr>
				</thead>
				<tbody class="divide-y divide-slate-50">
					{#each rows as c (c.id)}
						<tr class="transition hover:bg-slate-50">
							<td class="px-4 py-3 font-medium text-slate-800">{c.name}</td>
							<td class="px-4 py-3"><Badge label={enumLabel('channel', c.channel)} /></td>
							<td class="px-4 py-3 text-slate-500"
								>{c.scheduled_at ? dateTime(c.scheduled_at) : '—'}</td
							>
							<td class="px-4 py-3"
								><Badge
									label={enumLabel('campaign', c.status)}
									variant={statusVariant(c.status)}
								/></td
							>
							<td class="px-4 py-3 text-end">
								{#if canMarket && (c.status === 'draft' || c.status === 'scheduled') && (c.channel === 'sms' || c.channel === 'email')}
									<button
										onclick={() => (sendTarget = c)}
										class="inline-flex items-center gap-1.5 rounded-lg bg-brand-600 px-2.5 py-1.5 text-xs font-semibold text-white transition hover:bg-brand-700"
									>
										<Icon name="send" size={14} />{i18n.t('camp.send')}
									</button>
								{/if}
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	</DataState>
</div>

{#if showNew}
	<Modal title={i18n.t('camp.new')} onClose={() => (showNew = false)}>
		<div class="space-y-4">
			<Field label={i18n.t('camp.name')}
				><input bind:value={name} maxlength="255" class={INPUT} /></Field
			>
			<div class="grid grid-cols-2 gap-4">
				<Field label={i18n.t('camp.type')}>
					<select bind:value={type} class={INPUT}>
						{#each ['promotional', 'transactional', 'reminder', 'announcement'] as t (t)}<option
								value={t}>{i18n.t(`enum.${t}`)}</option
							>{/each}
					</select>
				</Field>
				<Field label={i18n.t('camp.channel')} hint={i18n.t('camp.channelNote')}>
					<select bind:value={channel} class={INPUT}>
						{#each ['email', 'sms', 'whatsapp', 'push'] as ch (ch)}<option value={ch}
								>{i18n.t(`enum.${ch}`)}</option
							>{/each}
					</select>
				</Field>
			</div>
			{#if channel === 'email'}
				<Field label={i18n.t('camp.subject')}
					><input bind:value={subject} maxlength="255" class={INPUT} /></Field
				>
			{/if}
			<Field label={i18n.t('camp.content')}
				><textarea bind:value={content} rows="4" class={INPUT}></textarea></Field
			>
			<div class="grid grid-cols-2 gap-4">
				<Field label={i18n.t('camp.audience')} optional
					><input bind:value={audience} maxlength="255" class={INPUT} /></Field
				>
				<Field label={i18n.t('camp.scheduledAt')} optional
					><input type="datetime-local" bind:value={scheduledAt} class={INPUT} dir="ltr" /></Field
				>
			</div>
		</div>
		{#snippet footer()}
			<button
				onclick={() => (showNew = false)}
				class="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-50"
				>{i18n.t('common.cancel')}</button
			>
			<button
				onclick={create}
				disabled={saving || !name || !content}
				class="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-60"
			>
				{#if saving}<Spinner size={16} />{/if}{i18n.t('common.create')}
			</button>
		{/snippet}
	</Modal>
{/if}

{#if sendTarget}
	<ConfirmDialog
		title={i18n.t('camp.sendTitle')}
		message={i18n.t('camp.sendConfirm')}
		confirmLabel={i18n.t('camp.send')}
		danger={false}
		busy={sendingBusy}
		onConfirm={confirmSend}
		onCancel={() => (sendTarget = null)}
	/>
{/if}
