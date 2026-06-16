<script>
	import { goto } from '$app/navigation';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { i18n } from '$lib/i18n/i18n.svelte.js';
	import Spinner from '$lib/components/ui/Spinner.svelte';

	// Once the session has hydrated, route to the app or the login screen.
	$effect(() => {
		if (auth.loading) return;
		goto(auth.isAuthenticated ? '/dashboard' : '/login', { replaceState: true });
	});
</script>

<div class="flex min-h-screen items-center justify-center text-slate-400">
	<Spinner size={28} />
	<span class="ms-3 text-sm">{i18n.t('common.loading')}</span>
</div>
