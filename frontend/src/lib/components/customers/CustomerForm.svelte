<script>
	import { i18n } from '$lib/i18n/i18n.svelte.js';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { toasts } from '$lib/stores/toast.svelte.js';
	import { customers } from '$lib/api/customers.js';
	import { ApiError, errMessage } from '$lib/api/client.js';
	import Modal from '$lib/components/ui/Modal.svelte';
	import Spinner from '$lib/components/ui/Spinner.svelte';

	/**
	 * Create a customer. Constraints mirror the model: first_name required
	 * (max 150), last_name optional (max 150), phone max 32, email optional.
	 * @type {{ onClose: () => void; onCreated: (customer: any) => void }}
	 */
	let { onClose, onCreated } = $props();

	const SOURCES = ['walk_in', 'online', 'phone', 'referral', 'social', 'import', 'other'];
	const GENDERS = ['male', 'female', 'other'];

	let firstName = $state('');
	let lastName = $state('');
	let phone = $state('');
	let email = $state('');
	let gender = $state('');
	let source = $state('walk_in');
	let saving = $state(false);
	/** @type {Record<string, string>} */
	let fieldErrors = $state({});

	/** @param {SubmitEvent} event */
	async function submit(event) {
		event.preventDefault();
		saving = true;
		fieldErrors = {};
		try {
			const created = await customers.create({
				organization: auth.currentOrgId,
				first_name: firstName,
				last_name: lastName,
				phone,
				email,
				gender,
				source
			});
			toasts.success(i18n.t('customers.created'));
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

<Modal title={i18n.t('customers.new')} {onClose}>
	<form id="customer-form" onsubmit={submit} class="space-y-4">
		<div class="grid grid-cols-2 gap-4">
			<div>
				<label for="cf-first" class="mb-1 block text-sm font-medium text-slate-700">
					{i18n.t('customers.form.firstName')}
				</label>
				<input
					id="cf-first"
					bind:value={firstName}
					required
					maxlength="150"
					class="w-full rounded-lg border-slate-300 text-sm focus:border-brand-500 focus:ring-brand-500"
				/>
				{#if fieldErrors.first_name}<p class="mt-1 text-xs text-rose-600">
						{fieldErrors.first_name}
					</p>{/if}
			</div>
			<div>
				<label for="cf-last" class="mb-1 block text-sm font-medium text-slate-700">
					{i18n.t('customers.form.lastName')}
					<span class="text-slate-400">({i18n.t('common.optional')})</span>
				</label>
				<input
					id="cf-last"
					bind:value={lastName}
					maxlength="150"
					class="w-full rounded-lg border-slate-300 text-sm focus:border-brand-500 focus:ring-brand-500"
				/>
			</div>
		</div>
		<div class="grid grid-cols-2 gap-4">
			<div>
				<label for="cf-phone" class="mb-1 block text-sm font-medium text-slate-700">
					{i18n.t('customers.form.phone')}
				</label>
				<input
					id="cf-phone"
					bind:value={phone}
					maxlength="32"
					dir="ltr"
					class="w-full rounded-lg border-slate-300 text-sm focus:border-brand-500 focus:ring-brand-500"
				/>
				{#if fieldErrors.phone}<p class="mt-1 text-xs text-rose-600">{fieldErrors.phone}</p>{/if}
			</div>
			<div>
				<label for="cf-email" class="mb-1 block text-sm font-medium text-slate-700">
					{i18n.t('customers.form.email')}
				</label>
				<input
					id="cf-email"
					type="email"
					bind:value={email}
					dir="ltr"
					class="w-full rounded-lg border-slate-300 text-sm focus:border-brand-500 focus:ring-brand-500"
				/>
				{#if fieldErrors.email}<p class="mt-1 text-xs text-rose-600">{fieldErrors.email}</p>{/if}
			</div>
		</div>
		<div class="grid grid-cols-2 gap-4">
			<div>
				<label for="cf-gender" class="mb-1 block text-sm font-medium text-slate-700">
					{i18n.t('customers.form.gender')}
				</label>
				<select
					id="cf-gender"
					bind:value={gender}
					class="w-full rounded-lg border-slate-300 text-sm focus:border-brand-500 focus:ring-brand-500"
				>
					<option value="">{i18n.t('common.none')}</option>
					{#each GENDERS as g (g)}<option value={g}>{i18n.t(`enum.${g}`)}</option>{/each}
				</select>
			</div>
			<div>
				<label for="cf-source" class="mb-1 block text-sm font-medium text-slate-700">
					{i18n.t('customers.form.source')}
				</label>
				<select
					id="cf-source"
					bind:value={source}
					class="w-full rounded-lg border-slate-300 text-sm focus:border-brand-500 focus:ring-brand-500"
				>
					{#each SOURCES as s (s)}<option value={s}>{i18n.t(`enum.${s}`)}</option>{/each}
				</select>
			</div>
		</div>
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
			form="customer-form"
			disabled={saving || !firstName}
			class="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-60"
		>
			{#if saving}<Spinner size={16} />{/if}
			{i18n.t('common.create')}
		</button>
	{/snippet}
</Modal>
