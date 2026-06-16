<script>
	import { i18n } from '$lib/i18n/i18n.svelte.js';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { toasts } from '$lib/stores/toast.svelte.js';
	import { aiRecommendations, aiConversations, aiMessages } from '$lib/api/ai.js';
	import { errMessage, isAbortError } from '$lib/api/client.js';
	import { scopeToOrg } from '$lib/utils/scope.js';
	import PageHeader from '$lib/components/ui/PageHeader.svelte';
	import Tabs from '$lib/components/ui/Tabs.svelte';
	import DataState from '$lib/components/ui/DataState.svelte';
	import Icon from '$lib/components/ui/Icon.svelte';
	import Spinner from '$lib/components/ui/Spinner.svelte';
	import RecommendationCard from '$lib/components/ai/RecommendationCard.svelte';

	let active = $state('recommendations');
	let loading = $state(true);
	let error = $state('');
	/** @type {any[]} */
	let recs = $state([]);
	/** @type {any[]} */
	let conversations = $state([]);
	/** @type {any[]} */
	let messages = $state([]);
	/** @type {string | null} */
	let activeConv = $state(null);
	let draft = $state('');
	let sending = $state(false);

	const tabs = $derived([
		{ key: 'recommendations', label: i18n.t('ai.tab.recommendations') },
		{ key: 'chat', label: i18n.t('ai.tab.chat') }
	]);

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
			const [r, c] = await Promise.all([
				aiRecommendations.list(undefined, { signal }),
				aiConversations.list(undefined, { signal })
			]);
			recs = scopeToOrg(r, orgId);
			conversations = scopeToOrg(c, orgId);
			if (!activeConv && conversations.length) selectConv(conversations[0].id);
		} catch (err) {
			if (isAbortError(err)) return;
			error = errMessage(err) || i18n.t('common.error');
		} finally {
			if (!signal?.aborted) loading = false;
		}
	}

	/** @param {string} id */
	async function selectConv(id) {
		activeConv = id;
		try {
			const all = await aiMessages.list();
			messages = all
				.filter((/** @type {any} */ m) => m.conversation === id)
				.sort((/** @type {any} */ a, /** @type {any} */ b) =>
					a.created_at < b.created_at ? -1 : 1
				);
		} catch (err) {
			toasts.error(errMessage(err) || i18n.t('common.error'));
		}
	}

	async function newChat() {
		try {
			const conv = await aiConversations.create({
				organization: auth.currentOrgId,
				user: auth.user?.id,
				title: i18n.t('ai.untitled')
			});
			conversations = [conv, ...conversations];
			activeConv = conv.id;
			messages = [];
		} catch (err) {
			toasts.error(errMessage(err) || i18n.t('common.error'));
		}
	}

	async function send() {
		if (!draft.trim() || !activeConv) return;
		sending = true;
		const body = draft;
		draft = '';
		try {
			const msg = await aiMessages.create({
				conversation: activeConv,
				role: 'user',
				content: body
			});
			messages = [...messages, msg];
			// Re-pull in case the backend appended an assistant reply.
			await selectConv(activeConv);
		} catch (err) {
			draft = body;
			toasts.error(errMessage(err) || i18n.t('common.error'));
		} finally {
			sending = false;
		}
	}

	const activeRecs = $derived(recs.filter((r) => r.status === 'active'));

	/** @param {any} updated */
	function onRecUpdated(updated) {
		recs = recs.map((r) => (r.id === updated.id ? updated : r));
	}
</script>

<div class="mx-auto max-w-5xl">
	<PageHeader title={i18n.t('ai.title')} subtitle={i18n.t('ai.subtitle')}>
		{#snippet actions()}
			<span
				class="flex items-center gap-1.5 rounded-full bg-violet-50 px-3 py-1 text-xs font-medium text-violet-700"
			>
				<Icon name="sparkles" size={14} />Namaa AI
			</span>
		{/snippet}
	</PageHeader>

	<div class="mb-6">
		<Tabs {tabs} {active} onSelect={(k) => (active = k)} />
	</div>

	<DataState {loading} {error} onRetry={() => auth.currentOrgId && load(auth.currentOrgId)}>
		{#if active === 'recommendations'}
			{#if activeRecs.length}
				<div class="grid grid-cols-1 gap-4 md:grid-cols-2">
					{#each activeRecs as rec (rec.id)}
						<RecommendationCard {rec} onUpdated={onRecUpdated} />
					{/each}
				</div>
			{:else}
				<div class="rounded-2xl border border-dashed border-slate-200 bg-white p-12 text-center">
					<span
						class="mx-auto mb-3 flex size-12 items-center justify-center rounded-2xl bg-violet-50 text-violet-500"
						><Icon name="sparkles" size={24} /></span
					>
					<p class="text-sm text-slate-400">{i18n.t('ai.rec.empty')}</p>
				</div>
			{/if}
		{:else}
			<div class="grid h-[32rem] grid-cols-1 gap-4 sm:grid-cols-[16rem_1fr]">
				<!-- Conversation list -->
				<aside
					class="flex flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm"
				>
					<button
						onclick={newChat}
						class="m-3 flex items-center justify-center gap-2 rounded-lg bg-brand-600 px-3 py-2 text-sm font-semibold text-white transition hover:bg-brand-700"
					>
						<Icon name="plus" size={16} />{i18n.t('ai.newChat')}
					</button>
					<div class="flex-1 overflow-y-auto px-2 pb-2">
						{#each conversations as c (c.id)}
							<button
								onclick={() => selectConv(c.id)}
								class="mb-1 w-full truncate rounded-lg px-3 py-2 text-start text-sm transition {activeConv ===
								c.id
									? 'bg-brand-50 font-medium text-brand-700'
									: 'text-slate-600 hover:bg-slate-50'}"
							>
								{c.title || i18n.t('ai.untitled')}
							</button>
						{/each}
					</div>
				</aside>

				<!-- Thread -->
				<section
					class="flex flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm"
				>
					{#if activeConv}
						<div class="flex-1 space-y-3 overflow-y-auto p-4">
							{#if messages.length}
								{#each messages as m (m.id)}
									<div class="flex {m.role === 'user' ? 'justify-end' : 'justify-start'}">
										<div
											class="max-w-[80%] rounded-2xl px-4 py-2 text-sm {m.role === 'user'
												? 'bg-brand-600 text-white'
												: 'bg-slate-100 text-slate-800'}"
										>
											<p class="whitespace-pre-wrap">{m.content}</p>
											{#if m.tokens_used}<p class="mt-1 text-[10px] opacity-60">
													{i18n.t('ai.tokens', { n: m.tokens_used })}
												</p>{/if}
										</div>
									</div>
								{/each}
							{:else}
								<p class="py-12 text-center text-sm text-slate-400">{i18n.t('ai.chat.empty')}</p>
							{/if}
						</div>
						<form
							onsubmit={(e) => {
								e.preventDefault();
								send();
							}}
							class="flex items-center gap-2 border-t border-slate-100 p-3"
						>
							<input
								bind:value={draft}
								placeholder={i18n.t('ai.chat.placeholder')}
								class="flex-1 rounded-lg border-slate-300 text-sm focus:border-brand-500 focus:ring-brand-500"
							/>
							<button
								type="submit"
								disabled={sending || !draft.trim()}
								class="flex size-9 items-center justify-center rounded-lg bg-brand-600 text-white transition hover:bg-brand-700 disabled:opacity-50"
							>
								{#if sending}<Spinner size={16} />{:else}<Icon name="send" size={16} />{/if}
							</button>
						</form>
					{:else}
						<div class="flex flex-1 items-center justify-center text-sm text-slate-400">
							{i18n.t('ai.noChat')}
						</div>
					{/if}
				</section>
			</div>
		{/if}
	</DataState>
</div>
