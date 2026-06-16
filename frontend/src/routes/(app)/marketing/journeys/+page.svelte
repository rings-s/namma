<script>
	import { i18n } from '$lib/i18n/i18n.svelte.js';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { toasts } from '$lib/stores/toast.svelte.js';
	import { journeys, journeySteps } from '$lib/api/marketing.js';
	import { messageTemplates } from '$lib/api/communications.js';
	import { errMessage, isAbortError } from '$lib/api/client.js';
	import { scopeToOrg } from '$lib/utils/scope.js';
	import { enumLabel } from '$lib/utils/status.js';
	import { number } from '$lib/utils/format.js';
	import PageHeader from '$lib/components/ui/PageHeader.svelte';
	import DataState from '$lib/components/ui/DataState.svelte';
	import StatCard from '$lib/components/ui/StatCard.svelte';
	import Badge from '$lib/components/ui/Badge.svelte';
	import Icon from '$lib/components/ui/Icon.svelte';
	import Modal from '$lib/components/ui/Modal.svelte';
	import Field from '$lib/components/ui/Field.svelte';
	import Spinner from '$lib/components/ui/Spinner.svelte';

	const INPUT =
		'w-full rounded-lg border-slate-300 text-sm focus:border-brand-500 focus:ring-brand-500';
	const canMarket = $derived(auth.hasRole('marketer'));
	const TRIGGERS = ['abandoned_booking', 'win_back', 'birthday', 'milestone', 'custom'];

	/** @type {any[]} */
	let rows = $state([]);
	/** @type {any[]} */
	let steps = $state([]);
	/** @type {any[]} */
	let templates = $state([]);
	let loading = $state(true);
	let error = $state('');
	let saving = $state(false);

	/** @type {'journey' | null} */
	let modal = $state(null);
	/** @type {any | null} */
	let stepTarget = $state(null);

	let jName = $state('');
	let jTrigger = $state('win_back');
	// step form
	let sOrder = $state('1');
	let sDelay = $state('24');
	let sChannel = $state('email');
	let sTemplate = $state('');

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
			const [j, st, t] = await Promise.all([
				journeys.list(undefined, { signal }),
				journeySteps.list(undefined, { signal }),
				messageTemplates.list(undefined, { signal })
			]);
			rows = scopeToOrg(j, orgId);
			steps = st;
			templates = scopeToOrg(t, orgId);
		} catch (err) {
			if (isAbortError(err)) return;
			error = errMessage(err) || i18n.t('common.error');
		} finally {
			if (!signal?.aborted) loading = false;
		}
	}

	/** @param {string} journeyId */
	function stepsFor(journeyId) {
		return steps
			.filter((s) => s.journey === journeyId)
			.sort((a, b) => (a.order ?? 0) - (b.order ?? 0));
	}

	const activeCount = $derived(rows.filter((j) => j.is_active).length);

	async function createJourney() {
		saving = true;
		try {
			const row = await journeys.create({
				organization: auth.currentOrgId,
				name: jName,
				trigger_type: jTrigger,
				is_active: false
			});
			rows = [row, ...rows];
			toasts.success(i18n.t('jrn.created'));
			modal = null;
			jName = '';
		} catch (err) {
			toasts.error(errMessage(err) || i18n.t('common.error'));
		} finally {
			saving = false;
		}
	}

	async function addStep() {
		if (!stepTarget) return;
		saving = true;
		try {
			const row = await journeySteps.create({
				journey: stepTarget.id,
				order: Number(sOrder) || 1,
				delay_hours: Number(sDelay) || 0,
				channel: sChannel,
				template: sTemplate || null
			});
			steps = [...steps, row];
			toasts.success(i18n.t('jrn.stepAdded'));
			stepTarget = null;
			sTemplate = '';
		} catch (err) {
			toasts.error(errMessage(err) || i18n.t('common.error'));
		} finally {
			saving = false;
		}
	}

	/** @param {any} journey */
	function openStep(journey) {
		stepTarget = journey;
		sOrder = String(stepsFor(journey.id).length + 1);
	}
</script>

<div class="mx-auto max-w-5xl">
	<PageHeader title={i18n.t('jrn.title')} subtitle={i18n.t('jrn.subtitle')}>
		{#snippet actions()}
			{#if canMarket}
				<button
					onclick={() => (modal = 'journey')}
					class="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700"
				>
					<Icon name="plus" size={16} />{i18n.t('jrn.new')}
				</button>
			{/if}
		{/snippet}
	</PageHeader>

	<div class="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2">
		<StatCard
			label={i18n.t('jrn.statTotal')}
			value={number(rows.length)}
			icon="send"
			tone="brand"
		/>
		<StatCard label={i18n.t('jrn.active')} value={number(activeCount)} icon="play" tone="sky" />
	</div>

	<DataState
		{loading}
		{error}
		empty={!rows.length}
		emptyText={i18n.t('jrn.empty')}
		onRetry={() => auth.currentOrgId && load(auth.currentOrgId)}
	>
		<div class="space-y-4">
			{#each rows as j (j.id)}
				<section class="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
					<header
						class="flex items-center justify-between gap-3 border-b border-slate-100 px-5 py-3.5"
					>
						<div class="flex items-center gap-2">
							<span
								class="flex size-8 items-center justify-center rounded-lg bg-brand-50 text-brand-600"
								><Icon name="send" size={16} /></span
							>
							<div>
								<p class="text-sm font-semibold text-slate-800">{j.name}</p>
								<p class="text-xs text-slate-400">{enumLabel('trigger', j.trigger_type)}</p>
							</div>
						</div>
						<div class="flex items-center gap-2">
							<Badge
								label={j.is_active ? i18n.t('jrn.active') : i18n.t('jrn.inactive')}
								variant={j.is_active ? 'green' : 'slate'}
							/>
							{#if canMarket}
								<button
									onclick={() => openStep(j)}
									class="flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-xs font-semibold text-brand-700 transition hover:bg-brand-50"
								>
									<Icon name="plus" size={14} />{i18n.t('jrn.addStep')}
								</button>
							{/if}
						</div>
					</header>
					{#if stepsFor(j.id).length}
						<ol class="divide-y divide-slate-50">
							{#each stepsFor(j.id) as s (s.id)}
								<li class="flex items-center gap-3 px-5 py-3">
									<span
										class="flex size-7 items-center justify-center rounded-full bg-slate-100 text-xs font-bold text-slate-500"
										>{number(s.order)}</span
									>
									<span class="flex-1 text-sm text-slate-700"
										><Badge label={enumLabel('channel', s.channel)} /></span
									>
									<span class="text-xs text-slate-400"
										>{i18n.t('jrn.delayHours')}: {number(s.delay_hours)}</span
									>
								</li>
							{/each}
						</ol>
					{:else}
						<p class="px-5 py-6 text-center text-sm text-slate-400">{i18n.t('jrn.noSteps')}</p>
					{/if}
				</section>
			{/each}
		</div>
	</DataState>
</div>

{#if modal === 'journey'}
	<Modal title={i18n.t('jrn.new')} onClose={() => (modal = null)} size="sm">
		<div class="space-y-4">
			<Field label={i18n.t('common.name')}
				><input bind:value={jName} maxlength="255" class={INPUT} /></Field
			>
			<Field label={i18n.t('jrn.trigger')}>
				<select bind:value={jTrigger} class={INPUT}>
					{#each TRIGGERS as t (t)}<option value={t}>{i18n.t(`enum.${t}`)}</option>{/each}
				</select>
			</Field>
		</div>
		{#snippet footer()}
			<button
				onclick={() => (modal = null)}
				class="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-50"
				>{i18n.t('common.cancel')}</button
			>
			<button
				onclick={createJourney}
				disabled={saving || !jName}
				class="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-60"
			>
				{#if saving}<Spinner size={16} />{/if}{i18n.t('common.create')}
			</button>
		{/snippet}
	</Modal>
{/if}

{#if stepTarget}
	<Modal title={i18n.t('jrn.addStep')} onClose={() => (stepTarget = null)} size="sm">
		<div class="space-y-4">
			<div class="grid grid-cols-2 gap-4">
				<Field label={i18n.t('jrn.order')}
					><input
						type="number"
						min="1"
						step="1"
						bind:value={sOrder}
						class={INPUT}
						dir="ltr"
					/></Field
				>
				<Field label={i18n.t('jrn.delayHours')}
					><input
						type="number"
						min="0"
						step="1"
						bind:value={sDelay}
						class={INPUT}
						dir="ltr"
					/></Field
				>
			</div>
			<Field label={i18n.t('camp.channel')}>
				<select bind:value={sChannel} class={INPUT}>
					{#each ['email', 'sms', 'whatsapp', 'push'] as ch (ch)}<option value={ch}
							>{i18n.t(`enum.${ch}`)}</option
						>{/each}
				</select>
			</Field>
			<Field label={i18n.t('jrn.template')} optional>
				<select bind:value={sTemplate} class={INPUT}>
					<option value="">{i18n.t('common.none.option')}</option>
					{#each templates as t (t.id)}<option value={t.id}>{t.name}</option>{/each}
				</select>
			</Field>
		</div>
		{#snippet footer()}
			<button
				onclick={() => (stepTarget = null)}
				class="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-50"
				>{i18n.t('common.cancel')}</button
			>
			<button
				onclick={addStep}
				disabled={saving}
				class="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-60"
			>
				{#if saving}<Spinner size={16} />{/if}{i18n.t('common.add')}
			</button>
		{/snippet}
	</Modal>
{/if}
