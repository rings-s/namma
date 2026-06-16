<script>
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { i18n } from '$lib/i18n/i18n.svelte.js';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { toasts } from '$lib/stores/toast.svelte.js';
	import { customers, pdplExport, pdplErase } from '$lib/api/customers.js';
	import { errMessage, isAbortError } from '$lib/api/client.js';
	import { enumLabel } from '$lib/utils/status.js';
	import { money, number, dateTime } from '$lib/utils/format.js';
	import PageHeader from '$lib/components/ui/PageHeader.svelte';
	import DataState from '$lib/components/ui/DataState.svelte';
	import Badge from '$lib/components/ui/Badge.svelte';
	import Icon from '$lib/components/ui/Icon.svelte';
	import Spinner from '$lib/components/ui/Spinner.svelte';
	import ConfirmDialog from '$lib/components/ui/ConfirmDialog.svelte';
	import Tabs from '$lib/components/ui/Tabs.svelte';
	import PreferencesTab from '$lib/components/customers/PreferencesTab.svelte';
	import PackagesTab from '$lib/components/customers/PackagesTab.svelte';
	import NotesTab from '$lib/components/customers/NotesTab.svelte';
	import DocumentsTab from '$lib/components/customers/DocumentsTab.svelte';
	import SurveyResponsesTab from '$lib/components/customers/SurveyResponsesTab.svelte';
	import ConsentTab from '$lib/components/customers/ConsentTab.svelte';
	import AiInsightsTab from '$lib/components/customers/AiInsightsTab.svelte';

	const customerId = $derived(page.params.id);

	/** @type {any} */
	let customer = $state(null);
	let loading = $state(true);
	let error = $state('');
	let togglingActive = $state(false);
	let exporting = $state(false);
	let confirmErase = $state(false);
	let erasing = $state(false);
	let activeTab = $state('preferences');

	const isAdmin = $derived(auth.hasRole('admin'));
	const currency = $derived(auth.currentOrg?.currency ?? 'SAR');

	const TABS = $derived([
		{ key: 'preferences', label: i18n.t('c360.tab.preferences') },
		{ key: 'packages', label: i18n.t('c360.tab.packages') },
		{ key: 'notes', label: i18n.t('c360.tab.notes') },
		{ key: 'documents', label: i18n.t('c360.tab.documents') },
		{ key: 'surveys', label: i18n.t('c360.tab.surveys') },
		{ key: 'consent', label: i18n.t('c360.tab.consent') },
		{ key: 'ai', label: i18n.t('c360.tab.ai') }
	]);

	const stats = $derived(
		customer
			? [
					{ key: 'c360.stat.points', value: number(customer.loyalty_points) },
					{ key: 'c360.stat.spent', value: money(customer.total_spent, currency) },
					{ key: 'c360.stat.visits', value: number(customer.visit_count) },
					{ key: 'c360.stat.lastVisit', value: dateTime(customer.last_visit_at) }
				]
			: []
	);

	$effect(() => {
		if (!customerId) return;
		const ctrl = new AbortController();
		load(customerId, ctrl.signal);
		return () => ctrl.abort();
	});

	/** @param {string} id @param {AbortSignal} [signal] */
	async function load(id, signal) {
		loading = true;
		error = '';
		try {
			customer = await customers.get(id, undefined, { signal });
		} catch (err) {
			if (isAbortError(err)) return;
			error = errMessage(err) || i18n.t('common.error');
		} finally {
			if (!signal?.aborted) loading = false;
		}
	}

	async function toggleActive() {
		togglingActive = true;
		try {
			customer = await customers.patch(customer.id, { is_active: !customer.is_active });
		} catch (err) {
			toasts.error(errMessage(err) || i18n.t('common.error'));
		} finally {
			togglingActive = false;
		}
	}

	async function exportData() {
		exporting = true;
		try {
			const data = await pdplExport(customer.id);
			const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
			const url = URL.createObjectURL(blob);
			const a = document.createElement('a');
			a.href = url;
			a.download = `customer-${customer.id}.json`;
			a.click();
			URL.revokeObjectURL(url);
			toasts.success(i18n.t('pdpl.exported'));
		} catch (err) {
			toasts.error(errMessage(err) || i18n.t('common.error'));
		} finally {
			exporting = false;
		}
	}

	async function erase() {
		erasing = true;
		try {
			await pdplErase(customer.id);
			toasts.success(i18n.t('pdpl.erased'));
			goto('/customers');
		} catch (err) {
			toasts.error(errMessage(err) || i18n.t('common.error'));
			erasing = false;
			confirmErase = false;
		}
	}

	const fullName = $derived(customer ? `${customer.first_name} ${customer.last_name}`.trim() : '');
</script>

<div class="mx-auto max-w-5xl">
	<DataState {loading} {error} onRetry={() => customerId && load(customerId)}>
		{#if customer}
			<PageHeader title={fullName || '—'} backHref="/customers">
				{#snippet actions()}
					{#if isAdmin}
						<button
							onclick={exportData}
							disabled={exporting}
							class="flex items-center gap-2 rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-50 disabled:opacity-60"
						>
							{#if exporting}<Spinner size={14} />{:else}<Icon name="download" size={16} />{/if}
							{i18n.t('pdpl.export')}
						</button>
						<button
							onclick={() => (confirmErase = true)}
							class="flex items-center gap-2 rounded-lg border border-rose-200 px-3 py-2 text-sm font-semibold text-rose-600 transition hover:bg-rose-50"
						>
							<Icon name="trash" size={16} />{i18n.t('pdpl.erase')}
						</button>
					{/if}
				{/snippet}
			</PageHeader>

			<!-- Identity -->
			<div class="mb-6 flex flex-wrap items-center gap-x-5 gap-y-2 text-sm text-slate-600">
				{#if customer.phone}<span class="flex items-center gap-1.5" dir="ltr"
						><Icon name="phone" size={15} class="text-slate-400" />{customer.phone}</span
					>{/if}
				{#if customer.email}<span class="flex items-center gap-1.5" dir="ltr"
						><Icon name="mail" size={15} class="text-slate-400" />{customer.email}</span
					>{/if}
				<Badge label={enumLabel('source', customer.source)} />
				<button
					onclick={toggleActive}
					disabled={togglingActive}
					class="flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium transition disabled:opacity-60 {customer.is_active
						? 'bg-emerald-100 text-emerald-700 hover:bg-emerald-200'
						: 'bg-slate-100 text-slate-500 hover:bg-slate-200'}"
				>
					{#if togglingActive}<Spinner size={12} />{/if}
					{customer.is_active ? i18n.t('enum.active') : i18n.t('enum.inactive')}
				</button>
			</div>

			<!-- System-maintained stats (read-only) -->
			<section class="mb-6">
				<div class="grid grid-cols-2 gap-4 sm:grid-cols-4">
					{#each stats as stat (stat.key)}
						<div class="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
							<p class="text-xs font-medium text-slate-400">{i18n.t(stat.key)}</p>
							<p class="mt-1 text-lg font-semibold text-slate-900">{stat.value}</p>
						</div>
					{/each}
				</div>
				<p class="mt-2 text-xs text-slate-400">{i18n.t('c360.statsReadonly')}</p>
			</section>

			<!-- Tabs -->
			<Tabs tabs={TABS} active={activeTab} onSelect={(k) => (activeTab = k)} />
			<div class="pt-6">
				{#if activeTab === 'preferences'}
					<PreferencesTab {customer} />
				{:else if activeTab === 'packages'}
					<PackagesTab {customer} />
				{:else if activeTab === 'notes'}
					<NotesTab {customer} />
				{:else if activeTab === 'documents'}
					<DocumentsTab {customer} />
				{:else if activeTab === 'surveys'}
					<SurveyResponsesTab {customer} />
				{:else if activeTab === 'consent'}
					<ConsentTab {customer} />
				{:else if activeTab === 'ai'}
					<AiInsightsTab {customer} />
				{/if}
			</div>
		{/if}
	</DataState>
</div>

{#if confirmErase}
	<ConfirmDialog
		title={i18n.t('pdpl.eraseTitle')}
		message={i18n.t('pdpl.eraseMsg')}
		confirmLabel={i18n.t('pdpl.erase')}
		busy={erasing}
		onConfirm={erase}
		onCancel={() => (confirmErase = false)}
	/>
{/if}
