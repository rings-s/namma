<script>
	import { i18n } from '$lib/i18n/i18n.svelte.js';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { toasts } from '$lib/stores/toast.svelte.js';
	import { appointments, employees } from '$lib/api/operations.js';
	import { services } from '$lib/api/commerce.js';
	import { branches } from '$lib/api/organizations.js';
	import { customers } from '$lib/api/customers.js';
	import { ApiError, errMessage, isAbortError } from '$lib/api/client.js';
	import { scopeToOrg, customerName } from '$lib/utils/scope.js';
	import Modal from '$lib/components/ui/Modal.svelte';
	import Field from '$lib/components/ui/Field.svelte';
	import Spinner from '$lib/components/ui/Spinner.svelte';

	/**
	 * Book an appointment. Branch, customer and service are required by the
	 * model; employee is optional. The viewset runs the conflict check
	 * server-side, so a clashing slot surfaces as a field/non-field error.
	 * @type {{ onClose: () => void; onCreated: (appt: any) => void }}
	 */
	let { onClose, onCreated } = $props();

	const INPUT =
		'w-full rounded-lg border-slate-300 text-sm focus:border-brand-500 focus:ring-brand-500';

	let loading = $state(true);
	let saving = $state(false);
	/** @type {any[]} */
	let branchRows = $state([]);
	/** @type {any[]} */
	let customerRows = $state([]);
	/** @type {any[]} */
	let employeeRows = $state([]);
	/** @type {any[]} */
	let serviceRows = $state([]);

	let branch = $state('');
	let customer = $state('');
	let employee = $state('');
	let service = $state('');
	let scheduledAt = $state('');
	let duration = $state('30');
	let notes = $state('');
	/** @type {Record<string, string>} */
	let fieldErrors = $state({});

	$effect(() => {
		const orgId = auth.currentOrgId;
		if (!orgId) return;
		const ctrl = new AbortController();
		load(orgId, ctrl.signal);
		return () => ctrl.abort();
	});

	/** @param {string} orgId @param {AbortSignal} [signal] */
	async function load(orgId, signal) {
		loading = true;
		try {
			const [b, c, e, s] = await Promise.all([
				branches.list(undefined, { signal }),
				customers.list(undefined, { signal }),
				employees.list(undefined, { signal }),
				services.list(undefined, { signal })
			]);
			branchRows = scopeToOrg(b, orgId).filter((/** @type {any} */ r) => r.is_active !== false);
			customerRows = scopeToOrg(c, orgId);
			employeeRows = scopeToOrg(e, orgId).filter((/** @type {any} */ r) => r.is_active !== false);
			serviceRows = scopeToOrg(s, orgId).filter((/** @type {any} */ r) => r.is_active !== false);
			branch = branchRows[0]?.id ?? '';
		} catch (err) {
			if (isAbortError(err)) return;
			toasts.error(errMessage(err) || i18n.t('common.error'));
		} finally {
			if (!signal?.aborted) loading = false;
		}
	}

	// When a service is chosen, default the duration from its catalog length.
	$effect(() => {
		const s = serviceRows.find((r) => r.id === service);
		if (s?.duration_minutes) duration = String(s.duration_minutes);
	});

	/** @param {SubmitEvent} event */
	async function submit(event) {
		event.preventDefault();
		saving = true;
		fieldErrors = {};
		try {
			const created = await appointments.create({
				organization: auth.currentOrgId,
				branch,
				customer,
				service,
				employee: employee || null,
				scheduled_at: new Date(scheduledAt).toISOString(),
				duration_minutes: Number(duration) || 30,
				source: 'staff'
			});
			toasts.success(i18n.t('cal.created'));
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

<Modal title={i18n.t('cal.new')} {onClose}>
	{#if loading}
		<div class="flex items-center justify-center py-12 text-slate-400"><Spinner size={24} /></div>
	{:else}
		<form id="appt-form" onsubmit={submit} class="space-y-4">
			{#if fieldErrors.non_field_errors}
				<p class="rounded-lg bg-rose-50 px-3 py-2 text-xs text-rose-700">
					{fieldErrors.non_field_errors}
				</p>
			{/if}
			<div class="grid grid-cols-2 gap-4">
				<Field label={i18n.t('common.branch')} error={fieldErrors.branch}>
					<select bind:value={branch} required class={INPUT}>
						{#each branchRows as b (b.id)}<option value={b.id}>{b.name}</option>{/each}
					</select>
				</Field>
				<Field label={i18n.t('common.customer')} error={fieldErrors.customer}>
					<select bind:value={customer} required class={INPUT}>
						<option value="" disabled>{i18n.t('common.none.option')}</option>
						{#each customerRows as c (c.id)}<option value={c.id}>{customerName(c)}</option>{/each}
					</select>
				</Field>
			</div>
			<div class="grid grid-cols-2 gap-4">
				<Field label={i18n.t('common.service')} error={fieldErrors.service}>
					<select bind:value={service} required class={INPUT}>
						<option value="" disabled>{i18n.t('common.none.option')}</option>
						{#each serviceRows as s (s.id)}<option value={s.id}>{s.name}</option>{/each}
					</select>
				</Field>
				<Field label={i18n.t('common.employee')} optional error={fieldErrors.employee}>
					<select bind:value={employee} class={INPUT}>
						<option value="">{i18n.t('common.none.option')}</option>
						{#each employeeRows as e (e.id)}
							<option value={e.id}>{e.job_title || e.employee_code || e.id.slice(0, 8)}</option>
						{/each}
					</select>
				</Field>
			</div>
			<div class="grid grid-cols-2 gap-4">
				<Field label={i18n.t('cal.when')} error={fieldErrors.scheduled_at}>
					<input type="datetime-local" bind:value={scheduledAt} required class={INPUT} dir="ltr" />
				</Field>
				<Field label={i18n.t('cal.duration')}>
					<input type="number" min="5" step="5" bind:value={duration} class={INPUT} dir="ltr" />
				</Field>
			</div>
			<Field label={i18n.t('common.notes')} optional>
				<textarea bind:value={notes} rows="2" class={INPUT}></textarea>
			</Field>
		</form>
	{/if}
	{#snippet footer()}
		<button
			onclick={onClose}
			class="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-50"
			>{i18n.t('common.cancel')}</button
		>
		<button
			type="submit"
			form="appt-form"
			disabled={saving || loading || !branch || !customer || !service || !scheduledAt}
			class="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-60"
		>
			{#if saving}<Spinner size={16} />{/if}{i18n.t('common.create')}
		</button>
	{/snippet}
</Modal>
