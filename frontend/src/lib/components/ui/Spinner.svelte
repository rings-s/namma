<script>
	let { size = 20, class: cls = '' } = $props();
</script>

<svg
	class="animate-spin {cls}"
	width={size}
	height={size}
	viewBox="0 0 24 24"
	fill="none"
	aria-hidden="true"
>
	<circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" class="opacity-25" />
	<path d="M12 2a10 10 0 0 1 10 10" stroke="currentColor" stroke-width="3" stroke-linecap="round" />
</svg>
