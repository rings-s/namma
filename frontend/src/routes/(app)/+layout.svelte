<script>
	import { goto } from '$app/navigation';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { i18n } from '$lib/i18n/i18n.svelte.js';
	import Sidebar from '$lib/components/shell/Sidebar.svelte';
	import OrgSwitcher from '$lib/components/shell/OrgSwitcher.svelte';
	import OrgOnboarding from '$lib/components/shell/OrgOnboarding.svelte';
	import UserMenu from '$lib/components/shell/UserMenu.svelte';
	import LanguageToggle from '$lib/components/ui/LanguageToggle.svelte';
	import Icon from '$lib/components/ui/Icon.svelte';
	import Spinner from '$lib/components/ui/Spinner.svelte';

	let { children } = $props();
	let mobileOpen = $state(false);

	// Auth guard: bounce to login once hydration confirms no session.
	$effect(() => {
		if (!auth.loading && !auth.isAuthenticated) goto('/login', { replaceState: true });
	});
</script>

{#if auth.loading || !auth.isAuthenticated}
	<div class="flex min-h-screen items-center justify-center text-slate-400">
		<Spinner size={28} />
		<span class="ms-3 text-sm">{i18n.t('common.loading')}</span>
	</div>
{:else if auth.organizations.length === 0}
	<!-- Authenticated but belongs to no organization (e.g. a fresh signup):
	     every page here is org-scoped, so onboard first instead of mounting
	     pages that would sit on a spinner with no org to load. -->
	<OrgOnboarding />
{:else}
	<div class="flex min-h-screen bg-slate-50">
		<!-- Desktop sidebar (border on the inline-end so it mirrors in RTL). -->
		<aside class="hidden w-64 shrink-0 border-e border-slate-200 lg:block">
			<div class="sticky top-0 h-screen">
				<Sidebar />
			</div>
		</aside>

		<!-- Mobile drawer -->
		{#if mobileOpen}
			<div class="fixed inset-0 z-30 lg:hidden">
				<button
					class="absolute inset-0 bg-slate-900/40"
					aria-label={i18n.t('common.close')}
					onclick={() => (mobileOpen = false)}
				></button>
				<div class="absolute inset-y-0 start-0 w-64 shadow-xl">
					<Sidebar onNavigate={() => (mobileOpen = false)} />
				</div>
			</div>
		{/if}

		<div class="flex min-w-0 flex-1 flex-col">
			<header
				class="sticky top-0 z-10 flex h-16 items-center gap-3 border-b border-slate-200 bg-white/90 px-4 backdrop-blur sm:px-6"
			>
				<button
					class="rounded-lg p-2 text-slate-500 hover:bg-slate-100 lg:hidden"
					onclick={() => (mobileOpen = true)}
					aria-label="menu"
				>
					<Icon name="menu" size={20} />
				</button>

				<OrgSwitcher />
				<div class="ms-auto flex items-center gap-2">
					<LanguageToggle class="hidden sm:inline-flex" />
					<UserMenu />
				</div>
			</header>

			<main class="flex-1 p-4 sm:p-6 lg:p-8">
				{@render children()}
			</main>
		</div>
	</div>
{/if}
