<script>
	import { i18n } from '$lib/i18n/i18n.svelte.js';
	import Icon from './Icon.svelte';

	let { class: cls = '' } = $props();
</script>

<button
	type="button"
	onclick={() => i18n.toggle()}
	class="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium text-slate-600 transition hover:bg-slate-50 {cls}"
	title={i18n.t('shell.language')}
>
	<Icon name="globe" size={16} />
	<span>{i18n.locale === 'ar' ? 'English' : 'العربية'}</span>
</button>
