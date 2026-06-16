<script>
	import './layout.css';
	import { onMount } from 'svelte';
	import favicon from '$lib/assets/favicon.svg';
	import { i18n } from '$lib/i18n/i18n.svelte.js';
	import { auth } from '$lib/stores/auth.svelte.js';
	import Toaster from '$lib/components/ui/Toaster.svelte';

	let { children } = $props();

	// Keep <html lang/dir> in sync with the active locale (RTL flip).
	$effect(() => {
		i18n.locale;
		i18n.syncDocument();
	});

	// Rehydrate the session from a stored token on first load.
	onMount(() => {
		auth.hydrate();
	});
</script>

<svelte:head><link rel="icon" href={favicon} /></svelte:head>

<Toaster />
{@render children()}
