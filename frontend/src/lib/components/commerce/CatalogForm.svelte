<script>
	import { i18n } from '$lib/i18n/i18n.svelte.js';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { toasts } from '$lib/stores/toast.svelte.js';
	import { services, products } from '$lib/api/commerce.js';
	import { ApiError, errMessage } from '$lib/api/client.js';
	import Modal from '$lib/components/ui/Modal.svelte';
	import Field from '$lib/components/ui/Field.svelte';
	import Spinner from '$lib/components/ui/Spinner.svelte';

	/**
	 * Create a catalog Service or Product. Mirrors the model fields: name + price
	 * required; services carry duration_minutes, products carry sku/stock.
	 * @type {{ kind: 'service' | 'product'; onClose: () => void; onCreated: (row: any) => void }}
	 */
	let { kind, onClose, onCreated } = $props();

	const INPUT =
		'w-full rounded-lg border-slate-300 text-sm focus:border-brand-500 focus:ring-brand-500';

	let name = $state('');
	let description = $state('');
	let price = $state('');
	let cost = $state('');
	let durationMinutes = $state('30');
	let sku = $state('');
	let stockQuantity = $state('0');
	let saving = $state(false);
	/** @type {Record<string, string>} */
	let fieldErrors = $state({});

	const title = $derived(
		kind === 'service' ? i18n.t('catalog.newService') : i18n.t('catalog.newProduct')
	);

	/** @param {SubmitEvent} event */
	async function submit(event) {
		event.preventDefault();
		saving = true;
		fieldErrors = {};
		try {
			const base = {
				organization: auth.currentOrgId,
				name,
				description,
				price: Number(price) || 0,
				cost: Number(cost) || 0
			};
			const created =
				kind === 'service'
					? await services.create({
							...base,
							duration_minutes: Number(durationMinutes) || 0
						})
					: await products.create({
							...base,
							sku,
							stock_quantity: Number(stockQuantity) || 0
						});
			toasts.success(
				kind === 'service' ? i18n.t('catalog.serviceCreated') : i18n.t('catalog.productCreated')
			);
			onCreated(created);
		} catch (err) {
			if (err instanceof ApiError && err.data && typeof err.data === 'object') {
				for (const [key, val] of Object.entries(err.data)) {
					fieldErrors[key] = Array.isArray(val) ? val.join(' ') : String(val);
				}
			}
			toasts.error(errMessage(err) || i18n.t('common.error'));
		} finally {
			saving = false;
		}
	}
</script>

<Modal {title} {onClose}>
	<form id="catalog-form" onsubmit={submit} class="space-y-4">
		<Field label={i18n.t('common.name')} error={fieldErrors.name}>
			<input bind:value={name} required maxlength="255" class={INPUT} />
		</Field>
		<Field label={i18n.t('common.description')} optional>
			<textarea bind:value={description} rows="2" class={INPUT}></textarea>
		</Field>
		<div class="grid grid-cols-2 gap-4">
			<Field label={i18n.t('common.price')} error={fieldErrors.price}>
				<input
					type="number"
					min="0"
					step="0.01"
					bind:value={price}
					required
					class={INPUT}
					dir="ltr"
				/>
			</Field>
			<Field label={i18n.t('catalog.cost')} optional>
				<input type="number" min="0" step="0.01" bind:value={cost} class={INPUT} dir="ltr" />
			</Field>
		</div>
		{#if kind === 'service'}
			<Field
				label={i18n.t('catalog.duration')}
				hint={i18n.t('catalog.minutes', { n: durationMinutes || '0' })}
			>
				<input
					type="number"
					min="0"
					step="5"
					bind:value={durationMinutes}
					class={INPUT}
					dir="ltr"
				/>
			</Field>
		{:else}
			<div class="grid grid-cols-2 gap-4">
				<Field label={i18n.t('catalog.sku')} optional error={fieldErrors.sku}>
					<input bind:value={sku} maxlength="100" class={INPUT} dir="ltr" />
				</Field>
				<Field label={i18n.t('catalog.stock')}>
					<input type="number" step="1" bind:value={stockQuantity} class={INPUT} dir="ltr" />
				</Field>
			</div>
		{/if}
	</form>
	{#snippet footer()}
		<button
			onclick={onClose}
			class="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-50"
		>
			{i18n.t('common.cancel')}
		</button>
		<button
			type="submit"
			form="catalog-form"
			disabled={saving || !name || price === ''}
			class="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-60"
		>
			{#if saving}<Spinner size={16} />{/if}
			{i18n.t('common.create')}
		</button>
	{/snippet}
</Modal>
