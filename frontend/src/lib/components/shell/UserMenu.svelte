<script>
	import { auth } from '$lib/stores/auth.svelte.js';
	import { i18n } from '$lib/i18n/i18n.svelte.js';
	import Icon from '$lib/components/ui/Icon.svelte';

	/** @type {HTMLDetailsElement} */
	let details;

	const fullName = $derived(
		[auth.user?.first_name, auth.user?.last_name].filter(Boolean).join(' ') ||
			auth.user?.email ||
			''
	);
	const initials = $derived(
		(fullName || '?')
			.split(' ')
			.map((/** @type {string} */ part) => part[0])
			.slice(0, 2)
			.join('')
			.toUpperCase()
	);

	function close() {
		if (details) details.open = false;
	}
</script>

<details bind:this={details} class="relative">
	<summary
		class="flex cursor-pointer list-none items-center gap-2 rounded-full border border-slate-200 bg-white py-1 ps-1 pe-2 transition hover:bg-slate-50"
	>
		<span
			class="grid h-7 w-7 place-items-center rounded-full bg-brand-600 text-xs font-bold text-white"
		>
			{initials}
		</span>
		<Icon name="chevron" size={16} class="text-slate-400" />
	</summary>

	<div
		class="absolute z-20 mt-2 w-60 rounded-xl border border-slate-200 bg-white p-1 shadow-lg end-0"
	>
		<div class="px-3 py-2">
			<p class="truncate text-sm font-semibold text-slate-900">{fullName}</p>
			<p class="truncate text-xs text-slate-400">{auth.user?.email}</p>
		</div>
		<div class="my-1 h-px bg-slate-100"></div>
		<a
			href="/profile"
			onclick={close}
			class="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-slate-700 hover:bg-slate-50"
		>
			<Icon name="user" size={16} />{i18n.t('nav.profile')}
		</a>
		<a
			href="/security"
			onclick={close}
			class="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-slate-700 hover:bg-slate-50"
		>
			<Icon name="shield" size={16} />{i18n.t('nav.security')}
		</a>
		<div class="my-1 h-px bg-slate-100"></div>
		<button
			type="button"
			onclick={() => {
				close();
				auth.logout();
			}}
			class="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-start text-sm text-rose-600 hover:bg-rose-50"
		>
			<Icon name="logout" size={16} />{i18n.t('auth.signout')}
		</button>
	</div>
</details>
