<script>
	import { i18n } from '$lib/i18n/i18n.svelte.js';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { toasts } from '$lib/stores/toast.svelte.js';
	import { employees } from '$lib/api/operations.js';
	import { branches } from '$lib/api/organizations.js';
	import { ApiError, errMessage, isAbortError } from '$lib/api/client.js';
	import { scopeToOrg } from '$lib/utils/scope.js';
	import Modal from '$lib/components/ui/Modal.svelte';
	import Field from '$lib/components/ui/Field.svelte';
	import Spinner from '$lib/components/ui/Spinner.svelte';

	/**
	 * Add an employee record. `user` is optional on the model (linked later), so
	 * the roster can hold profiles for staff without login accounts.
	 * @type {{ onClose: () => void; onCreated: (employee: any) => void }}
	 */
	let { onClose, onCreated } = $props();

	const INPUT =
		'w-full rounded-lg border-slate-300 text-sm focus:border-brand-500 focus:ring-brand-500';

	/** @type {any[]} */
	let branchRows = $state([]);
	let jobTitle = $state('');
	let department = $state('');
	let code = $state('');
	let branch = $state('');
	let salary = $state('');
	let hourly = $state('');
	let isSaudi = $state(false);
	let saving = $state(false);
	/** @type {Record<string, string>} */
	let fieldErrors = $state({});

	$effect(() => {
		const orgId = auth.currentOrgId;
		if (!orgId) return;
		const ctrl = new AbortController();
		branches
			.list(undefined, { signal: ctrl.signal })
			.then((b) => (branchRows = scopeToOrg(b, orgId)))
			.catch((err) => {
				if (!isAbortError(err)) toasts.error(errMessage(err) || i18n.t('common.error'));
			});
		return () => ctrl.abort();
	});

	/** @param {SubmitEvent} event */
	async function submit(event) {
		event.preventDefault();
		saving = true;
		fieldErrors = {};
		try {
			const created = await employees.create({
				organization: auth.currentOrgId,
				branch: branch || null,
				job_title: jobTitle,
				department,
				employee_code: code,
				monthly_salary: Number(salary) || 0,
				hourly_rate: hourly ? Number(hourly) : null,
				is_saudi: isSaudi
			});
			toasts.success(i18n.t('staff.created'));
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

<Modal title={i18n.t('staff.new')} {onClose}>
	<form id="emp-form" onsubmit={submit} class="space-y-4">
		<div class="grid grid-cols-2 gap-4">
			<Field label={i18n.t('staff.role')} error={fieldErrors.job_title}>
				<input bind:value={jobTitle} maxlength="150" class={INPUT} />
			</Field>
			<Field label={i18n.t('staff.department')} optional>
				<input bind:value={department} maxlength="150" class={INPUT} />
			</Field>
		</div>
		<div class="grid grid-cols-2 gap-4">
			<Field label={i18n.t('staff.code')} optional>
				<input bind:value={code} maxlength="50" class={INPUT} dir="ltr" />
			</Field>
			<Field label={i18n.t('common.branch')} optional>
				<select bind:value={branch} class={INPUT}>
					<option value="">{i18n.t('common.none.option')}</option>
					{#each branchRows as b (b.id)}<option value={b.id}>{b.name}</option>{/each}
				</select>
			</Field>
		</div>
		<div class="grid grid-cols-2 gap-4">
			<Field label={i18n.t('staff.salary')} optional>
				<input type="number" min="0" step="0.01" bind:value={salary} class={INPUT} dir="ltr" />
			</Field>
			<Field label={i18n.t('staff.hourly')} optional>
				<input type="number" min="0" step="0.01" bind:value={hourly} class={INPUT} dir="ltr" />
			</Field>
		</div>
		<label class="flex items-center gap-2 text-sm text-slate-700">
			<input
				type="checkbox"
				bind:checked={isSaudi}
				class="rounded border-slate-300 text-brand-600 focus:ring-brand-500"
			/>
			{i18n.t('staff.saudi')}
		</label>
	</form>
	{#snippet footer()}
		<button
			onclick={onClose}
			class="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-50"
			>{i18n.t('common.cancel')}</button
		>
		<button
			type="submit"
			form="emp-form"
			disabled={saving || !jobTitle}
			class="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-60"
		>
			{#if saving}<Spinner size={16} />{/if}{i18n.t('common.create')}
		</button>
	{/snippet}
</Modal>
