<script>
	import { i18n } from '$lib/i18n/i18n.svelte.js';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { toasts } from '$lib/stores/toast.svelte.js';
	import {
		conversations,
		conversationMessages,
		messageDispatches,
		assignConversation,
		resolveConversation,
		closeConversation
	} from '$lib/api/communications.js';
	import { customers } from '$lib/api/customers.js';
	import { userRoles } from '$lib/api/auth.js';
	import { errMessage, isAbortError } from '$lib/api/client.js';
	import { scopeToOrg, indexById, customerName } from '$lib/utils/scope.js';
	import { enumLabel, statusVariant } from '$lib/utils/status.js';
	import { dateTime, money } from '$lib/utils/format.js';
	import PageHeader from '$lib/components/ui/PageHeader.svelte';
	import DataState from '$lib/components/ui/DataState.svelte';
	import Badge from '$lib/components/ui/Badge.svelte';
	import Icon from '$lib/components/ui/Icon.svelte';
	import Modal from '$lib/components/ui/Modal.svelte';
	import Spinner from '$lib/components/ui/Spinner.svelte';

	const STATUSES = ['open', 'assigned', 'resolved', 'closed'];

	/** @type {any[]} */
	let threads = $state([]);
	/** @type {any[]} */
	let customersList = $state([]);
	/** @type {any[]} */
	let orgRoles = $state([]);
	/** @type {Map<string, any>} */
	let dispatchesById = $state(new Map());
	let loading = $state(true);
	let error = $state('');

	let statusFilter = $state('');
	let mineOnly = $state(false);
	/** @type {string | null} */
	let selectedId = $state(null);

	/** @type {any[]} */
	let messages = $state([]);
	let loadingMessages = $state(false);
	let reply = $state('');
	let sending = $state(false);

	// assign
	let showAssign = $state(false);
	let assignee = $state('');
	let assigning = $state(false);
	let busyStatus = $state(false);

	const customersById = $derived(indexById(customersList));
	const selected = $derived(threads.find((t) => t.id === selectedId) ?? null);
	const currency = $derived(auth.currentOrg?.currency ?? 'SAR');

	// user id → display name, from the embedded user_detail on each role
	// (MISSING_BACKEND #4 — resolved). Lets the inbox show assignee names.
	const staffById = $derived(
		new Map(orgRoles.filter((r) => r.user_detail).map((r) => [r.user, r.user_detail]))
	);
	/** @param {string | null} userId */
	const staffName = (userId) =>
		(userId && staffById.get(userId)?.full_name) || i18n.t('conv.unassigned');

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
			const [convs, custs, roles, dispatches] = await Promise.all([
				conversations.list(undefined, { signal }),
				customers.list(undefined, { signal }),
				userRoles.list(undefined, { signal }),
				messageDispatches.list(undefined, { signal })
			]);
			threads = scopeToOrg(convs, orgId);
			customersList = scopeToOrg(custs, orgId);
			orgRoles = roles.filter((/** @type {any} */ r) => r.organization === orgId);
			dispatchesById = indexById(scopeToOrg(dispatches, orgId));
		} catch (err) {
			if (isAbortError(err)) return;
			error = errMessage(err) || i18n.t('common.error');
		} finally {
			if (!signal?.aborted) loading = false;
		}
	}

	const filtered = $derived(
		threads.filter((t) => {
			if (statusFilter && t.status !== statusFilter) return false;
			if (mineOnly && t.assigned_to !== auth.user?.id) return false;
			return true;
		})
	);

	/** @param {string} convId */
	async function select(convId) {
		selectedId = convId;
		loadingMessages = true;
		messages = [];
		try {
			const all = await conversationMessages.list();
			messages = all.filter((/** @type {any} */ m) => m.conversation === convId);
		} catch (err) {
			toasts.error(errMessage(err) || i18n.t('common.error'));
		} finally {
			loadingMessages = false;
		}
	}

	/** @param {any} updated */
	function patchThread(updated) {
		threads = threads.map((t) => (t.id === updated.id ? { ...t, ...updated } : t));
	}

	async function sendReply() {
		if (!reply.trim() || !selected) return;
		sending = true;
		try {
			const created = await conversationMessages.create({
				conversation: selected.id,
				direction: 'outbound',
				body: reply.trim()
			});
			messages = [...messages, created];
			reply = '';
			toasts.success(i18n.t('conv.sentMsg'));
		} catch (err) {
			toasts.error(errMessage(err) || i18n.t('common.error'));
		} finally {
			sending = false;
		}
	}

	async function doAssign() {
		if (!assignee || !selected) return;
		assigning = true;
		try {
			const updated = await assignConversation(selected.id, { assigned_to: assignee });
			patchThread(updated);
			showAssign = false;
			assignee = '';
			toasts.success(i18n.t('conv.assigned'));
		} catch (err) {
			toasts.error(errMessage(err) || i18n.t('common.error'));
		} finally {
			assigning = false;
		}
	}

	/** @param {'resolve' | 'close'} which */
	async function transition(which) {
		if (!selected) return;
		busyStatus = true;
		try {
			const updated =
				which === 'resolve'
					? await resolveConversation(selected.id)
					: await closeConversation(selected.id);
			patchThread(updated);
			toasts.success(which === 'resolve' ? i18n.t('conv.resolvedMsg') : i18n.t('conv.closedMsg'));
		} catch (err) {
			toasts.error(errMessage(err) || i18n.t('common.error'));
		} finally {
			busyStatus = false;
		}
	}
</script>

<div class="mx-auto max-w-6xl">
	<PageHeader title={i18n.t('conv.title')} subtitle={i18n.t('conv.subtitle')} />

	<DataState {loading} {error} onRetry={() => auth.currentOrgId && load(auth.currentOrgId)}>
		<div class="grid gap-4 lg:grid-cols-[22rem_1fr]">
			<!-- Inbox list -->
			<div class="flex flex-col">
				<div class="mb-3 flex items-center gap-2">
					<select
						bind:value={statusFilter}
						class="flex-1 rounded-lg border-slate-300 text-sm focus:border-brand-500 focus:ring-brand-500"
					>
						<option value="">{i18n.t('common.status')}: {i18n.t('common.all')}</option>
						{#each STATUSES as s (s)}<option value={s}>{i18n.t(`enum.${s}`)}</option>{/each}
					</select>
					<label class="flex items-center gap-1.5 text-xs text-slate-600">
						<input
							type="checkbox"
							bind:checked={mineOnly}
							class="rounded border-slate-300 text-brand-600 focus:ring-brand-500"
						/>
						{i18n.t('common.filter')}
					</label>
				</div>
				{#if filtered.length}
					<ul class="space-y-2">
						{#each filtered as t (t.id)}
							<li>
								<button
									onclick={() => select(t.id)}
									class="w-full rounded-xl border px-4 py-3 text-start transition {selectedId ===
									t.id
										? 'border-brand-300 bg-brand-50'
										: 'border-slate-200 bg-white hover:bg-slate-50'}"
								>
									<div class="flex items-center justify-between gap-2">
										<span class="truncate font-medium text-slate-800"
											>{customerName(customersById.get(t.customer))}</span
										>
										<Badge
											label={enumLabel('conversation_status', t.status)}
											variant={statusVariant(t.status)}
										/>
									</div>
									<div class="mt-1 flex items-center justify-between gap-2 text-xs text-slate-400">
										<span class="flex items-center gap-1"
											><Icon name={t.channel === 'email' ? 'mail' : 'chat'} size={12} />{enumLabel(
												'channel',
												t.channel
											)}</span
										>
										<span>{dateTime(t.last_message_at || t.created_at)}</span>
									</div>
								</button>
							</li>
						{/each}
					</ul>
				{:else}
					<p
						class="rounded-xl border border-dashed border-slate-200 bg-white p-8 text-center text-sm text-slate-400"
					>
						{i18n.t('conv.empty')}
					</p>
				{/if}
			</div>

			<!-- Thread -->
			<div class="rounded-2xl border border-slate-200 bg-white shadow-sm">
				{#if !selected}
					<p class="p-12 text-center text-sm text-slate-400">{i18n.t('conv.selectThread')}</p>
				{:else}
					<div class="flex items-center justify-between gap-3 border-b border-slate-100 p-4">
						<div class="min-w-0">
							<p class="truncate font-semibold text-slate-900">
								{customerName(customersById.get(selected.customer))}
							</p>
							<p class="text-xs text-slate-400">
								{selected.subject || enumLabel('channel', selected.channel)}
								<span class="text-slate-300">·</span>
								{i18n.t('conv.assignedTo')}: {staffName(selected.assigned_to)}
							</p>
						</div>
						<div class="flex shrink-0 items-center gap-2">
							<button
								onclick={() => (showAssign = true)}
								class="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-semibold text-slate-600 transition hover:bg-slate-50"
								>{i18n.t('conv.assign')}</button
							>
							<button
								onclick={() => transition('resolve')}
								disabled={busyStatus || ['resolved', 'closed'].includes(selected.status)}
								class="rounded-lg border border-emerald-200 px-3 py-1.5 text-xs font-semibold text-emerald-700 transition hover:bg-emerald-50 disabled:opacity-40"
								>{i18n.t('conv.resolve')}</button
							>
							<button
								onclick={() => transition('close')}
								disabled={busyStatus || selected.status === 'closed'}
								class="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-semibold text-slate-600 transition hover:bg-slate-50 disabled:opacity-40"
								>{i18n.t('conv.close')}</button
							>
						</div>
					</div>

					<div class="max-h-[28rem] space-y-3 overflow-y-auto p-4">
						{#if loadingMessages}
							<div class="flex items-center gap-2 py-6 text-slate-400"><Spinner size={16} /></div>
						{:else}
							{#each messages as m (m.id)}
								{@const outbound = m.direction === 'outbound'}
								{@const dispatch = m.dispatch ? dispatchesById.get(m.dispatch) : null}
								<div class="flex {outbound ? 'justify-end' : 'justify-start'}">
									<div
										class="max-w-[75%] rounded-2xl px-4 py-2 text-sm {outbound
											? 'bg-brand-600 text-white'
											: 'bg-slate-100 text-slate-800'}"
									>
										<p class="whitespace-pre-wrap">{m.body}</p>
										<div
											class="mt-1 flex items-center gap-2 text-[10px] {outbound
												? 'text-brand-100'
												: 'text-slate-400'}"
										>
											<span>{enumLabel('direction', m.direction)}</span>
											<span>·</span>
											<span>{dateTime(m.created_at)}</span>
										</div>
										{#if dispatch}
											<p
												class="mt-0.5 text-[10px] {outbound ? 'text-brand-100' : 'text-slate-400'}"
											>
												{i18n.t('conv.dispatchInfo', {
													status: enumLabel('dispatch_status', dispatch.status),
													cost: money(dispatch.cost, currency)
												})}
											</p>
										{/if}
									</div>
								</div>
							{/each}
						{/if}
					</div>

					<!-- Reply -->
					<div class="border-t border-slate-100 p-4">
						<p class="mb-2 flex items-start gap-1.5 text-[11px] text-slate-400">
							<Icon name="alert" size={12} class="mt-0.5 shrink-0" />{i18n.t('conv.sendSeparate')}
						</p>
						<div class="flex items-end gap-2">
							<textarea
								bind:value={reply}
								rows="2"
								placeholder={i18n.t('conv.replyPlaceholder')}
								class="flex-1 resize-none rounded-lg border-slate-300 text-sm focus:border-brand-500 focus:ring-brand-500"
							></textarea>
							<button
								onclick={sendReply}
								disabled={sending || !reply.trim()}
								class="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-60"
							>
								{#if sending}<Spinner size={16} />{:else}<Icon name="send" size={16} />{/if}
							</button>
						</div>
					</div>
				{/if}
			</div>
		</div>
	</DataState>
</div>

{#if showAssign}
	<Modal title={i18n.t('conv.assignTo')} onClose={() => (showAssign = false)} size="sm">
		<p class="mb-3 text-xs text-slate-400">{i18n.t('conv.assignNote')}</p>
		<select
			bind:value={assignee}
			class="w-full rounded-lg border-slate-300 text-sm focus:border-brand-500 focus:ring-brand-500"
		>
			<option value="">{i18n.t('common.none')}</option>
			{#each orgRoles as r (r.id)}
				<option value={r.user}>
					{r.user_detail?.full_name ?? String(r.user).slice(0, 8)} · {enumLabel('role', r.role)}
				</option>
			{/each}
		</select>
		{#snippet footer()}
			<button
				onclick={() => (showAssign = false)}
				class="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-50"
				>{i18n.t('common.cancel')}</button
			>
			<button
				onclick={doAssign}
				disabled={!assignee || assigning}
				class="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-60"
			>
				{#if assigning}<Spinner size={16} />{/if}{i18n.t('conv.assign')}
			</button>
		{/snippet}
	</Modal>
{/if}
