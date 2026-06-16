<script>
	import { i18n } from '$lib/i18n/i18n.svelte.js';
	import PageHeader from '$lib/components/ui/PageHeader.svelte';
	import Tabs from '$lib/components/ui/Tabs.svelte';
	import SalesTab from '$lib/components/commerce/SalesTab.svelte';
	import CatalogTab from '$lib/components/commerce/CatalogTab.svelte';
	import StoredValueTab from '$lib/components/commerce/StoredValueTab.svelte';

	let active = $state('sales');

	const tabs = $derived([
		{ key: 'sales', label: i18n.t('commerce.tab.sales') },
		{ key: 'catalog', label: i18n.t('commerce.tab.catalog') },
		{ key: 'storedValue', label: i18n.t('commerce.tab.storedValue') }
	]);
</script>

<div class="mx-auto max-w-6xl">
	<PageHeader title={i18n.t('commerce.title')} subtitle={i18n.t('commerce.subtitle')} />

	<div class="mb-6">
		<Tabs {tabs} {active} onSelect={(k) => (active = k)} />
	</div>

	{#if active === 'sales'}
		<SalesTab />
	{:else if active === 'catalog'}
		<CatalogTab />
	{:else}
		<StoredValueTab />
	{/if}
</div>
