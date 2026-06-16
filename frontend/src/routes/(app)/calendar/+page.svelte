<script>
	import { i18n } from '$lib/i18n/i18n.svelte.js';
	import PageHeader from '$lib/components/ui/PageHeader.svelte';
	import Tabs from '$lib/components/ui/Tabs.svelte';
	import AppointmentsTab from '$lib/components/calendar/AppointmentsTab.svelte';
	import EventsTab from '$lib/components/calendar/EventsTab.svelte';
	import QueueTab from '$lib/components/calendar/QueueTab.svelte';

	let active = $state('appointments');

	const tabs = $derived([
		{ key: 'appointments', label: i18n.t('cal.tab.appointments') },
		{ key: 'events', label: i18n.t('cal.tab.events') },
		{ key: 'queue', label: i18n.t('cal.tab.queue') }
	]);
</script>

<div class="mx-auto max-w-6xl">
	<PageHeader title={i18n.t('cal.title')} subtitle={i18n.t('cal.subtitle')} />

	<div class="mb-6">
		<Tabs {tabs} {active} onSelect={(k) => (active = k)} />
	</div>

	{#if active === 'appointments'}
		<AppointmentsTab />
	{:else if active === 'events'}
		<EventsTab />
	{:else}
		<QueueTab />
	{/if}
</div>
